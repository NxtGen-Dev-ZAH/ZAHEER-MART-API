import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db import get_session
from app.models import Orders, OrdersBase, OrdersUpdate
from app import crud, kafka, order_pb2
from unittest.mock import AsyncMock, patch

# Setup in-memory test database
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

# Test API endpoints
def test_main(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Order Management Service"}

def test_get_order_details(client, session):
    order = Orders(order_id="test1", product_id="p1", user_id="u1", quantity=1, shipping_address="addr1", customer_notes="note1")
    session.add(order)
    session.commit()

    response = client.get("/order/test1")
    assert response.status_code == 200
    assert response.json()["order_id"] == "test1"

def test_get_order_details_not_found(client):
    response = client.get("/order/nonexistent")
    assert response.status_code == 404

def test_read_orders(client, session):
    order1 = Orders(order_id="test1", product_id="p1", user_id="u1", quantity=1, shipping_address="addr1", customer_notes="note1")
    order2 = Orders(order_id="test2", product_id="p2", user_id="u2", quantity=2, shipping_address="addr2", customer_notes="note2")
    session.add(order1)
    session.add(order2)
    session.commit()

    response = client.get("/orders")
    assert response.status_code == 200
    assert len(response.json()) == 2

@pytest.mark.asyncio
async def test_create_order(client):
    with patch('app.producer.publish_order_created', new_callable=AsyncMock) as mock_publish, \
         patch('app.kafka.consume_message_from_user_service', new_callable=AsyncMock) as mock_consume:
        mock_consume.return_value = order_pb2.User(user_id="u1", username="testuser", email="test@example.com")
        
        order_data = {
            "order_id": "new1",
            "product_id": "p1",
            "user_id": "u1",
            "quantity": 1,
            "shipping_address": "test address",
            "customer_notes": "test note"
        }
        response = client.post("/products/?product_id=p1", json=order_data)
        assert response.status_code == 200
        assert response.json()["order_id"] == "new1"
        mock_publish.assert_called_once()

@pytest.mark.asyncio
async def test_update_order(client):
    with patch('app.producer.publish_order_update', new_callable=AsyncMock) as mock_publish:
        update_data = {
            "quantity": 2,
            "shipping_address": "new address",
            "customer_notes": "updated note"
        }
        response = client.put("/order/test1", json=update_data)
        assert response.status_code == 200
        assert "Order update request for order ID test1 has been sent." in response.json()["detail"]
        mock_publish.assert_called_once()

@pytest.mark.asyncio
async def test_delete_order(client):
    with patch('app.producer.publish_order_deleted', new_callable=AsyncMock) as mock_publish:
        mock_publish.return_value = {"order_id": "test1", "user_id": "u1"}
        response = client.delete("/order/test1")
        assert response.status_code == 200
        assert "Order not deleted" in response.json()
        mock_publish.assert_called_once_with("test1", "test_user")

# Test CRUD operations
@pytest.mark.asyncio
async def test_create_order_crud(session):
    order_data = OrdersBase(order_id="crud1", product_id="p1", user_id="u1", quantity=1, shipping_address="addr1", customer_notes="note1")
    created_order = await crud.create_order(session, order_data, "u1", "p1")
    assert created_order.order_id == "crud1"
    assert created_order.product_id == "p1"

@pytest.mark.asyncio
async def test_get_order(session):
    order = Orders(order_id="get1", product_id="p1", user_id="u1", quantity=1, shipping_address="addr1", customer_notes="note1")
    session.add(order)
    session.commit()

    retrieved_order = await crud.get_order(session, "get1")
    assert retrieved_order is not None
    assert retrieved_order.order_id == "get1"

@pytest.mark.asyncio
async def test_update_order_crud(session):
    order = Orders(order_id="update1", product_id="p1", user_id="u1", quantity=1, shipping_address="addr1", customer_notes="note1")
    session.add(order)
    session.commit()

    update_data = OrdersUpdate(quantity=2, shipping_address="new addr", customer_notes="updated note")
    updated_order = await crud.update_order(session, "update1", update_data)
    assert updated_order is not None
    assert updated_order.quantity == 2
    assert updated_order.shipping_address == "new addr"

@pytest.mark.asyncio
async def test_delete_order_crud(session):
    order = Orders(order_id="delete1", product_id="p1", user_id="u1", quantity=1, shipping_address="addr1", customer_notes="note1")
    session.add(order)
    session.commit()

    deleted_order = await crud.delete_order(session, "delete1")
    assert deleted_order is not None
    assert deleted_order.order_id == "delete1"

    retrieved_order = await crud.get_order(session, "delete1")
    assert retrieved_order is None

# Test Kafka message handling
@pytest.mark.asyncio
async def test_process_message_create(session):
    from app.consumer.main import process_message
    
    order_proto = order_pb2.Order(
        order_id="kafka1",
        product_id="p1",
        user_id="u1",
        quantity=1,
        shipping_address="kafka addr",
        customer_notes="kafka note",
        option=order_pb2.SelectOption.CREATE
    )

    with patch('app.consumer.main.handle_create_order', new_callable=AsyncMock) as mock_handle_create:
        mock_handle_create.return_value = Orders(order_id="kafka1", product_id="p1", user_id="u1", quantity=1, shipping_address="kafka addr", customer_notes="kafka note")
        await process_message(order_proto)
        mock_handle_create.assert_called_once_with(order_proto)

@pytest.mark.asyncio
async def test_process_message_update(session):
    from app.consumer.main import process_message
    
    order_proto = order_pb2.Order(
        order_id="kafka2",
        quantity=2,
        shipping_address="updated addr",
        customer_notes="updated note",
        option=order_pb2.SelectOption.UPDATE
    )

    with patch('app.consumer.main.handle_update_order', new_callable=AsyncMock) as mock_handle_update:
        mock_handle_update.return_value = Orders(order_id="kafka2", product_id="p1", user_id="u1", quantity=2, shipping_address="updated addr", customer_notes="updated note")
        await process_message(order_proto)
        mock_handle_update.assert_called_once()

@pytest.mark.asyncio
async def test_process_message_delete(session):
    from app.consumer.main import process_message
    
    order_proto = order_pb2.Order(
        order_id="kafka3",
        option=order_pb2.SelectOption.DELETE
    )

    with patch('app.consumer.main.handle_delete_order', new_callable=AsyncMock) as mock_handle_delete:
        await process_message(order_proto)
        mock_handle_delete.assert_called_once_with("kafka3")

@pytest.mark.asyncio
async def test_process_message_payment(session):
    from app.consumer.main import process_message_payment
    
    payment_proto = order_pb2.Payment(
        order_id="payment1",
        user_id="u1",
        payment_status=order_pb2.PaymentStatus.PAID
    )

    with patch('app.consumer.main.handle_order_payment', new_callable=AsyncMock) as mock_handle_payment:
        await process_message_payment(payment_proto)
        mock_handle_payment.assert_called_once()

# pip install pytest pytest-asyncio sqlmodel fastapi httpx
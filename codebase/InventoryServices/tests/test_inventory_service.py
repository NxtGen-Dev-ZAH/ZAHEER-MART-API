import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db import get_session
from app.models import InventoryItem, InventoryItemBase, InventoryItemUpdate
from app import crud, kafka
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
    assert response.json() == {"Hello": "Welcome to Inventory Service ."}

def test_see_inventory_item(client, session):
    item = InventoryItem(inventory_id="test1", product_id="prod1", stock_level=10)
    session.add(item)
    session.commit()

    response = client.get("/inventory/test1")
    assert response.status_code == 200
    assert response.json()["inventory_id"] == "test1"

def test_see_inventory_item_not_found(client):
    response = client.get("/inventory/nonexistent")
    assert response.status_code == 404

def test_get_all_inventory_items(client, session):
    item1 = InventoryItem(inventory_id="test1", product_id="prod1", stock_level=10)
    item2 = InventoryItem(inventory_id="test2", product_id="prod2", stock_level=20)
    session.add(item1)
    session.add(item2)
    session.commit()

    response = client.get("/inventory/")
    assert response.status_code == 200
    assert len(response.json()) == 2

@pytest.mark.asyncio
async def test_create_inventory_item(client):
    with patch('app.producer.publish_inventory_create', new_callable=AsyncMock) as mock_publish:
        item_data = {
            "inventory_id": "new1",
            "product_id": "prod1",
            "stock_level": 15,
            "reserved_stock": 0,
            "sold_stock": 0
        }
        response = client.post("/inventory/create/", json=item_data)
        assert response.status_code == 200
        assert "Inventory creation request sent" in response.json()["message"]
        mock_publish.assert_called_once()

@pytest.mark.asyncio
async def test_update_inventory_item(client):
    with patch('app.producer.publish_inventory_update', new_callable=AsyncMock) as mock_publish:
        update_data = {
            "stock_level": 25,
            "reserved_stock": 5,
            "sold_stock": 10
        }
        response = client.put("/inventory/test1/add", json=update_data)
        assert response.status_code == 200
        mock_publish.assert_called_once()

@pytest.mark.asyncio
async def test_delete_inventory_item(client):
    with patch('app.producer.publish_product_deleted', new_callable=AsyncMock) as mock_publish:
        response = client.delete("/inventory/test1")
        assert response.status_code == 200
        assert "is deleted successfully" in response.json()[0]
        mock_publish.assert_called_once_with("test1")

@pytest.mark.asyncio
async def test_update_stock_level(client):
    with patch('app.producer.publish_inventory_update_stock_level', new_callable=AsyncMock) as mock_publish:
        response = client.put("/inventory/prod1/update_stock?quantity_change=5")
        assert response.status_code == 200
        assert response.json() == {"message": "Stock updated successfully"}
        mock_publish.assert_called_once()

@pytest.mark.asyncio
async def test_reduce_stock_level(client):
    with patch('app.producer.publish_inventory_reduce', new_callable=AsyncMock) as mock_publish:
        response = client.put("/inventory/prod1/reduce?quantity_change=3")
        assert response.status_code == 200
        assert response.json() == {"message": "Stock reduced successfully"}
        mock_publish.assert_called_once()

# Test CRUD operations
@pytest.mark.asyncio
async def test_create_inventory_item_crud(session):
    item_data = InventoryItemBase(inventory_id="crud1", product_id="prod1", stock_level=30)
    created_item = await crud.create_inventory_item(session, item_data)
    assert created_item.inventory_id == "crud1"
    assert created_item.stock_level == 30

@pytest.mark.asyncio
async def test_get_inventory_item(session):
    item = InventoryItem(inventory_id="get1", product_id="prod1", stock_level=40)
    session.add(item)
    session.commit()

    retrieved_item = await crud.get_inventory_item(session, "get1")
    assert retrieved_item is not None
    assert retrieved_item.inventory_id == "get1"

@pytest.mark.asyncio
async def test_update_inventory_item_crud(session):
    item = InventoryItem(inventory_id="update1", product_id="prod1", stock_level=50)
    session.add(item)
    session.commit()

    update_data = InventoryItemUpdate(stock_level=55, reserved_stock=5)
    updated_item = await crud.update_inventory_item(session, "update1", update_data)
    assert updated_item is not None
    assert updated_item.stock_level == 55
    assert updated_item.reserved_stock == 5

@pytest.mark.asyncio
async def test_delete_inventory_item_crud(session):
    item = InventoryItem(inventory_id="delete1", product_id="prod1", stock_level=60)
    session.add(item)
    session.commit()

    deleted_item = await crud.delete_inventory_item(session, "delete1")
    assert deleted_item is not None
    assert deleted_item.inventory_id == "delete1"

    retrieved_item = await crud.get_inventory_item(session, "delete1")
    assert retrieved_item is None

# Test Kafka message handling
@pytest.mark.asyncio
async def test_process_message_create(session):
    from app.consumer.main import process_message
    from app import inventory_pb2

    inventory_proto = inventory_pb2.Inventory(
        inventory_id="kafka1",
        product_id="prod1",
        stock_level=70,
        reserved_stock=0,
        sold_stock=0,
        option=inventory_pb2.SelectOption.CREATE
    )

    await process_message(inventory_proto)
    created_item = await crud.get_inventory_item(session, "kafka1")
    assert created_item is not None
    assert created_item.stock_level == 70

@pytest.mark.asyncio
async def test_process_message_update(session):
    from app.consumer.main import process_message
    from app import inventory_pb2

    item = InventoryItem(inventory_id="kafka2", product_id="prod2", stock_level=80)
    session.add(item)
    session.commit()

    inventory_proto = inventory_pb2.Inventory(
        inventory_id="kafka2",
        stock_level=85,
        reserved_stock=5,
        sold_stock=10,
        option=inventory_pb2.SelectOption.UPDATE
    )

    await process_message(inventory_proto)
    updated_item = await crud.get_inventory_item(session, "kafka2")
    assert updated_item is not None
    assert updated_item.stock_level == 85
    assert updated_item.reserved_stock == 5
    assert updated_item.sold_stock == 10

@pytest.mark.asyncio
async def test_process_message_delete(session):
    from app.consumer.main import process_message
    from app import inventory_pb2

    item = InventoryItem(inventory_id="kafka3", product_id="prod3", stock_level=90)
    session.add(item)
    session.commit()

    inventory_proto = inventory_pb2.Inventory(
        inventory_id="kafka3",
        option=inventory_pb2.SelectOption.DELETE
    )

    await process_message(inventory_proto)
    deleted_item = await crud.get_inventory_item(session, "kafka3")
    assert deleted_item is None

@pytest.mark.asyncio
async def test_process_message_inventory_check(session):
    from app.consumer.main import process_message_inventory_check
    from app import inventory_pb2

    item = InventoryItem(inventory_id="check1", product_id="prod4", stock_level=100, reserved_stock=0)
    session.add(item)
    session.commit()

    order_proto = inventory_pb2.Order(
        product_id="prod4",
        quantity=10,
        option=inventory_pb2.SelectOption.CREATE
    )

    with patch('app.kafka.send_producer_message', new_callable=AsyncMock) as mock_send:
        await process_message_inventory_check(order_proto)
        mock_send.assert_called()

    updated_item = await crud.get_inventory_item_by_product(session, "prod4")
    assert updated_item is not None
    assert updated_item.stock_level == 90
    assert updated_item.reserved_stock == 10

@pytest.mark.asyncio
async def test_process_message_product(session):
    from app.consumer.main import process_message_product
    from app import inventory_pb2

    product_proto = inventory_pb2.Product(
        product_id="new_prod",
        option=inventory_pb2.SelectOption.CREATE
    )

    await process_message_product(product_proto)
    created_item = await crud.get_inventory_item_by_product(session, "new_prod")
    assert created_item is not None
    assert created_item.stock_level == 0

    product_proto.option = inventory_pb2.SelectOption.DELETE
    await process_message_product(product_proto)
    deleted_item = await crud.get_inventory_item_by_product(session, "new_prod")
    assert deleted_item is None
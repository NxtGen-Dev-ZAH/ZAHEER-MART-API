import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db import get_session
from app.models import Product, ProductBase, ProductUpdate
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
    assert response.json() == "welcome to Product services "

def test_get_product_details(client, session):
    product = Product(product_id="test1", name="Test Product", description="Test Description", price=10.0)
    session.add(product)
    session.commit()

    response = client.get("/products/test1/details")
    assert response.status_code == 200
    assert response.json()["product_id"] == "test1"

def test_get_product_details_not_found(client):
    response = client.get("/products/nonexistent/details")
    assert response.status_code == 404

def test_read_products(client, session):
    product1 = Product(product_id="test1", name="Test Product 1", description="Test Description 1", price=10.0)
    product2 = Product(product_id="test2", name="Test Product 2", description="Test Description 2", price=20.0)
    session.add(product1)
    session.add(product2)
    session.commit()

    response = client.get("/products/")
    assert response.status_code == 200
    assert len(response.json()) == 2

@pytest.mark.asyncio
async def test_create_product(client):
    with patch('app.producer.publish_product_created', new_callable=AsyncMock) as mock_publish:
        product_data = {
            "product_id": "new1",
            "name": "New Product",
            "description": "New Description",
            "price": 15.0,
            "is_available": True
        }
        response = client.post("/products/", json=product_data)
        assert response.status_code == 200
        assert response.json() == product_data
        mock_publish.assert_called_once()

@pytest.mark.asyncio
async def test_update_product(client):
    with patch('app.producer.publish_product_updated', new_callable=AsyncMock) as mock_publish:
        update_data = {
            "name": "Updated Product",
            "price": 25.0
        }
        response = client.patch("/products/test1", json=update_data)
        assert response.status_code == 200
        assert "Update request for product ID test1 has been sent." in response.json()["detail"]
        mock_publish.assert_called_once()

@pytest.mark.asyncio
async def test_delete_product(client):
    with patch('app.producer.publish_product_deleted', new_callable=AsyncMock) as mock_publish:
        mock_publish.return_value = {"product_id": "test1", "name": "Test Product"}
        response = client.delete("/products/test1")
        assert response.status_code == 200
        assert "Product with id test1 is deleted" in response.text
        mock_publish.assert_called_once_with("test1")

# Test CRUD operations
@pytest.mark.asyncio
async def test_create_product_crud(session):
    product_data = ProductBase(product_id="crud1", name="CRUD Product", description="CRUD Description", price=30.0)
    created_product = await crud.create_product_crud(session, product_data)
    assert created_product.product_id == "crud1"
    assert created_product.name == "CRUD Product"

@pytest.mark.asyncio
async def test_get_product(session):
    product = Product(product_id="get1", name="Get Product", description="Get Description", price=40.0)
    session.add(product)
    session.commit()

    retrieved_product = await crud.get_product(session, "get1")
    assert retrieved_product is not None
    assert retrieved_product.product_id == "get1"

@pytest.mark.asyncio
async def test_update_product_crud(session):
    product = Product(product_id="update1", name="Update Product", description="Update Description", price=50.0)
    session.add(product)
    session.commit()

    update_data = ProductUpdate(name="Updated Name", price=55.0)
    updated_product = await crud.update_product(session, "update1", update_data)
    assert updated_product is not None
    assert updated_product.name == "Updated Name"
    assert updated_product.price == 55.0

@pytest.mark.asyncio
async def test_delete_product_crud(session):
    product = Product(product_id="delete1", name="Delete Product", description="Delete Description", price=60.0)
    session.add(product)
    session.commit()

    deleted_product = await crud.delete_product(session, "delete1")
    assert deleted_product is not None
    assert deleted_product.product_id == "delete1"

    retrieved_product = await crud.get_product(session, "delete1")
    assert retrieved_product is None

# Test Kafka message handling
@pytest.mark.asyncio
async def test_process_message_create(session):
    from app.consumer.main import process_message
    from app import product_pb2

    product_proto = product_pb2.Product(
        product_id="kafka1",
        name="Kafka Product",
        description="Kafka Description",
        price=70.0,
        is_available=True,
        option=product_pb2.SelectOption.CREATE
    )

    await process_message(product_proto)

    created_product = await crud.get_product(session, "kafka1")
    assert created_product is not None
    assert created_product.name == "Kafka Product"

@pytest.mark.asyncio
async def test_process_message_update(session):
    from app.consumer.main import process_message
    from app import product_pb2

    product = Product(product_id="kafka2", name="Original Kafka Product", description="Original Description", price=80.0)
    session.add(product)
    session.commit()

    product_proto = product_pb2.Product(
        product_id="kafka2",
        name="Updated Kafka Product",
        price=85.0,
        option=product_pb2.SelectOption.UPDATE
    )

    await process_message(product_proto)

    updated_product = await crud.get_product(session, "kafka2")
    assert updated_product is not None
    assert updated_product.name == "Updated Kafka Product"
    assert updated_product.price == 85.0

@pytest.mark.asyncio
async def test_process_message_delete(session):
    from app.consumer.main import process_message
    from app import product_pb2

    product = Product(product_id="kafka3", name="Kafka Product to Delete", description="Delete Description", price=90.0)
    session.add(product)
    session.commit()

    product_proto = product_pb2.Product(
        product_id="kafka3",
        option=product_pb2.SelectOption.DELETE
    )

    await process_message(product_proto)

    deleted_product = await crud.get_product(session, "kafka3")
    assert deleted_product is None

@pytest.mark.asyncio
async def test_process_message_stock(session):
    from app.consumer.main import process_message_stock
    from app import product_pb2

    product = Product(product_id="stock1", name="Stock Product", description="Stock Description", price=100.0, is_available=True)
    session.add(product)
    session.commit()

    inventory_proto = product_pb2.Inventory(
        product_id="stock1",
        stock_level=0
    )

    await process_message_stock(inventory_proto)

    updated_product = await crud.get_product(session, "stock1")
    assert updated_product is not None
    assert updated_product.is_available == False

    inventory_proto.stock_level = 10
    await process_message_stock(inventory_proto)

    updated_product = await crud.get_product(session, "stock1")
    assert updated_product is not None
    assert updated_product.is_available == True

# API endpoints (GET, POST, PATCH, DELETE)
# CRUD operations
# Kafka message handling for product creation, updates, deletions, and stock level changes

# To run these tests, you'll need to install the following dependencies:

# pytest
# pytest-asyncio
# httpx (for TestClient)
# pytest test_product_service.py
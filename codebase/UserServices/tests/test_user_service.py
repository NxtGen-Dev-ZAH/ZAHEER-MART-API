import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db import get_session
from app.models import UserClass, UserCreate, USERLOGIN, Usertoken
from app import crud, kafka, auth, settings, user_pb2
from unittest.mock import AsyncMock, patch, MagicMock
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.producer import producer
from app.consumer import main

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
def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "Welcome To User Services **"}

@pytest.mark.asyncio
async def test_read_user(client, session):
    user = UserClass(username="testuser", email="test@example.com", password="password", shipping_address="123 Test St", phone=1234567890)
    session.add(user)
    session.commit()

    response = client.get(f"/user/{user.email}")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_detail_of_all_users(client, session):
    user1 = UserClass(username="user1", email="user1@example.com", password="password1", shipping_address="123 Test St", phone=1234567890)
    user2 = UserClass(username="user2", email="user2@example.com", password="password2", shipping_address="456 Test Ave", phone=9876543210)
    session.add(user1)
    session.add(user2)
    session.commit()

    response = client.get("/users/all")
    assert response.status_code == 200
    assert len(response.json()) == 2

@pytest.mark.asyncio
async def test_register_user(client):
    with patch('app.producer.publish_user_register', new_callable=AsyncMock) as mock_publish:
        with patch('app.consumer.main.check_user_in_db', new_callable=AsyncMock) as mock_check_user:
            with patch('app.crud.get_user_by_username', new_callable=AsyncMock) as mock_get_user:
                mock_check_user.return_value = None
                mock_get_user.return_value = UserClass(username="newuser", email="new@example.com", password="password", shipping_address="789 New St", phone=5555555555)
                
                user_data = {
                    "username": "newuser",
                    "email": "new@example.com",
                    "password": "password",
                    "shipping_address": "789 New St",
                    "phone": 5555555555
                }
                response = client.post("/user/register", json=user_data)
                assert response.status_code == 200
                assert response.json()["username"] == "newuser"
                mock_publish.assert_called_once()

@pytest.mark.asyncio
async def test_delete_user(client):
    with patch('app.producer.publish_user_delete', new_callable=AsyncMock) as mock_publish:
        response = client.delete("/user/1")
        assert response.status_code == 200
        assert "User with id 1 is deleted successfully" in response.json()["message"]
        mock_publish.assert_called_once_with(1)

# Test CRUD operations
@pytest.mark.asyncio
async def test_get_user_by_username(session):
    user = UserClass(username="testuser", email="test@example.com", password="password", shipping_address="123 Test St", phone=1234567890)
    session.add(user)
    session.commit()

    result = await crud.get_user_by_username(session, "testuser")
    assert result is not None
    assert result.username == "testuser"

@pytest.mark.asyncio
async def test_get_user_by_email(session):
    user = UserClass(username="testuser", email="test@example.com", password="password", shipping_address="123 Test St", phone=1234567890)
    session.add(user)
    session.commit()

    result = await crud.get_user_by_email(session, "test@example.com")
    assert result is not None
    assert result.email == "test@example.com"

@pytest.mark.asyncio
async def test_get_all_users(session):
    user1 = UserClass(username="user1", email="user1@example.com", password="password1", shipping_address="123 Test St", phone=1234567890)
    user2 = UserClass(username="user2", email="user2@example.com", password="password2", shipping_address="456 Test Ave", phone=9876543210)
    session.add(user1)
    session.add(user2)
    session.commit()

    result = await crud.get_all_users(session)
    assert len(result) == 2

# Test auth functions
def test_hash_password():
    password = "testpassword"
    hashed = auth.hash_password(password)
    assert auth.verify_password(password, hashed)

def test_generate_token():
    data = {"sub": "testuser"}
    token = auth.generate_token(data, timedelta(minutes=15))
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == "testuser"

def test_verify_access_token():
    data = {"sub": "testuser"}
    token = auth.generate_token(data, timedelta(minutes=15))
    result = auth.verify_access_token(token)
    assert result == "testuser"

# Test Kafka producer functions
@pytest.mark.asyncio
async def test_publish_user_register():
    with patch('app.kafka.send_message', new_callable=AsyncMock) as mock_send:
        user = UserCreate(username="newuser", email="new@example.com", password="password", shipping_address="789 New St", phone=5555555555)
        await producer.publish_user_register(user)
        mock_send.assert_called_once()

@pytest.mark.asyncio
async def test_publish_user_delete():
    with patch('app.kafka.send_message', new_callable=AsyncMock) as mock_send:
        await producer.publish_user_delete(1)
        mock_send.assert_called_once()

# Test Kafka consumer functions
@pytest.mark.asyncio
async def test_handle_register_user():
    with patch('app.consumer.main.check_user_in_db', new_callable=AsyncMock) as mock_check:
        with patch('sqlmodel.Session') as mock_session:
            mock_check.return_value = None
            new_msg = user_pb2.User(
                username="newuser",
                email="new@example.com",
                password="password",
                shipping_address="789 New St",
                phone=5555555555
            )
            await main.handle_register_user(new_msg)
            mock_session.return_value.add.assert_called_once()
            mock_session.return_value.commit.assert_called_once()

@pytest.mark.asyncio
async def test_handle_login():
    with patch('app.consumer.main.check_user_in_db', new_callable=AsyncMock) as mock_check:
        with patch('app.auth.verify_password', return_value=True):
            with patch('app.auth.generate_token', return_value="test_token"):
                with patch('app.kafka.send_message', new_callable=AsyncMock) as mock_send:
                    mock_check.return_value = UserClass(username="testuser", email="test@example.com", password="password" ,shipping_address="address",phone=123)
                    new_msg = user_pb2.User(
                        username="testuser",
                        password="password",
                        service=user_pb2.SelectService.ORDER
                    )
                    await main.handle_login(new_msg)
                    mock_send.assert_called_once()

# Add more tests for other consumer functions (handle_verify_user, handle_refresh_token, handle_delete_user)
# as well as the process_message function

# Test the overall message processing flow
@pytest.mark.asyncio
async def test_process_message():
    with patch('app.consumer.main.handle_register_user', new_callable=AsyncMock) as mock_register:
        new_msg = user_pb2.User(
            username="newuser",
            email="new@example.com",
            password="password",
            shipping_address="789 New St",
            phone=5555555555,
            option=user_pb2.SelectOption.REGISTER
        )
        await main.process_message(new_msg)
        mock_register.assert_called_once_with(new_msg)

# Add more tests for other message types (LOGIN, CURRENT_USER, REFRESH_TOKEN, DELETE)


# pytest test_user_service.py

# pytest
# pytest-asyncio
# httpx (for TestClient)
# sqlmodel
# fastapi
# pyjwt
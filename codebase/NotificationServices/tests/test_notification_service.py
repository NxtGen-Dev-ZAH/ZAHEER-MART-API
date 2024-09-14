import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from unittest.mock import patch, AsyncMock
from app.main import app
from app.models import Notification
from app.db import get_session
from app import settings, notification_pb2
from app.consumer import main as consumer_main

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
    assert response.json() == {"message": "Notification Management Service"}

# Test database operations
@pytest.mark.asyncio
async def test_save_notification(session):
    notification = Notification(
        user_id=1,
        email="test@example.com",
        username="testuser",
        title="Test Notification",
        message="This is a test notification",
        notification_type="TEST",
    )
    await consumer_main.save_notification(notification)
    
    saved_notification = session.query(Notification).first()
    assert saved_notification is not None
    assert saved_notification.email == "test@example.com"
    assert saved_notification.username == "testuser"

# Test message processing
@pytest.mark.asyncio
async def test_process_message_user_registration(session):
    user_msg = notification_pb2.User(
        id=1,
        email="newuser@example.com",
        username="newuser",
        option=notification_pb2.SelectOption.REGISTER,
    )
    
    with patch('app.handle_email.send_email', new_callable=AsyncMock) as mock_send_email:
        await consumer_main.process_message_user(user_msg)
        
        mock_send_email.assert_called_once()
        
        saved_notification = session.query(Notification).first()
        assert saved_notification is not None
        assert saved_notification.email == "newuser@example.com"
        assert saved_notification.notification_type == "USER_REGISTRATION"

@pytest.mark.asyncio
async def test_process_message_payment_paid(session):
    payment_msg = notification_pb2.Payment(
        id=1,
        email="user@example.com",
        username="user",
        payment_status=notification_pb2.PaymentStatus.PAID,
    )
    
    with patch('app.handle_email.send_email', new_callable=AsyncMock) as mock_send_email:
        await consumer_main.process_message_payment(payment_msg)
        
        mock_send_email.assert_called_once()
        
        saved_notification = session.query(Notification).first()
        assert saved_notification is not None
        assert saved_notification.email == "user@example.com"
        assert saved_notification.notification_type == "PAYMENT_CONFIRMATION"

@pytest.mark.asyncio
async def test_process_message_order_created(session):
    order_msg = notification_pb2.Order(
        id=1,
        email="user@example.com",
        username="user",
        option=notification_pb2.SelectOption.CREATE,
    )
    
    with patch('app.handle_email.send_email', new_callable=AsyncMock) as mock_send_email:
        await consumer_main.process_message_order(order_msg)
        
        mock_send_email.assert_called_once()
        
        saved_notification = session.query(Notification).first()
        assert saved_notification is not None
        assert saved_notification.email == "user@example.com"
        assert saved_notification.notification_type == "ORDER_CONFIRMATION"

# Test Kafka consumers
@pytest.mark.asyncio
async def test_start_consuming_user(session):
    with patch('app.kafka.consume_message_user', new_callable=AsyncMock) as mock_consume:
        mock_consume.return_value = [
            notification_pb2.User(
                id=1,
                email="user1@example.com",
                username="user1",
                option=notification_pb2.SelectOption.REGISTER,
            )
        ]
        
        with patch('app.consumer.main.process_message_user', new_callable=AsyncMock) as mock_process:
            await consumer_main.start_consuming_user()
            
            mock_consume.assert_called_once_with(
                settings.KAFKA_TOPIC_USER,
                settings.KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_NEW_USER,
            )
            mock_process.assert_called_once()

@pytest.mark.asyncio
async def test_start_consuming_payment(session):
    with patch('app.kafka.consume_message_payment', new_callable=AsyncMock) as mock_consume:
        mock_consume.return_value = [
            notification_pb2.Payment(
                id=1,
                email="user1@example.com",
                username="user1",
                payment_status=notification_pb2.PaymentStatus.PAID,
            )
        ]
        
        with patch('app.consumer.main.process_message_payment', new_callable=AsyncMock) as mock_process:
            await consumer_main.start_consuming_payment()
            
            mock_consume.assert_called_once_with(
                settings.KAFKA_TOPIC_PAYMENT,
                settings.KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_PAYMENT_DONE,
            )
            mock_process.assert_called_once()

@pytest.mark.asyncio
async def test_start_consuming_order(session):
    with patch('app.kafka.consume_message_order', new_callable=AsyncMock) as mock_consume:
        mock_consume.return_value = [
            notification_pb2.Order(
                id=1,
                email="user1@example.com",
                username="user1",
                option=notification_pb2.SelectOption.CREATE,
            )
        ]
        
        with patch('app.consumer.main.process_message_order', new_callable=AsyncMock) as mock_process:
            await consumer_main.start_consuming_order()
            
            mock_consume.assert_called_once_with(
                settings.KAFKA_TOPIC_ORDER,
                settings.KAFKA_CONSUMER_GROUP_ID_TO_CONSUME_ORDER_CREATED,
            )
            mock_process.assert_called_once()

# Test email sending
@pytest.mark.asyncio
async def test_send_email():
    with patch('smtplib.SMTP_SSL') as mock_smtp:
        mock_server = AsyncMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        await handle_email.send_email(
            body="Test email body",
            subject="Test Subject",
            user_email="test@example.com"
        )
        
        mock_server.login.assert_called_once_with(settings.FROM_EMAIL, settings.FROM_EMAIL_APP_PASSWORD)
        mock_server.sendmail.assert_called_once()

# Test Kafka producer
@pytest.mark.asyncio
async def test_produce_message():
    with patch('aiokafka.AIOKafkaProducer') as mock_producer:
        mock_producer_instance = AsyncMock()
        mock_producer.return_value = mock_producer_instance
        
        await kafka.produce_message("test_topic", b"test_message")
        
        mock_producer_instance.start.assert_called_once()
        mock_producer_instance.send_and_wait.assert_called_once_with("test_topic", b"test_message")
        mock_producer_instance.stop.assert_called_once()
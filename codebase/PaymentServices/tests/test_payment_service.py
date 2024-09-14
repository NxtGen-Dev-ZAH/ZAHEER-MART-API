import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db import get_session
from app.models import Payment, PaymentRequest, CheckoutRequest
from app import crud, kafka, auth, settings, payment_pb2
from unittest.mock import AsyncMock, patch, MagicMock
from app.producer import main
from app.consumer import main
from app.stripe.payment import create_payment


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


@pytest.fixture
def mock_kafka():
    with patch("app.kafka.send_kafka_message", new_callable=AsyncMock) as mock_send:
        with patch(
            "app.kafka.consume_message_from_user_service", new_callable=AsyncMock
        ) as mock_consume_user:
            with patch(
                "app.consumer.main.consume_payment_response", new_callable=AsyncMock
            ) as mock_consume_payment:
                yield mock_send, mock_consume_user, mock_consume_payment


@pytest.fixture
def mock_stripe():
    with patch("stripe.PaymentIntent.create") as mock_create:
        yield mock_create


# Test API endpoints
def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Payment Management Service Of Mart Api"}


@pytest.mark.asyncio
async def test_payment_request_success(client, mock_kafka):
    mock_send, mock_consume_user, mock_consume_payment = mock_kafka

    mock_consume_user.return_value = payment_pb2.User(
        user_id="123", username="testuser", email="test@example.com"
    )
    mock_consume_payment.return_value = payment_pb2.Payment(
        payment_status=payment_pb2.PaymentStatus.PAID
    )

    payment_request = {
        "amount": 1000,
        "card_number": "4242424242424242",
        "exp_month": 12,
        "exp_year": 2025,
        "cvc": "123",
        "order_id": "order123",
    }

    response = client.put(
        "/payment", json=payment_request, headers={"Authorization": "Bearer test_token"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "payment_status": "Paid",
        "message": "Payment Successful",
    }


@pytest.mark.asyncio
async def test_payment_request_failure(client, mock_kafka):
    mock_send, mock_consume_user, mock_consume_payment = mock_kafka

    mock_consume_user.return_value = payment_pb2.User(
        user_id="123", username="testuser", email="test@example.com"
    )
    mock_consume_payment.return_value = payment_pb2.Payment(
        payment_status=payment_pb2.PaymentStatus.FAILED
    )

    payment_request = {
        "amount": 1000,
        "card_number": "4242424242424242",
        "exp_month": 12,
        "exp_year": 2025,
        "cvc": "123",
        "order_id": "order123",
    }

    response = client.put(
        "/payment", json=payment_request, headers={"Authorization": "Bearer test_token"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "payment_status": "Pending",
        "message": "Payment Unsuccessful",
    }


@pytest.mark.asyncio
async def test_create_checkout_session(client, mock_stripe):
    mock_stripe.return_value = {"id": "test_session_id"}

    checkout_request = {"amount": 1000, "currency": "usd"}

    response = client.post("/create-checkout-session/", json=checkout_request)

    assert response.status_code == 200
    assert response.json() == {"sessionId": "test_session_id"}


# Test CRUD operations
@pytest.mark.asyncio
async def test_get_order(session):
    payment = Payment(
        order_id="order123",
        user_id="user123",
        payment_status="Pending",
        payment_id="pay123",
    )
    session.add(payment)
    session.commit()

    result = await crud.get_order(session, "order123")
    assert result is not None
    assert result.order_id == "order123"


# Test Stripe payment creation
@pytest.mark.asyncio
async def test_create_payment_success():
    payment_request = PaymentRequest(
        amount=1000,
        card_number=4242424242424242,
        exp_month=12,
        exp_year=2025,
        cvc=123,
        order_id="order123",
    )

    with patch("stripe.PaymentIntent.create") as mock_create:
        mock_create.return_value = {"status": "succeeded"}
        result = await create_payment(payment_request)

    assert result == payment_pb2.PaymentStatus.PAID


@pytest.mark.asyncio
async def test_create_payment_failure():
    payment_request = PaymentRequest(
        amount=1000,
        card_number=4242424242424242,
        exp_month=12,
        exp_year=2025,
        cvc=123,
        order_id="order123",
    )

    with patch("stripe.PaymentIntent.create") as mock_create:
        mock_create.return_value = {"status": "failed"}
        result = await create_payment(payment_request)

    assert result == payment_pb2.PaymentStatus.FAILED


# Test Kafka consumer functions
@pytest.mark.asyncio
async def test_process_order_message_create():
    with patch("sqlmodel.Session") as mock_session:
        message = payment_pb2.Order(
            option=payment_pb2.SelectOption.CREATE,
            order_id="order123",
            user_id="user123",
        )

        await main.process_order_message(message)

        mock_session.return_value.add.assert_called_once()
        mock_session.return_value.commit.assert_called_once()


@pytest.mark.asyncio
async def test_process_order_message_delete():
    with patch("sqlmodel.Session") as mock_session:
        with patch("app.crud.get_order", new_callable=AsyncMock) as mock_get_order:
            mock_get_order.return_value = Payment(
                order_id="order123", user_id="user123", payment_id="payment123"
            )

            message = payment_pb2.Order(
                option=payment_pb2.SelectOption.DELETE, order_id="order123"
            )

            await main.process_order_message(message)

            mock_session.return_value.delete.assert_called_once()
            mock_session.return_value.commit.assert_called_once()


# Test the overall message processing flow
@pytest.mark.asyncio
async def test_process_message():
    with patch(
        "app.consumer.main.handle_create_order", new_callable=AsyncMock
    ) as mock_create_order:
        message = payment_pb2.Order(
            option=payment_pb2.SelectOption.CREATE,
            order_id="order123",
            user_id="user123",
        )
        await main.process_order_message(message)

        mock_create_order.assert_called_once_with(message)


# Add more tests for other message types and scenarios as needed

# Run tests with: pytest test_payment_service.py

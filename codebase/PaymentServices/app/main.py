# main.py
import asyncio
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException
from app.consumer import main
from app.models import CheckoutRequest, Payment, User, PaymentRequest
from app import auth, db, kafka, payment_pb2, settings
from app.producer.main import publish_payment_request
from app.router import user
import stripe

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_table()
    logger.info("In the Database All The Tables Are Created")
    await kafka.create_topic()
    loop = asyncio.get_event_loop()
    task1 = loop.create_task(main.start_consuming())
    task2 = loop.create_task(main.start_order_consumer())
    try:
        yield
    finally:
        for task in [task1, task2]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app: FastAPI = FastAPI(lifespan=lifespan)
app.include_router(router=user.user_router)


@app.get("/")
async def root():
    return {"message": "Payment Management Service Of Mart Api"}


#  Endpoint to add payment
@app.put("/payment", response_model=dict)
async def payment_request(
    payment_request_detail: PaymentRequest,
    verify_token: str = Depends(auth.verify_access_token),
):
    await publish_payment_request(payment_request_detail, verify_token)
    payment_proto = await main.consume_payment_response()

    if payment_proto.error_message:
        return {"Message": payment_proto.error_message}
    elif payment_proto.payment_status == payment_pb2.PaymentStatus.PAID:
        return {"payment_status": "Paid", "message": "Payment Successful"}
    else:
        return {"payment_status": "Pending", "message": "Payment Unsuccessful"}


@app.post("/create-checkout-session/")
async def create_checkout_session(checkout_request: CheckoutRequest):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": checkout_request.currency,
                        "product_data": {
                            "name": "Your Product Name",
                        },
                        "unit_amount": checkout_request.amount,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url="https://your-domain.com/success",
            cancel_url="https://your-domain.com/cancel",
        )
        return {"sessionId": session.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/success")
async def success_page():
    return {"message": "Payment Successful"}

@app.get("/cancel")
async def cancel_page():
    return {"message": "Payment Cancelled"}

# from fastapi import FastAPI, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# from pydantic import BaseModel
# from typing import Optional
# from fastapi.openapi.utils import get_openapi
# from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI()

# # OAuth2 scheme for authentication
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# # Fake user database
# fake_users_db = {
#     "user1": {
#         "username": "user1",
#         "full_name": "User One",
#         "email": "user1@example.com",
#         "hashed_password": "fakehashedpassword1122ss",
#         "disabled": False,
#     }
# }


# # User and Token models
# class Token(BaseModel):
#     access_token: str
#     token_type: str


# class User(BaseModel):
#     username: str
#     full_name: Optional[str] = None
#     email: Optional[str] = None
#     disabled: Optional[bool] = None


# class UserInDB(User):
#     hashed_password: str


# def fake_hash_password(password: str):
#     return "fakehashed" + password


# def get_user(db, username: str):
#     if username in db:
#         user_dict = db[username]
#         return UserInDB(**user_dict)


# def authenticate_user(fake_db, username: str, password: str):
#     user = get_user(fake_db, username)
#     if not user:
#         return False
#     if user.hashed_password != fake_hash_password(password):
#         return False
#     return user


# # Dependency for getting the current user
# async def get_current_user(token: str = Depends(oauth2_scheme)):
#     user = get_user(fake_users_db, token)  # Replace with actual token logic
#     if user is None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid authentication credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     return user


# # Route to get a token
# @app.post("/token", response_model=Token)
# async def login(form_data: OAuth2PasswordRequestForm = Depends()):
#     user = authenticate_user(fake_users_db, form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     return {"access_token": form_data.username, "token_type": "bearer"}


# # Secured route
# @app.get("/users/me", response_model=User)
# async def read_users_me(current_user: User = Depends(get_current_user)):
#     return current_user


# # Custom OpenAPI schema to include security
# def custom_openapi():
#     if app.openapi_schema:
#         return app.openapi_schema
#     openapi_schema = get_openapi(
#         title="Secure FastAPI",
#         version="1.0.0",
#         description="A secure FastAPI application",
#         routes=app.routes,
#     )
#     openapi_schema["components"]["securitySchemes"] = {
#         "Bearer Auth": {
#             "type": "oauth2",
#             "flows": {"password": {"tokenUrl": "token", "scopes": {}}},
#         }
#     }
#     openapi_schema["security"] = [{"Bearer Auth": []}]
#     app.openapi_schema = openapi_schema
#     return app.openapi_schema


# app.openapi = custom_openapi

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Global dependency to enforce authentication on all routes
# app.dependency_overrides[oauth2_scheme] = oauth2_scheme

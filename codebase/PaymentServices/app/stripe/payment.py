# payment.py
import logging
import random
from app import models
from app import payment_pb2
import stripe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

stripe.api_key = "sk_test_51PyRId02JMk1g3mjz4wm5o0KXT9F0DOeeIN3t13IX8wqG2Nil4TFeCYHfHCW0l36H7aTiXstkzieVsRhTch8sFim00hCVmd3jZ"


# Stripe payment handling function
async def create_payment(payment_request: models.PaymentRequest):
    try:
        # Create a payment intent with Stripe
        payment_intent = stripe.PaymentIntent.create(
            amount=payment_request.amount,
            currency="usd",  # Or use payment_request.currency if it varies
            payment_method_data={
                "type": "card",
                "card": {
                    "number": payment_request.card_number,
                    "exp_month": payment_request.exp_month,
                    "exp_year": payment_request.exp_year,
                    "cvc": payment_request.cvc,
                },
            },
        )

        if payment_intent["status"] == "succeeded":
            return payment_pb2.PaymentStatus.PAID
        else:
            return payment_pb2.PaymentStatus.FAILED

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        return payment_pb2.PaymentStatus.FAILED

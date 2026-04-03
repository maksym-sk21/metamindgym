import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(user, course, success_url, cancel_url):
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': course.stripe_price_id,
            'quantity': 1,
        }],
        mode='payment',
        customer_email=user.email,
        metadata={
            'user_id': str(user.id),
            'course_id': str(course.id),
        },
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session

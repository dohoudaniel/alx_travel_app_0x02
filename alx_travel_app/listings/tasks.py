# listings/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Payment
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_payment_confirmation_email(payment_id):
    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        logger.error("Payment not found for email task: %s", payment_id)
        return

    subject = f"Payment confirmation for booking {payment.booking_reference}"
    message = f"""
    Hello,

    Your payment for booking {payment.booking_reference} has been received.
    Amount: {payment.amount} {payment.currency}
    Reference: {payment.tx_ref}
    Status: {payment.status}

    Thank you.
    """
    recipient = payment.user.email if payment.user and payment.user.email else None
    if not recipient:
        logger.error("No recipient email for payment %s", payment_id)
        return

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        fail_silently=False,
    )
    logger.info("Payment confirmation email sent for payment %s", payment_id)


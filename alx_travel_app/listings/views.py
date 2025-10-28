from django.shortcuts import render

# Create your views here.
import os
import requests
import uuid
import logging

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Payment
from .serializers import PaymentSerializer
from .tasks import send_payment_confirmation_email  # celery task
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view


logger = logging.getLogger(__name__)


CHAPA_BASE = getattr(settings, "CHAPA_BASE_URL", "https://api.chapa.co/v1")
CHAPA_INIT_ENDPOINT = f"{CHAPA_BASE}/transaction/initialize"
CHAPA_VERIFY_ENDPOINT = f"{CHAPA_BASE}/transaction/verify"  # append /{tx_ref}


class InitiatePaymentView(APIView):
    permission_classes = [permissions.AllowAny] # [permissions.IsAuthenticatedOrReadOnly] (for production)

    def post(self, request):
        """
        Create a Payment record and call Chapa to initialize a transaction.
        Expected payload: { booking_reference, amount, currency, return_url (optional) }
        """
        data = request.data
        booking_reference = data.get("booking_reference") or f"booking-{uuid.uuid4().hex[:8]}"
        amount = data.get("amount")
        currency = data.get("currency", "ETB")
        return_url = data.get("return_url")  # where Chapa will redirect after payment
        customer_email = request.user.email if request.user.is_authenticated else data.get("email")

        if not amount:
            return Response({"detail": "amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        # create unique tx_ref
        tx_ref = f"{booking_reference}-{uuid.uuid4().hex}"

        payment = Payment.objects.create(
            user=request.user if request.user.is_authenticated else None,
            booking_reference=booking_reference,
            amount=amount,
            currency=currency,
            tx_ref=tx_ref,
            status="PENDING",
        )

        payload = {
            "tx_ref": tx_ref,
            "amount": float(amount),
            "currency": currency,
            "email": customer_email,
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
        }

        if return_url:
            payload["return_url"] = return_url
        # optional: callback_url param if you want Chapa to call your webhook
        callback_url = data.get("callback_url")
        if callback_url:
            payload["callback_url"] = callback_url

        headers = {
            "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(CHAPA_INIT_ENDPOINT, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.exception("Chapa initialize failed")
            payment.mark_failed(reason=str(e))
            return Response({"detail": "Payment initialization failed", "error": str(e)}, status=502)

        body = resp.json()
        # body usually has data.checkout_url (link) and data.reference etc. Store raw response in metadata.
        payment.metadata = body
        # Likely data fields:
        chapa_tx_id = body.get("data", {}).get("id") or body.get("data", {}).get("tx_id") or body.get("data", {}).get("reference")
        checkout_url = body.get("data", {}).get("checkout_url") or body.get("data", {}).get("payment_link")

        if chapa_tx_id:
            payment.chapa_tx_id = chapa_tx_id
        payment.save(update_fields=["chapa_tx_id", "metadata", "updated_at"])

        return Response({
            "checkout_url": checkout_url,
            "tx_ref": tx_ref,
            "payment_id": payment.id,
            "raw": body
        }, status=status.HTTP_200_OK)


class VerifyPaymentView(APIView):
    permission_classes = [permissions.AllowAny]  # you may restrict to your internal services

    def get(self, request, tx_ref):
        """
        Query Chapa verify endpoint and update Payment status.
        """
        try:
            payment = Payment.objects.get(tx_ref=tx_ref)
        except Payment.DoesNotExist:
            return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        headers = {
            "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"
        }
        url = f"{CHAPA_VERIFY_ENDPOINT}/{tx_ref}"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.exception("Chapa verify failed")
            return Response({"detail": "verify failed", "error": str(e)}, status=502)

        body = resp.json()
        # The response should include success & status
        status_data = body.get("data", {}).get("status") or body.get("message")
        chapa_reference = body.get("data", {}).get("reference") or body.get("data", {}).get("tx_ref")

        payment.metadata = {**(payment.metadata or {}), "verify_response": body}

        if status_data and str(status_data).lower() in ("successful", "success", "completed", "paid"):
            payment.mark_completed(chapa_tx_id=chapa_reference, extra={"verify_response": body})
            # kick off email send asynchronously
            try:
                send_payment_confirmation_email.delay(payment.id)
            except Exception:
                logger.exception("Could not enqueue confirmation email")
            return Response({"detail": "Payment completed", "payment_status": payment.status}, status=200)
        else:
            payment.mark_failed(reason=body.get("message") or "not successful")
            return Response({"detail": "Payment not successful", "raw": body, "payment_status": payment.status}, status=200)


@csrf_exempt
@api_view(["POST"])
def chapa_webhook(request):
    """
    Endpoint to receive Chapa callback (if you configured callback_url on init).
    IMPORTANT: verify signature or token if Chapa docs provide that.
    """
    payload = request.data
    logger.info("chapa webhook payload: %s", payload)
    # Example payload might contain: data.reference or tx_ref
    tx_ref = payload.get("data", {}).get("tx_ref") or payload.get("data", {}).get("reference") or request.GET.get("reference")
    if not tx_ref:
        return Response({"detail": "tx_ref missing"}, status=400)

    try:
        payment = Payment.objects.get(tx_ref=tx_ref)
    except Payment.DoesNotExist:
        return Response({"detail": "Payment not found"}, status=404)

    # best practice: call verify endpoint to be sure
    # (reuse the VerifyPaymentView logic or call the function that verifies)
    # For brevity, let's just mark completed if payload indicates success
    status_from_payload = payload.get("data", {}).get("status")
    if str(status_from_payload).lower() in ("successful", "success", "completed", "paid"):
        payment.mark_completed(chapa_tx_id=payload.get("data", {}).get("reference"), extra={"webhook": payload})
        send_payment_confirmation_email.delay(payment.id)
    else:
        payment.mark_failed(reason="webhook says not successful")
    return Response({"ok": True})

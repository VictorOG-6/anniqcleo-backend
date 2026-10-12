import hashlib
import hmac
import os
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx


class AfripayError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def naira_to_kobo(amount_naira: int) -> int:
    if amount_naira <= 0:
        raise ValueError("Payment amount must be greater than zero")
    return amount_naira * 100


def checkout_origin_from_api_base(api_base: str) -> str:
    origin = api_base.rstrip("/")
    for suffix in ("/api/merchant", "/api/v1"):
        if origin.endswith(suffix):
            return origin[: -len(suffix)]
    return origin


def resolve_checkout_session(
    data: dict[str, Any],
    *,
    checkout_origin: str,
) -> tuple[str | None, str | None]:
    token_raw = data.get("token") or data.get("access_code")
    token = str(token_raw).strip() if token_raw else None

    checkout_url_raw = (
        data.get("checkout_url")
        or data.get("authorization_url")
        or data.get("payment_url")
    )
    checkout_url = str(checkout_url_raw).strip() if checkout_url_raw else None

    if not checkout_url and token:
        checkout_url = f"{checkout_origin.rstrip('/')}/link/{token}"

    if checkout_url and not token and "/link/" in checkout_url:
        token = checkout_url.rstrip("/").split("/link/")[-1] or None

    return checkout_url, token


def provider_amount_to_kobo(amount: Any) -> int:
    if amount is None:
        raise ValueError("Missing payment amount")
    try:
        naira = Decimal(str(amount))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid payment amount") from exc
    kobo = int(naira * 100)
    if kobo <= 0:
        raise ValueError("Payment amount must be greater than zero")
    return kobo


class AfripayService:
    def __init__(
        self,
        client_id: str | None = None,
        secret_key: str | None = None,
        webhook_secret: str | None = None,
        base_url: str | None = None,
        callback_url: str | None = None,
        timeout: float = 15.0,
    ):
        self.client_id = client_id or os.getenv("AFRIPAY_CLIENT_ID")
        self.secret_key = secret_key or os.getenv("AFRIPAY_SECRET_KEY")
        self.webhook_secret = webhook_secret or os.getenv("AFRIPAY_WEBHOOK_SECRET")
        self.base_url = (
            base_url
            or os.getenv("AFRIPAY_BASE_URL")
            or "https://business.goafripay.com/api/merchant"
        ).rstrip("/")
        self.callback_url = callback_url or os.getenv("AFRIPAY_CALLBACK_URL")
        self.checkout_origin = (
            os.getenv("AFRIPAY_CHECKOUT_ORIGIN")
            or checkout_origin_from_api_base(self.base_url)
        ).rstrip("/")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        if not self.secret_key:
            raise AfripayError("Afripay is not configured", status_code=503)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.client_id:
            headers["X-Client-Id"] = self.client_id
            headers["X-Client-Secret"] = self.secret_key
        else:
            headers["Authorization"] = f"Bearer {self.secret_key}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(),
                json=json,
                timeout=self.timeout,
            )
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AfripayError("Unable to communicate with Afripay") from exc

        if not response.is_success or not payload.get("status"):
            message = payload.get("message", "Afripay request failed")
            raise AfripayError(message)
        return payload["data"]

    def initialize_transaction(
        self,
        *,
        email: str,
        amount_naira: int,
        reference: str,
        order_id: str,
        user_id: str,
        name: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "amount": amount_naira,
            "currency": "NGN",
            "customer": {
                "name": name,
                "email": email,
            },
            "reference": reference,
            "metadata": {
                "order_id": order_id,
                "user_id": user_id,
            },
        }
        if title:
            payload["title"] = title
        if self.callback_url:
            payload["callback_url"] = self.callback_url
        return self._request("POST", "/checkout/initialize", json=payload)

    def verify_transaction(self, reference: str) -> dict[str, Any]:
        return self._request("GET", f"/checkout/verify/{reference}")

    def create_full_refund(
        self,
        *,
        transaction_reference: str,
        merchant_note: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/refund",
            json={
                "transaction": transaction_reference,
                "merchant_note": merchant_note,
            },
        )

    def verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:
        secret = self.webhook_secret
        if not secret or not signature:
            return False
        expected = hmac.new(
            secret.encode(),
            raw_body,
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


afripay_service = AfripayService()

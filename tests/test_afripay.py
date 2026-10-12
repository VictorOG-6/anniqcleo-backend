import hashlib
import hmac
import unittest
from unittest.mock import patch

import httpx

from services.afripay import (
    AfripayError,
    AfripayService,
    checkout_origin_from_api_base,
    naira_to_kobo,
    provider_amount_to_kobo,
    resolve_checkout_session,
)


class AfripayServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = AfripayService(
            client_id="mch_test_client",
            secret_key="sk_test_secret",
            webhook_secret="whsec_test",
            base_url="https://business.goafripay.com/api/merchant",
            callback_url="https://shop.test/payment/callback",
        )

    def test_naira_is_converted_to_kobo(self):
        self.assertEqual(naira_to_kobo(5_000), 500_000)
        with self.assertRaises(ValueError):
            naira_to_kobo(0)

    def test_provider_amount_parses_decimal_strings(self):
        self.assertEqual(provider_amount_to_kobo("5000.00"), 500_000)
        self.assertEqual(provider_amount_to_kobo(5000), 500_000)

    def test_checkout_origin_is_derived_from_api_base(self):
        self.assertEqual(
            checkout_origin_from_api_base(
                "https://sandbox-business.goafripay.com/api/merchant"
            ),
            "https://sandbox-business.goafripay.com",
        )

    def test_resolve_checkout_session_builds_link_from_token(self):
        checkout_url, token = resolve_checkout_session(
            {"token": "abc123"},
            checkout_origin="https://sandbox-business.goafripay.com",
        )
        self.assertEqual(token, "abc123")
        self.assertEqual(
            checkout_url,
            "https://sandbox-business.goafripay.com/link/abc123",
        )

    def test_webhook_signature_uses_webhook_secret_and_raw_body(self):
        body = b'{"event":"charge.success","data":{"reference":"ord-1"}}'
        signature = hmac.new(
            b"whsec_test",
            body,
            hashlib.sha512,
        ).hexdigest()

        self.assertTrue(
            self.service.verify_webhook_signature(body, signature)
        )
        self.assertFalse(
            self.service.verify_webhook_signature(body + b" ", signature)
        )

    @patch("services.afripay.httpx.request")
    def test_initialize_transaction_sends_naira_amount(self, request):
        request.return_value = httpx.Response(
            201,
            json={
                "status": True,
                "data": {
                    "checkout_url": "https://business.goafripay.com/link/qtujnmgstm",
                    "token": "qtujnmgstm",
                    "reference": "ord-1-attempt",
                },
            },
        )

        result = self.service.initialize_transaction(
            email="buyer@example.com",
            name="Buyer",
            amount_naira=5_000,
            reference="ord-1-attempt",
            order_id="order-uuid",
            user_id="user-uuid",
            title="Payment for order ORD-1",
        )

        headers = request.call_args.kwargs["headers"]
        payload = request.call_args.kwargs["json"]
        self.assertEqual(headers["X-Client-Id"], "mch_test_client")
        self.assertEqual(headers["X-Client-Secret"], "sk_test_secret")
        self.assertEqual(payload["amount"], 5_000)
        self.assertEqual(payload["currency"], "NGN")
        self.assertEqual(payload["reference"], "ord-1-attempt")
        self.assertEqual(payload["metadata"]["order_id"], "order-uuid")
        self.assertEqual(payload["title"], "Payment for order ORD-1")
        self.assertEqual(
            payload["callback_url"],
            "https://shop.test/payment/callback",
        )
        self.assertEqual(result["token"], "qtujnmgstm")

    @patch("services.afripay.httpx.request")
    def test_provider_errors_do_not_look_successful(self, request):
        request.return_value = httpx.Response(
            400,
            json={"status": False, "message": "Invalid amount"},
        )

        with self.assertRaisesRegex(AfripayError, "Invalid amount"):
            self.service.verify_transaction("bad-reference")

    @patch("services.afripay.httpx.request")
    def test_refund_request_is_full_and_uses_transaction_reference(self, request):
        request.return_value = httpx.Response(
            200,
            json={
                "status": True,
                "data": {"status": "pending", "id": 42},
            },
        )

        self.service.create_full_refund(
            transaction_reference="ord-1-attempt",
            merchant_note="Customer cancellation",
        )

        payload = request.call_args.kwargs["json"]
        self.assertEqual(payload["transaction"], "ord-1-attempt")
        self.assertNotIn("amount", payload)


if __name__ == "__main__":
    unittest.main()

"""NOWPayments Binance/Crypto billing & IPN webhook security tests: signature verification, fulfillment, idempotency."""
import hashlib
import hmac
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from fastapi.testclient import TestClient

import api.main as main
from billing.ledger import BillingLedger

TEST_IPN_SECRET = "4S2s74y4dTnqdyDt2zfXrX8yLHzF8X3y"

@pytest.fixture()
def client(tmp_path, monkeypatch):
    ledger = BillingLedger(str(tmp_path / "np_ledger.json"))
    monkeypatch.setattr(main, "ledger", ledger)
    monkeypatch.setattr(main.nowpayments_service, "ledger", ledger)
    monkeypatch.setattr(main.nowpayments_service, "ipn_secret", TEST_IPN_SECRET)
    monkeypatch.setattr(main.nowpayments_service, "api_key", "C75Y01Q-test-key")
    return TestClient(main.app)

def sign_nowpayments_ipn(body_dict: dict, secret: str = TEST_IPN_SECRET) -> str:
    def sort_dict(item):
        if isinstance(item, dict):
            return {k: sort_dict(v) for k, v in sorted(item.items())}
        if isinstance(item, list):
            return [sort_dict(i) for i in item]
        return item

    sorted_body = sort_dict(body_dict)
    serialized = json.dumps(sorted_body, separators=(',', ':'), sort_keys=True)
    return hmac.new(secret.encode("utf-8"), serialized.encode("utf-8"), hashlib.sha512).hexdigest()

def test_nowpayments_webhook_rejects_unsigned(client):
    body = {"payment_status": "finished", "order_id": "np_cli_test_pack_micro_15_1234"}
    r = client.post("/v1/billing/nowpayments-webhook", json=body)
    assert r.status_code == 400

def test_nowpayments_webhook_rejects_bad_signature(client):
    body = {"payment_status": "finished", "order_id": "np_cli_test_pack_micro_15_1234"}
    raw_body = json.dumps(body).encode("utf-8")
    headers = {"x-nowpayments-sig": "invalid_sig_hex"}
    r = client.post("/v1/billing/nowpayments-webhook", content=raw_body, headers=headers)
    assert r.status_code == 400

def test_nowpayments_webhook_credits_account_idempotently(client):
    main.ledger.create_account("cli_crypto_user")
    order_id = "np__cli_crypto_user__pack_pro_200__a1b2c3d4"
    payment_event = {
        "payment_id": 99887766,
        "payment_status": "finished",
        "price_amount": 69,
        "price_currency": "usd",
        "pay_amount": 69.1,
        "pay_currency": "usdttrc20",
        "order_id": order_id,
        "customer_email": "agency@crypto-leads.com"
    }
    raw_body = json.dumps(payment_event).encode("utf-8")
    sig = sign_nowpayments_ipn(payment_event)
    headers = {"x-nowpayments-sig": sig, "Content-Type": "application/json"}

    # First fulfillment: must credit 200 leads
    r1 = client.post("/v1/billing/nowpayments-webhook", content=raw_body, headers=headers)
    assert r1.status_code == 200
    res1 = r1.json()
    assert res1["status"] == "PROCESSED"
    assert res1["credits_added"] == 200
    assert main.ledger.get_by_client_id("cli_crypto_user").credits_balance == 200

    # Second fulfillment: must be idempotent (0 extra credits)
    r2 = client.post("/v1/billing/nowpayments-webhook", content=raw_body, headers=headers)
    assert r2.status_code == 200
    res2 = r2.json()
    assert res2["status"] == "ALREADY_PROCESSED"
    assert res2["credits_added"] == 0
    assert main.ledger.get_by_client_id("cli_crypto_user").credits_balance == 200

def test_nowpayments_buy_creates_invoice_session(client, monkeypatch):
    class FakeResponse:
        status_code = 200
        def json(self):
            return {
                "id": "6020077650",
                "invoice_url": "https://nowpayments.io/payment/?iid=6020077650"
            }

    import requests
    def fake_post(url, json=None, headers=None, timeout=None):
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)

    r = client.post("/v1/billing/buy", json={"package_id": "pack_starter_60", "email": "test@buyer.com"})
    assert r.status_code == 200
    data = r.json()
    assert data["checkout_url"] == "https://nowpayments.io/payment/?iid=6020077650"
    assert data["session_id"].startswith("np_")
    assert data["credits_to_add"] == 60
    assert data["mode"] == "nowpayments_binance"


def test_nowpayments_agent_buy_creates_direct_crypto_instructions(client, monkeypatch):
    class FakePaymentResponse:
        status_code = 201
        def json(self):
            return {
                "payment_id": "4763998780",
                "payment_status": "waiting",
                "pay_address": "TKfJPVjgTgSSDsQdnrLx49pbPTEeCV2m6t",
                "price_amount": 15,
                "price_currency": "usd",
                "pay_amount": 14.945,
                "pay_currency": "usdttrc20",
                "network": "trx",
                "valid_until": "2026-10-20T01:34:37.262Z"
            }

    import requests
    def fake_post(url, json=None, headers=None, timeout=None):
        return FakePaymentResponse()

    monkeypatch.setattr(requests, "post", fake_post)

    r = client.post("/v1/billing/agent-buy", json={"package_id": "pack_micro_25", "pay_currency": "usdttrc20"})
    assert r.status_code == 200
    data = r.json()
    assert data["payment_status"] == "waiting"
    assert data["pay_address"] == "TKfJPVjgTgSSDsQdnrLx49pbPTEeCV2m6t"
    assert data["pay_amount"] == 14.945
    assert data["pay_currency"] == "usdttrc20"
    assert data["network"] == "trx"
    assert data["credits_to_add"] == 25
    assert data["order_id"].startswith("np__cli_agent_")
    assert "poll check_status_url" in data["instructions"]

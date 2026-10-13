"""Polar.sh billing & webhook security tests: signature verification, fulfillment, idempotency."""
import base64
import hashlib
import hmac
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from fastapi.testclient import TestClient

import api.main as main
from billing.ledger import BillingLedger

TEST_WEBHOOK_SECRET = "whsec_dGVzdF9zZWNyZXRfa2V5XzEyMzQ1Njc4OQ=="  # base64 encoded secret

@pytest.fixture()
def client(tmp_path, monkeypatch):
    ledger = BillingLedger(str(tmp_path / "polar_ledger.json"))
    monkeypatch.setattr(main, "ledger", ledger)
    monkeypatch.setattr(main.polar_service, "ledger", ledger)
    monkeypatch.setattr(main.polar_service, "webhook_secret", TEST_WEBHOOK_SECRET)
    monkeypatch.setattr(main.polar_service, "access_token", "polar_at_test_123")
    return TestClient(main.app)

def sign_polar_webhook(raw_body: bytes, secret: str = TEST_WEBHOOK_SECRET) -> dict:
    webhook_id = f"msg_{int(time.time()*1000)}"
    webhook_timestamp = str(int(time.time()))
    to_sign = f"{webhook_id}.{webhook_timestamp}.".encode("utf-8") + raw_body
    
    secret_clean = secret[6:] if secret.startswith("whsec_") else secret
    secret_bytes = base64.b64decode(secret_clean)
    signature = base64.b64encode(hmac.new(secret_bytes, to_sign, hashlib.sha256).digest()).decode("utf-8")
    
    return {
        "webhook-id": webhook_id,
        "webhook-timestamp": webhook_timestamp,
        "webhook-signature": f"v1,{signature}"
    }

def test_polar_webhook_rejects_unsigned(client):
    body = {"type": "order.created", "data": {"id": "ord_123"}}
    r = client.post("/v1/billing/polar-webhook", json=body)
    assert r.status_code == 400

def test_polar_webhook_rejects_bad_signature(client):
    raw_body = json.dumps({"type": "order.created", "data": {"id": "ord_123"}}).encode("utf-8")
    headers = {
        "webhook-id": "msg_test",
        "webhook-timestamp": "12345678",
        "webhook-signature": "v1,invalid_signature"
    }
    r = client.post("/v1/billing/polar-webhook", content=raw_body, headers=headers)
    assert r.status_code == 400

def test_polar_webhook_credits_account_idempotently(client):
    main.ledger.create_account("cli_polar_user")
    order_event = {
        "type": "order.created",
        "data": {
            "id": "ord_order_999",
            "customer_email": "agency@miami-leads.com",
            "metadata": {
                "client_id": "cli_polar_user",
                "package_id": "pack_pro_200"
            }
        }
    }
    raw_body = json.dumps(order_event).encode("utf-8")
    headers = sign_polar_webhook(raw_body)

    # First fulfillment: must add 200 credits
    r1 = client.post("/v1/billing/polar-webhook", content=raw_body, headers=headers)
    assert r1.status_code == 200
    res1 = r1.json()
    assert res1["status"] == "PROCESSED"
    assert res1["credits_added"] == 200
    assert main.ledger.get_by_client_id("cli_polar_user").credits_balance == 200

    # Second fulfillment with same order id: must be idempotent (0 additional credits)
    r2 = client.post("/v1/billing/polar-webhook", content=raw_body, headers=headers)
    assert r2.status_code == 200
    res2 = r2.json()
    assert res2["status"] == "ALREADY_PROCESSED"
    assert res2["credits_added"] == 0
    assert main.ledger.get_by_client_id("cli_polar_user").credits_balance == 200

def test_multi_country_scan(client):
    main.ledger.create_account("demo_client", initial_credits=10)
    # Test USA high-ticket scan
    req = {
        "niche": "dental implants",
        "location": "Miami",
        "country_code": "US",
        "max_leads": 2,
        "min_score": 50,
        "auto_dispatch_webhooks": False
    }
    r = client.post("/v1/leads/trigger-scan", json=req)
    assert r.status_code == 200
    leads = r.json()
    assert len(leads) > 0
    assert leads[0]["location"]["city"] == "Miami"
    assert leads[0]["location"]["country"] == "US"

def test_polar_retrieve_and_fulfill(client, monkeypatch):
    main.ledger.create_account("cli_buyer_polar")
    
    # Mock Polar API response
    class FakeResponse:
        def __init__(self, data, status_code=200):
            self._data = data
            self.status_code = status_code
            self.text = json.dumps(data)
        def json(self):
            return self._data

    mock_state = {"status": "open"}
    def fake_get(url, headers=None, timeout=None):
        return FakeResponse({
            "id": "polar_sess_123",
            "status": mock_state["status"],
            "metadata": {
                "client_id": "cli_buyer_polar",
                "package_id": "pack_micro_15"
            },
            "customer_email": "buyer@polar.sh"
        })

    import requests
    monkeypatch.setattr(requests, "get", fake_get)

    # 1. Open / Pending session
    r1 = client.get("/v1/billing/session/polar_sess_123")
    assert r1.status_code == 200
    assert r1.json()["status"] == "PENDING"

    # 2. Paid / Confirmed session
    mock_state["status"] = "confirmed"
    r2 = client.get("/v1/billing/session/polar_sess_123")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["status"] == "PAID"
    assert data2["credits_added"] == 25
    assert main.ledger.get_by_client_id("cli_buyer_polar").credits_balance == 25

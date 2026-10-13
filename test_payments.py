"""Payment security tests: no free credits, signed webhooks only, idempotent fulfillment."""
import hashlib
import hmac
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["STRIPE_SECRET_KEY"] = ""          # payments NOT configured by default
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"

import pytest
from fastapi.testclient import TestClient

import api.main as main
from billing.ledger import BillingLedger
import billing.stripe_service as ss


@pytest.fixture()
def client(tmp_path, monkeypatch):
    ledger = BillingLedger(str(tmp_path / "ledger.json"))
    monkeypatch.setattr(main, "ledger", ledger)
    monkeypatch.setattr(main.stripe_service, "ledger", ledger)
    monkeypatch.setattr(main.stripe_service, "webhook_secret", "whsec_test_secret")
    monkeypatch.setattr(main.stripe_service, "api_key", "")
    monkeypatch.setattr(main.polar_service, "access_token", None)
    monkeypatch.setattr(main.nowpayments_service, "api_key", None)
    return TestClient(main.app)


def sign(payload: bytes, secret: str = "whsec_test_secret") -> str:
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def paid_event(session_id="cs_test_1", client_id="cli_abc", package_id="pack_micro_15"):
    return {
        "id": "evt_1",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": session_id, "object": "checkout.session", "payment_status": "paid",
            "client_reference_id": client_id,
            "metadata": {"client_id": client_id, "package_id": package_id, "credits": "999999"},
            "customer_details": {"email": "buyer@example.com"},
        }},
    }


# --- free-credit holes are closed -------------------------------------------
def test_paypal_activate_requires_admin(client):
    body = {"client_id": "x", "payer_email": "a@b.com", "package_id": "pack_pro_200"}
    assert client.post("/v1/billing/paypal-activate", json=body).status_code == 403
    assert client.post("/v1/billing/paypal-activate", json=body,
                       headers={"x-admin-token": "wrong"}).status_code == 403
    ok = client.post("/v1/billing/paypal-activate", json=body, headers={"x-admin-token": "test-admin-token"})
    assert ok.status_code == 200 and ok.json()["credits_added"] == 200


def test_topup_requires_admin(client):
    assert client.post("/v1/billing/topup-dev", json={"client_id": "x", "credits_to_add": 500}).status_code == 403


def test_admin_blocked_when_token_not_configured(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN")
    r = client.post("/v1/billing/topup-dev", json={"client_id": "x"}, headers={"x-admin-token": ""})
    assert r.status_code == 403


# --- webhook ------------------------------------------------------------------
def test_webhook_rejects_unsigned(client):
    r = client.post("/v1/billing/stripe-webhook", json=paid_event())
    assert r.status_code == 400
    assert main.ledger.get_by_client_id("cli_abc") is None


def test_webhook_rejects_bad_signature(client):
    payload = json.dumps(paid_event()).encode()
    r = client.post("/v1/billing/stripe-webhook", content=payload,
                    headers={"stripe-signature": sign(payload, "whsec_attacker")})
    assert r.status_code == 400


def test_webhook_credits_once_and_ignores_metadata_credits(client):
    main.ledger.create_account("cli_abc")
    payload = json.dumps(paid_event()).encode()
    headers = {"stripe-signature": sign(payload)}
    r1 = client.post("/v1/billing/stripe-webhook", content=payload, headers=headers)
    assert r1.status_code == 200 and r1.json()["status"] == "PROCESSED"
    # credits come from the server catalog (15), not from editable metadata (999999)
    assert main.ledger.get_by_client_id("cli_abc").credits_balance == 15
    r2 = client.post("/v1/billing/stripe-webhook", content=payload, headers=headers)
    assert r2.json()["status"] == "ALREADY_PROCESSED"
    assert main.ledger.get_by_client_id("cli_abc").credits_balance == 15


def test_unpaid_session_not_credited(client):
    ev = paid_event()
    ev["data"]["object"]["payment_status"] = "unpaid"
    payload = json.dumps(ev).encode()
    r = client.post("/v1/billing/stripe-webhook", content=payload, headers={"stripe-signature": sign(payload)})
    assert r.json()["status"] == "PENDING"
    assert main.ledger.get_by_client_id("cli_abc") is None


# --- buy / success flow -----------------------------------------------------
def test_buy_returns_503_when_payments_not_configured(client):
    r = client.post("/v1/billing/buy", json={"package_id": "pack_micro_15", "email": "a@b.com"})
    assert r.status_code == 503
    assert r.json()["detail"]["contact"] == "hola@nexusleadengine.io"


def test_buy_rejects_bad_package_and_bad_key(client):
    assert client.post("/v1/billing/buy", json={"package_id": "nope", "email": "a@b.com"}).status_code == 400
    r = client.post("/v1/billing/buy", json={"package_id": "pack_micro_15", "email": "a@b.com", "api_key": "sk_live_fake"})
    assert r.status_code == 401


def test_buy_creates_server_side_client_id(client, monkeypatch):
    monkeypatch.setattr(main.stripe_service, "api_key", "sk_test_123")
    captured = {}

    class FakeSession:
        url = "https://checkout.stripe.com/c/pay/cs_test_1"
        id = "cs_test_1"

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeSession()

    monkeypatch.setattr(ss.stripe.checkout.Session, "create", staticmethod(fake_create))
    r = client.post("/v1/billing/buy", json={"package_id": "pack_pro_200", "email": "buyer@example.com"})
    assert r.status_code == 200
    assert r.json()["checkout_url"].startswith("https://checkout.stripe.com")
    assert captured["metadata"]["client_id"].startswith("cli_")
    assert captured["customer_email"] == "buyer@example.com"
    assert captured["line_items"][0]["price_data"]["unit_amount"] == 6900
    assert "tu-dominio.com" not in captured["success_url"]


def test_session_endpoint_only_returns_key_when_stripe_says_paid(client, monkeypatch):
    monkeypatch.setattr(main.stripe_service, "api_key", "sk_test_123")
    main.ledger.create_account("cli_abc")
    state = {"status": "unpaid"}

    class FakeSession(dict):
        def to_dict(self):
            return dict(self)

    def fake_retrieve(sid):
        ev = paid_event(session_id=sid)["data"]["object"]
        ev["payment_status"] = state["status"]
        return FakeSession(ev)

    monkeypatch.setattr(ss.stripe.checkout.Session, "retrieve", staticmethod(fake_retrieve))

    r = client.get("/v1/billing/session/cs_test_1")
    assert r.json()["status"] == "PENDING" and "api_key" not in r.json()

    state["status"] = "paid"
    r = client.get("/v1/billing/session/cs_test_1")
    assert r.json()["status"] == "PAID"
    assert r.json()["api_key"] == main.ledger.get_by_client_id("cli_abc").api_key
    assert main.ledger.get_by_client_id("cli_abc").credits_balance == 15
    client.get("/v1/billing/session/cs_test_1")  # reload page: must not double credit
    assert main.ledger.get_by_client_id("cli_abc").credits_balance == 15


def test_pages_served(client):
    assert client.get("/billing/success?session_id=x").status_code == 200
    r = client.get("/billing/cancel", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/#pricing"
    assert "buyPack(" in client.get("/").text

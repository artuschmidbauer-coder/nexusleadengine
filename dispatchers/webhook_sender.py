import hmac
import hashlib
import json
import time
from typing import List, Dict, Any
import requests
from models.schema import EnrichedLead, WebhookSubscription

class WebhookDispatcher:
    """Dispatches enriched leads Machine-to-Machine (M2M) to client bots and CRMs."""

    def __init__(self):
        self._subscriptions: Dict[str, WebhookSubscription] = {}
        self._delivery_log: List[Dict[str, Any]] = []

    def register_subscriber(self, sub: WebhookSubscription) -> None:
        self._subscriptions[sub.client_id] = sub

    def list_subscribers(self) -> List[WebhookSubscription]:
        return list(self._subscriptions.values())

    def dispatch(self, lead: EnrichedLead) -> List[Dict[str, Any]]:
        results = []
        payload_bytes = lead.model_dump_json().encode("utf-8")

        for client_id, sub in self._subscriptions.items():
            if not sub.is_active:
                continue

            # Check min score requirement
            if lead.score < sub.min_score_threshold:
                continue

            # Check niche match
            niche_match = (
                "*" in sub.target_niches
                or any(n.lower() in lead.category.lower() for n in sub.target_niches)
            )
            if not niche_match:
                continue

            # Generate HMAC signature
            signature = hmac.new(
                sub.secret_key.encode("utf-8"),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "LeadStream-M2M-Agent/1.0",
                "X-Lead-Id": lead.lead_id,
                "X-Signature-SHA256": signature,
                "X-Timestamp": str(int(time.time()))
            }

            delivery_record = {
                "client_id": client_id,
                "endpoint_url": sub.endpoint_url,
                "lead_id": lead.lead_id,
                "timestamp": int(time.time()),
                "status": "PENDING",
                "response_code": None
            }

            try:
                # Deliver to client bot webhook
                resp = requests.post(
                    sub.endpoint_url,
                    data=payload_bytes,
                    headers=headers,
                    timeout=4
                )
                delivery_record["status"] = "SUCCESS" if resp.status_code < 300 else "FAILED"
                delivery_record["response_code"] = resp.status_code
            except Exception as e:
                delivery_record["status"] = "NETWORK_ERROR"
                delivery_record["error"] = str(e)

            self._delivery_log.append(delivery_record)
            results.append(delivery_record)

        return results

    def get_logs(self) -> List[Dict[str, Any]]:
        return self._delivery_log

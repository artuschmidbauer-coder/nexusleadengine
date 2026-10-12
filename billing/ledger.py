import json
import os
import uuid
from typing import Dict, Optional
from models.schema import ApiKeyAccount

LEDGER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "billing_ledger.json")

class BillingLedger:
    """Persistent ledger managing client API keys and credit balances."""

    def __init__(self, path: str = LEDGER_PATH):
        self.path = path
        self._accounts: Dict[str, ApiKeyAccount] = {}
        self._client_to_key: Dict[str, str] = {}
        self._load()

        # Seed default test client if empty
        if not self._accounts:
            default_acc = self.create_account("demo_client", initial_credits=10)
            print(f"💳 [BillingLedger] Creada cuenta demo inicial: {default_acc.client_id} (API Key: {default_acc.api_key}) con 10 créditos gratis.")

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.values():
                        acc = ApiKeyAccount(**item)
                        self._accounts[acc.api_key] = acc
                        self._client_to_key[acc.client_id] = acc.api_key
            except Exception as e:
                print(f"Error loading ledger: {e}")

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                data = {k: v.model_dump() for k, v in self._accounts.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving ledger: {e}")

    # --- Idempotency: payment sessions already credited ---------------------
    @property
    def _sessions_path(self) -> str:
        return self.path.replace(".json", "_sessions.json")

    def _load_sessions(self) -> set:
        if not hasattr(self, "_processed_sessions"):
            self._processed_sessions = set()
            if os.path.exists(self._sessions_path):
                try:
                    with open(self._sessions_path, "r", encoding="utf-8") as f:
                        self._processed_sessions = set(json.load(f))
                except Exception as e:
                    print(f"Error loading processed sessions: {e}")
        return self._processed_sessions

    def is_session_processed(self, session_id: str) -> bool:
        return session_id in self._load_sessions()

    def mark_session_processed(self, session_id: str) -> None:
        sessions = self._load_sessions()
        sessions.add(session_id)
        try:
            with open(self._sessions_path, "w", encoding="utf-8") as f:
                json.dump(sorted(sessions), f)
        except Exception as e:
            print(f"Error saving processed sessions: {e}")

    def create_account(self, client_id: str, initial_credits: int = 0) -> ApiKeyAccount:
        if client_id in self._client_to_key:
            return self._accounts[self._client_to_key[client_id]]

        api_key = f"sk_live_{uuid.uuid4().hex}"
        acc = ApiKeyAccount(
            api_key=api_key,
            client_id=client_id,
            credits_balance=initial_credits,
            total_purchased=initial_credits
        )
        self._accounts[api_key] = acc
        self._client_to_key[client_id] = api_key
        self._save()
        return acc

    def get_by_api_key(self, api_key: str) -> Optional[ApiKeyAccount]:
        return self._accounts.get(api_key)

    def get_by_client_id(self, client_id: str) -> Optional[ApiKeyAccount]:
        key = self._client_to_key.get(client_id)
        return self._accounts.get(key) if key else None

    def add_credits(self, client_id: str, credits: int) -> ApiKeyAccount:
        acc = self.get_by_client_id(client_id)
        if not acc:
            acc = self.create_account(client_id)

        acc.credits_balance += credits
        acc.total_purchased += credits
        self._save()
        return acc

    def deduct_credits(self, api_key: str, count: int = 1) -> bool:
        acc = self.get_by_api_key(api_key)
        if not acc or acc.credits_balance < count:
            return False

        acc.credits_balance -= count
        acc.total_consumed += count
        self._save()
        return True

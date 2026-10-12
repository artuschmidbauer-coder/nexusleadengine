from typing import Optional
from fastapi import Header, HTTPException, status
from models.schema import ApiKeyAccount
from .ledger import BillingLedger

def get_or_create_account(ledger: BillingLedger, api_key: Optional[str] = None, client_id: Optional[str] = None) -> ApiKeyAccount:
    if api_key:
        acc = ledger.get_by_api_key(api_key)
        if acc:
            return acc

    if client_id:
        acc = ledger.get_by_client_id(client_id)
        if acc:
            return acc
        return ledger.create_account(client_id, initial_credits=10)

    # Fallback to demo client
    return ledger.get_by_client_id("demo_client")

def deduct_credit_for_delivery(ledger: BillingLedger, api_key: str, leads_count: int = 1) -> ApiKeyAccount:
    acc = ledger.get_by_api_key(api_key)
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida o no registrada."
        )

    if acc.credits_balance < leads_count:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "INSUFFICIENT_CREDITS",
                "message": f"Saldo insuficiente. Tienes {acc.credits_balance} créditos y necesitas {leads_count}.",
                "reload_url": "POST /v1/billing/create-checkout",
                "client_id": acc.client_id
            }
        )

    ledger.deduct_credits(api_key, leads_count)
    return acc

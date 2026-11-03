"""Opt-in sandbox webhook, isolated from commercial accounts and credentials."""
from contextlib import closing
import logging
import os
from pathlib import Path
import sqlite3
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from data.database import DATABASE_PATH
from services.billing_service import BillingError, billing_config, process_webhook


router = APIRouter()
logger = logging.getLogger("uvicorn.error")


def sandbox_configuration(environment, production_database):
    database = Path(production_database).parent / "cenlio-stripe-qa.sqlite"
    if (database.resolve() == Path(production_database).resolve()
            or database.is_symlink() or not database.is_file()
            or database.stat().st_nlink != 1):
        raise BillingError("Base de test isolée indisponible.")
    env = {
        "IMMORADAR_BILLING_ENABLED": "1",
        "IMMORADAR_BILLING_MODE": "test",
        "IMMORADAR_STRIPE_AUTOMATIC_TAX_ENABLED": "0",
        "IMMORADAR_PUBLIC_URL": environment.get("IMMORADAR_PUBLIC_URL", ""),
        "STRIPE_SECRET_KEY": environment.get("STRIPE_TEST_SECRET_KEY", ""),
        "STRIPE_WEBHOOK_SECRET": environment.get("STRIPE_TEST_WEBHOOK_SECRET", ""),
        "STRIPE_PREMIUM_PRICE_ID": environment.get("STRIPE_TEST_PREMIUM_PRICE_ID", ""),
    }
    billing_config(env)  # Reject live keys or missing test credentials.
    return database, env


def handle_sandbox_event(payload, signature):
    database, env = sandbox_configuration(os.environ, DATABASE_PATH)
    result = process_webhook(payload, signature, database, environment=env)
    # Aggregate proof in private server logs; no payloads, identities or secrets.
    with closing(sqlite3.connect(database)) as connection:
        total, premium = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(status IN ('active','trialing') AND access_until>?),0) "
            "FROM billing_accounts WHERE mode='test'", (int(time.time()),)
        ).fetchone()
    logger.info("Cenlio sandbox webhook: %s; premium_accounts=%s; free_accounts=%s", result, premium, total-premium)
    return result


@router.post("/stripe/test-webhook")
async def sandbox_webhook(request: Request):
    if os.environ.get("IMMORADAR_STRIPE_QA_WEBHOOK_ENABLED") != "1":
        return JSONResponse({"error": "not_found"}, status_code=404)
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > 1_000_000:
            return JSONResponse({"error": "payload_too_large"}, status_code=413)
    try:
        result = await run_in_threadpool(handle_sandbox_event, bytes(payload), request.headers.get("stripe-signature", ""))
    except BillingError as error:
        invalid = str(error) in {"Signature de paiement invalide.", "Mode de paiement incompatible."}
        return JSONResponse({"error": "invalid_event" if invalid else "processing_unavailable"}, status_code=400 if invalid else 503)
    except Exception:
        return JSONResponse({"error": "processing_unavailable"}, status_code=503)
    return {"status": result}

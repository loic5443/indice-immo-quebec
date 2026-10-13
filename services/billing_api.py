"""Independent HTTPS webhook service; shares the app's persistent database."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from data.database import DATABASE_PATH, initialize_database
from services.billing_service import BillingError, process_webhook


@asynccontextmanager
async def lifespan(app):
    initialize_database(DATABASE_PATH)
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/stripe/webhook")
async def webhook(request: Request):
    # Bound body buffering even when Content-Length is omitted.
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > 1_000_000:
            return JSONResponse({"error": "payload_too_large"}, status_code=413)
    try:
        result = await run_in_threadpool(process_webhook, bytes(payload), request.headers.get("stripe-signature", ""), DATABASE_PATH)
    except BillingError as error:
        invalid = str(error) in {"Signature de paiement invalide.", "Mode de paiement incompatible."}
        # Provider/DB failures must be retried by Stripe, not acknowledged.
        return JSONResponse({"error": "invalid_event" if invalid else "processing_unavailable"}, status_code=400 if invalid else 503)
    except Exception:
        return JSONResponse({"error": "processing_unavailable"}, status_code=503)
    return {"status": result}

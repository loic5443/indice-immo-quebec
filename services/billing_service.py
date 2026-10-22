"""Stripe subscription boundary: a browser redirect never grants Premium.

Only Stripe objects retrieved by the server can change subscription rights.
No card details, full webhook payloads or provider exception messages are stored.
"""

import hashlib
import os
import time
import uuid
from contextlib import closing
from dataclasses import dataclass
from urllib.parse import urlsplit

import stripe

from repositories.sqlite_repository import SQLiteRepository


class BillingError(Exception):
    """Safe message suitable for a user; never wrap raw provider errors."""


@dataclass(frozen=True)
class BillingConfig:
    secret_key: str
    webhook_secret: str
    price_id: str
    app_url: str
    mode: str


def billing_config(environment=None):
    env = os.environ if environment is None else environment
    if env.get("IMMORADAR_BILLING_ENABLED") != "1":
        return None
    mode = env.get("IMMORADAR_BILLING_MODE", "test")
    key = env.get("STRIPE_SECRET_KEY", "")
    hook = env.get("STRIPE_WEBHOOK_SECRET", "")
    price = env.get("STRIPE_PREMIUM_PRICE_ID", "")
    url = env.get("IMMORADAR_PUBLIC_URL", "").rstrip("/")
    parsed = urlsplit(url)
    # Restricted keys are preferred; claimable sandboxes issue rkcs_test_ keys.
    # A claimable sandbox key must never be accepted for live billing.
    key_prefixes = (f"sk_{mode}_", f"rk_{mode}_")
    if mode == "test":
        key_prefixes += ("rkcs_test_",)
    if (mode not in {"test", "live"} or not key.startswith(key_prefixes)
            or not hook.startswith("whsec_") or not price.startswith("price_")
            or parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise BillingError("La configuration des abonnements est incomplète. Aucun paiement n’est proposé.")
    return BillingConfig(key, hook, price, url, mode)


def _provider(config):
    return stripe.StripeClient(config.secret_key, max_network_retries=2, http_client=stripe.RequestsClient(timeout=10))


def _call(operation, *args, **kwargs):
    try:
        result = operation(*args, **kwargs)
        return result.to_dict() if isinstance(result, stripe.StripeObject) else result
    except stripe.StripeError:
        raise BillingError("Le service de paiement est momentanément indisponible. Réessayez plus tard.") from None


def _id(value):
    return value if isinstance(value, str) else (value or {}).get("id")


def _mode_matches(obj, config):
    return obj.get("livemode") is (config.mode == "live")


def _price(config, client):
    price = _call(client.v1.prices.retrieve, config.price_id)
    recurring = price.get("recurring") or {}
    if (not _mode_matches(price, config) or not price.get("active")
            or price.get("currency") != "cad" or recurring.get("interval") != "month"
            or recurring.get("interval_count") != 1 or not isinstance(price.get("unit_amount"), int)
            or price["unit_amount"] <= 0 or price.get("type") != "recurring"):
        raise BillingError("L’offre Premium n’est pas encore disponible à l’achat.")
    return price


def premium_offer(environment=None, client=None):
    config = billing_config(environment)
    if config is None:
        return None
    price = _price(config, client or _provider(config))
    amount = f"{price['unit_amount'] / 100:.2f}".replace(".", ",")
    return {"price_label": f"{amount} $ CA / mois", "mode": config.mode,
            "tax_inclusive": price.get("tax_behavior") == "inclusive"}


def billing_account(user_id, database_path):
    with closing(SQLiteRepository(database_path)._connect()) as connection:
        row = connection.execute("SELECT * FROM billing_accounts WHERE user_id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def effective_plan(user_id, legacy_plan, database_path, now=None, environment=None):
    """Commercial accounts cannot inherit unverified beta Premium rights."""
    env = os.environ if environment is None else environment
    account = billing_account(user_id, database_path)
    if account is None:
        return "free" if env.get("IMMORADAR_BILLING_ENABLED") == "1" else legacy_plan
    if account["mode"] != env.get("IMMORADAR_BILLING_MODE", "test"):
        return "free"
    paid = account["status"] in {"active", "trialing"} and account["access_until"] > (time.time() if now is None else now)
    return "premium" if paid else "free"


def create_checkout(user_id, database_path, environment=None, client=None):
    config = billing_config(environment)
    if config is None:
        raise BillingError("Les abonnements ne sont pas encore ouverts.")
    client = client or _provider(config)
    _price(config, client)
    # Serialize attempts for one account, including provider idempotency keys.
    with closing(SQLiteRepository(database_path)._connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        user = connection.execute("SELECT id,email FROM users WHERE id=?", (user_id,)).fetchone()
        if user is None:
            raise BillingError("Connectez-vous pour choisir Premium.")
        account = connection.execute("SELECT * FROM billing_accounts WHERE user_id=?", (user_id,)).fetchone()
        if account is None:
            customer = _call(client.v1.customers.create,
                             {"email": user["email"], "metadata": {"immoradar_user_id": str(user_id)}},
                             options={"idempotency_key": f"immoradar-customer-{config.mode}-{user_id}"})
            connection.execute("INSERT INTO billing_accounts(user_id,customer_id,mode) VALUES(?,?,?)", (user_id, customer["id"], config.mode))
            customer_id = customer["id"]
        else:
            if account["mode"] != config.mode:
                raise BillingError("Le compte de test doit être séparé du compte de production.")
            customer_id = account["customer_id"]
        # Check Stripe too: a delayed webhook must not allow a second purchase.
        subscriptions = _call(client.v1.subscriptions.list, {"customer": customer_id, "status": "all", "limit": 100})
        if subscriptions.get("has_more") or any(s.get("status") not in {"canceled", "incomplete_expired"}
                                                for s in subscriptions.get("data", [])):
            raise BillingError("Un abonnement existe déjà. Gérez-le depuis votre espace Premium.")
        attempt = connection.execute("SELECT * FROM billing_checkouts WHERE user_id=?", (user_id,)).fetchone()
        if attempt and attempt["session_id"]:
            session = _call(client.v1.checkout.sessions.retrieve, attempt["session_id"])
            if session.get("status") == "open":
                connection.commit()
                return _safe_url(session.get("url"), "checkout.stripe.com")
            if session.get("status") == "complete":
                raise BillingError("Votre paiement est en cours de vérification. Actualisez votre abonnement.")
        # Persist the key before the API call. A timeout can safely reuse it.
        if not attempt or attempt["session_id"] or attempt["created_at"] < time.time() - 23 * 3600:
            request_key = str(uuid.uuid4())
            connection.execute("INSERT INTO billing_checkouts(user_id,request_key,created_at) VALUES(?,?,?) "
                               "ON CONFLICT(user_id) DO UPDATE SET request_key=excluded.request_key,session_id=NULL,created_at=excluded.created_at",
                               (user_id, request_key, int(time.time())))
        else:
            request_key = attempt["request_key"]
        connection.commit()
        # Keep the flow tag stable when an idempotent request is retried.
        flow_suffix = "".join(chr(97 + byte % 26) for byte in hashlib.sha256(request_key.encode()).digest()[:8])
        session = _call(client.v1.checkout.sessions.create, {
            "mode": "subscription", "customer": customer_id,
            "locale": "fr-CA", "integration_identifier": "immoradar-premium-" + flow_suffix,
            "client_reference_id": str(user_id), "line_items": [{"price": config.price_id, "quantity": 1}],
            "subscription_data": {"metadata": {"immoradar_user_id": str(user_id)}},
            "success_url": config.app_url + "/?billing=success&session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": config.app_url + "/?billing=cancel",
            # Customers are created before Checkout without an address. Tax must
            # use and save the billing address collected on the hosted page.
            "billing_address_collection": "required", "customer_update": {"address": "auto"},
            "automatic_tax": {"enabled": True},
        }, options={"idempotency_key": request_key})
        with connection:
            connection.execute("UPDATE billing_checkouts SET session_id=? WHERE user_id=? AND request_key=?",
                               (session["id"], user_id, request_key))
        return _safe_url(session.get("url"), "checkout.stripe.com")


def _safe_url(url, hostname):
    parsed = urlsplit(url or "")
    if parsed.scheme != "https" or parsed.hostname != hostname or parsed.username or parsed.password:
        raise BillingError("Le lien de paiement n’a pas pu être créé. Réessayez plus tard.")
    return url


def create_portal(user_id, database_path, environment=None, client=None):
    config = billing_config(environment)
    if config is None:
        raise BillingError("Les abonnements ne sont pas encore ouverts.")
    account = billing_account(user_id, database_path)
    if account is None or account["mode"] != config.mode:
        raise BillingError("Aucun abonnement n’est associé à votre compte.")
    client = client or _provider(config)
    session = _call(client.v1.billing_portal.sessions.create,
                    {"customer": account["customer_id"], "return_url": config.app_url + "/?billing=portal", "locale": "fr-CA"})
    return _safe_url(session.get("url"), "billing.stripe.com")


def _save_subscription(connection, subscription, config):
    """Validate both ownership and the purchased price before granting rights."""
    customer_id = _id(subscription.get("customer"))
    account = connection.execute("SELECT * FROM billing_accounts WHERE customer_id=?", (customer_id,)).fetchone()
    if account is None:
        return False  # Another Stripe product/customer is outside this app.
    if (account["mode"] != config.mode or not _mode_matches(subscription, config)
            or str(subscription.get("metadata", {}).get("immoradar_user_id")) != str(account["user_id"])):
        raise BillingError("L’abonnement ne correspond pas à ce compte.")
    items = (subscription.get("items") or {}).get("data", [])
    eligible = len(items) == 1 and _id(items[0].get("price")) == config.price_id and items[0].get("quantity") == 1
    status = subscription.get("status", "unknown") if eligible else "ineligible"
    until = int(items[0].get("current_period_end") or subscription.get("current_period_end") or 0) if eligible else 0
    # Do not let an old canceled subscription overwrite a replacement.
    if account["subscription_id"] and account["subscription_id"] != subscription["id"]:
        if status in {"canceled", "incomplete_expired"}:
            return False
        if account["status"] not in {"none", "canceled", "incomplete_expired"}:
            raise BillingError("Un autre abonnement est déjà associé au compte.")
    connection.execute("UPDATE billing_accounts SET subscription_id=?,status=?,access_until=?,cancel_at_period_end=?,updated_at=? WHERE user_id=?",
                       (subscription["id"], status, until, int(bool(subscription.get("cancel_at_period_end"))), int(time.time()), account["user_id"]))
    if status in {"active", "trialing", "canceled", "incomplete_expired"}:
        connection.execute("DELETE FROM billing_checkouts WHERE user_id=?", (account["user_id"],))
    return True


def confirm_checkout(user_id, session_id, database_path, environment=None, client=None):
    config = billing_config(environment)
    if config is None:
        raise BillingError("Les abonnements ne sont pas encore ouverts.")
    client = client or _provider(config)
    session = _call(client.v1.checkout.sessions.retrieve, session_id)
    account = billing_account(user_id, database_path)
    if (account is None or account["mode"] != config.mode or not _mode_matches(session, config) or session.get("mode") != "subscription"
            or session.get("client_reference_id") != str(user_id)
            or _id(session.get("customer")) != account["customer_id"]):
        raise BillingError("Ce paiement ne correspond pas à votre compte.")
    if session.get("status") != "complete" or session.get("payment_status") not in {"paid", "no_payment_required"}:
        return False
    subscription_id = _id(session.get("subscription"))
    if not subscription_id:
        return False
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        subscription = _call(client.v1.subscriptions.retrieve, subscription_id)
        _save_subscription(connection, subscription, config)
    return effective_plan(user_id, "free", database_path, environment=environment) == "premium"


def refresh_subscription(user_id, database_path, environment=None, client=None):
    config = billing_config(environment)
    account = billing_account(user_id, database_path)
    if config is None or not account:
        return False
    if account["mode"] != config.mode:
        raise BillingError("Le compte de test doit être séparé du compte de production.")
    client = client or _provider(config)
    if account["subscription_id"]:
        with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            subscription = _call(client.v1.subscriptions.retrieve, account["subscription_id"])
            _save_subscription(connection, subscription, config)
    else:
        subscriptions = _call(client.v1.subscriptions.list, {"customer": account["customer_id"], "status": "all", "limit": 100})
        for subscription in subscriptions.get("data", []):
            if subscription.get("status") not in {"canceled", "incomplete_expired"}:
                with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
                    _save_subscription(connection, subscription, config)
                break
    return effective_plan(user_id, "free", database_path, environment=environment) == "premium"


def process_webhook(payload, signature, database_path, environment=None, client=None):
    config = billing_config(environment)
    if config is None:
        raise BillingError("Les abonnements ne sont pas encore ouverts.")
    try:
        event = stripe.Webhook.construct_event(payload, signature, config.webhook_secret).to_dict()
    except (ValueError, stripe.SignatureVerificationError):
        raise BillingError("Signature de paiement invalide.") from None
    if not _mode_matches(event, config):
        raise BillingError("Mode de paiement incompatible.")
    client = client or _provider(config)
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("SELECT 1 FROM billing_events WHERE event_id=?", (event["id"],)).fetchone():
            return "duplicate"
        obj = event["data"]["object"]
        kind = event["type"]
        subscription_id = None
        if kind.startswith("customer.subscription."):
            subscription_id = obj.get("id")
        elif kind in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            subscription_id = _id(obj.get("subscription"))
        elif kind in {"invoice.paid", "invoice.payment_failed", "invoice.payment_action_required"}:
            subscription_id = _id(obj.get("subscription")) or _id((obj.get("parent") or {}).get("subscription_details", {}).get("subscription"))
        if subscription_id:
            # Retrieve current state, rather than trusting an out-of-order event.
            subscription = _call(client.v1.subscriptions.retrieve, subscription_id)
            _save_subscription(connection, subscription, config)
        connection.execute("INSERT INTO billing_events VALUES(?,?,?)", (event["id"], kind, int(time.time())))
    return "processed"

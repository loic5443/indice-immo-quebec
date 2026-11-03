"""Explicit operator preflight: configure providers and expire an unpaid checkout."""
import secrets

import stripe

from services.billing_service import _provider, billing_config, premium_offer


def _data(value):
    return value.to_dict() if isinstance(value, stripe.StripeObject) else value


def prepare_launch(environment, client=None):
    stage = "configuration"
    customer_id = session_id = None
    report = {"status": "blocked", "stage": stage}
    try:
        env = dict(environment)
        env.update(IMMORADAR_BILLING_ENABLED="1", IMMORADAR_BILLING_MODE="live")
        config = billing_config(env)
        client = client or _provider(config)
        stage = "price"
        offer = premium_offer(env, client)
        if offer["price_label"] != "14,99 $ CA / mois":
            raise ValueError("Unexpected launch price")
        stage = "portal_configuration"
        portal_id = env["STRIPE_LAUNCH_PORTAL_ID"]
        stage = "portal_read"
        portal = _data(client.v1.billing_portal.configurations.retrieve(portal_id))
        stage = "portal_validation"
        if (not portal.get("livemode") or not portal.get("active") or not portal.get("is_default")
                or not portal["features"]["subscription_cancel"]["enabled"]
                or portal["features"]["subscription_cancel"]["mode"] != "at_period_end"):
            raise ValueError("Unexpected portal configuration")
        stage = "portal_links"
        client.v1.billing_portal.configurations.update(portal_id, {
            "business_profile": {"headline": "Cenlio — gérer mon abonnement",
                                 "terms_of_service_url": config.app_url + "/conditions",
                                 "privacy_policy_url": config.app_url + "/confidentialite"},
            "default_return_url": config.app_url + "/?billing=portal"})
        # Check reads required by the refund/dispute object graph, without logging data.
        stage = "risk_api_permissions"
        denied_reads = []
        for resource, operation in (("charges", client.v1.charges.list),
                                     ("invoice_payments", client.v1.invoice_payments.list),
                                     ("invoices", client.v1.invoices.list)):
            try:
                operation({"limit": 1})
            except stripe.StripeError as error:
                denied_reads.append({"resource": resource, "http_status": error.http_status})
        if denied_reads:
            return {"status": "blocked", "stage": stage, "required_reads": denied_reads}
        # Endpoint administration is done by the account owner or operator, not
        # by granting webhook-management permission to the application key.
        if env.get("CENLIO_LIVE_WEBHOOK_EVENTS_VERIFIED") != "1":
            return {"status": "blocked", "stage": "webhook_events_not_verified"}
        stage = "customer_and_portal"
        customer = client.v1.customers.create({"name": "Cenlio — vérification technique",
            "metadata": {"purpose": "cenlio_launch_probe"}})
        customer_id = customer["id"]
        portal_session = _data(client.v1.billing_portal.sessions.create({"customer": customer_id,
            "return_url": config.app_url + "/", "locale": "fr-CA"}))
        if not portal_session.get("livemode"):
            raise ValueError("Wrong portal mode")
        stage = "checkout"
        checkout = _data(client.v1.checkout.sessions.create({
            "mode": "subscription", "customer": customer_id, "locale": "fr-CA",
            "integration_identifier": "cenlio-launch-" + "".join(secrets.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(8)),
            "line_items": [{"price": config.price_id, "quantity": 1}],
            "billing_address_collection": "required", "customer_update": {"address": "auto"},
            "automatic_tax": {"enabled": config.automatic_tax},
            "success_url": config.app_url + "/?billing=success&session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": config.app_url + "/?billing=cancel"}))
        session_id = checkout["id"]
        if not checkout.get("livemode") or checkout.get("status") != "open":
            raise ValueError("Wrong checkout mode")
        stage = "expire_unpaid_checkout"
        expired = _data(client.v1.checkout.sessions.expire(session_id))
        if expired.get("status") != "expired":
            raise ValueError("Checkout not expired")
        session_id = None
        report = {"status": "ready", "stage": "complete", "price": "14.99 CAD/month", "charged": False}
    except stripe.StripeError as error:
        report = {"status": "blocked", "stage": stage, "http_status": error.http_status}
    except Exception as error:
        report = {"status": "blocked", "stage": stage, "error_type": type(error).__name__}
    finally:
        if client and session_id:
            try:
                client.v1.checkout.sessions.expire(session_id)
            except Exception:
                report = {"status": "blocked", "stage": "checkout_cleanup"}
        if client and customer_id:
            try:
                client.v1.customers.delete(customer_id)
            except Exception:
                report = {"status": "blocked", "stage": "customer_cleanup"}
    return report

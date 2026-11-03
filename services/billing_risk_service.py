"""Resolve risk events through Stripe's invoice graph into an operator queue."""
from contextlib import closing
import time

from repositories.sqlite_repository import SQLiteRepository


RISK_EVENTS = {"charge.refunded", "charge.dispute.created", "radar.early_fraud_warning.created"}


def affected_subscriptions(kind, obj, client, config):
    from services.billing_service import BillingError, _call, _id, _mode_matches
    charge_id = obj.get("id") if kind == "charge.refunded" else _id(obj.get("charge"))
    charge = _call(client.v1.charges.retrieve, charge_id) if charge_id else {}
    if charge and not _mode_matches(charge, config):
        raise BillingError("Mode de paiement incompatible.")
    invoice_ids = set()
    if _id(charge.get("invoice")):
        invoice_ids.add(_id(charge["invoice"]))  # Legacy API versions.
    else:
        intent = _id(charge.get("payment_intent")) or _id(obj.get("payment_intent"))
        if intent:
            payments = _call(client.v1.invoice_payments.list, {
                "payment": {"type": "payment_intent", "payment_intent": intent}, "limit": 100})
            if payments.get("has_more"):
                raise BillingError("Le paiement nécessite une vérification supplémentaire.")
            invoice_ids.update(_id(p.get("invoice")) for p in payments.get("data", []) if _id(p.get("invoice")))
    subscriptions = set()
    for invoice_id in invoice_ids:
        invoice = _call(client.v1.invoices.retrieve, invoice_id)
        if not _mode_matches(invoice, config):
            raise BillingError("Mode de paiement incompatible.")
        subscription = _id(invoice.get("subscription")) or _id(
            (invoice.get("parent") or {}).get("subscription_details", {}).get("subscription"))
        if subscription:
            subscriptions.add(subscription)
    return subscriptions


def open_reviews(actor_id, database_path):
    from services.beta_service import _admin
    _admin(actor_id, database_path)
    with closing(SQLiteRepository(database_path)._connect()) as connection:
        return [dict(row) for row in connection.execute(
            "SELECT * FROM billing_risk_reviews WHERE resolved_at IS NULL ORDER BY created_at DESC LIMIT 100")]


def resolve_review(actor_id, database_path, event_id, subscription_id):
    from services.beta_service import _admin
    _admin(actor_id, database_path)
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute("UPDATE billing_risk_reviews SET resolved_at=?,resolved_by=? "
                           "WHERE event_id=? AND subscription_id=? AND resolved_at IS NULL",
                           (int(time.time()), actor_id, event_id, subscription_id))
        connection.execute("INSERT INTO admin_audit_log(actor_id,action,metadata) VALUES(?,?,?)",
                           (actor_id, "billing_risk_review_resolved", '{"reviewed_in_stripe":true}'))

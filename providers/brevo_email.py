"""Optional Brevo transport. It remains inert until local configuration is enabled."""

from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


BREVO_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoUnavailable(RuntimeError):
    """Raised before any transport when local delivery is not explicitly enabled."""


def delivery_status(environment: dict[str, str] | None = None) -> str:
    """Return a non-sensitive status; never expose configuration values."""

    environment = environment or os.environ
    if environment.get("IMMORADAR_ALERT_DELIVERY_ENABLED", "").strip().lower() != "true":
        return "disabled"
    if not environment.get("BREVO_API_KEY", "").strip() or not environment.get("BREVO_SENDER_EMAIL", "").strip():
        return "not_configured"
    return "ready"


def send_email(recipient: str, subject: str, html_content: str, *, environment: dict[str, str] | None = None, opener=urlopen) -> None:
    """Send one explicitly consented email; callers must never log its inputs."""

    environment = environment or os.environ
    if delivery_status(environment) != "ready":
        raise BrevoUnavailable("La livraison courriel n’est pas configurée localement.")
    payload = json.dumps({
        "sender": {"email": environment["BREVO_SENDER_EMAIL"], "name": "ImmoRadar"},
        "to": [{"email": recipient}], "subject": subject, "htmlContent": html_content,
    }).encode("utf-8")
    request = Request(BREVO_URL, data=payload, method="POST", headers={
        "accept": "application/json", "content-type": "application/json", "api-key": environment["BREVO_API_KEY"],
    })
    with opener(request, timeout=10) as response:
        if not 200 <= int(response.status) < 300:
            raise BrevoUnavailable("Le fournisseur de courriel a refusé la demande.")

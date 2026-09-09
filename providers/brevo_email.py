"""Optional Brevo transport. It remains inert until local configuration is enabled."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BREVO_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_ACCOUNT_URL = "https://api.brevo.com/v3/account"


class BrevoUnavailable(RuntimeError):
    """Raised before any transport when local delivery is not explicitly enabled."""


def delivery_status(environment: dict[str, str] | None = None) -> str:
    """Return a non-sensitive status; never expose configuration values."""

    # An explicit empty mapping is meaningful in tests and must never fall
    # back to the local process environment (which may contain real keys).
    environment = environment if environment is not None else os.environ
    if environment.get("IMMORADAR_ALERT_DELIVERY_ENABLED", "").strip().lower() != "true":
        return "disabled"
    if not environment.get("BREVO_API_KEY", "").strip() or not environment.get("BREVO_SENDER_EMAIL", "").strip():
        return "not_configured"
    return "ready"


def verify_delivery_configuration(
    environment: dict[str, str] | None = None, *, opener=urlopen,
) -> str:
    """Check Brevo credentials only after an explicit user action.

    The check calls Brevo's account endpoint, never sends an email, and
    returns categorical outcomes only.  It intentionally exposes neither a
    key, an account record nor a provider response body.
    """

    status = delivery_status(environment)
    if status != "ready":
        return status
    environment = environment if environment is not None else os.environ
    request = Request(
        BREVO_ACCOUNT_URL,
        headers={"accept": "application/json", "api-key": environment["BREVO_API_KEY"]},
    )
    try:
        with opener(request, timeout=10) as response:
            return "verified" if 200 <= int(response.status) < 300 else "provider_unavailable"
    except HTTPError as error:
        return "credentials_rejected" if error.code in {401, 403} else "provider_unavailable"
    except URLError:
        return "provider_unavailable"
    except OSError:
        return "transport_error"


def send_email(recipient: str, subject: str, html_content: str, *, environment: dict[str, str] | None = None, opener=urlopen) -> None:
    """Send one explicitly consented email; callers must never log its inputs."""

    environment = environment if environment is not None else os.environ
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

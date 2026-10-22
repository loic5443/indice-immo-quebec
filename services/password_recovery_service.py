"""Single-use emailed recovery tokens, hashed at rest and invalidating sessions."""
import hashlib
import os
import secrets
import time
from contextlib import closing
from html import escape
from urllib.parse import urlsplit

from providers.brevo_email import send_email
from repositories.sqlite_repository import SQLiteRepository
from services.auth_attempt_service import claim_attempt, identity_hash
from services.auth_service import _hash_password


REQUEST_MESSAGE = "Si un compte correspond à cette adresse, un lien de récupération vous sera envoyé. Vérifiez aussi vos indésirables."
INVALID_MESSAGE = "Ce lien est invalide, expiré ou déjà utilisé. Demandez un nouveau lien."


def recovery_ready(environment=None):
    env = os.environ if environment is None else environment
    url = urlsplit(env.get("IMMORADAR_PUBLIC_URL", ""))
    return (env.get("IMMORADAR_AUTH_EMAIL_ENABLED") == "1" and bool(env.get("BREVO_API_KEY"))
            and bool(env.get("BREVO_SENDER_EMAIL")) and url.scheme == "https" and bool(url.hostname)
            and not url.username and not url.password and not url.query and not url.fragment)


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def request_recovery(email, database_path, environment=None, sender=send_email, now=None):
    env = os.environ if environment is None else environment
    if not recovery_ready(env):
        return False, "La récupération par courriel n’est pas disponible pour le moment."
    now = int(time.time() if now is None else now)
    normalized = str(email).strip().lower()
    if not claim_attempt(normalized, "reset", database_path, now):
        return True, REQUEST_MESSAGE
    user = SQLiteRepository(database_path).get_user_by_email(normalized)
    if user is None:
        return True, REQUEST_MESSAGE
    token = secrets.token_urlsafe(32)
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute("DELETE FROM password_reset_tokens WHERE expires_at < ? OR user_id=?", (now, user["id"]))
        connection.execute("INSERT INTO password_reset_tokens(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)", (_hash(token), user["id"], now + 1800, now))
    url = env["IMMORADAR_PUBLIC_URL"].rstrip("/") + "/?reset_token=" + token
    # Transactional recovery is independent of optional alert/marketing consent.
    delivery_env = {**env, "IMMORADAR_ALERT_DELIVERY_ENABLED": "true"}
    try:
        sender(user["email"], "Réinitialisez votre mot de passe Cenlio",
               "<p>Une demande de récupération a été faite pour votre compte Cenlio.</p>"
               f"<p><a href='{escape(url, quote=True)}'>Choisir un nouveau mot de passe</a></p>"
               "<p>Ce lien expire dans 30 minutes et ne peut être utilisé qu’une fois. Si vous n’avez pas fait cette demande, ignorez ce message.</p>",
               environment=delivery_env)
    except Exception:
        with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
            connection.execute("DELETE FROM password_reset_tokens WHERE token_hash=?", (_hash(token),))
        # Do not reveal account existence or expose provider diagnostics.
    return True, REQUEST_MESSAGE


def redeem_recovery(token, password, confirmation, database_path, now=None):
    if len(password) < 12 or len(password) > 1024:
        return False, "Le mot de passe doit contenir entre 12 et 1 024 caractères."
    if password != confirmation:
        return False, "La confirmation du mot de passe ne correspond pas."
    if not isinstance(token, str) or len(token) < 32 or len(token) > 128:
        return False, INVALID_MESSAGE
    now = int(time.time() if now is None else now)
    password_hash, salt = _hash_password(password)
    with closing(SQLiteRepository(database_path)._connect()) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT * FROM password_reset_tokens WHERE token_hash=?", (_hash(token),)).fetchone()
        if row is None or row["used_at"] is not None or now >= row["expires_at"]:
            return False, INVALID_MESSAGE
        user = connection.execute("SELECT email FROM users WHERE id=?", (row["user_id"],)).fetchone()
        if user is None:
            return False, INVALID_MESSAGE
        connection.execute("UPDATE users SET password_hash=?,password_salt=?,session_version=session_version+1,failed_login_count=0,locked_until=NULL WHERE id=?", (password_hash, salt, row["user_id"]))
        connection.execute("UPDATE password_reset_tokens SET used_at=? WHERE user_id=?", (now, row["user_id"]))
        connection.execute("DELETE FROM auth_attempt_windows WHERE identity_hash=? AND purpose='login'", (identity_hash(user["email"]),))
    return True, "Votre mot de passe a été modifié. Reconnectez-vous; les anciennes sessions ont été fermées."

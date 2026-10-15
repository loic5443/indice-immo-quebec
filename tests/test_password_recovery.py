from contextlib import closing
import hashlib
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from data.database import authenticate_user, create_user, get_user, initialize_database
from services.auth_attempt_service import claim_attempt
from services.password_recovery_service import request_recovery, redeem_recovery, recovery_ready, REQUEST_MESSAGE


ENV = {"IMMORADAR_AUTH_EMAIL_ENABLED": "1", "IMMORADAR_PUBLIC_URL": "https://immoradar.example",
       "BREVO_API_KEY": "test-placeholder", "BREVO_SENDER_EMAIL": "sender@example.test"}


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "reset.sqlite"
        initialize_database(self.db)
        create_user("Client", "client@example.test", "old-long-password", self.db)
        self.sender = Mock()

    def tearDown(self):
        self.temp.cleanup()

    def request(self, now=1000):
        result = request_recovery("client@example.test", self.db, ENV, self.sender, now)
        html = self.sender.call_args.args[2]
        token = re.search(r"reset_token=([A-Za-z0-9_-]+)", html).group(1)
        return result, token

    def test_disabled_configuration_never_sends_or_stores(self):
        self.assertFalse(recovery_ready({}))
        self.assertFalse(request_recovery("client@example.test", self.db, {}, self.sender)[0])
        self.sender.assert_not_called()
        with closing(sqlite3.connect(self.db)) as connection, connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM password_reset_tokens").fetchone()[0], 0)

    def test_token_is_hashed_single_use_and_invalidates_old_session(self):
        before = get_user(1, self.db)
        result, token = self.request()
        self.assertEqual(result, (True, REQUEST_MESSAGE))
        with closing(sqlite3.connect(self.db)) as connection, connection:
            stored = connection.execute("SELECT token_hash FROM password_reset_tokens").fetchone()[0]
        self.assertNotEqual(stored, token)
        self.assertEqual(stored, hashlib.sha256(token.encode()).hexdigest())
        self.assertTrue(redeem_recovery(token, "new-long-password", "new-long-password", self.db, now=1100)[0])
        self.assertFalse(redeem_recovery(token, "other-long-password", "other-long-password", self.db, now=1101)[0])
        self.assertIsNone(authenticate_user("client@example.test", "old-long-password", self.db))
        self.assertIsNotNone(authenticate_user("client@example.test", "new-long-password", self.db))
        self.assertEqual(get_user(1, self.db)["session_version"], before["session_version"] + 1)

    def test_expired_and_mismatched_passwords_do_not_consume_valid_token(self):
        _, token = self.request()
        self.assertFalse(redeem_recovery(token, "new-long-password", "different", self.db, now=1001)[0])
        self.assertFalse(redeem_recovery(token, "new-long-password", "new-long-password", self.db, now=2800)[0])
        self.assertIsNotNone(authenticate_user("client@example.test", "old-long-password", self.db))

    def test_new_request_invalidates_previous_token(self):
        _, old = self.request()
        _, new = self.request(now=1100)
        self.assertNotEqual(old, new)
        self.assertFalse(redeem_recovery(old, "new-long-password", "new-long-password", self.db, now=1101)[0])
        self.assertTrue(redeem_recovery(new, "new-long-password", "new-long-password", self.db, now=1101)[0])

    def test_unknown_address_receives_same_public_response(self):
        known, _ = self.request()
        self.assertEqual(request_recovery("unknown@example.test", self.db, ENV, self.sender, now=1000), known)
        self.sender.assert_called_once()

    def test_send_failure_exposes_no_provider_details_and_removes_token(self):
        self.sender.side_effect = RuntimeError("private secret")
        self.assertEqual(request_recovery("client@example.test", self.db, ENV, self.sender, now=1000), (True, REQUEST_MESSAGE))
        with closing(sqlite3.connect(self.db)) as connection, connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM password_reset_tokens").fetchone()[0], 0)

    def test_reset_throttle_and_login_window_expiry(self):
        for _ in range(3):
            request_recovery("client@example.test", self.db, ENV, self.sender, now=1000)
        request_recovery("client@example.test", self.db, ENV, self.sender, now=1001)
        self.assertEqual(self.sender.call_count, 3)
        for _ in range(10):
            self.assertTrue(claim_attempt("other@example.test", "login", self.db, now=1000))
        self.assertFalse(claim_attempt("other@example.test", "login", self.db, now=1001))
        self.assertTrue(claim_attempt("other@example.test", "login", self.db, now=1900))

    def test_actual_login_throttles_known_and_unknown_email(self):
        for _ in range(10):
            self.assertIsNone(authenticate_user("client@example.test", "wrong", self.db))
        self.assertIsNone(authenticate_user("client@example.test", "old-long-password", self.db))
        with closing(sqlite3.connect(self.db)) as connection, connection:
            rows = connection.execute("SELECT identity_hash,purpose FROM auth_attempt_windows").fetchall()
        self.assertTrue(all("@" not in key for key, purpose in rows))

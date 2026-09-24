"""Regression tests for atomic private-beta registration."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from data.database import initialize_database
from domain.models import UserProfile
from repositories.sqlite_repository import SQLiteRepository
from services.beta_service import create_invitation, register_beta_user, validate_invitation


class BetaRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database_path = Path(self.tmp.name) / "beta-registration.sqlite"
        initialize_database(self.database_path)
        registered, _ = register_beta_user(
            "Fondateur", "founder@example.test", "mot-de-passe-solide",
            self.database_path, development_mode=True,
        )
        self.assertTrue(registered)
        with closing(SQLiteRepository(self.database_path)._connect()) as connection, connection:
            connection.execute("UPDATE users SET role='admin' WHERE id=1")
            connection.execute(
                "UPDATE beta_settings SET registrations_open=1, invitation_required=1, max_participants=10"
            )

    def tearDown(self):
        self.tmp.cleanup()

    def _count_users(self):
        with closing(SQLiteRepository(self.database_path)._connect()) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM users").fetchone()[0])

    def test_success_creates_account_and_consumes_invitation_together(self):
        code = create_invitation(1, self.database_path, "bêta", 1)
        created, _ = register_beta_user(
            "Bêta", "beta@example.test", "mot-de-passe-solide", self.database_path,
            invitation_code=code, profile=UserProfile(),
        )
        self.assertTrue(created)
        self.assertEqual(self._count_users(), 2)
        self.assertEqual(validate_invitation(code, self.database_path), "exhausted")

    def test_failed_duplicate_does_not_consume_an_active_invitation(self):
        code = create_invitation(1, self.database_path, "bêta", 1)
        first, _ = register_beta_user(
            "Déjà là", "duplicate@example.test", "mot-de-passe-solide", self.database_path,
            invitation_code=code, profile=UserProfile(),
        )
        self.assertTrue(first)
        # A separate active code must remain usable when the insert itself fails.
        second_code = create_invitation(1, self.database_path, "réessai", 1)
        created, message = register_beta_user(
            "Double", "duplicate@example.test", "mot-de-passe-solide", self.database_path,
            invitation_code=second_code, profile=UserProfile(),
        )
        self.assertFalse(created)
        self.assertIn("existe déjà", message)
        self.assertEqual(validate_invitation(second_code, self.database_path), "active")
        self.assertEqual(self._count_users(), 2)

    def test_required_code_and_global_capacity_are_checked_inside_transaction(self):
        missing, message = register_beta_user(
            "Sans code", "missing@example.test", "mot-de-passe-solide", self.database_path,
        )
        self.assertFalse(missing)
        self.assertIn("Code d'invitation", message)
        with closing(SQLiteRepository(self.database_path)._connect()) as connection, connection:
            connection.execute("UPDATE beta_settings SET invitation_required=0, max_participants=1")
        blocked, message = register_beta_user(
            "Capacité", "capacity@example.test", "mot-de-passe-solide", self.database_path,
        )
        self.assertFalse(blocked)
        self.assertIn("capacité", message)
        self.assertEqual(self._count_users(), 1)


if __name__ == "__main__":
    unittest.main()

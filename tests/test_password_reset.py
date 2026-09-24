import tempfile
import unittest
from pathlib import Path

from data.database import authenticate_user, create_user, initialize_database
from services.auth_service import reset_user_password


class PasswordResetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.database_path = Path(self.temp.name) / "reset.sqlite"
        initialize_database(self.database_path)
        created, _ = create_user("Compte test", "reset@example.test", "ancien-mot-de-passe", self.database_path)
        self.assertTrue(created)

    def tearDown(self):
        self.temp.cleanup()

    def test_reset_replaces_password_with_a_new_hash(self):
        updated, _ = reset_user_password(
            "reset@example.test", "nouveau-mot-de-passe", "nouveau-mot-de-passe", self.database_path,
        )
        self.assertTrue(updated)
        self.assertIsNone(authenticate_user("reset@example.test", "ancien-mot-de-passe", self.database_path))
        self.assertIsNotNone(authenticate_user("reset@example.test", "nouveau-mot-de-passe", self.database_path))

    def test_reset_rejects_short_or_mismatched_passwords(self):
        self.assertFalse(reset_user_password("reset@example.test", "court", "court", self.database_path)[0])
        self.assertFalse(reset_user_password("reset@example.test", "mot-de-passe-solide", "different", self.database_path)[0])
        self.assertIsNotNone(authenticate_user("reset@example.test", "ancien-mot-de-passe", self.database_path))


if __name__ == "__main__":
    unittest.main()

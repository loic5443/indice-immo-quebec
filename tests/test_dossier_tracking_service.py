"""Tests for local follow selections and their account isolation."""

import tempfile
import unittest
from pathlib import Path

from data.database import authenticate_user, create_user, delete_analysis, initialize_database, save_analysis
from services.dossier_tracking_service import (
    DossierTrackingAccessError,
    filter_tracked_analyses,
    set_dossier_tracking,
    tracked_dossier_fingerprints,
)


class DossierTrackingServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "tracking.sqlite"
        initialize_database(self.database_path)
        self.alice = self._user("Alice", "alice@example.test")
        self.bob = self._user("Bob", "bob@example.test")
        values = {
            "price": 400_000, "down_payment": 80_000, "rental_income": 2_500,
            "monthly_expenses": 2_000, "cash_flow": 300, "cash_on_cash_return": 3.0,
            "capitalization_rate": 5.0, "debt_service_coverage_ratio": 1.1,
        }
        self.alice_first = save_analysis(self.alice["id"], "Dossier suivi", values, self.database_path)
        self.alice_second = save_analysis(self.alice["id"], "dossier suivi", values, self.database_path)
        self.bob_analysis = save_analysis(self.bob["id"], "Dossier suivi", values, self.database_path)

    def tearDown(self):
        self.temp.cleanup()

    def _user(self, name, email):
        created, _ = create_user(name, email, "Motdepasse1", self.database_path)
        self.assertTrue(created)
        return authenticate_user(email, "Motdepasse1", self.database_path)

    def test_tracking_follows_all_versions_of_one_owned_dossier(self):
        analyses = [
            {"id": self.alice_first, "property_name": "Dossier suivi"},
            {"id": self.alice_second, "property_name": "dossier suivi"},
        ]
        set_dossier_tracking(self.alice["id"], self.alice_first, True, self.database_path)
        self.assertEqual([item["id"] for item in filter_tracked_analyses(self.alice["id"], analyses, self.database_path)], [self.alice_first, self.alice_second])
        set_dossier_tracking(self.alice["id"], self.alice_second, False, self.database_path)
        self.assertEqual(filter_tracked_analyses(self.alice["id"], analyses, self.database_path), [])

    def test_cannot_change_another_accounts_follow_selection(self):
        with self.assertRaises(DossierTrackingAccessError):
            set_dossier_tracking(self.alice["id"], self.bob_analysis, True, self.database_path)

    def test_deleting_last_snapshot_stops_local_tracking_without_touching_other_accounts(self):
        set_dossier_tracking(self.alice["id"], self.alice_first, True, self.database_path)
        self.assertTrue(tracked_dossier_fingerprints(self.alice["id"], self.database_path))
        self.assertTrue(delete_analysis(self.alice["id"], self.alice_first, self.database_path))
        self.assertTrue(tracked_dossier_fingerprints(self.alice["id"], self.database_path))
        self.assertTrue(delete_analysis(self.alice["id"], self.alice_second, self.database_path))
        self.assertEqual(tracked_dossier_fingerprints(self.alice["id"], self.database_path), set())
        self.assertFalse(tracked_dossier_fingerprints(self.bob["id"], self.database_path))


if __name__ == "__main__":
    unittest.main()

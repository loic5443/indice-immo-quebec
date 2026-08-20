"""Regression tests for immutable, owner-scoped dossier timelines."""

import unittest

from services.snapshot_history_service import snapshot_positions


class SnapshotHistoryServiceTests(unittest.TestCase):
    def test_groups_only_exact_normalized_dossier_names_latest_first(self):
        positions = snapshot_positions([
            {"id": 1, "property_name": "Projet du Marché", "created_at": "2026-01-10 09:00 UTC"},
            {"id": 2, "property_name": "projet du marche", "created_at": "2026-02-10 09:00 UTC"},
            {"id": 3, "property_name": "Autre projet", "created_at": "2026-03-10 09:00 UTC"},
        ])
        self.assertEqual((positions[2].position, positions[2].total), (1, 2))
        self.assertTrue(positions[2].is_latest)
        self.assertEqual((positions[1].position, positions[1].total), (2, 2))
        self.assertEqual((positions[3].position, positions[3].total), (1, 1))

    def test_does_not_merge_similar_but_different_dossier_names(self):
        positions = snapshot_positions([
            {"id": 1, "property_name": "Projet du Marché", "created_at": "2026-01-10"},
            {"id": 2, "property_name": "Projet du Marché 2", "created_at": "2026-02-10"},
        ])
        self.assertEqual(positions[1].total, 1)
        self.assertEqual(positions[2].total, 1)


if __name__ == "__main__":
    unittest.main()

"""Local filtering regressions for the owner-scoped dossier list."""

import unittest

from components.saved_analyses import _filter_saved_analyses
from services.dossier_tracking_service import dossier_fingerprint


class SavedAnalysisFiltersTests(unittest.TestCase):
    def setUp(self):
        self.user_id = 7
        self.analyses = [
            {"id": 1, "property_name": "Projet Alpha", "created_at": "2026-01-02", "is_favorite": 0, "immo_score": 60},
            {"id": 2, "property_name": "Projet Bêta", "created_at": "2026-03-02", "is_favorite": 1, "immo_score": 40},
            {"id": 3, "property_name": "Projet Alpha", "created_at": "2026-02-02", "is_favorite": 0, "immo_score": None},
        ]
        self.tracked = {dossier_fingerprint(self.user_id, "Projet Alpha")}

    def test_search_and_scope_only_filter_the_supplied_owner_list(self):
        result = _filter_saved_analyses(self.analyses, "alpha", "Suivis", "Plus récent", self.tracked, self.user_id)
        self.assertEqual([item["id"] for item in result], [3, 1])
        favorites = _filter_saved_analyses(self.analyses, "", "Favoris", "Plus récent", self.tracked, self.user_id)
        self.assertEqual([item["id"] for item in favorites], [2])

    def test_sorting_keeps_missing_scores_last(self):
        result = _filter_saved_analyses(self.analyses, "", "Tous", "Score le plus élevé", self.tracked, self.user_id)
        self.assertEqual([item["id"] for item in result], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()

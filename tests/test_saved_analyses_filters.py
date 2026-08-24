"""Local filtering regressions for the owner-scoped dossier list."""

import unittest

from components.saved_analyses import _filter_saved_analyses, _saved_immovalue, _saved_official_role, _snapshot_history_rows, _tracking_overview
from services.dossier_tracking_service import dossier_fingerprint
from streamlit.testing.v1 import AppTest


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

    def test_tracking_overview_counts_only_factual_alert_categories(self):
        analysis = {
            "id": 1, "property_name": "Projet Alpha", "created_at": "2026-02-01",
            "cash_flow": 100, "immovalue_json": "{}", "official_role_snapshot_json": "{}",
            "resilience_json": '{"tests": [{"name": "Taux +1 point", "financial": {"cash_flow_monthly": -25}}]}',
        }
        self.assertEqual(_tracking_overview([analysis]), {"total": 1, "important": 1, "updates": 0})

    def test_saved_official_role_remains_a_fiscal_snapshot(self):
        snapshot = _saved_official_role({
            "official_role_snapshot_json": '{"total_value": 404100, "role_year": 2026, "reference_date": "2026-01-01"}',
        })
        self.assertEqual(snapshot["total_value"], 404_100)
        self.assertIsNone(_saved_official_role({"official_role_snapshot_json": "{}"}))

    def test_saved_immovalue_reads_only_a_real_completed_snapshot(self):
        value = _saved_immovalue({
            "immovalue_json": '{"available": true, "estimated_value": 425000, "low": 400000, "high": 450000, "confidence": 62}',
        })
        self.assertEqual(value["estimated_value"], 425_000)
        self.assertEqual(value["low"], 400_000)
        self.assertEqual(value["high"], 450_000)
        self.assertEqual(value["confidence"], 62)
        self.assertIsNone(_saved_immovalue({"immovalue_json": '{"available": false}'}))
        self.assertIsNone(_saved_immovalue({"immovalue_json": '{"estimated_value": 425000}'}))

    def test_saved_dossier_shows_three_value_references_without_confusing_them(self):
        app = AppTest.from_string(
            "import components.saved_analyses as page\n"
            "page._show_saved_value_context({'immovalue_json': '{\\\"available\\\": true, \\\"estimated_value\\\": 425000, \\\"low\\\": 400000, \\\"high\\\": 450000, \\\"confidence\\\": 62, \\\"subject\\\": {\\\"asking_price\\\": 440000}}', 'official_role_snapshot_json': '{\\\"total_value\\\": 404100, \\\"role_year\\\": 2026}'})\n"
        ).run(timeout=20)
        labels = [metric.label for metric in app.metric]
        self.assertEqual(labels, ["Valeur au rôle municipal", "Estimation ImmoValue", "Prix demandé déclaré"])
        text = "\n".join(item.value for item in app.caption)
        self.assertIn("Repère fiscal officiel", text)
        self.assertIn("estimation expérimentale", text)

    def test_snapshot_history_uses_only_saved_values_and_marks_absences(self):
        rows = _snapshot_history_rows((
            {"created_at": "2026-02-01", "cash_flow": 250, "immo_score": 65, "official_role_snapshot_json": '{"total_value": 404100}'},
            {"created_at": "2026-01-01", "cash_flow": 0, "immo_score": None, "official_role_snapshot_json": "{}"},
        ))
        self.assertEqual(rows[0]["Flux mensuel"], "250 $")
        self.assertEqual(rows[0]["Rôle municipal"], "404 100 $")
        self.assertEqual(rows[1]["Flux mensuel"], "0 $")
        self.assertEqual(rows[1]["Score"], "Non disponible")
        self.assertEqual(rows[1]["Rôle municipal"], "Non disponible")

        missing = _snapshot_history_rows(({"created_at": "2026-01-01", "cash_flow": None, "immo_score": None},))
        self.assertEqual(missing[0]["Flux mensuel"], "Non disponible")


if __name__ == "__main__":
    unittest.main()

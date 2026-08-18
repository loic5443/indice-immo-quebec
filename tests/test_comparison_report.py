"""Integrity checks for the Premium two-snapshot comparison report."""

import unittest
from io import BytesIO

from pypdf import PdfReader

from services.report_service import generate_comparison_report_pdf


class ComparisonReportTests(unittest.TestCase):
    def test_report_contains_only_the_selected_snapshots_and_limits(self):
        comparison = {
            "a": {"name": "Dossier A", "date": "2026-08-18", "profile": "Investisseur locatif", "engine_version": "ImmoEngine 1.1"},
            "b": {"name": "Dossier B", "date": "2026-08-17", "profile": "Investisseur locatif", "engine_version": "ImmoEngine 1.0"},
            "conclusion": "La propriété A semble mieux alignée avec vos hypothèses sauvegardées.",
            "engine_versions_differ": True,
            "indicators": [
                {"key": "cash_flow", "label": "Flux de trésorerie mensuel", "a": 250, "b": 100, "relation": "avantage_a"},
                {"key": "score", "label": "Score ImmoRadar", "a": 72, "b": None, "relation": "non_comparable"},
            ],
            "scenarios": {"current": {"label": "Situation actuelle", "a": 250, "b": 100}},
            "strengths": {"a": ["Flux plus favorable."], "b": []},
            "checks": {"a": [], "b": ["Score non disponible."]},
        }
        content = generate_comparison_report_pdf(comparison)
        self.assertTrue(content.startswith(b"%PDF"))
        reader = PdfReader(BytesIO(content))
        extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
        for expected in ("Rapport comparatif", "Dossier A", "Dossier B", "Flux de trésorerie", "Sources et limites"):
            self.assertIn(expected, extracted)
        self.assertNotIn("Dossier C", extracted)
        self.assertIn("ne constitue ni une recommandation", extracted)


if __name__ == "__main__":
    unittest.main()

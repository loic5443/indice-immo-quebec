import json
import unittest
from dataclasses import replace
from io import BytesIO

from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

from calculations.real_estate import calculate_analysis, validate_inputs
from services.demo_service import demo_inputs, demo_snapshot
from services.report_service import generate_report_pdf


class DemoTests(unittest.TestCase):
    def test_demo_changes_calculated_output_without_real_property(self):
        base, financial = demo_snapshot()
        changed, changed_financial = demo_snapshot(demo_inputs(rental_income=3000))
        self.assertLess(changed_financial.cash_flow_monthly, financial.cash_flow_monthly)
        self.assertIn("fictif", base["property_name"])
        self.assertEqual(json.loads(base["immovalue_json"]), {})
        self.assertEqual(json.loads(base["official_role_snapshot_json"]), {})
        pdf = PdfReader(BytesIO(generate_report_pdf(base)))
        text = " ".join(page.extract_text() for page in pdf.pages)
        self.assertIn("DÉMONSTRATION", text)
        self.assertIn("Aucun dossier réel", text)
        self.assertGreater(len(pdf.pages), 2)

    def test_financial_nonfinite_inputs_are_rejected(self):
        for value in (float("nan"), float("inf"), True, "500000"):
            with self.subTest(value=value):
                inputs = replace(demo_inputs(), price=value)
                self.assertTrue(validate_inputs(inputs))
                with self.assertRaises(ValueError):
                    calculate_analysis(inputs)

    def test_guest_can_try_demo_and_change_hypotheses(self):
        app = AppTest.from_string("from components.demo import show_demo\nshow_demo()").run(timeout=20)
        self.assertFalse(app.exception)
        first = next(metric.value for metric in app.metric if metric.label == "Flux après dépenses")
        app.slider(key="demo_rent").set_value(3000).run(timeout=20)
        self.assertFalse(app.exception)
        second = next(metric.value for metric in app.metric if metric.label == "Flux après dépenses")
        self.assertNotEqual(first, second)
        self.assertEqual([button.label for button in app.button], ["Analyser ma propre propriété", "Découvrir les outils Premium"])

    def test_no_rent_stays_explicitly_not_applicable(self):
        app = AppTest.from_string("from components.demo import show_demo\nshow_demo()").run(timeout=20)
        app.slider(key="demo_rent").set_value(0).run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(next(metric.value for metric in app.metric if metric.label == "Couverture de dette"), "Non applicable")

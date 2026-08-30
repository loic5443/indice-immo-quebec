"""Focused Streamlit assertions for the unified property summary."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class PropertySummaryUiTests(unittest.TestCase):
    def setUp(self):
        import components.property_analysis as page

        self.page = page
        self.originals = {
            "is_authenticated": page.is_authenticated,
            "current_user": page.current_user,
            "quota_status": page.quota_status,
            "quota_is_enforced": page.quota_is_enforced,
        }

    def tearDown(self):
        for name, value in self.originals.items():
            setattr(self.page, name, value)

    def test_summary_prioritizes_known_results_and_keeps_details_secondary(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "from calculations.real_estate import PropertyInputs, calculate_analysis\n"
            "page.is_authenticated = lambda: False\n"
            "inputs = PropertyInputs(price=500000, down_payment=100000, annual_interest_rate=5, amortization_years=25, municipal_taxes_annual=3600, school_taxes_annual=400, insurance_monthly=100, condo_fees_monthly=0, rental_income_monthly=3200, other_expenses_monthly=200)\n"
            "page._show_results(inputs, calculate_analysis(inputs), 'Investisseur locatif')\n"
        ).run(timeout=20)
        text = "\n".join([item.value for item in app.markdown] + [item.value for item in app.caption])
        self.assertIn("Votre synthèse immobilière", text)
        labels = [metric.label for metric in app.metric]
        for label in ("ImmoScore", "Confiance", "Paiement hypothécaire", "Dépenses mensuelles", "Revenus locatifs", "Flux de trésorerie", "Taux de capitalisation", "Rendement sur mise", "Capacité à couvrir la dette (DSCR)"):
            self.assertIn(label, labels)
        buttons = [button.label for button in app.button]
        self.assertIn("Créer mon espace gratuit", buttons)
        self.assertIn("Modifier mes chiffres", buttons)
        self.assertIn("Découvrir Premium", buttons)
        self.assertEqual(
            [item.label for item in app.tabs],
            ["Vue d’ensemble", "Finances", "Risques et vérifications", "Détails et sources"],
        )

    def test_detail_tabs_extend_the_summary_without_repeating_it(self):
        source = (Path("components") / "property_analysis.py").read_text(encoding="utf-8")
        results_section = source[source.index("def _show_results"):source.index("def _show_immovalue")]
        self.assertIn("Les indicateurs essentiels sont déjà résumés plus haut", results_section)
        self.assertIn("Estimation marchande ImmoValue", results_section)
        self.assertNotIn('score.metric("Score ImmoRadar", f"{engine_result.score:.0f} / 100" if engine_result.score is not None else "Indisponible")', results_section)

    def test_authenticated_summary_makes_saving_the_clear_primary_action(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "from calculations.real_estate import PropertyInputs, calculate_analysis\n"
            "page.is_authenticated = lambda: True\n"
            "page.current_user = lambda: {'id': 1, 'plan': 'free', 'role': 'user'}\n"
            "page.quota_status = lambda *_args: {'label': '1 estimation complète restante ce mois-ci'}\n"
            "page.quota_is_enforced = lambda *_args: False\n"
            "inputs = PropertyInputs(price=500000, down_payment=100000, annual_interest_rate=5, amortization_years=25, municipal_taxes_annual=3600, school_taxes_annual=400, insurance_monthly=100, condo_fees_monthly=0, rental_income_monthly=3200, other_expenses_monthly=200)\n"
            "page._show_results(inputs, calculate_analysis(inputs), 'Investisseur locatif')\n"
        ).run(timeout=20)
        buttons = [button.label for button in app.button]
        self.assertIn("Sauvegarder mon dossier", buttons)
        self.assertIn("Voir les avantages Premium", buttons)
        self.assertIn("Modifier mes chiffres", buttons)

    def test_selected_address_prefills_save_name_without_replacing_a_custom_name(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "from calculations.real_estate import PropertyInputs, calculate_analysis\n"
            "original_authenticated, original_user = page.is_authenticated, page.current_user\n"
            "original_quota_status, original_quota_enforced = page.quota_status, page.quota_is_enforced\n"
            "try:\n"
            "    page.is_authenticated = lambda: True\n"
            "    page.current_user = lambda: {'id': 1, 'plan': 'free', 'role': 'user'}\n"
            "    page.quota_status = lambda *_args: {'label': '1 estimation complète restante ce mois-ci'}\n"
            "    page.quota_is_enforced = lambda *_args: False\n"
            "    page.st.session_state[page.ADDRESS_STATE_KEY] = page.prepare_address_submission('123 rue Exemple', 'Montréal', 'H2Z1A4', consent=True)\n"
            "    inputs = PropertyInputs(price=500000, down_payment=100000, annual_interest_rate=5, amortization_years=25, municipal_taxes_annual=3600, school_taxes_annual=400, insurance_monthly=100, condo_fees_monthly=0, rental_income_monthly=3200, other_expenses_monthly=200)\n"
            "    page._show_results(inputs, calculate_analysis(inputs), 'Investisseur locatif')\n"
            "finally:\n"
            "    page.is_authenticated, page.current_user = original_authenticated, original_user\n"
            "    page.quota_status, page.quota_is_enforced = original_quota_status, original_quota_enforced\n"
        ).run(timeout=20)
        field = app.text_input(key="saved_property_name")
        self.assertEqual(field.value, "123 rue Exemple, Montréal")
        self.assertIn("facultatif si une adresse est sélectionnée", field.label)

    def test_non_rental_summary_does_not_present_zero_as_a_return(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "from calculations.real_estate import PropertyInputs, calculate_analysis\n"
            "page.is_authenticated = lambda: False\n"
            "inputs = PropertyInputs(price=500000, down_payment=100000, annual_interest_rate=5, amortization_years=25, municipal_taxes_annual=3600, school_taxes_annual=400, insurance_monthly=100, condo_fees_monthly=0, rental_income_monthly=0, other_expenses_monthly=0)\n"
            "page._show_results(inputs, calculate_analysis(inputs), 'Premier acheteur')\n"
        ).run(timeout=20)
        values = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(values["Revenus locatifs"], "Non applicable")
        self.assertEqual(values["Flux de trésorerie"], "Non applicable")

    def test_value_comparison_explains_the_fiscal_role_limit(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "page._show_summary_value_cards(None, None)\n"
        ).run(timeout=20)
        notices = "\n".join(item.value for item in app.info)
        self.assertIn("repère fiscal officiel", notices)
        self.assertIn("plus élevée ou plus basse", notices)
        self.assertIn("secteur", notices)

    def test_revealed_role_gives_one_clear_next_step_without_calling_it_market_value(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "from calculations.real_estate import PropertyInputs\n"
            "state = page.prepare_address_submission('123 rue Exemple', 'Ville de test', 'H2Z1A4', consent=True)\n"
            "lookup = {'consent': True, 'matches': [{'total_value': 400000, 'role_year': 2026}]}\n"
            "inputs = PropertyInputs(price=0, down_payment=0, annual_interest_rate=0, amortization_years=25, municipal_taxes_annual=0, school_taxes_annual=0, insurance_monthly=0, condo_fees_monthly=0, rental_income_monthly=0, other_expenses_monthly=0)\n"
            "page._show_dossier_summary(state, lookup, inputs, 'Premier acheteur')\n"
        ).run(timeout=20)
        messages = "\n".join([item.value for item in app.info] + [item.value for item in app.caption])
        self.assertIn("Le rôle municipal est révélé", messages)
        self.assertIn("trois comparables admissibles", messages)
        self.assertIn("n’est pas un prix de vente", messages)
        rendered = "\n".join([item.value for item in app.markdown] + [item.value for item in app.caption])
        self.assertIn("Pour poursuivre simplement", rendered)
        self.assertIn("prix demandé est facultatif", rendered)

    def test_saved_immovalue_snapshot_keeps_declared_price_without_an_address(self):
        app = AppTest.from_string(
            "import json\n"
            "import streamlit as st\n"
            "import components.property_analysis as page\n"
            "page.st.session_state['iv_asking'] = 575000\n"
            "page.st.session_state['workflow_property_type'] = 'Maison'\n"
            "st.code(json.dumps(page._immovalue_snapshot_for_save({'available': True, 'estimated_value': 560000}), ensure_ascii=False))\n"
        ).run(timeout=20)
        payload = app.code[0].value
        self.assertIn('"asking_price": 575000.0', payload)
        self.assertIn('"property_type": "Maison"', payload)
        self.assertNotIn("Adresse", payload)
        self.assertNotIn('"street"', payload.casefold())

    def test_property_stage_collects_an_optional_asking_price_before_finances(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "page._show_property_stage()\n"
        ).run(timeout=20)
        asking = app.number_input(key="iv_asking")
        self.assertEqual(asking.label, "Prix demandé (facultatif)")
        asking.set_value(575_000.0).run(timeout=20)
        self.assertEqual(app.number_input(key="iv_asking").value, 575_000.0)
        captions = "\n".join(item.value for item in app.caption)
        self.assertIn("Il ne remplace pas le prix retenu", captions)

    def test_financial_price_is_labeled_as_a_separate_assumption(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "page._show_finance_stage()\n"
        ).run(timeout=20)
        self.assertEqual(app.number_input(key="property_price").label, "Prix retenu pour vos calculs ($)")
        captions = "\n".join(item.value for item in app.caption)
        self.assertIn("reste distinct du rôle municipal et d’ImmoValue", captions)

    def test_renewal_date_is_optional_in_advanced_financial_inputs(self):
        app = AppTest.from_string(
            "import components.property_analysis as page\n"
            "page._show_finance_stage()\n"
        ).run(timeout=20)
        self.assertEqual(app.date_input(key="mortgage_renewal_date").label, "Date de renouvellement hypothécaire (facultatif)")


if __name__ == "__main__":
    unittest.main()

"""Real Streamlit form regressions for canonical address-state synchronization."""

import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from streamlit.testing.v1 import AppTest

from data.database import create_user, initialize_database
from services.address_form_service import restore_address_form, serialize_address_form, submit_address_form
from services.analysis_workflow import load_draft, save_draft
from services.quebec_role_admin_service import import_territory, refresh_index


INDEX = (
    "code géographique,nom du territoire,lien,date de modification\n"
    "01023,Ville-exemple,https://mamh.gouv.qc.ca/role/RM01023.xml,2025-12-19\n"
).encode()
XML = (
    b'\xef\xbb\xbf<?xml version="1.0"?><RL><VERSION>2.9</VERSION><RLM01A>01023</RLM01A>'
    b'<RLM02A>2026</RLM02A><RLUEx><RL0101><RL0101Ax>123</RL0101Ax>'
    b'<RL0101Gx>RUE EXEMPLE</RL0101Gx></RL0101><RL0104><RL0104A>1</RL0104A>'
    b'</RL0104><RL0402A>125400</RL0402A><RL0403A>278700</RL0403A><RL0404A>404100</RL0404A>'
    b'<RL0401A>2024-07-01</RL0401A></RLUEx></RL>'
)


class AddressFormUiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "address-ui.sqlite"
        initialize_database(self.db)
        create_user("Admin", "admin@example.com", "Motdepasse1", self.db)
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE users SET role='admin' WHERE email='admin@example.com'")
        refresh_index(1, self.db, lambda _: INDEX)
        import_territory(1, self.db, "01023", lambda _: XML)
        self.app_source = (
            "from pathlib import Path\n"
            "import components.property_analysis as page\n"
            f"page.DATABASE_PATH = Path({str(self.db)!r})\n"
            "page.show_property_analysis()\n"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _app(self, authenticated=False):
        source = self.app_source
        if authenticated:
            source = (
                "import streamlit as st\n"
                "import components.account as account\n"
                "account.get_user = lambda user_id: {'id': user_id, 'user_type': 'Investisseur locatif', 'plan': 'free'}\n"
                "st.session_state.setdefault('current_user', {'id': 1})\n"
                + source
            )
        app = AppTest.from_string(source)
        app.run(timeout=20)
        return app

    @staticmethod
    def _submit_exact(app):
        app.session_state["address_form_editor_street"] = "123 rue Exemple, Ville-exemple, QC, Canada"
        app.text_input(key="address_form_city").set_value("Ville-exemple")
        app.text_input(key="address_form_postal").set_value("H2X1Y4")
        app.checkbox(key="address_form_consent").set_value(True)
        app.button(key="address_lookup_submit").click().run(timeout=20)

    def test_exact_submission_visible_values_and_two_reruns_are_consistent(self):
        app = self._app()
        self.assertEqual(list(app.error), [])
        self._submit_exact(app)
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")
        self.assertEqual(app.text_input(key="address_form_postal").value, "H2X 1Y4")
        self.assertTrue(app.checkbox(key="address_form_consent").value)
        self.assertEqual(list(app.error), [])

    def test_public_role_is_visible_before_calculation_and_survives_reruns(self):
        """A public role lookup must not depend on private financial calculation."""
        app = self._app()
        self._submit_exact(app)
        labels = [metric.label for metric in app.metric]
        self.assertIn("Terrain", labels)
        self.assertIn("Bâtiment", labels)
        self.assertIn("Total au rôle", labels)
        self.assertIn("Valeur au rôle municipal", labels)
        self.assertIn("ImmoValue", labels)
        self.assertIn("Score ImmoRadar", labels)
        self.assertTrue(any("Ce qu’ImmoRadar sait pour l’instant" in item.value for item in app.markdown))
        self.assertTrue(any("Référence fiscale officielle" in item.value for item in app.caption))
        self.assertTrue(any("Adresse normalisée" in item.value for item in app.caption))
        self.assertTrue(any("valeur marchande" in item.value for item in app.markdown))
        self.assertTrue(any("Aucune analyse personnelle" in item.value for item in app.info))
        app.run(timeout=20)
        app.run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")
        self.assertEqual(app.text_input(key="address_form_postal").value, "H2X 1Y4")
        self.assertIn("Total au rôle", [metric.label for metric in app.metric])

    def test_home_reveal_opens_the_empty_canonical_analyzer_form(self):
        """Accueil never collects an address; Analyse owns the empty form."""
        source = (
            "from pathlib import Path\n"
            "import streamlit as st\n"
            "import components.home as home\n"
            "import components.property_analysis as analysis\n"
            f"analysis.DATABASE_PATH = Path({str(self.db)!r})\n"
            "if st.session_state.get('main_navigation', 'Accueil') == 'Analyser':\n"
            "    analysis.show_property_analysis()\n"
            "else:\n"
            "    home.show_home()\n"
        )
        app = AppTest.from_string(source)
        # An anonymous visitor may already have initialized Analyser before
        # coming back to Accueil; this is the original regression condition.
        app.session_state["main_navigation"] = "Analyser"
        app.run(timeout=20)
        app.session_state["main_navigation"] = "Accueil"
        app.run(timeout=20)
        self.assertEqual(list(app.text_input), [])
        next(button for button in app.button if button.label == "Révéler la valeur").click().run(timeout=20)
        app.run(timeout=20)
        self.assertEqual(app.session_state["main_navigation"], "Analyser")
        self.assertEqual(app.session_state["address_form_editor_street"], "")
        self.assertEqual(app.text_input(key="address_form_city").value, "")
        self.assertEqual(app.text_input(key="address_form_postal").value, "")
        self.assertEqual(list(app.exception), [])

    def test_consented_address_form_shows_public_role_without_calculation(self):
        """The Analyser form reveals a covered public role without financial calculation."""
        source = (
            "from pathlib import Path\n"
            "import components.property_analysis as page\n"
            f"page.DATABASE_PATH = Path({str(self.db)!r})\n"
            "page.show_property_analysis()\n"
        )
        app = AppTest.from_string(source).run(timeout=20)
        app.session_state["address_form_editor_street"] = "123 rue Exemple"
        app.session_state["address_form_city"] = "Ville-exemple"
        app.session_state["address_form_postal"] = "H2X 1Y4"
        app.checkbox(key="address_form_consent").set_value(True)
        app.button(key="address_lookup_submit").click().run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")
        self.assertEqual(app.text_input(key="address_form_postal").value, "H2X 1Y4")
        self.assertIn("Total au rôle", [metric.label for metric in app.metric])
        self.assertTrue(any("Aucune analyse personnelle" in item.value for item in app.info))

    def test_unconsented_home_address_never_resolves_publicly(self):
        source = (
            "from pathlib import Path\n"
            "import components.property_analysis as page\n"
            f"page.DATABASE_PATH = Path({str(self.db)!r})\n"
            "original_resolver = page.resolve_freeform_address\n"
            "page.resolve_freeform_address = lambda *_: (_ for _ in ()).throw(AssertionError('public lookup should not run'))\n"
            "try:\n"
            "    page.show_property_analysis()\n"
            "finally:\n"
            "    page.resolve_freeform_address = original_resolver\n"
        )
        app = AppTest.from_string(source).run(timeout=20)
        app.session_state["address_form_editor_street"] = "122 rue Publique, Territoire-test"
        app.button(key="address_lookup_submit").click().run(timeout=20)
        self.assertNotIn("address_form_resolution", app.session_state)
        self.assertEqual(list(app.exception), [])

    def test_external_failure_uses_clickable_local_role_suggestion(self):
        source = (
            "from pathlib import Path\n"
            "import streamlit as st\n"
            "import components.property_analysis as page\n"
            f"page.DATABASE_PATH = Path({str(self.db)!r})\n"
            "original_suggest = page.suggest_addresses\n"
            "page.suggest_addresses = lambda *_: page.SuggestionResponse('unavailable', message='source externe indisponible')\n"
            "st.session_state.setdefault('address_form_consent', True)\n"
            "st.session_state.setdefault('address_form_street_input', '123 rue Ex')\n"
            "try:\n"
            "    page.show_property_analysis()\n"
            "finally:\n"
            "    page.suggest_addresses = original_suggest\n"
        )
        app = AppTest.from_string(source).run(timeout=20)
        self.assertEqual(app.button(key="address_suggestion_select_0").label, "123 Rue Exemple · Ville-exemple")
        app.button(key="address_suggestion_select_0").click().run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")
        self.assertIn("Total au rôle", [metric.label for metric in app.metric])
        self.assertFalse(any("source externe indisponible" in item.value for item in app.info))

    def test_local_selection_without_postal_survives_reruns(self):
        """A selected public role needs no second confirmation when postal is absent."""
        source = (
            "from pathlib import Path\n"
            "import streamlit as st\n"
            "import components.property_analysis as page\n"
            f"page.DATABASE_PATH = Path({str(self.db)!r})\n"
            "original_suggest = page.suggest_addresses\n"
            "original_resolver = page.resolve_freeform_address\n"
            "page.suggest_addresses = lambda *_: page.SuggestionResponse('unavailable', message='source externe indisponible')\n"
            "page.resolve_freeform_address = lambda *_: page.SuggestionResponse('unavailable', message='source externe indisponible')\n"
            "st.session_state.setdefault('address_form_consent', True)\n"
            "st.session_state.setdefault('address_form_street_input', '123 rue Ex')\n"
            "if st.session_state.get('repeat_public_address'):\n"
            "    page._set_address_editor_street('123 Rue Exemple')\n"
            "if st.session_state.get('change_public_address'):\n"
            "    page._set_address_editor_street('124 rue Nouvelle')\n"
            "try:\n"
            "    page.show_property_analysis()\n"
            "finally:\n"
            "    page.suggest_addresses = original_suggest\n"
            "    page.resolve_freeform_address = original_resolver\n"
        )
        app = AppTest.from_string(source).run(timeout=20)
        app.button(key="address_suggestion_select_0").click().run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_postal").value, "")
        self.assertIn("Total au rôle", [metric.label for metric in app.metric])
        self.assertEqual(list(app.error), [])
        self.assertFalse(any("source externe indisponible" in item.value for item in app.info))
        self.assertTrue(any("code postal n’est pas publié" in item.value for item in app.info))
        self.assertNotIn("address_lookup_submit", [button.key for button in app.button])
        app.session_state["repeat_public_address"] = True
        app.run(timeout=20)
        self.assertIn("Total au rôle", [metric.label for metric in app.metric])
        app.session_state["change_public_address"] = True
        app.run(timeout=20)
        self.assertNotIn("Total au rôle", [metric.label for metric in app.metric])

    def test_suggestion_actions_remain_clickable_in_the_single_live_editor(self):
        """A selected local role replaces the redundant reveal action with confirmation."""
        source = (
            "from pathlib import Path\n"
            "import streamlit as st\n"
            "import components.property_analysis as page\n"
            f"page.DATABASE_PATH = Path({str(self.db)!r})\n"
            "original_suggest = page.suggest_addresses\n"
            "page.suggest_addresses = lambda *_: page.SuggestionResponse('unavailable', message='source externe indisponible')\n"
            "st.session_state.setdefault('address_form_consent', True)\n"
            "st.session_state.setdefault('address_form_street_input', '123 rue Ex')\n"
            "try:\n"
            "    page.show_property_analysis()\n"
            "finally:\n"
            "    page.suggest_addresses = original_suggest\n"
        )
        app = AppTest.from_string(source).run(timeout=20)
        self.assertEqual(app.button(key="address_suggestion_select_0").label, "123 Rue Exemple · Ville-exemple")
        self.assertIn("address_lookup_submit", [button.key for button in app.button])
        app.button(key="address_suggestion_select_0").click().run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")
        self.assertIn("Total au rôle", [metric.label for metric in app.metric])
        self.assertTrue(any("Renseignements publics révélés" in item.value for item in app.success))
        self.assertNotIn("address_lookup_submit", [button.key for button in app.button])
        app.run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")
        self.assertIn("Total au rôle", [metric.label for metric in app.metric])
        self.assertNotIn("address_lookup_submit", [button.key for button in app.button])

    def test_failed_role_lookup_keeps_action_and_explains_the_failure(self):
        """No role match keeps the action available and exposes the manual fallback."""
        app = self._app()
        app.session_state["address_form_editor_street"] = "999 rue Inconnue"
        app.text_input(key="address_form_city").set_value("Ville-exemple")
        app.text_input(key="address_form_postal").set_value("H2X 1Y4")
        app.checkbox(key="address_form_consent").set_value(True)
        app.button(key="address_lookup_submit").click().run(timeout=20)
        self.assertIn("address_lookup_submit", [button.key for button in app.button])
        self.assertTrue(any("aucune unité officielle" in item.value.casefold() for item in app.error))

    def test_local_selection_enriches_postal_without_delaying_role_result(self):
        source = (
            "from pathlib import Path\n"
            "import streamlit as st\n"
            "import components.property_analysis as page\n"
            f"page.DATABASE_PATH = Path({str(self.db)!r})\n"
            "st.session_state.setdefault('address_form_consent', True)\n"
            "st.session_state.setdefault('address_form_street_input', '123 rue Ex')\n"
            "page.show_property_analysis()\n"
        )
        app = AppTest.from_string(source).run(timeout=20)
        self.assertEqual(app.button(key="address_suggestion_select_0").label, "123 Rue Exemple · Ville-exemple")
        import components.property_analysis as page
        enriched = page.AddressSuggestion("123 Rue Exemple", "Ville-exemple", "H2X 1Y4", "", "123 Rue Exemple · Ville-exemple · H2X 1Y4")
        with patch.object(page, "_enrich_local_suggestion", return_value=enriched):
            app.button(key="address_suggestion_select_0").click().run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_postal").value, "H2X 1Y4")
        self.assertIn("Total au rôle", [metric.label for metric in app.metric])
        self.assertFalse(any("code postal n’est pas publié" in item.value for item in app.info))

    def test_street_only_submission_keeps_city_postal_and_consent_canonical(self):
        app = self._app()
        app.session_state["address_form_editor_street"] = "123 rue Exemple"
        app.text_input(key="address_form_city").set_value("Ville-exemple")
        app.text_input(key="address_form_postal").set_value("H2X 1Y4")
        app.checkbox(key="address_form_consent").set_value(True)
        app.button(key="address_lookup_submit").click().run(timeout=20)
        self.assertEqual(app.session_state["address_form_editor_street"], "123 rue Exemple")
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")
        self.assertEqual(app.text_input(key="address_form_postal").value, "H2X 1Y4")
        self.assertTrue(app.checkbox(key="address_form_consent").value)
        self.assertEqual(list(app.error), [])
        self.assertFalse(any("indisponibles automatiquement" in item.value for item in app.info))
        app.run(timeout=20)
        app.run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")
        self.assertEqual(app.text_input(key="address_form_postal").value, "H2X 1Y4")
        self.assertEqual(list(app.error), [])

    def test_error_is_cleared_only_by_a_valid_new_submission(self):
        app = self._app()
        app.session_state["address_form_editor_street"] = "123 rue Exemple"
        app.text_input(key="address_form_city").set_value("")
        app.text_input(key="address_form_postal").set_value("H2X1Y4")
        app.button(key="address_lookup_submit").click().run(timeout=20)
        self.assertTrue(any("Ce champ est requis." in item.value for item in app.error))
        app.text_input(key="address_form_city").set_value("Ville-exemple")
        app.checkbox(key="address_form_consent").set_value(True)
        app.button(key="address_lookup_submit").click().run(timeout=20)
        self.assertEqual(list(app.error), [])
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")

    def test_drafts_restore_the_same_canonical_values_without_cross_user_leakage(self):
        first = submit_address_form("123 rue Exemple, Ville-exemple, QC, Canada", "Ville-exemple", "H2X1Y4", consent=True)
        second = submit_address_form("12 rue du Port", "Montréal", "H2X1Y4", consent=False)
        self.assertTrue(first.valid); self.assertTrue(second.valid)
        create_user("Deux", "deux@example.com", "Motdepasse1", self.db)
        save_draft(1, {"address_form": serialize_address_form(first)}, 2, self.db)
        save_draft(2, {"address_form": serialize_address_form(second)}, 2, self.db)
        first_payload, _ = load_draft(1, self.db)
        second_payload, _ = load_draft(2, self.db)
        first_restored = restore_address_form(first_payload["address_form"])
        second_restored = restore_address_form(second_payload["address_form"])
        self.assertEqual(first_restored.values["postal"], "H2X 1Y4")
        self.assertEqual(first_restored.values["city"], "Ville-exemple")
        self.assertNotEqual(first_restored.values["street"], second_restored.values["street"])
        self.assertFalse(second_restored.values["consent"])

    def test_authenticated_draft_resumes_in_the_real_form(self):
        state = submit_address_form("123 rue Exemple, Ville-exemple, QC, Canada", "Ville-exemple", "H2X1Y4", consent=True)
        save_draft(1, {"address_form": serialize_address_form(state)}, 2, self.db)
        app = self._app(authenticated=True)
        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.session_state["address_form_editor_street"], "123 rue Exemple, Ville-exemple, QC, Canada")
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")
        self.assertEqual(app.text_input(key="address_form_postal").value, "H2X 1Y4")
        self.assertTrue(app.checkbox(key="address_form_consent").value)
        app.run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")

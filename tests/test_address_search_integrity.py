"""Regressions discovered by the real-address acceptance audit."""
import unittest
from unittest.mock import patch

from domain.address import normalize_address
from services.quebec_address_geocoder import (
    AddressSuggestion, _candidate_to_suggestion, _parse_response,
    clear_suggestion_cache, resolve_freeform_address, resolve_suggestion, suggest_addresses,
)


def candidate(number=350, street="Boulevard Exemple Ouest", direction="Ouest", unit=""):
    return {"attributes": {"Num": number, "Odonyme": street, "Dir": direction,
                           "Unite": unit, "City": "Ville-exemple", "ZIP": "H2X1Y4"}}


class AddressSearchIntegrityTests(unittest.TestCase):
    def setUp(self):
        clear_suggestion_cache()

    def test_direction_is_not_appended_twice(self):
        item = _candidate_to_suggestion(candidate())
        self.assertEqual(item.street, "350 Boulevard Exemple Ouest")
        self.assertEqual(_candidate_to_suggestion(candidate(street="Boulevard Exemple")).street,
                         "350 Boulevard Exemple Ouest")

    def test_units_at_one_address_have_distinct_labels_and_survive_merge(self):
        from components.property_analysis import _merge_address_suggestions
        items = _parse_response({"candidates": [candidate(unit="A"), candidate(unit="B")]})
        self.assertEqual(len(items), 2)
        self.assertEqual(len({item.label for item in items}), 2)
        self.assertIn("Unité A", items[0].label)
        self.assertEqual(len(_merge_address_suggestions(items, [])), 2)

    def test_empty_suggestions_try_the_official_candidate_operation(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return {"suggestions": []} if "/suggest?" in url else {"candidates": [candidate()]}
        result = suggest_addresses("350 boul Exemple Ouest", True, fetch_json=fetch, now=lambda: 10)
        self.assertEqual(result.suggestions[0].street, "350 Boulevard Exemple Ouest")
        self.assertEqual(len(calls), 2)

    def test_expired_suggestion_key_recovers_only_the_exact_selected_label(self):
        selected = _candidate_to_suggestion(candidate())
        selected = AddressSuggestion("", "", "", "", selected.label, "expired")
        def fetch(url):
            if "magicKey=" in url:
                raise TimeoutError()
            return {"candidates": [candidate()]}
        self.assertEqual(resolve_suggestion(selected, True, fetch_json=fetch).street,
                         "350 Boulevard Exemple Ouest")
        def wrong_city(url):
            if "magicKey=" in url:
                return {"candidates": []}
            data = candidate(); data["attributes"]["City"] = "Autre ville"
            return {"candidates": [data]}
        self.assertIsNone(resolve_suggestion(selected, True, fetch_json=wrong_city))

    def test_complete_query_cannot_resolve_to_a_different_civic_number(self):
        result = resolve_freeform_address("70 rue Exemple", True,
            fetch_json=lambda _: {"candidates": [candidate(number=470)]}, now=lambda: 10)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.suggestions, ())
        selected = AddressSuggestion("", "", "", "", "70 rue Exemple, Ville-exemple", "opaque")
        self.assertIsNone(resolve_suggestion(selected, True,
            fetch_json=lambda _: {"candidates": [candidate(number=470)]}))

    def test_street_only_and_other_building_are_not_full_address_suggestions(self):
        result = suggest_addresses("350 rue Exemple", True, now=lambda: 10,
            fetch_json=lambda _: {"candidates": [candidate(), candidate(number=3500), candidate(number="")]})
        self.assertEqual([item.street for item in result.suggestions], ["350 Boulevard Exemple Ouest"])

    def test_number_only_search_remains_a_prefix_search(self):
        result = suggest_addresses("350", True, now=lambda: 10,
            fetch_json=lambda _: {"candidates": [candidate(), candidate(number=3500)]})
        self.assertEqual(len(result.suggestions), 2)

    def test_typographic_apostrophes_are_valid_in_real_municipality_names(self):
        for city in ("L’Île-Perrot", "L’Ancienne-Lorette", "Baie-D’Urfé"):
            with self.subTest(city=city):
                self.assertEqual(normalize_address("12 rue Exemple", city, "H2X1Y4").city, city)

    def test_official_index_compares_typography_without_guessing_a_different_city(self):
        from services.quebec_role_sync import municipality_key
        self.assertEqual(municipality_key("L’Île‑Perrot"), municipality_key("L'Île-Perrot"))
        self.assertNotEqual(municipality_key("L’Île-Perrot"), municipality_key("Notre-Dame-de-l'Île-Perrot"))

    def test_new_official_selection_cannot_inherit_old_postal_code_or_unit(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_string('''
import streamlit as st
from unittest.mock import patch
import components.property_analysis as page
from services.address_form_service import submit_address_form
st.session_state[page.ADDRESS_STATE_KEY] = submit_address_form(
    "123 rue Ancienne", "Ville-ancienne", "H2X1Y4", "A", True)
st.session_state[page.ADDRESS_WIDGET_KEYS["consent"]] = True
st.session_state["official_role_unit"] = 0
with patch.multiple(page, _enrich_local_suggestion=lambda *_: None,
    _official_lookup=lambda *_: {}, _queue_auto_role_sync=lambda *_: None,
    _remember_aerial_image=lambda *_: None, _persist_address_draft=lambda *_: None):
    page._select_address_suggestion({"street": "350 Boulevard Exemple Ouest",
        "city": "Ville-nouvelle", "postal_code": "", "unit": "", "source": "rqa"})
''').run(timeout=20)
        self.assertFalse(app.exception)
        state = app.session_state["address_form_state"]
        self.assertTrue(state.valid)
        self.assertEqual(state.address.city, "Ville-nouvelle")
        self.assertEqual(state.address.postal_code, "")
        self.assertEqual(state.address.unit, "")
        self.assertNotIn("official_role_unit", app.session_state)

    def test_multiple_official_units_require_an_explicit_choice_before_export(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_string('''
import streamlit as st
import components.property_analysis as page
matches=[{"matricule":str(i),"address_text":f"350 Exemple, unité {i}",
    "land_value":100,"building_value":100,"total_value":i*1000,
    "role_year":2026,"market_reference_date":"2024-07-01"} for i in (1,2)]
lookup={"matches":matches,"consent":True,"coverage":True}
page._show_role_overview(lookup)
st.session_state["tested_snapshot"]=page._official_role_snapshot(lookup)
''').run(timeout=20)
        self.assertFalse(app.exception)
        self.assertIsNone(app.selectbox(key="official_role_unit").value)
        self.assertEqual(app.session_state["tested_snapshot"],{})
        app.selectbox(key="official_role_unit").set_value(1).run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["tested_snapshot"]["total_value"],2000)

    def test_requested_apartment_cannot_receive_another_units_assessment(self):
        import components.property_analysis as page
        matches=[{"address_unit":"A","total_value":100000},
                 {"address_unit":"B","total_value":200000}]
        with patch.object(page,"territory_for_municipality",return_value="01023"), \
             patch.object(page,"search_role_units",return_value=matches), \
             patch.object(page,"role_street_variants",return_value=[]):
            found=page._official_lookup_fields("350 rue Exemple","Ville test",True,unit="B")
            self.assertEqual(found["matches"],[matches[1]])
            absent=page._official_lookup_fields("350 rue Exemple","Ville test",True,unit="C")
            self.assertEqual(absent["matches"],[])

    def test_resolver_expands_common_street_abbreviations_without_changing_editor_query(self):
        from urllib.parse import parse_qs,urlsplit
        from services.quebec_address_geocoder import _official_url,_expanded_street_query
        query="350 boul de Maisonneuve O Montreal"
        self.assertEqual(parse_qs(urlsplit(_official_url(query)).query)["SingleLine"],
                         ["350 boulevard de Maisonneuve Ouest Montreal"])
        self.assertEqual(_expanded_street_query("12 ch. du Canal E, Ville-exemple"),
                         "12 chemin du Canal Est, Ville-exemple")
        self.assertEqual(_expanded_street_query("Ville O"),"Ville O")
        self.assertEqual(_expanded_street_query("12 rue Saint-Ours"),"12 rue Saint-Ours")

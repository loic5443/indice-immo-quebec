"""Offline regressions for consented, live MRNF address suggestions."""

from pathlib import Path
import unittest

from services.quebec_address_geocoder import AddressSuggestion, clear_suggestion_cache, resolve_suggestion, suggest_addresses


MRNF_SUGGEST_PAYLOAD = {
    "suggestions": [
        {"text": "123 rue Exemple, Ville-exemple H2X1Y4", "magicKey": "opaque-key-1", "isCollection": False},
        {"text": "rue Exemple, Ville-exemple", "magicKey": "opaque-key-2", "isCollection": False},
    ]
}

MRNF_CANDIDATE_PAYLOAD = {
    "candidates": [
        {
            "address": "123 rue Exemple, Ville-exemple H2X1Y4",
            "location": {"x": -73.57, "y": 45.50},
            "score": 85.24,
            "attributes": {
                "Match_addr": "123 rue Exemple, Ville-exemple H2X1Y4",
                "ZIP": "H2X1Y4",
                "City": "Ville-exemple",
                "Num": 123,
                "Odonyme": "rue Exemple",
                "Dir": "",
                "Unite": "",
                "SufNum": "",
            },
        },
        {
            "address": "rue Exemple, Ville-exemple",
            "location": {"x": -73.57, "y": 45.50},
            "score": 80.0,
            "attributes": {"ZIP": "", "City": "Ville-exemple", "Num": "", "Odonyme": "rue Exemple", "Dir": "", "Unite": "", "SufNum": ""},
        },
    ]
}


class QuebecAddressGeocoderTests(unittest.TestCase):
    def setUp(self):
        clear_suggestion_cache()

    def test_anonymized_candidate_uses_only_public_form_fields(self):
        result = suggest_addresses("123 rue Exemple, Ville-exemple", True, fetch_json=lambda _: MRNF_SUGGEST_PAYLOAD, now=lambda: 10)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.suggestions), 2)
        first = result.suggestions[0]
        self.assertEqual((first.street, first.city, first.postal_code, first.unit), ("", "", "", ""))
        self.assertEqual(first.label, "123 rue Exemple, Ville-exemple H2X1Y4")
        self.assertEqual(first.lookup_key, "opaque-key-1")
        self.assertNotIn("location", first.to_dict())
        self.assertNotIn("score", first.to_dict())
        self.assertNotIn("Match_addr", first.to_dict())

    def test_accents_apostrophes_and_hyphens_reach_mocked_provider_without_rewriting(self):
        received = []
        result = suggest_addresses("12, chemin de l’Église-du-Nord", True, fetch_json=lambda url: received.append(url) or MRNF_SUGGEST_PAYLOAD, now=lambda: 10)
        self.assertEqual(result.status, "ok")
        self.assertIn("/suggest?", received[0])
        self.assertIn("%C3%89glise-du-Nord", received[0])

    def test_no_network_without_consent_or_for_one_or_two_characters(self):
        calls = []
        fetcher = lambda url: calls.append(url) or MRNF_SUGGEST_PAYLOAD
        self.assertEqual(suggest_addresses("123 rue Exemple", False, fetch_json=fetcher, now=lambda: 10).status, "consent_required")
        self.assertEqual(suggest_addresses("12", True, fetch_json=fetcher, now=lambda: 11).status, "too_short")
        self.assertEqual(calls, [])

    def test_three_characters_and_cache_support_live_search_without_duplicate_request(self):
        calls = []
        fetcher = lambda url: calls.append(url) or MRNF_SUGGEST_PAYLOAD
        first = suggest_addresses("123", True, fetch_json=fetcher, now=lambda: 10)
        second = suggest_addresses("123  ", True, fetch_json=fetcher, now=lambda: 11)
        self.assertEqual(first.status, "ok")
        self.assertTrue(second.cached)
        self.assertEqual(len(calls), 1)

    def test_missing_result_and_service_failure_keep_manual_mode(self):
        empty = suggest_addresses("999 rue absente", True, fetch_json=lambda _: {"suggestions": []}, now=lambda: 10)
        self.assertEqual(empty.status, "ok")
        self.assertEqual(empty.suggestions, ())
        clear_suggestion_cache()
        unavailable = suggest_addresses("999 rue absente", True, fetch_json=lambda _: (_ for _ in ()).throw(TimeoutError()), now=lambda: 20)
        self.assertEqual(unavailable.status, "unavailable")
        self.assertNotIn("999", unavailable.message)

    def test_invalid_schema_is_rejected_without_exposing_payload(self):
        result = suggest_addresses("123 rue Exemple", True, fetch_json=lambda _: {"error": {"message": "address secret"}}, now=lambda: 10)
        self.assertEqual(result.status, "unavailable")
        self.assertNotIn("secret", result.message.lower())

    def test_selection_contract_has_no_coordinates_or_query(self):
        suggestion = AddressSuggestion("123 rue Exemple", "Ville-exemple", "H2X 1Y4", "", "123 rue Exemple · Ville-exemple · H2X 1Y4")
        self.assertEqual(set(suggestion.to_dict()), {"street", "city", "postal_code", "unit", "label"})
        self.assertNotIn("lookup_key", suggestion.to_dict())

    def test_selected_option_is_resolved_to_structured_form_fields(self):
        selected = AddressSuggestion("", "", "", "", "123 rue Exemple, Ville-exemple H2X1Y4", "opaque-key")
        requested = []
        resolved = resolve_suggestion(selected, True, fetch_json=lambda url: requested.append(url) or MRNF_CANDIDATE_PAYLOAD)
        self.assertEqual((resolved.street, resolved.city, resolved.postal_code), ("123 rue Exemple", "Ville-exemple", "H2X 1Y4"))
        self.assertIn("findAddressCandidates", requested[0])

    def test_selected_option_is_not_resolved_without_consent(self):
        selected = AddressSuggestion("", "", "", "", "123 rue Exemple, Ville-exemple H2X1Y4", "opaque-key")
        self.assertIsNone(resolve_suggestion(selected, False, fetch_json=lambda _: self.fail("network must not run")))

    def test_provider_does_not_write_to_telemetry_or_diagnostics(self):
        source = Path("services/quebec_address_geocoder.py").read_text(encoding="utf-8")
        self.assertNotIn("record_event", source)
        self.assertNotIn("record_error", source)


class QuebecAddressGeocoderUiTests(unittest.TestCase):
    def test_searchbox_is_debounced_and_selection_populates_fields(self):
        from streamlit.testing.v1 import AppTest

        source = '''
import streamlit as st
import components.property_analysis as page
def fake_searchbox(search_function, **kwargs):
    st.session_state["observed_debounce"] = kwargs["debounce"]
    if not st.session_state.get("selected_once"):
        st.session_state["selected_once"] = True
        kwargs["submit_function"]({"street":"123 rue Exemple", "city":"Ville-exemple", "postal_code":"H2X 1Y4", "unit":"", "label":"123 rue Exemple · Ville-exemple · H2X 1Y4"})
page.st_searchbox = fake_searchbox
page.resolve_suggestion = lambda *_: page.AddressSuggestion("123 rue Exemple", "Ville-exemple", "H2X 1Y4", "", "123 rue Exemple · Ville-exemple · H2X 1Y4")
page.show_property_analysis()
'''
        app = AppTest.from_string(source).run(timeout=20)
        self.assertEqual(app.session_state["observed_debounce"], 400)
        self.assertEqual(app.text_input(key="address_form_city").value, "Ville-exemple")
        self.assertEqual(app.text_input(key="address_form_postal").value, "H2X 1Y4")
        self.assertEqual(list(app.error), [])

    def test_manual_mode_never_calls_provider(self):
        from streamlit.testing.v1 import AppTest

        source = '''
import streamlit as st
import components.property_analysis as page
st.session_state.setdefault("address_form_consent", True)
st.session_state.setdefault("address_form_manual_mode", True)
page.suggest_addresses = lambda query, consent: (_ for _ in ()).throw(AssertionError("provider should not run"))
def fake_searchbox(search_function, **kwargs):
    st.session_state["manual_options"] = search_function("123 rue Exemple")
page.st_searchbox = fake_searchbox
page.show_property_analysis()
'''
        app = AppTest.from_string(source).run(timeout=20)
        self.assertEqual(app.session_state["manual_options"], [])
        self.assertTrue(any("Mode manuel actif" in item.value for item in app.caption))

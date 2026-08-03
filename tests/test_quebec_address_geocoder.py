"""Offline regressions for the consented MRNF address suggestion provider."""

import unittest
from pathlib import Path

from services.quebec_address_geocoder import (
    AddressSuggestion,
    SuggestionResponse,
    clear_suggestion_cache,
    suggest_addresses,
)


MRNF_PAYLOAD = {
    "candidates": [
        {
            "address": "262 Rue Edgar-Hébert, Beauharnois J6N0A4",
            "location": {"x": -73.8786, "y": 45.3019},
            "score": 85.24,
            "attributes": {
                "Match_addr": "262 Rue Edgar-Hébert, Beauharnois J6N0A4",
                "ZIP": "J6N0A4",
                "City": "Beauharnois",
                "Num": 262,
                "Odonyme": "Rue Edgar-Hébert",
                "Dir": "",
                "Unite": "",
                "SufNum": "",
            },
        },
        {
            "address": "Rue Edgar-Hébert, Beauharnois",
            "location": {"x": -73.87, "y": 45.30},
            "score": 95.71,
            "attributes": {"ZIP": "", "City": "Beauharnois", "Num": "", "Odonyme": "Rue Edgar-Hébert", "Dir": "", "Unite": "", "SufNum": ""},
        },
    ]
}


class QuebecAddressGeocoderTests(unittest.TestCase):
    def setUp(self):
        clear_suggestion_cache()

    def test_beauharnois_candidate_uses_only_public_form_fields(self):
        result = suggest_addresses("262 Rue Edgar-Hébert, Beauharnois", True, fetch_json=lambda _: MRNF_PAYLOAD, now=lambda: 10)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.suggestions), 2)
        first = result.suggestions[0]
        self.assertEqual(first.street, "262 Rue Edgar-Hébert")
        self.assertEqual(first.city, "Beauharnois")
        self.assertEqual(first.postal_code, "J6N 0A4")
        self.assertEqual(first.unit, "")
        self.assertNotIn("location", first.to_dict())
        self.assertNotIn("score", first.to_dict())
        self.assertNotIn("Match_addr", first.to_dict())

    def test_accents_apostrophes_and_hyphens_reach_mocked_provider_without_rewriting(self):
        received = []
        result = suggest_addresses("12, chemin de l’Église-du-Nord", True, fetch_json=lambda url: received.append(url) or MRNF_PAYLOAD, now=lambda: 10)
        self.assertEqual(result.status, "ok")
        self.assertIn("%C3%89glise-du-Nord", received[0])

    def test_no_network_without_consent_or_for_short_query(self):
        calls = []
        fetcher = lambda url: calls.append(url) or MRNF_PAYLOAD
        self.assertEqual(suggest_addresses("262 Rue Edgar-Hébert", False, fetch_json=fetcher, now=lambda: 10).status, "consent_required")
        self.assertEqual(suggest_addresses("262", True, fetch_json=fetcher, now=lambda: 11).status, "too_short")
        self.assertEqual(calls, [])

    def test_cache_avoids_repeated_request_for_identical_rerun(self):
        calls = []
        fetcher = lambda url: calls.append(url) or MRNF_PAYLOAD
        first = suggest_addresses("262 Rue Edgar-Hébert", True, fetch_json=fetcher, now=lambda: 10)
        second = suggest_addresses("262   Rue Edgar-Hébert", True, fetch_json=fetcher, now=lambda: 11)
        self.assertEqual(first.status, "ok")
        self.assertTrue(second.cached)
        self.assertEqual(len(calls), 1)

    def test_missing_result_and_service_failure_keep_manual_mode(self):
        empty = suggest_addresses("999 Rue inconnue", True, fetch_json=lambda _: {"candidates": []}, now=lambda: 10)
        self.assertEqual(empty.status, "ok")
        self.assertEqual(empty.suggestions, ())
        clear_suggestion_cache()
        unavailable = suggest_addresses("999 Rue inconnue", True, fetch_json=lambda _: (_ for _ in ()).throw(TimeoutError()), now=lambda: 20)
        self.assertEqual(unavailable.status, "unavailable")
        self.assertNotIn("999", unavailable.message)

    def test_invalid_schema_is_rejected_without_exposing_payload(self):
        result = suggest_addresses("262 Rue Edgar-Hébert", True, fetch_json=lambda _: {"error": {"message": "address secret"}}, now=lambda: 10)
        self.assertEqual(result.status, "unavailable")
        self.assertNotIn("secret", result.message.lower())

    def test_selection_contract_has_no_coordinates_or_query(self):
        suggestion = AddressSuggestion("262 Rue Edgar-Hébert", "Beauharnois", "J6N 0A4", "", "262 Rue Edgar-Hébert · Beauharnois · J6N 0A4")
        self.assertEqual(set(suggestion.to_dict()), {"street", "city", "postal_code", "unit", "label"})

    def test_provider_does_not_write_to_telemetry_or_diagnostics(self):
        source = Path("services/quebec_address_geocoder.py").read_text(encoding="utf-8")
        self.assertNotIn("record_event", source)
        self.assertNotIn("record_error", source)


class QuebecAddressGeocoderUiTests(unittest.TestCase):
    def test_selecting_suggestion_populates_fields_without_saving_or_looking_up(self):
        from streamlit.testing.v1 import AppTest

        source = '''
import components.property_analysis as page
from services.quebec_address_geocoder import AddressSuggestion, SuggestionResponse
page.suggest_addresses = lambda query, consent: SuggestionResponse("ok", (AddressSuggestion("262 Rue Edgar-Hébert", "Beauharnois", "J6N 0A4", "", "262 Rue Edgar-Hébert · Beauharnois · J6N 0A4"),))
page.source_enabled = lambda source_id, database_path: True
page.show_property_analysis()
'''
        app = AppTest.from_string(source).run(timeout=20)
        app.checkbox(key="address_form_consent").set_value(True).run(timeout=20)
        app.text_input(key="address_form_street").set_value("262 Rue Edgar-Hébert").run(timeout=20)
        self.assertIsNotNone(app.button(key="address_suggestion_0"))
        app.button(key="address_suggestion_0").click().run(timeout=20)
        self.assertEqual(app.text_input(key="address_form_street").value, "262 Rue Edgar-Hébert")
        self.assertEqual(app.text_input(key="address_form_city").value, "Beauharnois")
        self.assertEqual(app.text_input(key="address_form_postal").value, "J6N 0A4")
        self.assertEqual(list(app.error), [])

    def test_disabled_source_stays_manual_and_never_calls_provider(self):
        from streamlit.testing.v1 import AppTest

        source = '''
import components.property_analysis as page
page.source_enabled = lambda source_id, database_path: False
page.suggest_addresses = lambda query, consent: (_ for _ in ()).throw(AssertionError("provider should not run"))
page.show_property_analysis()
'''
        app = AppTest.from_string(source).run(timeout=20)
        app.text_input(key="address_form_street").set_value("262 Rue Edgar-Hébert")
        app.checkbox(key="address_form_consent").set_value(True).run(timeout=20)
        self.assertTrue(any("temporairement indisponibles" in item.value for item in app.info))

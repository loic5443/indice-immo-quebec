"""Offline tests for the consented official aerial-image context."""

from io import BytesIO
from base64 import b64encode
from pathlib import Path
import unittest

from PIL import Image, ImageDraw

from services.quebec_aerial_imagery import (
    MAX_IMAGE_BYTES,
    SOURCE_LABEL,
    fetch_aerial_image,
)
from services.quebec_address_geocoder import AddressSuggestion


def _image_bytes() -> bytes:
    """Create a non-uniform anonymous PNG without a real property image."""

    image = Image.new("RGB", (40, 30), "#356f45")
    ImageDraw.Draw(image).rectangle((0, 0, 20, 15), fill="#a8c478")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class QuebecAerialImageryTests(unittest.TestCase):
    def test_consent_is_required_before_any_official_request(self):
        calls: list[str] = []
        result = fetch_aerial_image(-73.5, 45.5, False, fetch_image=lambda url: calls.append(url) or (_image_bytes(), "image/png"))
        self.assertEqual(result.status, "consent_required")
        self.assertEqual(calls, [])

    def test_valid_official_image_is_bounded_and_attributed(self):
        calls: list[str] = []
        result = fetch_aerial_image(-73.5, 45.5, True, fetch_image=lambda url: calls.append(url) or (_image_bytes(), "image/png"))
        self.assertEqual(result.status, "available")
        self.assertEqual(result.acquisition_year, 2025)
        self.assertEqual(result.mime_type, "image/png")
        self.assertTrue(result.image_bytes)
        self.assertEqual(len(calls), 1)
        self.assertIn("servicesmatriciels.mern.gouv.qc.ca", calls[0])
        self.assertNotIn("address", calls[0].lower())
        self.assertIn("MRNF", SOURCE_LABEL)

    def test_blank_or_invalid_render_falls_back_without_blocking(self):
        blank = BytesIO()
        Image.new("RGB", (20, 20), "white").save(blank, format="PNG")
        result = fetch_aerial_image(-73.5, 45.5, True, fetch_image=lambda _: (blank.getvalue(), "image/png"))
        self.assertEqual(result.status, "unavailable")
        self.assertIn("continuer", result.message)
        too_large = fetch_aerial_image(-73.5, 45.5, True, fetch_image=lambda _: (b"x" * (MAX_IMAGE_BYTES + 1), "image/png"))
        self.assertEqual(too_large.status, "unavailable")

    def test_invalid_coordinates_never_start_a_request(self):
        result = fetch_aerial_image("not-a-coordinate", 45.5, True, fetch_image=lambda _: self.fail("request must not run"))
        self.assertEqual(result.status, "unavailable")

    def test_coordinates_stay_out_of_safe_suggestion_serialization(self):
        suggestion = AddressSuggestion(
            "123 rue Exemple", "Ville-exemple", "H2X 1Y4", "", "123 rue Exemple · Ville-exemple",
            longitude=-73.5, latitude=45.5,
        )
        self.assertNotIn("longitude", suggestion.to_dict())
        self.assertNotIn("latitude", suggestion.to_dict())

    def test_implementation_has_no_telemetry_or_persistent_storage(self):
        source = Path("services/quebec_aerial_imagery.py").read_text(encoding="utf-8")
        self.assertNotIn("record_event", source)
        self.assertNotIn("record_error", source)
        self.assertNotIn("sqlite", source.lower())
        self.assertNotIn("Path(", source)

    def test_revealed_public_result_shows_only_a_labelled_aerial_context(self):
        from streamlit.testing.v1 import AppTest

        encoded_image = b64encode(_image_bytes()).decode("ascii")
        source = f'''
import streamlit as st
from base64 import b64decode
from components.property_analysis import ADDRESS_AERIAL_IMAGE_KEY, _show_aerial_view
st.session_state[ADDRESS_AERIAL_IMAGE_KEY] = {{
    "status": "available", "image_bytes": b64decode("{encoded_image}"),
    "mime_type": "image/png", "acquisition_year": 2025, "message": "",
}}
_show_aerial_view({{"consent": True, "matches": [{{"total_value": 1}}]}})
'''
        app = AppTest.from_string(source).run(timeout=20)
        headings = [item.value for item in app.markdown]
        captions = [item.value for item in app.caption]
        self.assertTrue(any("contexte visuel" in value.lower() for value in headings))
        self.assertTrue(any("ImmoValue" in value for value in captions))

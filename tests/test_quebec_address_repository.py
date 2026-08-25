"""No-network coverage for the local, consent-gated Québec address cache."""

from __future__ import annotations

import csv
import io
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from data.database import initialize_database
from streamlit.testing.v1 import AppTest
from services.quebec_address_repository import (
    RQA_ARCHIVE_URL,
    import_rqa_archive,
    present_rqa_text,
    suggest_rqa_addresses,
    synchronize_rqa_snapshot,
)


HEADERS = [
    "identifiant_unique_adresse", "numero_municipal", "numero_municipal_suffixe", "numero_unite",
    "code_postal", "odonyme_recompose_normal", "adresse_formatee", "nom_municipalite",
    "nom_municipalite_complet", "code_municipalite", "date_fin", "longitude", "latitude",
]


def row(identifier: str, number: str, street: str, city: str, postal: str = "H2X 1Y4", **extra: str) -> dict[str, str]:
    values = {header: "" for header in HEADERS}
    values.update({
        "identifiant_unique_adresse": identifier,
        "numero_municipal": number,
        "code_postal": postal,
        "odonyme_recompose_normal": street,
        "adresse_formatee": f"{number} {street}, {city}",
        "nom_municipalite": city,
        "code_municipalite": "99999",
        "longitude": "-73.57",
        "latitude": "45.51",
    })
    values.update(extra)
    return values


def archive(path: Path, rows: list[dict[str, str]], headers: list[str] = HEADERS) -> None:
    content = io.StringIO()
    writer = csv.DictWriter(content, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    with ZipFile(path, "w") as output:
        output.writestr("RQA.csv", content.getvalue().encode("utf-8"))


class QuebecAddressRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "rqa.sqlite"
        initialize_database(self.db)
        self.snapshot = self.root / "rqa.zip"

    def tearDown(self):
        self.temp.cleanup()

    def test_import_is_public_minimal_and_searches_normalized_prefixes(self):
        archive(self.snapshot, [
            row("public-1", "123", "RUE DE L’ÉGLISE", "Ville-Test"),
            row("public-2", "124", "RUE DE L’ÉGLISE", "Ville-Test", date_fin="2026-01-01"),
        ])
        result = import_rqa_archive(self.snapshot, self.db)
        self.assertEqual((result.status, result.imported_rows), ("ready", 2))
        results = suggest_rqa_addresses(self.db, "123 rue eglise")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["postal_code"], "H2X 1Y4")
        self.assertEqual(results[0]["municipality"], "Ville-Test")
        self.assertEqual(results[0]["municipality_code"], "99999")
        self.assertEqual(suggest_rqa_addresses(self.db, "église")[0]["civic_number"], "123")
        with closing(sqlite3.connect(self.db)) as connection:
            columns = {entry[1] for entry in connection.execute("PRAGMA table_info(rqa_addresses)")}
        self.assertFalse({"owner", "proprietaire", "assessment", "value"} & columns)

    def test_new_snapshot_switches_atomically_and_invalid_snapshot_preserves_previous(self):
        archive(self.snapshot, [row("old", "10", "RUE PUBLIQUE", "Ville-Test")])
        self.assertEqual(import_rqa_archive(self.snapshot, self.db).status, "ready")
        replacement = self.root / "replacement.zip"
        archive(replacement, [row("new", "20", "CHEMIN NOUVEAU", "Ville-Test")])
        self.assertEqual(import_rqa_archive(replacement, self.db).status, "ready")
        self.assertFalse(suggest_rqa_addresses(self.db, "10 publique"))
        self.assertEqual(suggest_rqa_addresses(self.db, "20 nouveau")[0]["street_name"], "CHEMIN NOUVEAU")
        broken = self.root / "broken.zip"
        archive(broken, [{"identifiant_unique_adresse": "bad"}], ["identifiant_unique_adresse"])
        with self.assertRaises(ValueError):
            import_rqa_archive(broken, self.db)
        self.assertEqual(suggest_rqa_addresses(self.db, "20 nouveau")[0]["street_name"], "CHEMIN NOUVEAU")

    def test_limit_and_presentation_are_bounded(self):
        archive(self.snapshot, [row(f"row-{index}", str(index), "RUE EXEMPLE", "Ville-Test") for index in range(1, 12)])
        import_rqa_archive(self.snapshot, self.db)
        self.assertEqual(len(suggest_rqa_addresses(self.db, "rue exemple", limit=99)), 8)
        self.assertEqual(present_rqa_text("RUE D'EXEMPLE"), "Rue d'Exemple")

    def test_synchronization_uses_a_temporary_file_and_deletes_it(self):
        archive(self.snapshot, [row("public-1", "123", "RUE PUBLIQUE", "Ville-Test")])

        def fake_download(_url: str, destination: Path) -> int:
            destination.write_bytes(self.snapshot.read_bytes())
            return destination.stat().st_size

        with patch("services.quebec_address_repository._download_archive", side_effect=fake_download):
            self.assertEqual(synchronize_rqa_snapshot(self.db).status, "ready")
        self.assertEqual(suggest_rqa_addresses(self.db, "123 publique")[0]["municipality"], "Ville-Test")

    def test_rqa_results_are_used_before_external_geocoding_when_consent_exists(self):
        """UI adapter keeps the privacy gate and avoids network when RQA matches."""
        import components.property_analysis as page
        archive(self.snapshot, [row("public-1", "123", "RUE PUBLIQUE", "Ville-Test")])
        import_rqa_archive(self.snapshot, self.db)
        source = (
            "import streamlit as st\n"
            "import components.property_analysis as page\n"
            "st.session_state.setdefault('address_form_consent', True)\n"
            "st.session_state.setdefault('address_form_street_input', '123 rue Pub')\n"
            "page.show_property_analysis()\n"
        )
        with (
            patch.object(page, "DATABASE_PATH", self.db),
            patch.object(page, "suggest_addresses", side_effect=AssertionError("no external lookup")),
            patch.object(page, "_queue_auto_role_sync", return_value=None),
        ):
            app = AppTest.from_string(source).run(timeout=20)
            self.assertEqual(app.button(key="address_suggestion_select_0").label, "123 Rue Publique · Ville-Test · H2X 1Y4")
        self.assertEqual(list(app.exception), [])

    def test_rqa_selection_queues_its_exact_geographic_code_for_one_role_sync(self):
        """RQA does not fall back to a fuzzy municipality name before import."""
        import components.property_analysis as page
        from services.quebec_role_auto_sync import AutoSyncResult

        archive(self.snapshot, [row("public-1", "123", "RUE PUBLIQUE", "Ville-Test", code_municipalite="01023")])
        import_rqa_archive(self.snapshot, self.db)
        source = (
            "import streamlit as st\n"
            "import components.property_analysis as page\n"
            "st.session_state.setdefault('address_form_consent', True)\n"
            "st.session_state.setdefault('address_form_street_input', '123 rue Pub')\n"
            "page.show_property_analysis()\n"
        )
        with (
            patch.object(page, "DATABASE_PATH", self.db),
            patch.object(page, "suggest_addresses", side_effect=AssertionError("no external lookup")),
            patch.object(page, "synchronize_selected_territory", return_value=AutoSyncResult("available", "Renseignements officiels disponibles.", "01023")) as sync,
        ):
            app = AppTest.from_string(source).run(timeout=20)
            app.button(key="address_suggestion_select_0").click().run(timeout=20)
        sync.assert_called_once_with(self.db, "01023", True)
        self.assertEqual(list(app.exception), [])


if __name__ == "__main__":
    unittest.main()

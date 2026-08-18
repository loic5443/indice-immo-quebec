"""Targeted no-network tests for controlled on-demand municipal role sync."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data.database import initialize_database
from streamlit.testing.v1 import AppTest
from services.quebec_role_auto_sync import (
    AutoSyncResult,
    resolve_official_territory,
    synchronize_selected_municipality,
)


INDEX = (
    "code géographique,nom du territoire,lien,date de modification\n"
    "01023,Ville test,https://mamh.gouv.qc.ca/role/RM01023.xml,2026-01-01\n"
).encode()
XML = (
    b'\xef\xbb\xbf<?xml version="1.0"?><RL><VERSION>2.9</VERSION><RLM01A>01023</RLM01A>'
    b'<RLM02A>2026</RLM02A><RLUEx><RL0101><RL0101Ax>12</RL0101Ax>'
    b'<RL0101Gx>RUE PUBLIQUE</RL0101Gx></RL0101><RL0104><RL0104A>1</RL0104A>'
    b'</RL0104><RL0402A>100</RL0402A><RL0403A>200</RL0403A><RL0404A>300</RL0404A>'
    b'</RLUEx></RL>'
)


class ControlledAutoRoleSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "auto-role.sqlite"
        initialize_database(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def _sync(self, fetcher=lambda _: XML):
        return synchronize_selected_municipality(self.db, "Ville test", True, fetcher=fetcher, index_fetcher=lambda _: INDEX)

    def test_exact_official_index_entry_syncs_one_territory_atomically(self):
        result = self._sync()
        self.assertEqual(result.status, "synchronized")
        self.assertEqual(result.territory_code, "01023")
        self.assertEqual(result.imported_units, 1)
        self.assertEqual(result.size_bytes, len(XML))
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM role_assessment_units WHERE territory_code='01023'").fetchone()[0], 1)
            history = connection.execute("SELECT detail FROM role_sync_history WHERE territory_code='01023'").fetchall()
        self.assertEqual(history[-1][0], "official_xml_validated")

    def test_existing_active_cache_never_downloads_again(self):
        self._sync()
        result = self._sync(lambda _: (_ for _ in ()).throw(AssertionError("must use cached territory")))
        self.assertEqual(result.status, "available")

    def test_disabled_territory_is_never_reactivated_or_downloaded(self):
        resolve_official_territory(self.db, "Ville test", index_fetcher=lambda _: INDEX)
        with sqlite3.connect(self.db) as connection, connection:
            connection.execute("INSERT INTO role_territory_settings(territory_code,enabled) VALUES('01023',0)")
        result = self._sync(lambda _: (_ for _ in ()).throw(AssertionError("disabled territory must not download")))
        self.assertEqual(result.status, "territory_disabled")

    def test_disabled_source_never_downloads(self):
        with sqlite3.connect(self.db) as connection, connection:
            connection.execute("UPDATE data_sources SET enabled=0 WHERE source_id='mamh_quebec_assessment_rolls'")
        result = self._sync(lambda _: (_ for _ in ()).throw(AssertionError("disabled source must not download")))
        self.assertEqual(result.status, "source_disabled")

    def test_failure_cools_down_without_repeated_downloads(self):
        calls = []

        def failing_fetcher(_):
            calls.append(1)
            raise ValueError("official_network_unavailable")

        self.assertEqual(self._sync(failing_fetcher).status, "failed")
        self.assertEqual(self._sync(failing_fetcher).status, "cooldown")
        self.assertEqual(len(calls), 1)

    def test_persistent_lock_prevents_parallel_import(self):
        resolve_official_territory(self.db, "Ville test", index_fetcher=lambda _: INDEX)
        with sqlite3.connect(self.db) as connection, connection:
            connection.execute("INSERT INTO role_auto_sync_locks(territory_code,acquired_at) VALUES('01023',datetime('now'))")
        self.assertEqual(self._sync().status, "in_progress")

    def test_incompatible_xml_keeps_the_territory_empty_and_allows_manual_mode(self):
        incompatible = XML.replace(b"<VERSION>2.9</VERSION>", b"<VERSION>3.0</VERSION>")
        result = self._sync(lambda _: incompatible)
        self.assertEqual(result.status, "unsupported_format")
        self.assertIn("format", result.message)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM role_assessment_units").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT error_code FROM role_auto_sync_attempts WHERE territory_code='01023'").fetchone()[0], "unsupported_xml_format")

    def test_non_exact_municipality_is_not_guessed(self):
        resolve_official_territory(self.db, "Ville test", index_fetcher=lambda _: INDEX)
        result = synchronize_selected_municipality(self.db, "Ville test voisine", True, fetcher=lambda _: XML)
        self.assertEqual(result.status, "not_covered")

    def test_no_consent_does_not_fetch_or_record_user_data(self):
        result = synchronize_selected_municipality(
            self.db, "Ville test", False, fetcher=lambda _: (_ for _ in ()).throw(AssertionError("no consent"))
        )
        self.assertEqual(result.status, "consent_required")
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM role_sync_history").fetchone()[0], 0)

    def test_selected_address_triggers_one_controlled_sync_in_the_analysis_ui(self):
        """The public selection works without an administrator and reveals the imported role."""
        import components.property_analysis as page
        from services.quebec_address_geocoder import AddressSuggestion, SuggestionResponse

        suggestion = AddressSuggestion(
            "12 rue Publique", "Ville test", "H2X 1Y4", "", "12 rue Publique · Ville test · H2X 1Y4", "opaque", "external"
        )
        source = (
            "from pathlib import Path\n"
            "import streamlit as st\n"
            "import components.property_analysis as page\n"
            f"page.DATABASE_PATH = Path({str(self.db)!r})\n"
            "st.session_state.setdefault('address_form_consent', True)\n"
            "st.session_state.setdefault('address_form_street_input', '12 rue Pub')\n"
            "page.show_property_analysis()\n"
        )
        with (
            patch.object(page, "suggest_addresses", return_value=SuggestionResponse("ok", (suggestion,))),
            patch.object(page, "resolve_suggestion", side_effect=lambda item, _: item),
            patch.object(
                page,
                "synchronize_selected_municipality",
                side_effect=lambda database, city, consent: synchronize_selected_municipality(
                    database, city, consent, fetcher=lambda _: XML, index_fetcher=lambda _: INDEX
                ),
            ),
        ):
            app = AppTest.from_string(source).run(timeout=20)
            app.button(key="address_suggestion_select_0").click().run(timeout=20)
        self.assertIn("Total au rôle", [metric.label for metric in app.metric])
        self.assertEqual(len(app.status), 1)
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM role_territory_imports WHERE territory_code='01023'").fetchone()[0], 1)

"""Renaming generated provenance must preserve existing accounts and dossiers."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from data.database import initialize_database, create_user, authenticate_user
from migrations.runner import applied_migrations
from services.demo_service import demo_snapshot
from data.database import save_analysis, list_analyses


class BrandMigrationTests(unittest.TestCase):
    def test_existing_account_and_dossier_survive_brand_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / 'accounts.sqlite'
            initialize_database(db)
            self.assertTrue(create_user('Compte existant', 'brand@example.test', 'fixture-password-only-123', db)[0])
            snapshot, _ = demo_snapshot()
            analysis_id = save_analysis(1, 'Dossier conservé', snapshot, db)
            legacy = "Hypothèses saisies par l'utilisateur; calculs financiers ImmoRadar; aucune estimation de valeur."
            with closing(sqlite3.connect(db)) as connection, connection:
                connection.execute("DELETE FROM schema_migrations WHERE version='0029'")
                connection.execute('UPDATE analyses SET data_provenance=? WHERE id=?', (legacy, analysis_id))
                user_before = connection.execute('SELECT * FROM users WHERE id=1').fetchone()
                analysis_before = connection.execute('SELECT price,cash_flow,financial_inputs_json,official_role_snapshot_json FROM analyses WHERE id=?', (analysis_id,)).fetchone()
            self.assertEqual(initialize_database(db), ['0029'])
            self.assertIsNotNone(authenticate_user('brand@example.test', 'fixture-password-only-123', db))
            analyses = list_analyses(1, db)
            self.assertEqual(len(analyses), 1)
            self.assertEqual(analyses[0]['property_name'], 'Dossier conservé')
            self.assertEqual(analyses[0]['data_provenance'], legacy.replace('ImmoRadar', 'Cenlio'))
            with closing(sqlite3.connect(db)) as connection:
                self.assertEqual(connection.execute('SELECT * FROM users WHERE id=1').fetchone(), user_before)
                self.assertEqual(connection.execute('SELECT price,cash_flow,financial_inputs_json,official_role_snapshot_json FROM analyses WHERE id=?', (analysis_id,)).fetchone(), analysis_before)
            self.assertEqual(initialize_database(db), [])
            self.assertIn('0029', applied_migrations(db))

import tempfile
import unittest
from pathlib import Path

from data.database import create_user, initialize_database
from domain.models import UserProfile
from services.privacy_service import delete_account, export_user_data
from services.telemetry_service import record_event

class PrivacyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/"beta.db"; initialize_database(self.db)
        create_user("Beta", "beta@example.com", "motdepasse-solide", self.db, UserProfile())
    def tearDown(self): self.tmp.cleanup()
    def test_export_excludes_password_and_deletion_removes_account(self):
        exported=export_user_data(1,self.db); self.assertNotIn("password_hash",exported); self.assertTrue(delete_account(1,self.db)); self.assertIsNone(export_user_data(1,self.db))
    def test_telemetry_uses_only_allowlisted_event_name(self):
        record_event(1,"analysis_started",self.db); record_event(1,"address",self.db)
        from repositories.sqlite_repository import SQLiteRepository
        from contextlib import closing
        with closing(SQLiteRepository(self.db)._connect()) as con: self.assertEqual(con.execute("SELECT COUNT(*) FROM privacy_events").fetchone()[0],1)

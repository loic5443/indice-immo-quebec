import tempfile,unittest
from pathlib import Path
from data.database import initialize_database
from services.telemetry_service import aggregate_events,record_event
class TelemetryTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.db=Path(self.t.name)/"t.db";initialize_database(self.db);self.p={"event_name":"analysis_started","event_version":"1","page_code":"analysis"}
 def tearDown(self):self.t.cleanup()
 def test_consent_allowlist_sensitive_and_idempotence(self):
  self.assertFalse(record_event(None,self.p,self.db,False,"a"));self.assertTrue(record_event(None,self.p,self.db,True,"a"));self.assertFalse(record_event(None,self.p,self.db,True,"a"))
  with self.assertRaises(ValueError):record_event(None,{"event_name":"analysis_started","price":1},self.db,True)
  self.assertEqual(aggregate_events(self.db)["analysis_started"],None)

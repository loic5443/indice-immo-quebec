import unittest
import tempfile
from pathlib import Path
from services.usage_measurement import record, summary

class UsageTest(unittest.TestCase):
    def test_consent_deduplication_and_funnel(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Path(directory)/"usage.db"
            self.assertFalse(record(db,"a"*32,"visit"))
            self.assertFalse(db.exists())
            for _ in range(3):
                record(db,"a"*32,"visit",True)
            record(db,"b"*32,"visit",True)
            record(db,"a"*32,"analysis_completed",True)
            self.assertEqual(summary(db)["visit"],2)
            self.assertEqual(summary(db)["analysis_completed"],1)
            with self.assertRaises(ValueError): record(db,"someone@example.com","visit",True)
            with self.assertRaises(ValueError): record(db,"a"*32,"address",True)

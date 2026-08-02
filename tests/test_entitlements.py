import tempfile,unittest
from pathlib import Path
from data.database import initialize_database,create_user
from domain.models import UserProfile
from repositories.sqlite_repository import SQLiteRepository
from services.entitlements_service import consume_estimation,quota_status
class EntitlementsTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.db=Path(self.t.name)/"q.db";initialize_database(self.db);create_user("Q","q@q.ca","motdepasse-solide",self.db,UserProfile());self.user=SQLiteRepository(self.db).get_user_by_id(1)
 def tearDown(self):self.t.cleanup()
 def test_free_quota_is_idempotent(self):
  self.assertTrue(consume_estimation(1,self.user,self.db,"x"));self.assertTrue(consume_estimation(1,self.user,self.db,"x"));self.assertEqual(quota_status(1,self.user,self.db)["remaining"],0)

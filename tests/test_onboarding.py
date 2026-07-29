import tempfile, unittest
from pathlib import Path
from data.database import create_user, initialize_database
from domain.models import UserProfile
from repositories.sqlite_repository import SQLiteRepository
from services.onboarding_service import complete, progress

class OnboardingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/"onboarding.db"; initialize_database(self.db); create_user("Test", "test@example.com", "motdepasse-solide", self.db, UserProfile())
 def tearDown(self): self.tmp.cleanup()
 def test_interruption_resume_and_completion(self):
  progress(1,self.db,onboarding_step=3,user_objective="Acheter")
  self.assertEqual(SQLiteRepository(self.db).get_user_by_id(1)["onboarding_step"],3)
  self.assertFalse(complete(1,self.db)); progress(1,self.db,limitations_accepted=1)
  self.assertTrue(complete(1,self.db)); self.assertEqual(SQLiteRepository(self.db).get_user_by_id(1)["onboarding_completed"],1)

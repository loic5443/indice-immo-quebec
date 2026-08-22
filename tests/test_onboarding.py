import tempfile, unittest
from pathlib import Path
from data.database import create_user, initialize_database
from domain.models import UserProfile
from repositories.sqlite_repository import SQLiteRepository
from services.onboarding_service import complete, progress
from streamlit.testing.v1 import AppTest

class OnboardingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/"onboarding.db"; initialize_database(self.db); create_user("Test", "test@example.com", "motdepasse-solide", self.db, UserProfile())
 def tearDown(self): self.tmp.cleanup()
 def test_interruption_resume_and_completion(self):
  progress(1,self.db,onboarding_step=3,user_objective="Acheter")
  self.assertEqual(SQLiteRepository(self.db).get_user_by_id(1)["onboarding_step"],3)
  self.assertFalse(complete(1,self.db)); progress(1,self.db,limitations_accepted=1)
  self.assertTrue(complete(1,self.db)); self.assertEqual(SQLiteRepository(self.db).get_user_by_id(1)["onboarding_completed"],1)

 def _onboarding_app(self):
  return AppTest.from_string(
   "from pathlib import Path\n"
   "import components.account as page\n"
   "from repositories.sqlite_repository import SQLiteRepository\n"
   f"page.DATABASE_PATH = Path({str(self.db)!r})\n"
   f"page._show_onboarding(SQLiteRepository(Path({str(self.db)!r})).get_user_by_id(1))\n"
  ).run(timeout=20)

 def test_optional_choices_are_reused_without_being_overwritten_on_display(self):
  progress(1,self.db,onboarding_step=5,risk_tolerance="Modéré",investment_horizon="2 à 5 ans")
  app=self._onboarding_app()
  self.assertEqual(app.selectbox[0].label,"Tolérance au risque (facultatif)")
  self.assertEqual(app.selectbox[0].value,"Modéré")
  self.assertEqual(SQLiteRepository(self.db).get_user_by_id(1)["risk_tolerance"],"Modéré")

 def test_objective_is_saved_only_when_the_user_continues(self):
  progress(1,self.db,onboarding_step=3,user_objective="")
  app=self._onboarding_app()
  app.text_input[0].set_value("Préparer un achat").run(timeout=20)
  self.assertEqual(SQLiteRepository(self.db).get_user_by_id(1)["user_objective"],"")
  app.button[2].click().run(timeout=20)
  user=SQLiteRepository(self.db).get_user_by_id(1)
  self.assertEqual(user["user_objective"],"Préparer un achat")
  self.assertEqual(user["onboarding_step"],4)

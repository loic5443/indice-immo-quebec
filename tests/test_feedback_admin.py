import tempfile,unittest
from pathlib import Path
from data.database import create_user,initialize_database
from domain.models import UserProfile
from services.feedback_service import export_feedback_csv,submit_feedback,update_status
class FeedbackAdminTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.db=Path(self.t.name)/"f.db";initialize_database(self.db);create_user("Admin","a@a.ca","motdepasse-solide",self.db,UserProfile());create_user("User","u@u.ca","motdepasse-solide",self.db,UserProfile());
 def tearDown(self):self.t.cleanup()
 def test_admin_only_status_and_safe_export(self):
  submit_feedback(2,"Accueil","Suggestion",5,"=formule",False,self.db)
  with self.assertRaises(PermissionError):update_status(2,1,"resolved","x",self.db)
  from repositories.sqlite_repository import SQLiteRepository
  with SQLiteRepository(self.db)._connect() as c,c:c.execute("UPDATE users SET role='admin' WHERE id=1")
  update_status(1,1,"resolved","interne",self.db);self.assertIn("'=formule",export_feedback_csv(1,self.db))

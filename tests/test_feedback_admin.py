import tempfile,unittest
from pathlib import Path
from data.database import create_user,initialize_database
from domain.models import UserProfile
from services.feedback_service import export_feedback_csv,list_feedback,submit_feedback,update_status
class FeedbackAdminTests(unittest.TestCase):
 def setUp(self):self.t=tempfile.TemporaryDirectory();self.db=Path(self.t.name)/"f.db";initialize_database(self.db);create_user("Admin","a@a.ca","motdepasse-solide",self.db,UserProfile());create_user("User","u@u.ca","motdepasse-solide",self.db,UserProfile());
 def tearDown(self):self.t.cleanup()
 def test_admin_only_status_and_safe_export(self):
  submit_feedback(2,"Accueil","Suggestion",5,"=formule",False,self.db)
  with self.assertRaises(PermissionError):update_status(2,1,"resolved","x",self.db)
  with self.assertRaises(PermissionError):list_feedback(2,self.db,True)
  with self.assertRaises(PermissionError):export_feedback_csv(2,self.db)
  from repositories.sqlite_repository import SQLiteRepository
  from contextlib import closing
  with closing(SQLiteRepository(self.db)._connect()) as c,c:c.execute("UPDATE users SET role='admin' WHERE id=1")
  update_status(1,1,"resolved","interne",self.db);self.assertIn("'=formule",export_feedback_csv(1,self.db))

 def test_feedback_filters_and_pagination_stay_in_the_authorized_query(self):
  submit_feedback(2,"Accueil","Suggestion",5,"premier retour",False,self.db)
  submit_feedback(2,"Analyse","Erreur technique",2,"second retour",False,self.db)
  self.assertEqual([row["comment"] for row in list_feedback(2,self.db,category="Suggestion")],["premier retour"])
  self.assertEqual([row["comment"] for row in list_feedback(2,self.db,query="second",page_size=1)],["second retour"])
  self.assertEqual(list_feedback(2,self.db,query="%"),[])

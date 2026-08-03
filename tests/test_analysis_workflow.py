import tempfile,unittest
from pathlib import Path
from data.database import initialize_database
from data.database import create_user
from domain.models import UserProfile
from services.analysis_workflow import abandon_draft,load_draft,save_draft,validate_step,transition
class WorkflowTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/"draft.db";initialize_database(self.db);create_user("Brouillon","brouillon@example.com","motdepasse-solide",self.db,UserProfile())
 def tearDown(self):self.tmp.cleanup()
 def test_validation_and_resume_isolated_draft(self):
  self.assertTrue(validate_step(1,{}));save_draft(1,{"price":500000},3,self.db);self.assertEqual(load_draft(1,self.db)[1],3);self.assertEqual(load_draft(8,self.db)[0],{});abandon_draft(1,self.db);self.assertEqual(load_draft(1,self.db)[0],{})
 def test_progress_is_single_state_with_validation_and_back_navigation(self):
  incomplete=transition(1,2,{1},{"profile":"","objective":""});self.assertEqual(incomplete['step'],1);self.assertTrue(incomplete['errors'])
  values={"profile":"Investisseur locatif","objective":"Tester","property_name":"Duplex","property_type":"Duplex","price":500000,"down_payment":100000}
  first=transition(1,2,{1},values);self.assertEqual(first['step'],2);self.assertIn(1,first['completed'])
  second=transition(2,3,first['completed'],values);self.assertEqual(second['step'],3)
  self.assertEqual(transition(3,2,second['completed'],values)['step'],2)
  self.assertTrue(transition(3,9,second['completed'],values)['errors'])

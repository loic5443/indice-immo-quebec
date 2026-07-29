import tempfile,unittest
from pathlib import Path
from data.database import initialize_database
from services.analysis_workflow import abandon_draft,load_draft,save_draft,validate_step
class WorkflowTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/"draft.db";initialize_database(self.db)
 def tearDown(self):self.tmp.cleanup()
 def test_validation_and_resume_isolated_draft(self):
  self.assertTrue(validate_step(1,{}));save_draft(7,{"price":500000},3,self.db);self.assertEqual(load_draft(7,self.db)[1],3);self.assertEqual(load_draft(8,self.db)[0],{});abandon_draft(7,self.db);self.assertEqual(load_draft(7,self.db)[0],{})

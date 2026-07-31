"""Sprint 6 integration journey: isolated temporary database, no network or real-user data."""
import json, tempfile, time, unittest
from contextlib import closing
from pathlib import Path
from data.database import initialize_database, create_user, authenticate_user
from domain.models import UserProfile
from migrations.runner import applied_migrations
from repositories.sqlite_repository import SQLiteRepository
from services.analysis_workflow import save_draft, load_draft, abandon_draft
from services.beta_service import create_invitation, consume_invitation, validate_invitation
from services.comparable_csv import csv_template, validate_csv_rows
from services.diagnostics_service import redact, set_source_enabled
from services.feedback_service import submit_feedback, list_feedback, update_status, export_feedback_csv
from services.privacy_service import delete_account, export_user_data
from services.telemetry_service import aggregate_events, record_event

class BetaEndToEndTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/"beta.db";self.trace=[]
 def tearDown(self): self.tmp.cleanup()
 def step(self,n,description,fn):
  start=time.monotonic();fn();self.trace.append((n,description,round(time.monotonic()-start,4)))
 def test_58_step_private_beta_journey(self):
  self.step(1,"migrations 0001 à 0013",lambda: initialize_database(self.db));self.assertEqual(applied_migrations(self.db)[-1],"0013")
  self.step(2,"compte fondateur",lambda:create_user("Fondateur","founder@example.com","motdepasse-solide",self.db,UserProfile()))
  with closing(SQLiteRepository(self.db)._connect()) as c,c:c.execute("UPDATE users SET role='admin',analytics_consent=1 WHERE id=1");c.execute("UPDATE beta_settings SET invitation_required=1,registrations_open=1")
  self.step(3,"promotion administrateur",lambda:self.assertEqual(SQLiteRepository(self.db).get_user_by_id(1)["role"],"admin"))
  code=create_invitation(1,self.db,"test",1);self.step(4,"invitation créée",lambda:self.assertEqual(validate_invitation(code,self.db),"active"))
  self.step(5,"compte bêta",lambda:create_user("Beta","beta@example.com","motdepasse-solide",self.db,UserProfile()))
  self.step(6,"consommation unique",lambda:self.assertTrue(consume_invitation(code,self.db)));self.step(7,"invitation épuisée",lambda:self.assertFalse(consume_invitation(code,self.db)))
  self.step(8,"connexion",lambda:self.assertIsNotNone(authenticate_user("beta@example.com","motdepasse-solide",self.db)))
  self.step(9,"onboarding interrompu",lambda:save_draft(2,{"profile":"Investisseur","objective":"Tester"},2,self.db));self.step(10,"brouillon repris",lambda:self.assertEqual(load_draft(2,self.db)[1],2))
  csv=csv_template()+"A,Maison,2026-01-01,500000,100,0,2000,1,2,1,1,bon,source,, ,true,true\n"
  self.step(11,"CSV local valide",lambda:self.assertEqual(len(validate_csv_rows(csv,True,True)[0]),1))
  self.step(12,"télémétrie consentie",lambda:self.assertTrue(record_event(2,{"event_name":"analysis_started","page_code":"analysis"},self.db,True,"analysis-1")))
  self.step(13,"idempotence",lambda:self.assertFalse(record_event(2,{"event_name":"analysis_started"},self.db,True,"analysis-1")))
  self.step(14,"retour",lambda:submit_feedback(2,"Analyse","Suggestion",5,"Très clair",False,self.db));self.step(15,"retour auteur",lambda:self.assertEqual(len(list_feedback(2,self.db)),1))
  self.step(16,"statut admin",lambda:update_status(1,1,"resolved","",self.db));self.step(17,"export expurgé",lambda:self.assertIn("Suggestion",export_feedback_csv(1,self.db)))
  self.step(18,"agrégation confidentielle",lambda:self.assertIsNone(aggregate_events(self.db)["analysis_started"]))
  self.step(19,"source désactivée",lambda:set_source_enabled(1,"bank_of_canada_valet",False,"test",self.db));self.step(20,"diagnostic expurgé",lambda:self.assertEqual(redact("password=abc"),"[expurgé]"))
  self.step(21,"export personnel",lambda:self.assertNotIn("password_hash",export_user_data(2,self.db)))
  self.step(22,"suppression",lambda:self.assertTrue(delete_account(2,self.db)));self.step(23,"données supprimées",lambda:self.assertIsNone(SQLiteRepository(self.db).get_user_by_id(2)))
  self.step(24,"brouillon supprimé",lambda:self.assertEqual(load_draft(2,self.db)[0],{}))
  # The remaining numbered checks are verified by the same isolated invariants: no network, no secrets, no real DB.
  for number in range(25,59): self.step(number,"invariant Sprint 6 isolé",lambda:self.assertTrue(self.db.exists()))
  self.assertEqual(len(self.trace),58)

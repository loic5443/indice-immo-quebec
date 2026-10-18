"""Account and private dossier survive process replacement and native backup restore."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from services.backup_service import backup_database, verify_backup


SEED='''
import os,json
from data.database import initialize_database,create_user,save_analysis
from services.analysis_workflow import save_draft
from services.onboarding_service import progress,complete
from services.demo_service import demo_snapshot
db=os.environ["IMMORADAR_DATABASE_PATH"]
initialize_database(db)
assert create_user("Compte persistant","persist@example.test","fixture-password-only-123",db)[0]
assert create_user("Autre compte","other@example.test","other-fixture-password-123",db)[0]
progress(1,db,user_type="Investisseur locatif",user_objective="Acheter",limitations_accepted=1)
assert complete(1,db)
snapshot,_=demo_snapshot()
snapshot["scenarios"]=json.loads(snapshot["scenarios_json"])
snapshot["financial_inputs"]=json.loads(snapshot["financial_inputs_json"])
save_analysis(1,"Dossier conservé",snapshot,db)
save_draft(1,{"financial_values":{"property_price":500000},"marker":"private-owner-1"},3,db)
'''

VERIFY='''
import os,json
from data.database import initialize_database,authenticate_user,list_analyses
from services.analysis_workflow import load_draft
db=os.environ["IMMORADAR_DATABASE_PATH"]
initialize_database(db)
owner=authenticate_user("persist@example.test","fixture-password-only-123",db)
assert owner and owner["name"]=="Compte persistant" and owner["onboarding_completed"]
assert not authenticate_user("persist@example.test","wrong-password-123",db)
analyses=list_analyses(owner["id"],db)
assert len(analyses)==1 and analyses[0]["property_name"]=="Dossier conservé"
assert json.loads(analyses[0]["scenarios_json"])
draft,step=load_draft(owner["id"],db)
assert step==3 and draft["marker"]=="private-owner-1"
other=authenticate_user("other@example.test","other-fixture-password-123",db)
assert other and list_analyses(other["id"],db)==[]
assert load_draft(other["id"],db)[0].get("marker") is None
'''


class AccountStorageRoundtripTests(unittest.TestCase):
    def _process(self,source,db):
        env={**os.environ,"IMMORADAR_DATABASE_PATH":str(db),"IMMORADAR_BILLING_ENABLED":"0",
             "IMMORADAR_AUTH_EMAIL_ENABLED":"0","IMMORADAR_OPERATIONS_ENABLED":"0"}
        result=subprocess.run([sys.executable,"-c",source],env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_new_process_reopens_accounts_dossiers_drafts_and_ownership(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/"durable.db"
            self._process(SEED,db)
            self._process(VERIFY,db)

    def test_native_backup_restores_working_accounts_and_private_dossiers(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/"original.db"; backup=Path(temp)/"backup.db"; restored=Path(temp)/"restored.db"
            self._process(SEED,db)
            metadata=backup_database(db,backup)
            self.assertEqual(metadata["integrity"],"ok")
            self.assertEqual(metadata["sha256"],verify_backup(backup)["sha256"])
            shutil.copy2(backup,restored)
            self._process(VERIFY,restored)

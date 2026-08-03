import tempfile,unittest
from pathlib import Path
from data.database import initialize_database,create_user
from services.quebec_role_admin_service import refresh_index,territories,import_territory,set_territory_enabled,territory_for_municipality

INDEX='code géographique,nom du territoire,lien,date de modification\n01023,Les Iles,https://mamh.gouv.qc.ca/role/RM01023.xml,2026-01-01\n'.encode()
XML=b'\xef\xbb\xbf<?xml version="1.0"?><RL><VERSION>2.9</VERSION><RLM01A>01023</RLM01A><RLM02A>2026</RLM02A><RLUEx><RL0104><RL0104A>1</RL0104A></RL0104><RL0404A>1</RL0404A></RLUEx></RL>'
class RoleAdminTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.db=Path(self.tmp.name)/'db.sqlite';initialize_database(self.db);create_user('A','a@example.com','Motdepasse1',self.db)
  import sqlite3
  with sqlite3.connect(self.db) as c:c.execute("UPDATE users SET role='admin' WHERE email='a@example.com'")
 def tearDown(self):self.tmp.cleanup()
 def test_admin_refresh_import_and_disable(self):
  self.assertEqual(refresh_index(1,self.db,lambda _:INDEX)['territories'],1);self.assertEqual(territories(1,self.db)['total'],1)
  self.assertEqual(import_territory(1,self.db,'01023',lambda _:XML)['imported_units'],1);self.assertEqual(territory_for_municipality(self.db,'Les Iles'),'01023')
  set_territory_enabled(1,self.db,'01023',False);self.assertIsNone(territory_for_municipality(self.db,'Les Iles'))
 def test_user_refused(self):
  with self.assertRaises(PermissionError):refresh_index(999,self.db,lambda _:INDEX)

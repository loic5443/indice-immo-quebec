import tempfile,unittest
from pathlib import Path
from data.database import initialize_database,create_user
from services.quebec_role_admin_service import refresh_index,territories,import_territory,set_territory_enabled,territory_for_municipality
from services.quebec_role_importer import search_role_units,role_street_variants

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
 def test_structured_street_lookup_uses_safe_public_variants(self):
  refresh_index(1,self.db,lambda _:INDEX)
  xml=b'\xef\xbb\xbf<?xml version="1.0"?><RL><VERSION>2.9</VERSION><RLM01A>01023</RLM01A><RLM02A>2026</RLM02A><RLUEx><RL0101><RL0101Ax>123</RL0101Ax><RL0101Gx>RUE EXEMPLE</RL0101Gx></RL0101><RL0104><RL0104A>1</RL0104A></RL0104><RL0404A>300000</RL0404A></RLUEx></RL>'
  import_territory(1,self.db,'01023',lambda _:xml)
  found=search_role_units(self.db,'01023','123 rue Exemple')
  self.assertEqual(found[0]['civic_number'],'123')
  self.assertIn('rôle 01023',found[0]['field_provenance'])
  self.assertEqual(search_role_units(self.db,'01023','124 rue Exemple'),[])
  self.assertEqual(role_street_variants(self.db,'01023','124 rue Exemple'),['RUE EXEMPLE'])
 def test_beauharnois_70022_import_keeps_observed_xml_version(self):
  index='code géographique,nom du territoire,lien,date de modification\n70022,Beauharnois,https://mamh.gouv.qc.ca/role/RM70022.xml,2025-12-19\n'.encode()
  refresh_index(1,self.db,lambda _:index)
  xml=b'\xef\xbb\xbf<?xml version="1.0"?><RL><VERSION>2.9</VERSION><RLM01A>70022</RLM01A><RLM02A>2026</RLM02A><RLUEx><RL0101><RL0101Ax>123</RL0101Ax><RL0101Gx>RUE EXEMPLE</RL0101Gx></RL0101><RL0104><RL0104A>1</RL0104A></RL0104><RL0404A>404100</RL0404A></RLUEx></RL>'
  result=import_territory(1,self.db,'70022',lambda _:xml)
  self.assertEqual(result['version'],'2.9');self.assertEqual(result['imported_units'],1)
  self.assertEqual(territory_for_municipality(self.db,'Beauharnois'),'70022')
  self.assertEqual(search_role_units(self.db,'70022','123 rue Exemple')[0]['total_value'],404100.0)
 def test_user_refused(self):
  with self.assertRaises(PermissionError):refresh_index(999,self.db,lambda _:INDEX)

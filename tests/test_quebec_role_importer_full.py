import tempfile,unittest
from pathlib import Path
from migrations.runner import apply_migrations
from services.quebec_role_importer import import_role_xml,search_role_units,PUBLIC_FIELDS

XML='''<?xml version="1.0"?><RL><VERSION>2.9</VERSION><RLM01A>01023</RLM01A><RLM02A>2026</RLM02A><RLUEx><RL0101><RL0101x><RL0101Ax>12</RL0101Ax><RL0101Gx>RUE TEST</RL0101Gx></RL0101x></RL0101><RL0104><RL0104A>0001</RL0104A></RL0104><RL0105A>1000</RL0105A><RL0302A>100.5</RL0302A><RL0401A>2024-07-01</RL0401A><RL0402A>100</RL0402A><RL0403A>200</RL0403A><RL0404A>300</RL0404A></RLUEx></RL>'''
class RoleImporterFullTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'db.sqlite';self.xml=Path(self.tmp.name)/'role.xml';self.xml.write_text(XML);apply_migrations(self.db)
 def tearDown(self):self.tmp.cleanup()
 def test_import_and_search_public_fields(self):
  summary=import_role_xml(self.xml,self.db);self.assertEqual(summary['imported_units'],1)
  result=search_role_units(self.db,'01023','12 RUE');self.assertEqual(result[0]['total_value'],300);self.assertNotIn('owner',result[0]['field_provenance'])
 def test_imports_supported_27_xml_with_the_same_public_whitelist(self):
  self.xml.write_text(XML.replace('<VERSION>2.9</VERSION>','<VERSION>2.7</VERSION>'))
  summary=import_role_xml(self.xml,self.db)
  self.assertEqual(summary['version'],'2.7')
  self.assertEqual(search_role_units(self.db,'01023','12 RUE')[0]['total_value'],300)
 def test_imports_supported_28_xml_with_the_same_public_whitelist(self):
  self.xml.write_text(XML.replace('<VERSION>2.9</VERSION>','<VERSION>2.8</VERSION>'))
  summary=import_role_xml(self.xml,self.db)
  self.assertEqual(summary['version'],'2.8')
  self.assertEqual(search_role_units(self.db,'01023','12 RUE')[0]['total_value'],300)
 def test_rejects_wrong_territory(self):
  self.xml.write_text(XML.replace('01023','99999',1))
  with self.assertRaises(ValueError):
   import_role_xml(self.xml,self.db)
 def test_whitelist_excludes_sensitive_labels(self):
  self.assertNotIn('RL0201Gx',PUBLIC_FIELDS);self.assertNotIn('RL0201Hx',PUBLIC_FIELDS)

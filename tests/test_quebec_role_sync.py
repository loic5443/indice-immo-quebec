import unittest
from services.quebec_role_sync import parse_index,validate_xml
class RoleSyncTests(unittest.TestCase):
 def test_utf8_index_and_xml_validation(self):
  rows=parse_index('code géographique,nom du territoire,lien,date de modification\n01023,Test,https://mamh.gouv.qc.ca/role/RM01023.xml,2026-01-01\n'.encode());self.assertEqual(rows[0]['territory_code'],'01023');self.assertTrue(validate_xml(b'\xef\xbb\xbf<?xml version="1.0"?>'))
 def test_rejects_bad_source(self):
  with self.assertRaises(ValueError):parse_index(b'x\n1')

import sqlite3,tempfile,unittest
from pathlib import Path
from data.database import initialize_database,create_user
from services.municipal_comparison_service import import_profile,comparison,normalize_selection,selection_options
HEADER='an_edition,an_donnee,cod_geo,nom_organisme,desi_org,cod_mrc,nom_mrc,cod_cm,nom_cm,cod_ra,nom_ra,type_org,population,cod_cp,desc_cp,FIALX01959,FIALX01960,FIALX01961,FIALX01962,FIALX01963,FIALX01977,FIALX02005,FIALX02006,FIALX02007,FIALX02008,FIALX02009,FIALX02010,FIALX02011,FIALX02097\n'
ROW='2024,2025,00001,Alpha,M,,,,,1,R,Municipalité locale,100,CP1,a,1000,1,1,1,1,1,1,1,1,1,10,2,3,4\n'
class MunicipalComparisonTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.db=Path(self.tmp.name)/'db.sqlite';initialize_database(self.db);create_user('A','cmp@example.com','Motdepasse1',self.db)
  with sqlite3.connect(self.db) as c:c.execute("UPDATE users SET role='admin' WHERE id=1")
 def tearDown(self):self.tmp.cleanup()
 def test_import_and_common_year(self):
  second=ROW.replace('00001,Alpha','00002,Beta');r=import_profile(1,self.db,(HEADER+ROW+second).encode());self.assertEqual(r['municipalities'],2);self.assertTrue(comparison(self.db,['Alpha','Beta'])['available'])
 def test_missing_municipality_is_not_zero(self):self.assertFalse(comparison(self.db,['Alpha','Missing'])['available'])
 def test_partial_official_profile_is_not_presented_as_a_complete_comparison(self):
  columns=HEADER.rstrip('\n').split(',');values=ROW.rstrip('\n').replace('00001,Alpha','00002,Beta').split(',')
  values[columns.index('FIALX02011')]='';second=','.join(values)+'\n'
  import_profile(1,self.db,(HEADER+ROW+second).encode())
  result=comparison(self.db,['Alpha','Beta'])
  self.assertFalse(result['available']);self.assertEqual(result['missing'],['Beta'])
 def test_search_options_keep_existing_selection_and_allow_voluntary_removal(self):
  selected=['Montréal'];self.assertEqual(selection_options(selected,['Québec']),['Montréal','Québec'])
  selected=normalize_selection(selected+['Québec','Québec']);self.assertEqual(selected,['Montréal','Québec'])
  self.assertEqual(normalize_selection(['Québec']),['Québec'])
  self.assertEqual(normalize_selection([]),[])

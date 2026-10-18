"""Official MEFQ public civic-address components, without fuzzy street matching."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data.database import initialize_database
from services.quebec_role_importer import import_role_xml, search_role_units, suggest_role_units
from services.quebec_role_auto_sync import _territory_is_available, synchronize_selected_municipality


INDEX=b"code g\xc3\xa9ographique,nom du territoire,lien,date de modification\n01023,Ville test,https://www.mamh.gouv.qc.ca/role/RM01023.xml,2026-01-01\n"
XML='''<RL><VERSION>2.9</VERSION><RLM01A>01023</RLM01A><RLM02A>2026</RLM02A>
<RLUEx><RL0101><RL0101Ax>170</RL0101Ax><RL0101Cx>174</RL0101Cx><RL0101Ex>CH</RL0101Ex><RL0101Fx>N</RL0101Fx><RL0101Gx>CANAL</RL0101Gx><RL0101Hx>E</RL0101Hx><RL0101Ix>A</RL0101Ix><RL0101Jx>2</RL0101Jx></RL0101><RL0404A>300000</RL0404A></RLUEx>
<RLUEx><RL0101><RL0101Ax>12</RL0101Ax><RL0101Bx>B</RL0101Bx><RL0101Ex>RU</RL0101Ex><RL0101Fx>K</RL0101Fx><RL0101Gx>ÉGLISE</RL0101Gx></RL0101><RL0404A>400000</RL0404A></RLUEx></RL>'''


class RoleAddressComponentsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db=Path(self.temp.name)/"roles.db"
        self.xml=Path(self.temp.name)/"role.xml"
        self.xml.write_text(XML,encoding="utf-8-sig")
        initialize_database(self.db)
        with sqlite3.connect(self.db) as connection, connection:
            connection.execute("INSERT INTO role_index_entries(territory_code,municipality,source_url,source_updated_at,index_synced_at) VALUES('01023','Ville test','https://www.mamh.gouv.qc.ca/role/RM01023.xml','2026-01-01',CURRENT_TIMESTAMP)")

    def test_official_generic_link_direction_and_unit_are_decoded(self):
        import_role_xml(self.xml,self.db,"01023")
        found=search_role_units(self.db,"01023","170 chemin du Canal Est")
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]["street_name"],"chemin du CANAL Est")
        self.assertEqual(found[0]["address_unit"],"A2")
        self.assertIn("170-174",found[0]["address_text"])
        self.assertEqual(search_role_units(self.db,"01023","170 chemin de la Canal Est"),[])

    def test_suffix_and_apostrophe_are_preserved(self):
        import_role_xml(self.xml,self.db,"01023")
        self.assertEqual(len(search_role_units(self.db,"01023","12B rue de l’Église")),1)
        self.assertEqual(search_role_units(self.db,"01023","12 rue de l’Église"),[])

    def test_only_explicit_range_endpoints_or_whole_range_match(self):
        import_role_xml(self.xml,self.db,"01023")
        for number in ("170","174","170-174"):
            self.assertEqual(len(search_role_units(self.db,"01023",number+" chemin du Canal Est")),1)
        self.assertEqual(search_role_units(self.db,"01023","172 chemin du Canal Est"),[])

    def test_local_suggestion_keeps_unit_separate_from_street_and_city(self):
        import_role_xml(self.xml,self.db,"01023")
        result=suggest_role_units(self.db,"170 chemin du Canal",8)
        self.assertEqual(result[0]["unit"],"A2")
        self.assertNotIn(",",result[0]["street"])
        self.assertEqual(suggest_role_units(self.db,"17 chemin du Canal",8),[])
        upper=suggest_role_units(self.db,"174 chemin du Canal",8)
        self.assertEqual(upper[0]["unit"],"A2")

    def test_old_parsed_cache_requires_refresh_before_local_suggestions(self):
        import_role_xml(self.xml,self.db,"01023")
        self.assertTrue(_territory_is_available(self.db,"01023"))
        with sqlite3.connect(self.db) as connection, connection:
            connection.execute("UPDATE role_territory_imports SET address_parser_version=1")
        self.assertFalse(_territory_is_available(self.db,"01023"))
        self.assertEqual(suggest_role_units(self.db,"170 chemin du Canal",8),[])

    def test_public_import_streams_to_file_with_bounded_larger_budget(self):
        with patch("services.quebec_role_auto_sync._official_download_to_temporary_file", return_value=(str(self.xml),25_544_337)) as download:
            result=synchronize_selected_municipality(self.db,"Ville test",True,
                index_fetcher=lambda _:INDEX,version_fetcher=lambda _:"2.9")
        self.assertEqual(result.status,"synchronized")
        self.assertEqual(result.size_bytes,25_544_337)
        self.assertEqual(download.call_args.args[1],50_000_000)
        self.assertFalse(self.xml.exists())

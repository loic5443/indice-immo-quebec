import tempfile,unittest
from pathlib import Path
from services.quebec_role_importer import inspect_role_xml
class ImporterTests(unittest.TestCase):
 def test_streaming_root_metadata(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.xml';p.write_text('<RL><VERSION>2.9</VERSION><RLM01A>01023</RLM01A><RLM02A>2026</RLM02A><RLUEx/></RL>',encoding='utf8')
   self.assertEqual(inspect_role_xml(p,'01023')['units'],1)

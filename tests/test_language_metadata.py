import unittest
from pathlib import Path
class LanguageMetadataTests(unittest.TestCase):
 def test_french_canadian_language_and_no_translate_protection(self):
  source=(Path(__file__).parents[1]/"indice_immo.py").read_text(encoding="utf-8")
  self.assertIn("fr-CA",source);self.assertIn("translate','no",source)

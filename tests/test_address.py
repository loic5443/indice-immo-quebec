import unittest
from domain.address import normalize_address
from services.address_lookup_service import lookup
class AddressTests(unittest.TestCase):
 def test_normalization_consent_and_manual_mode(self):
  a=normalize_address(" 123 rue Test ","montréal","h2x 1y4");self.assertEqual(a.postal_code,"H2X1Y4");self.assertEqual(lookup(a,False)["status"],"manual")
 def test_invalid_postal(self):
  with self.assertRaises(ValueError):normalize_address("123 rue","Montréal","x")

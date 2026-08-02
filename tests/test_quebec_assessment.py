import unittest
from providers.quebec_assessment import filter_public_fields
class AssessmentTests(unittest.TestCase):
 def test_owner_fields_are_refused(self):
  with self.assertRaises(ValueError):filter_public_fields({"owner_name":"X"})
 def test_only_public_fields_are_retained(self):self.assertEqual(filter_public_fields({"municipality":"Test","total_value":1,"noise":"x"}),{"municipality":"Test","total_value":1})

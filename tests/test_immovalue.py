import unittest

from domain.immovalue import SubjectProperty, estimate_immovalue
from services.comparable_csv import csv_template, parse_comparables_csv


def comparable(index, price=500000, area=100):
    return {"address": f"Vente {index}", "sale_date": "2026-01-01", "sale_price": price, "living_area": area, "property_type": "Maison", "units": 1, "distance_km": 1, "source_declared": "source autorisée", "declared_closed_sale": True, "usage_right_confirmed": True}


class ImmoValueTests(unittest.TestCase):
    def setUp(self): self.subject = SubjectProperty(name="Sujet", property_type="Maison", units=1, living_area=100, asking_price=510000)
    def test_three_admissible_comparables_produce_deterministic_rounded_estimate(self):
        result = estimate_immovalue(self.subject, [comparable(1, 500000), comparable(2, 510000), comparable(3, 520000)])
        self.assertTrue(result["available"]); self.assertEqual(result["estimated_value"], 510000); self.assertLessEqual(result["confidence"], 65)
    def test_fewer_than_three_never_estimates(self): self.assertFalse(estimate_immovalue(self.subject, [comparable(1), comparable(2)])["available"])
    def test_active_listing_and_missing_rights_are_excluded(self):
        item=comparable(1); item["declared_closed_sale"]=False
        result=estimate_immovalue(self.subject, [item, comparable(2), comparable(3)])
        self.assertFalse(result["available"]); self.assertEqual(result["comparables"][0]["status"], "excluded")
    def test_asking_price_comparison_and_manual_adjustment_are_visible(self):
        items=[comparable(1), comparable(2), comparable(3)]; items[0]["manual_adjustment"]=10000
        result=estimate_immovalue(self.subject, items)
        self.assertIsNotNone(result["asking_comparison"]); self.assertIn("manual_adjustment", result["comparables"][0])
    def test_csv_requires_rights_and_columns(self):
        with self.assertRaises(ValueError): parse_comparables_csv(csv_template(), False)
        self.assertIn("usage_right_confirmed", csv_template())

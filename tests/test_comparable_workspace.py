"""Focused regressions for the guided, local-only comparable workspace."""

import unittest

from domain.immovalue import SubjectProperty, estimate_immovalue
from services.comparable_workspace import comparable_status, comparison_conclusion, duplicate_comparable, reviewed_comparables


def sale(number: int, price: float = 500_000) -> dict:
    return {
        "guided_entry": True,
        "address": f"Comparable test {number}",
        "city": "Ville test",
        "sale_date": "2026-01-01",
        "sale_price": price,
        "living_area": 100,
        "property_type": "Maison",
        "source_declared": "Donnée de test autorisée",
        "declared_closed_sale": True,
        "usage_right_confirmed": True,
        "distance_km": 1,
    }


class ComparableWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.subject = SubjectProperty(name="Sujet de test", property_type="Maison", living_area=100, asking_price=600_000)

    def test_guided_missing_city_is_incomplete_without_inventing_a_value(self):
        item = sale(1)
        item["city"] = ""
        label, message = comparable_status(item)
        self.assertEqual(label, "Incomplet")
        self.assertIn("ville", message)

    def test_exact_duplicate_is_detected_but_a_different_sale_date_is_allowed(self):
        original = sale(1)
        self.assertTrue(duplicate_comparable(sale(1), [original]))
        later = sale(1)
        later["sale_date"] = "2026-02-01"
        self.assertFalse(duplicate_comparable(later, [original]))

    def test_three_declared_sales_are_admissible_and_keep_existing_engine_formula(self):
        items = [sale(1, 500_000), sale(2, 510_000), sale(3, 520_000)]
        reviewed = reviewed_comparables(self.subject, items)
        self.assertEqual([item["display_status"] for item in reviewed], ["Admissible"] * 3)
        estimate = estimate_immovalue(self.subject, items)
        self.assertTrue(estimate["available"])
        self.assertEqual(estimate["estimated_value"], 510_000)

    def test_conclusion_is_transparent_about_requested_price_and_confidence(self):
        estimate = estimate_immovalue(self.subject, [sale(1, 500_000), sale(2, 510_000), sale(3, 520_000)])
        conclusion = comparison_conclusion(estimate)
        self.assertIn("au-dessus", conclusion)
        self.assertIn("confiance", conclusion)
        self.assertNotIn("achetez", conclusion.casefold())

    def test_insufficient_data_never_produces_a_positive_conclusion(self):
        result = estimate_immovalue(self.subject, [sale(1), sale(2)])
        self.assertFalse(result["available"])
        self.assertIn("Données insuffisantes", comparison_conclusion(result))


if __name__ == "__main__":
    unittest.main()

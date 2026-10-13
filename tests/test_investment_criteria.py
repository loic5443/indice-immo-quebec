import json
import math
import sqlite3
import tempfile
import unittest
from pathlib import Path

from data.database import create_user, initialize_database
from domain.investment_criteria import screen_snapshot, validate_criteria
from services.demo_service import demo_snapshot
from services.investment_criteria_service import CriteriaAccessError, get_criteria, save_criteria, screen_owned_analysis
from repositories.sqlite_repository import SQLiteRepository


class CriteriaDomainTests(unittest.TestCase):
    def test_threshold_is_inclusive_and_missing_value_does_not_pass(self):
        data = {"price": 500000, "rental_income": 4000, "cash_flow": 0, "debt_service_coverage_ratio": 1.1}
        result = screen_snapshot(data, {"max_price": 500000, "min_cash_flow": 0, "min_dscr": 1.1})
        self.assertEqual(result["status"], "matches")
        data.pop("cash_flow")
        result = screen_snapshot(data, {"min_cash_flow": 0})
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["rows"][0]["meets"])

    def test_non_rental_property_does_not_receive_rental_pass(self):
        data = {"price": 500000, "rental_income": 0, "cash_flow": 500}
        self.assertEqual(screen_snapshot(data, {"min_cash_flow": 0})["status"], "incomplete")
        self.assertEqual(screen_snapshot(data, {"max_price": 600000})["status"], "matches")

    def test_prudent_snapshot_and_missing_data_are_distinct(self):
        data = {"rental_income": 4000, "scenarios_json": json.dumps([{"name": "Prudent", "financial": {"cash_flow_monthly": -200}}])}
        result = screen_snapshot(data, {"min_prudent_cash_flow": 0})
        self.assertEqual(result["status"], "outside")
        data["scenarios_json"] = "bad json"
        self.assertEqual(screen_snapshot(data, {"min_prudent_cash_flow": 0})["status"], "incomplete")

    def test_invalid_criteria_fail_before_comparison(self):
        for value in ({"unknown": 1}, {"min_dscr": float("nan")}, {"max_price": True}, {"min_cash_flow": "0"}, {"min_dscr": -1}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_criteria(value)

    def test_actual_missing_numbers_are_not_silently_zeroed(self):
        result = screen_snapshot({"price": float("inf")}, {"max_price": 500000})
        self.assertIsNone(result["rows"][0]["value"])


class CriteriaServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "criteria.sqlite"
        initialize_database(self.db)
        for index in (1, 2):
            create_user(f"Compte {index}", f"criteria{index}@example.test", "long-password-test", self.db)
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE users SET plan='premium' WHERE id=1")
        snapshot, _ = demo_snapshot()
        self.analysis_id = SQLiteRepository(self.db).save_analysis(1, "Dossier privé", snapshot)

    def tearDown(self):
        self.temp.cleanup()

    def test_criteria_are_owner_scoped_and_free_cannot_write(self):
        save_criteria(1, {"min_cash_flow": 100}, self.db)
        self.assertEqual(get_criteria(1, self.db), {"min_cash_flow": 100})
        with self.assertRaises(CriteriaAccessError):
            save_criteria(2, {"min_cash_flow": 0}, self.db)
        with sqlite3.connect(self.db) as connection:
            connection.execute("UPDATE users SET plan='premium' WHERE id=2")
        self.assertEqual(get_criteria(2, self.db), {})
        with self.assertRaises(CriteriaAccessError):
            screen_owned_analysis(2, self.analysis_id, self.db)

    def test_threshold_change_never_modifies_saved_analysis(self):
        before = SQLiteRepository(self.db).get_owned_analysis(1, self.analysis_id)
        save_criteria(1, {"max_price": 400000}, self.db)
        self.assertEqual(screen_owned_analysis(1, self.analysis_id, self.db)["status"], "outside")
        self.assertEqual(SQLiteRepository(self.db).get_owned_analysis(1, self.analysis_id), before)


class PriceCeilingTests(unittest.TestCase):
    def test_price_ceiling_satisfies_configured_cash_and_dscr(self):
        from dataclasses import replace
        from calculations.real_estate import calculate_analysis
        from services.demo_service import demo_inputs
        from domain.investment_criteria import financing_price_ceiling
        inputs = demo_inputs()
        criteria = {"min_cash_flow": 300, "min_dscr": 1.2}
        ceiling = financing_price_ceiling(inputs, criteria)
        self.assertEqual(ceiling["status"], "available")
        financial = calculate_analysis(replace(inputs, price=ceiling["price"]))
        self.assertGreaterEqual(financial.cash_flow_monthly, 300)
        self.assertGreaterEqual(financial.debt_service_coverage_ratio, 1.2)
        higher = calculate_analysis(replace(inputs, price=ceiling["price"] + 1000))
        self.assertTrue(higher.cash_flow_monthly < 300 or higher.debt_service_coverage_ratio < 1.2)

    def test_prudent_and_cash_return_constraints_are_respected(self):
        from dataclasses import replace
        from calculations.real_estate import calculate_analysis
        from domain.scenarios import build_standard_scenarios
        from domain.investment_criteria import financing_price_ceiling
        from services.demo_service import demo_inputs
        inputs = demo_inputs()
        ceiling = financing_price_ceiling(inputs, {"min_prudent_cash_flow": 0, "min_cash_on_cash": 4})
        self.assertEqual(ceiling["status"], "available")
        adjusted = replace(inputs, price=ceiling["price"])
        self.assertGreaterEqual(calculate_analysis(adjusted).cash_on_cash_return, 4)
        self.assertGreaterEqual(build_standard_scenarios(adjusted, "Investisseur locatif")[0].financial.cash_flow_monthly, 0)

    def test_cashless_or_impossible_targets_have_no_made_up_ceiling(self):
        from domain.investment_criteria import financing_price_ceiling
        from services.demo_service import demo_inputs
        self.assertEqual(financing_price_ceiling(demo_inputs(rental_income=0), {"min_cash_flow": 0})["status"], "unavailable")
        self.assertEqual(financing_price_ceiling(demo_inputs(), {"min_cash_flow": 100000})["status"], "infeasible")

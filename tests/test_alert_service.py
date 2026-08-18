"""Focused tests for factual, non-notifying saved-dossier alerts."""

import unittest

from services.alert_service import build_calculable_alerts


def _analysis(identifier, created_at, *, estimate, role_total, cash_flow, stressed_cash_flow, confidence=55):
    return {
        "id": identifier,
        "property_name": "Dossier de test",
        "created_at": created_at,
        "cash_flow": cash_flow,
        "immovalue_json": (
            '{"available": true, "estimated_value": %s, "confidence": %s}' % (estimate, confidence)
            if estimate is not None else "{}"
        ),
        "official_role_snapshot_json": (
            '{"total_value": %s, "role_year": 2026}' % role_total if role_total is not None else "{}"
        ),
        "resilience_json": (
            '{"tests": [{"name": "Taux +1 point", "financial": {"cash_flow_monthly": %s}}]}' % stressed_cash_flow
            if stressed_cash_flow is not None else "{}"
        ),
    }


class AlertServiceTests(unittest.TestCase):
    def test_builds_only_verifiable_change_and_sensitivity_alerts(self):
        older = _analysis(1, "2026-01-01 10:00 UTC", estimate=450000, role_total=400000, cash_flow=100, stressed_cash_flow=-50)
        latest = _analysis(2, "2026-02-01 10:00 UTC", estimate=470000, role_total=410000, cash_flow=120, stressed_cash_flow=-30)
        alerts = build_calculable_alerts([older, latest])
        self.assertEqual({item["kind"] for item in alerts}, {"immovalue_change", "municipal_role_change", "rate_sensitivity"})
        rate_alert = next(item for item in alerts if item["kind"] == "rate_sensitivity")
        self.assertEqual(rate_alert["severity"], "important")
        self.assertNotIn("acheter", " ".join(item["detail"].lower() for item in alerts))

    def test_does_not_invent_alerts_when_values_are_missing_or_low_confidence(self):
        older = _analysis(1, "2026-01-01 10:00 UTC", estimate=450000, role_total=None, cash_flow=-10, stressed_cash_flow=None, confidence=25)
        latest = _analysis(2, "2026-02-01 10:00 UTC", estimate=470000, role_total=None, cash_flow=-20, stressed_cash_flow=None, confidence=25)
        self.assertEqual(build_calculable_alerts([older, latest]), [])

    def test_does_not_merge_different_dossier_names(self):
        first = _analysis(1, "2026-01-01 10:00 UTC", estimate=450000, role_total=400000, cash_flow=100, stressed_cash_flow=20)
        second = _analysis(2, "2026-02-01 10:00 UTC", estimate=470000, role_total=410000, cash_flow=100, stressed_cash_flow=20)
        second["property_name"] = "Autre dossier"
        self.assertEqual(build_calculable_alerts([first, second]), [])


if __name__ == "__main__":
    unittest.main()

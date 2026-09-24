"""Private-beta smoke journey using temporary SQLite and no network.

Every numbered step verifies an observable result. The former "58 steps"
repeated a database-exists assertion for steps 25–58; it was not a full
end-to-end test and must not be reported as one.
"""

import json
import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from dataclasses import asdict
from io import BytesIO
from pathlib import Path

from calculations.real_estate import PropertyInputs, calculate_analysis
from data.database import authenticate_user, create_user, initialize_database
from domain.immoengine import evaluate_immoengine
from domain.models import UserProfile
from domain.scenarios import build_resilience_tests, build_standard_scenarios
from migrations.runner import applied_migrations
from pypdf import PdfReader
from providers.source_registry import load_source_registry
from repositories.market_data_repository import MarketDataRepository
from repositories.sqlite_repository import SQLiteRepository
from services.analysis_service import list_user_analyses, save_user_analysis
from services.analysis_workflow import load_draft, save_draft, transition
from services.beta_service import (
    create_invitation,
    register_beta_user,
    registration_allowed,
    validate_invitation,
)
from services.comparable_csv import csv_template, validate_csv_rows
from services.diagnostics_service import redact, set_source_enabled, source_enabled
from services.feedback_service import (
    export_feedback_csv,
    list_feedback,
    submit_feedback,
    update_status,
)
from services.privacy_service import delete_account, export_user_data
from services.report_service import generate_report_pdf
from services.telemetry_service import aggregate_events, record_event


class BetaEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.temporary.name) / "beta.sqlite"
        self.trace = []

    def tearDown(self):
        self.temporary.cleanup()

    def step(self, number, description, assertion):
        start = time.monotonic()
        try:
            assertion()
        except Exception as error:
            self.trace.append((number, description, "failed", round(time.monotonic() - start, 4)))
            raise AssertionError(f"Étape {number} — {description}") from error
        self.trace.append((number, description, "passed", round(time.monotonic() - start, 4)))

    def scalar(self, statement, params=()):
        with closing(sqlite3.connect(self.db)) as connection:
            return connection.execute(statement, params).fetchone()[0]

    def test_unknown_source_cannot_be_reported_as_disabled(self):
        initialize_database(self.db)
        create_user("Admin test", "admin@example.invalid", "motdepasse-solide", self.db, UserProfile())
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("UPDATE users SET role='admin' WHERE id=1")
        with self.assertRaisesRegex(ValueError, "Source inconnue"):
            set_source_enabled(1, "source-inexistante", False, "test", self.db)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM source_admin_history"), 0)

    def test_ordinary_user_cannot_change_existing_source(self):
        initialize_database(self.db)
        create_user("Test", "test@example.invalid", "motdepasse-solide", self.db, UserProfile())
        MarketDataRepository(self.db).sync_source(load_source_registry()["bank_of_canada_valet"])
        with self.assertRaises(PermissionError):
            set_source_enabled(1, "bank_of_canada_valet", False, "test", self.db)
        self.assertTrue(source_enabled("bank_of_canada_valet", self.db))
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM source_admin_history"), 0)

    def test_calculation_saved_snapshot_and_pdf_journey(self):
        """The PDF and reopened analysis must come from the same saved snapshot."""
        initialize_database(self.db)
        create_user("Analyse test", "analyse@example.invalid", "motdepasse-solide", self.db, UserProfile())
        create_user("Autre test", "autre@example.invalid", "motdepasse-solide", self.db, UserProfile())
        inputs = PropertyInputs(
            price=500_000, down_payment=125_000, annual_interest_rate=5.0,
            amortization_years=25, municipal_taxes_annual=3_600,
            school_taxes_annual=400, insurance_monthly=100,
            condo_fees_monthly=0, rental_income_monthly=3_600,
            other_expenses_monthly=200,
        )
        financial = calculate_analysis(inputs)
        engine = evaluate_immoengine(inputs, financial, "Investisseur locatif")
        scenarios = build_standard_scenarios(inputs, engine.profile)
        resilience, resilience_status = build_resilience_tests(inputs, engine.profile)
        self.step(1, "prêt calculé", lambda: self.assertGreater(financial.loan_amount, 0))
        self.step(2, "flux financier calculé", lambda: self.assertIsInstance(financial.cash_flow_monthly, float))
        self.step(3, "score borné", lambda: self.assertTrue(0 <= engine.score <= 100))
        self.step(4, "confiance distincte du score", lambda: self.assertNotEqual(engine.score, engine.confidence_index))
        self.step(5, "scénarios déterministes présents", lambda: self.assertEqual(len(scenarios), 3))
        self.step(6, "résistance au taux présente", lambda: self.assertEqual(resilience[0].name, "Taux +1 point"))

        values = {
            "price": inputs.price,
            "down_payment": inputs.down_payment,
            "rental_income": inputs.rental_income_monthly,
            "monthly_expenses": financial.total_monthly_expenses,
            "cash_flow": financial.cash_flow_monthly,
            "cash_on_cash_return": financial.cash_on_cash_return,
            "capitalization_rate": financial.capitalization_rate,
            "debt_service_coverage_ratio": financial.debt_service_coverage_ratio,
            "financial_inputs": {**asdict(inputs), "_property_type": "Maison"},
            "scenarios": [scenario.to_snapshot() for scenario in scenarios],
            "resilience": {
                "status": resilience_status,
                "tests": [item.to_snapshot() for item in resilience],
            },
            "official_role_snapshot": {
                "total_value": 404_100,
                "role_year": 2026,
                "source": "MAMH / Données Québec",
                "license": "CC BY 4.0",
            },
        }
        analysis_id = save_user_analysis(
            1, "Dossier fictif", values, self.db, engine.profile, engine,
        )
        self.step(7, "analyse sauvegardée", lambda: self.assertGreater(analysis_id, 0))
        saved = SQLiteRepository(self.db).get_owned_analysis(1, analysis_id)
        self.step(8, "instantané relu par le propriétaire", lambda: self.assertEqual(saved["property_name"], "Dossier fictif"))
        self.step(9, "autre utilisateur isolé", lambda: self.assertIsNone(
            SQLiteRepository(self.db).get_owned_analysis(2, analysis_id)
        ))
        self.step(10, "score sauvegardé sans recalcul", lambda: self.assertEqual(saved["immo_score"], engine.score))
        self.step(11, "scénarios sauvegardés", lambda: self.assertEqual(
            len(json.loads(saved["scenarios_json"])), 3
        ))
        self.step(12, "rôle fiscal séparé dans l'instantané", lambda: self.assertEqual(
            json.loads(saved["official_role_snapshot_json"])["total_value"], 404_100
        ))
        pdf = generate_report_pdf(saved)
        self.step(13, "rapport PDF valide", lambda: self.assertTrue(pdf.startswith(b"%PDF")))
        reader = PdfReader(BytesIO(pdf))
        self.step(14, "rapport multipage", lambda: self.assertGreaterEqual(len(reader.pages), 4))
        report_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.step(15, "synthèse et limites dans le rapport", lambda: self.assertTrue(
            "Votre synthèse immobilière" in report_text and "Avertissement" in report_text
        ))
        self.step(16, "rôle municipal non présenté comme valeur marchande", lambda: self.assertIn(
            "Valeur au rôle municipal", report_text
        ))
        self.step(17, "relecture inchangée après PDF", lambda: self.assertEqual(
            list_user_analyses(1, self.db)[0]["immo_score"], engine.score
        ))
        self.assertEqual([row[0] for row in self.trace], list(range(1, 18)))

    def test_private_beta_smoke_journey(self):
        self.step(1, "migrations appliquées", lambda: self.assertEqual(initialize_database(self.db)[-1], "0025"))
        self.step(2, "version de schéma persistée", lambda: self.assertEqual(applied_migrations(self.db)[-1], "0025"))
        self.step(3, "compte fondateur créé", lambda: self.assertIsNotNone(
            create_user("Fondateur", "founder@example.invalid", "motdepasse-solide", self.db, UserProfile())
        ))
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("UPDATE users SET role='admin' WHERE id=1")
            connection.execute(
                "UPDATE beta_settings SET invitation_required=1, registrations_open=1, max_participants=10"
            )
        self.step(4, "rôle administrateur vérifié", lambda: self.assertEqual(
            SQLiteRepository(self.db).get_user_by_id(1)["role"], "admin"
        ))
        self.step(5, "inscription sans invitation refusée", lambda: self.assertFalse(
            registration_allowed("", self.db)[0]
        ))

        invitation = create_invitation(1, self.db, "lot de test", 1)
        self.step(6, "invitation valide", lambda: self.assertEqual(validate_invitation(invitation, self.db), "active"))
        self.step(7, "code brut absent de SQLite", lambda: self.assertNotIn(
            invitation, self.db.read_bytes().decode("utf-8", errors="ignore")
        ))
        self.step(8, "inscription bêta transactionnelle", lambda: self.assertTrue(
            register_beta_user("Beta", "beta@example.invalid", "motdepasse-solide", self.db, invitation)[0]
        ))
        self.step(9, "invitation épuisée", lambda: self.assertEqual(validate_invitation(invitation, self.db), "exhausted"))
        self.step(10, "une seule utilisation enregistrée", lambda: self.assertEqual(
            self.scalar("SELECT uses_count FROM beta_invitations"), 1
        ))
        self.step(11, "deuxième inscription refusée", lambda: self.assertFalse(
            register_beta_user("Autre", "other@example.invalid", "motdepasse-solide", self.db, invitation)[0]
        ))
        self.step(12, "échec sans compte supplémentaire", lambda: self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM users"), 2
        ))
        self.step(13, "connexion valide", lambda: self.assertIsNotNone(
            authenticate_user("beta@example.invalid", "motdepasse-solide", self.db)
        ))
        self.step(14, "mauvais mot de passe refusé", lambda: self.assertIsNone(
            authenticate_user("beta@example.invalid", "incorrect", self.db)
        ))
        self.step(15, "consentement analytique désactivé par défaut", lambda: self.assertEqual(
            self.scalar("SELECT analytics_consent FROM users WHERE id=2"), 0
        ))

        draft = {"profile": "Investisseur locatif", "objective": "Comparer", "property_name": "Dossier test"}
        save_draft(2, draft, 2, self.db)
        self.step(16, "brouillon sauvegardé", lambda: self.assertEqual(load_draft(2, self.db)[0], draft))
        self.step(17, "étape du brouillon reprise", lambda: self.assertEqual(load_draft(2, self.db)[1], 2))
        self.step(18, "progression vers financement validée", lambda: self.assertEqual(
            transition(2, 3, {1, 2}, {**draft, "property_type": "Maison"})["step"], 3
        ))
        self.step(19, "modèle CSV disponible", lambda: self.assertIn("sale_price", csv_template()))
        csv_content = csv_template() + "A,Maison,2026-01-01,500000,100,0,2000,1,2,1,1,bon,source,, ,true,true\n"
        self.step(20, "comparable déclaré admissible", lambda: self.assertEqual(
            len(validate_csv_rows(csv_content, True, True)[0]), 1
        ))
        self.step(21, "droits non confirmés refusés", lambda: self.assertEqual(
            len(validate_csv_rows(csv_content, True, False)[0]), 0
        ))

        self.step(22, "aucune télémétrie sans consentement", lambda: self.assertFalse(
            record_event(2, "analysis_started", self.db, False, "analysis-1")
        ))
        self.step(23, "aucun événement stocké sans consentement", lambda: self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM privacy_events"), 0
        ))
        self.step(24, "événement consenti stocké", lambda: self.assertTrue(
            record_event(2, {"event_name": "analysis_started", "page_code": "analysis"}, self.db, True, "analysis-1")
        ))
        self.step(25, "même action idempotente", lambda: self.assertFalse(
            record_event(2, "analysis_started", self.db, True, "analysis-1")
        ))
        self.step(26, "un seul événement persistant", lambda: self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM privacy_events"), 1
        ))
        self.step(27, "petit groupe masqué", lambda: self.assertIsNone(
            aggregate_events(self.db)["analysis_started"]
        ))

        submit_feedback(2, "Analyse", "Suggestion", 5, "Retour fictif", False, self.db)
        self.step(28, "retour visible par son auteur", lambda: self.assertEqual(len(list_feedback(2, self.db)), 1))
        self.step(29, "retour isolé d’un autre utilisateur", lambda: self.assertEqual(len(list_feedback(1, self.db)), 0))
        update_status(1, 1, "resolved", "Traitement test", self.db)
        self.step(30, "statut administratif appliqué", lambda: self.assertEqual(
            list_feedback(1, self.db, is_admin=True)[0]["status"], "resolved"
        ))
        self.step(31, "changement de statut journalisé", lambda: self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM feedback_audit WHERE feedback_id=1"), 1
        ))
        self.step(32, "export des retours sans note interne", lambda: self.assertNotIn(
            "Traitement test", export_feedback_csv(1, self.db)
        ))
        MarketDataRepository(self.db).sync_source(load_source_registry()["bank_of_canada_valet"])
        set_source_enabled(1, "bank_of_canada_valet", False, "test", self.db)
        self.step(33, "source réellement désactivée", lambda: self.assertFalse(
            source_enabled("bank_of_canada_valet", self.db)
        ))
        self.step(34, "changement de source journalisé", lambda: self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM source_admin_history WHERE source_id=?", ("bank_of_canada_valet",)), 1
        ))
        self.step(35, "diagnostic sensible expurgé", lambda: self.assertEqual(
            redact("password=abc"), "[expurgé]"
        ))
        personal_export = export_user_data(2, self.db)
        self.step(36, "export personnel sans hachage", lambda: self.assertNotIn("password_hash", personal_export))
        self.step(37, "export personnel limité à son compte", lambda: self.assertEqual(
            json.loads(personal_export)["profile"]["email"], "beta@example.invalid"
        ))
        self.step(38, "suppression du compte", lambda: self.assertTrue(delete_account(2, self.db)))
        self.step(39, "compte absent après suppression", lambda: self.assertIsNone(
            SQLiteRepository(self.db).get_user_by_id(2)
        ))
        self.step(40, "brouillon supprimé", lambda: self.assertEqual(load_draft(2, self.db)[0], {}))
        self.step(41, "retour personnel supprimé", lambda: self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM feedback WHERE user_id=2"), 0
        ))
        self.step(42, "événement sans lien vers le compte supprimé", lambda: self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM privacy_events WHERE user_id=2"), 0
        ))
        self.step(43, "administrateur préservé", lambda: self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM users WHERE role='admin'"), 1
        ))
        self.assertEqual([row[0] for row in self.trace], list(range(1, 44)))
        self.assertTrue(all(row[2] == "passed" for row in self.trace))

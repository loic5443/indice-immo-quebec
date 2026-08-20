"""SQLite repository: all analysis mutations are scoped by their owner."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


class SQLiteRepository:
    """Local repository with parameterized statements and explicit ownership checks."""

    def __init__(self, database_path: Path | str):
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_user(self, values: dict[str, str]) -> bool:
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    """INSERT INTO users (
                    name, email, password_hash, password_salt, plan, created_at,
                    user_type, investment_horizon, risk_tolerance
                    ) VALUES (?, ?, ?, ?, 'free', ?, ?, ?, ?)""",
                    (
                        values["name"], values["email"], values["password_hash"],
                        values["password_salt"], values["created_at"], values["user_type"],
                        values["investment_horizon"], values["risk_tolerance"],
                    ),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def count_analyses(self, user_id: int) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT COUNT(*) FROM analyses WHERE user_id = ?", (user_id,)).fetchone()
        return int(row[0])

    def save_analysis(self, user_id: int, property_name: str, values: dict[str, Any]) -> int:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """INSERT INTO analyses (
                user_id, property_name, created_at, price, down_payment, rental_income,
                monthly_expenses, cash_flow, cash_on_cash_return, capitalization_rate,
                debt_service_coverage_ratio, engine_version, data_provenance, user_profile,
                immo_score, confidence_index, engine_verdict, positive_factors_json,
                negative_factors_json, missing_data_json, recommended_checks_json, immodna_json,
                financial_inputs_json, scenarios_json, resilience_json, market_context_json, immovalue_json,
                official_role_snapshot_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, property_name, values["created_at"], values["price"], values["down_payment"],
                 values["rental_income"], values["monthly_expenses"], values["cash_flow"],
                 values["cash_on_cash_return"], values["capitalization_rate"],
                 values["debt_service_coverage_ratio"], values["engine_version"], values["data_provenance"],
                 values["user_profile"], values["immo_score"], values["confidence_index"],
                 values["engine_verdict"], values["positive_factors_json"], values["negative_factors_json"],
                 values["missing_data_json"], values["recommended_checks_json"], values["immodna_json"],
                 values["financial_inputs_json"], values["scenarios_json"], values["resilience_json"],
                 values["market_context_json"], values["immovalue_json"], values["official_role_snapshot_json"]),
            )
        return int(cursor.lastrowid)

    def list_analyses(self, user_id: int) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM analyses WHERE user_id = ? ORDER BY is_favorite DESC, created_at DESC", (user_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_owned_analysis(self, user_id: int, analysis_id: int) -> dict[str, Any] | None:
        """Load one saved analysis only when it belongs to the active account."""

        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id),
            ).fetchone()
        return dict(row) if row else None

    def get_owned_analyses_for_comparison(
        self, user_id: int, analysis_a_id: int, analysis_b_id: int,
    ) -> list[dict[str, Any]]:
        """Return exactly two saved snapshots owned by one user, in requested order.

        This is deliberately a scoped SQL query instead of loading a user's whole
        history in the interface and filtering it there.  There is no administrator
        bypass: comparison is always a view of the signed-in user's own dossiers.
        """
        if analysis_a_id == analysis_b_id:
            return []
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM analyses WHERE user_id = ? AND id IN (?, ?)",
                (user_id, analysis_a_id, analysis_b_id),
            ).fetchall()
        by_id = {int(row["id"]): dict(row) for row in rows}
        return [by_id[analysis_id] for analysis_id in (analysis_a_id, analysis_b_id) if analysis_id in by_id]

    def delete_analysis(self, user_id: int, analysis_id: int) -> bool:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute("DELETE FROM analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id))
        return cursor.rowcount == 1

    def toggle_favorite(self, user_id: int, analysis_id: int) -> bool:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """UPDATE analyses SET is_favorite = CASE is_favorite WHEN 1 THEN 0 ELSE 1 END
                WHERE id = ? AND user_id = ?""", (analysis_id, user_id)
            )
        return cursor.rowcount == 1

    def tracked_dossier_fingerprints(self, user_id: int) -> set[str]:
        """Return follow selections for one account only."""

        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT dossier_fingerprint FROM tracked_dossiers WHERE user_id = ?", (user_id,)
            ).fetchall()
        return {str(row["dossier_fingerprint"]) for row in rows}

    def set_dossier_tracking(self, user_id: int, fingerprint: str, enabled: bool) -> None:
        """Persist one owner-scoped follow choice without saving dossier content."""

        with closing(self._connect()) as connection, connection:
            if enabled:
                connection.execute(
                    "INSERT OR IGNORE INTO tracked_dossiers (user_id, dossier_fingerprint) VALUES (?, ?)",
                    (user_id, fingerprint),
                )
            else:
                connection.execute(
                    "DELETE FROM tracked_dossiers WHERE user_id = ? AND dossier_fingerprint = ?",
                    (user_id, fingerprint),
                )

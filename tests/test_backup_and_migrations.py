from contextlib import closing
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from data.database import create_user, initialize_database
from migrations.runner import apply_migrations, applied_migrations
from services.backup_service import BackupError, backup_database, verify_backup


class OperationalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "source.sqlite"
        initialize_database(self.db)
        create_user("Client", "backup@example.test", "long-password-test", self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_backup_restores_accounts_and_migrations_without_touching_source(self):
        target = self.root / "backup.sqlite"
        before = self.db.read_bytes()
        metadata = backup_database(self.db, target)
        self.assertEqual(metadata["integrity"], "ok")
        self.assertEqual(metadata["schema_version"], "0028")
        self.assertEqual(verify_backup(target)["sha256"], metadata["sha256"])
        self.assertEqual(self.db.read_bytes(), before)
        with closing(sqlite3.connect(target)) as connection, connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
        self.assertEqual(applied_migrations(target), applied_migrations(self.db))
        with self.assertRaises(BackupError):
            backup_database(self.db, target)

    def test_random_sqlite_is_not_accepted_as_immoradar_backup(self):
        unknown = self.root / "unknown.sqlite"
        with closing(sqlite3.connect(unknown)) as connection, connection:
            connection.execute("CREATE TABLE unrelated(id INTEGER)")
        with self.assertRaises(BackupError):
            verify_backup(unknown)

    def test_failed_migration_rolls_back_schema_and_marker(self):
        directory = self.root / "broken-migrations"
        directory.mkdir()
        (directory / "0001_test.sql").write_text("CREATE TABLE should_not_survive(id INTEGER); INSERT INTO missing_table VALUES(1);")
        target = self.root / "broken.sqlite"
        with patch("migrations.runner.MIGRATIONS_DIRECTORY", directory):
            with self.assertRaises(sqlite3.Error):
                apply_migrations(target)
        with closing(sqlite3.connect(target)) as connection, connection:
            self.assertIsNone(connection.execute("SELECT 1 FROM sqlite_master WHERE name='should_not_survive'").fetchone())
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0], 0)

    def test_two_initializers_do_not_apply_schema_twice(self):
        target = self.root / "concurrent.sqlite"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(apply_migrations, [target, target]))
        combined = results[0] + results[1]
        self.assertEqual(len(combined), len(set(combined)))
        self.assertEqual(sorted(combined), applied_migrations(target))
        self.assertEqual(applied_migrations(target)[-1], "0028")

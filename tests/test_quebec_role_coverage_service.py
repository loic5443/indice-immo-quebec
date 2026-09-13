"""No-network checks for resumable official-role coverage batches."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from data.database import initialize_database
from services.quebec_role_auto_sync import resolve_official_territory
from services.quebec_role_coverage_service import coverage_status, synchronize_role_coverage


INDEX = (
    "code géographique,nom du territoire,lien,date de modification\n"
    "01023,Ville A,https://mamh.gouv.qc.ca/role/RM01023.xml,2026-01-01\n"
    "02048,Ville B,https://mamh.gouv.qc.ca/role/RM02048.xml,2026-01-01\n"
    "03011,Ville C,https://mamh.gouv.qc.ca/role/RM03011.xml,2026-01-01\n"
).encode()


def xml(code: str) -> bytes:
    return (
        b'\xef\xbb\xbf<?xml version="1.0"?><RL><VERSION>2.9</VERSION><RLM01A>' + code.encode()
        + b'</RLM01A><RLM02A>2026</RLM02A><RLUEx><RL0101><RL0101Ax>1</RL0101Ax>'
        + b'<RL0101Gx>RUE PUBLIQUE</RL0101Gx></RL0101><RL0104><RL0104A>1</RL0104A></RL0104>'
        + b'<RL0402A>1</RL0402A><RL0403A>2</RL0403A><RL0404A>3</RL0404A></RLUEx></RL>'
    )


class RoleCoverageSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = Path(self.tmp.name) / "coverage.sqlite"
        initialize_database(self.db)
        resolve_official_territory(self.db, "Ville A", index_fetcher=lambda _: INDEX)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def _fetcher(url):
        return xml(url[-9:-4])

    def test_limited_batch_is_resumable_and_records_aggregate_history(self):
        first = synchronize_role_coverage(self.db, territory_limit=2, byte_budget=1_000_000, fetcher=self._fetcher, version_fetcher=lambda _: "2.9")
        self.assertEqual((first.synchronized, first.remaining), (2, 1))
        second = synchronize_role_coverage(self.db, territory_limit=2, byte_budget=1_000_000, fetcher=self._fetcher, version_fetcher=lambda _: "2.9")
        self.assertEqual((second.synchronized, second.remaining, second.status), (1, 0, "completed"))
        self.assertEqual(coverage_status(self.db), {"indexed": 3, "imported": 3, "remaining": 0, "units": 3})
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM role_coverage_runs").fetchone()[0], 2)

    def test_disabled_territory_is_not_downloaded(self):
        with sqlite3.connect(self.db) as connection, connection:
            connection.execute("INSERT INTO role_territory_settings(territory_code,enabled) VALUES('02048',0)")
        result = synchronize_role_coverage(self.db, territory_limit=None, byte_budget=1_000_000, fetcher=self._fetcher, version_fetcher=lambda _: "2.9")
        # A disabled territory is intentionally not downloaded, but it is
        # still visibly uncovered rather than reported as a completed job.
        self.assertEqual((result.synchronized, result.remaining, result.status), (2, 1, "stopped"))
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM role_territory_imports WHERE territory_code='02048'").fetchone()[0], 0)

    def test_source_disabled_refuses_the_batch_before_download(self):
        with sqlite3.connect(self.db) as connection, connection:
            connection.execute("UPDATE data_sources SET enabled=0 WHERE source_id='mamh_quebec_assessment_rolls'")
        with self.assertRaisesRegex(ValueError, "official_source_disabled"):
            synchronize_role_coverage(self.db, fetcher=lambda _: self.fail("download must not run"))

    def test_recent_failure_does_not_block_the_next_territory_in_a_small_batch(self):
        def failing_first(url):
            if "01023" in url:
                raise ValueError("official_network_unavailable")
            return self._fetcher(url)

        first = synchronize_role_coverage(self.db, territory_limit=1, byte_budget=1_000_000, fetcher=failing_first, version_fetcher=lambda _: "2.9")
        self.assertEqual((first.synchronized, first.failed), (0, 1))
        second = synchronize_role_coverage(self.db, territory_limit=1, byte_budget=1_000_000, fetcher=self._fetcher, version_fetcher=lambda _: "2.9")
        self.assertEqual((second.synchronized, second.failed), (1, 0))

    def test_cooldown_failure_remains_uncovered_in_the_completion_count(self):
        failed = synchronize_role_coverage(
            self.db, territory_limit=1, byte_budget=1_000_000,
            fetcher=lambda _: (_ for _ in ()).throw(ValueError("official_network_unavailable")),
            version_fetcher=lambda _: "2.9",
        )
        self.assertEqual((failed.status, failed.remaining), ("stopped", 3))


if __name__ == "__main__":
    unittest.main()

from contextlib import closing
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from fastapi.testclient import TestClient
from data.database import initialize_database
from scripts.render_server import runtime_environment, service_commands, supervise
from services import billing_api, deployment_api


class RenderEnvironmentTests(unittest.TestCase):
    def test_render_url_replaces_missing_public_url_without_enabling_payments(self):
        env = runtime_environment({"RENDER_EXTERNAL_URL": "https://immoradar.example/"})
        self.assertEqual(env["IMMORADAR_PUBLIC_URL"], "https://immoradar.example")
        self.assertNotIn("IMMORADAR_BILLING_ENABLED", env)
        self.assertEqual(runtime_environment({"IMMORADAR_PUBLIC_URL": "https://custom.example", "RENDER_EXTERNAL_URL": "https://fallback.example"})["IMMORADAR_PUBLIC_URL"], "https://custom.example")

    def test_invalid_origin_cannot_put_recovery_tokens_on_a_foreign_path_or_http(self):
        for url in ["http://example.test", "https://user:password@example.test", "https://example.test/path", "https://example.test/?token=secret"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                runtime_environment({"IMMORADAR_PUBLIC_URL": url})

    def test_render_refuses_ephemeral_or_absent_mount(self):
        with patch("scripts.render_server.os.path.ismount", return_value=False):
            with self.assertRaises(ValueError):
                runtime_environment({"RENDER": "true"})
        with patch("scripts.render_server.os.path.ismount", return_value=True):
            with self.assertRaises(ValueError):
                runtime_environment({"RENDER": "true", "IMMORADAR_DATABASE_PATH": "/tmp/lost.db"})
            env = runtime_environment({"RENDER": "true"})
            self.assertEqual(env["IMMORADAR_DATABASE_PATH"], "/app/var/immoradar.db")

    def test_invalid_or_reserved_port_does_not_start_a_partial_instance(self):
        for port in ("not-a-port", "80", "8501", "8000", "65536"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                runtime_environment({"PORT": port})

    def test_operations_are_opt_in_and_internal_servers_bind_loopback(self):
        commands = service_commands({})
        self.assertEqual([name for name, _ in commands], ["billing", "application", "proxy"])
        self.assertIn("127.0.0.1", commands[0][1])
        self.assertIn("--server.address=127.0.0.1", commands[1][1])
        self.assertEqual(service_commands({"IMMORADAR_OPERATIONS_ENABLED": "1"})[-1][0], "operations")


class SupervisorTests(unittest.TestCase):
    def run_recording_children(self, commands, stop):
        actual = subprocess.Popen
        children = []
        def launch(*args, **kwargs):
            process = actual(*args, **kwargs)
            children.append(process)
            return process
        with patch("scripts.render_server.subprocess.Popen", side_effect=launch):
            result = supervise(commands, dict(os.environ), stop, poll_interval=0.02, shutdown_timeout=1)
        self.assertTrue(all(process.poll() is not None for process in children))
        return result

    def test_one_service_exit_stops_the_other_process(self):
        commands = [("sleeping", [sys.executable, "-c", "import time; time.sleep(30)"]),
                    ("failed", [sys.executable, "-c", "raise SystemExit(3)"])]
        self.assertEqual(self.run_recording_children(commands, threading.Event()), 1)

    def test_shutdown_event_stops_children_cleanly(self):
        event = threading.Event()
        timer = threading.Timer(0.15, event.set)
        timer.start()
        try:
            self.assertEqual(self.run_recording_children([("server", [sys.executable, "-c", "import time; time.sleep(30)"])], event), 0)
        finally:
            timer.cancel()

    def test_failed_second_launch_reaps_the_first_child(self):
        actual = subprocess.Popen
        process = actual([sys.executable, "-c", "import time; time.sleep(30)"])
        with patch("scripts.render_server.subprocess.Popen", side_effect=[process, OSError("launch failed")]):
            with self.assertRaises(OSError):
                supervise([("first", []), ("second", [])], dict(os.environ), threading.Event(), shutdown_timeout=1)
        self.assertIsNotNone(process.poll())


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "deployment.sqlite"
        initialize_database(self.db)
        self.database_patch = patch.object(deployment_api, "DATABASE_PATH", self.db)
        self.database_patch.start()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.database_patch.stop)

    def get_readiness(self):
        with patch.object(billing_api, "DATABASE_PATH", self.db), TestClient(deployment_api.app) as client:
            return client.get("/_deployment/ready")

    def test_healthy_database_and_streamlit_are_both_required(self):
        response = Mock(status=200)
        with patch.object(deployment_api, "urlopen") as get:
            get.return_value.__enter__.return_value = response
            result = self.get_readiness()
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json(), {"status": "ok"})
            get.assert_called_once_with("http://127.0.0.1:8501/_stcore/health", timeout=2)

    def test_failed_streamlit_is_not_reported_as_healthy(self):
        with patch.object(deployment_api, "urlopen", side_effect=URLError("private diagnostic")):
            result = self.get_readiness()
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.json(), {"status": "unavailable"})

    def test_missing_database_is_not_silently_created_by_a_health_probe(self):
        missing = Path(self.temp.name) / "missing.sqlite"
        with patch.object(deployment_api, "DATABASE_PATH", missing), TestClient(deployment_api.app) as client:
            result = client.get("/_deployment/ready")
        self.assertEqual(result.status_code, 503)
        self.assertFalse(missing.exists())

    def test_incomplete_database_is_unavailable_even_if_file_exists(self):
        import sqlite3
        incomplete = Path(self.temp.name) / "incomplete.sqlite"
        with closing(sqlite3.connect(incomplete)) as connection:
            connection.execute("CREATE TABLE users(id INTEGER)")
        with patch.object(deployment_api, "DATABASE_PATH", incomplete), TestClient(deployment_api.app) as client:
            result = client.get("/_deployment/ready")
        self.assertEqual(result.status_code, 503)


if __name__ == "__main__":
    unittest.main()

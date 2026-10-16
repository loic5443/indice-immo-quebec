"""Single-instance deployment: three supervised processes on one SQLite disk."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent


def runtime_environment(source):
    env = dict(source)
    port = env.get("PORT", "10000")
    if not port.isdigit() or not 1024 <= int(port) <= 65535 or int(port) in {8000, 8501}:
        raise ValueError("Invalid public server port.")
    env["PORT"] = port
    database = Path(env.get("IMMORADAR_DATABASE_PATH", "/app/var/immoradar.db"))
    if not database.is_absolute():
        raise ValueError("The database path must be absolute.")
    if env.get("RENDER") == "true":
        if not database.resolve().is_relative_to(Path("/app/var")) or not os.path.ismount("/app/var"):
            raise ValueError("The persistent disk must be mounted at /app/var.")
    env["IMMORADAR_DATABASE_PATH"] = str(database)
    public_url = env.get("IMMORADAR_PUBLIC_URL") or env.get("RENDER_EXTERNAL_URL", "")
    if public_url:
        parsed = urlsplit(public_url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path not in {"", "/"}):
            raise ValueError("The public URL must be an HTTPS origin.")
        env["IMMORADAR_PUBLIC_URL"] = public_url.rstrip("/")
    env["XDG_DATA_HOME"] = str(database.parent / ".local-share")
    env["XDG_CONFIG_HOME"] = str(database.parent / ".config")
    return env


def prepare_directory_and_drop_privileges(database):
    directory = Path(database).parent
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if hasattr(os, "getuid") and os.getuid() == 0:
        import pwd
        account = pwd.getpwnam("app")
        os.chown(directory, account.pw_uid, account.pw_gid)
        os.chmod(directory, 0o700)
        os.initgroups(account.pw_name, account.pw_gid)
        os.setgid(account.pw_gid)
        os.setuid(account.pw_uid)
        os.environ["HOME"] = account.pw_dir


def service_commands(env):
    commands = [
        ("billing", [sys.executable, "-m", "uvicorn", "services.deployment_api:app", "--host", "127.0.0.1", "--port", "8000", "--workers", "1", "--no-access-log"]),
        ("application", [sys.executable, "-m", "streamlit", "run", "indice_immo.py", "--server.address=127.0.0.1", "--server.port=8501", "--server.headless=true"]),
        ("proxy", ["caddy", "run", "--config", str(ROOT / "deployment/RenderCaddyfile"), "--adapter", "caddyfile"]),
    ]
    if env.get("IMMORADAR_OPERATIONS_ENABLED") == "1":
        commands.append(("operations", [sys.executable, "-m", "scripts.operations_worker"]))
    return commands


def supervise(commands, env, stop, *, poll_interval=0.2, shutdown_timeout=10):
    children = []
    try:
        for name, command in commands:
            children.append((name, subprocess.Popen(command, env=env, cwd=ROOT)))
        while not stop.wait(poll_interval):
            for name, process in children:
                if process.poll() is not None:
                    print(f"Service stopped: {name}; restarting the instance is required.", file=sys.stderr, flush=True)
                    return 1
        return 0
    finally:
        for _, process in children:
            if process.poll() is None:
                process.terminate()
        deadline = time.monotonic() + shutdown_timeout
        for _, process in children:
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main():
    env = runtime_environment(os.environ)
    prepare_directory_and_drop_privileges(env["IMMORADAR_DATABASE_PATH"])
    # Refresh HOME after dropping root; all children inherit the same database.
    env["HOME"] = os.environ.get("HOME", "/home/app")
    os.environ.update(env)
    from data.database import initialize_database
    initialize_database(Path(env["IMMORADAR_DATABASE_PATH"]))
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    return supervise(service_commands(env), env, stop)


if __name__ == "__main__":
    raise SystemExit(main())

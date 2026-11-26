"""Opt-in session funnel; never collects addresses, money, IPs or user IDs."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import re
import sqlite3

EVENTS = {"visit", "demo", "analysis_started", "analysis_completed", "premium", "checkout_started"}

def record(path, session, event, consent=False):
    if not consent:
        return False
    if event not in EVENTS or not re.fullmatch(r"[a-f0-9]{32}", session):
        raise ValueError("Invalid measurement")
    now = datetime.now(timezone.utc)
    with closing(sqlite3.connect(path, timeout=5)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS usage_sessions (day TEXT NOT NULL, session TEXT NOT NULL, event TEXT NOT NULL, PRIMARY KEY(day,session,event))")
        db.execute("DELETE FROM usage_sessions WHERE day < ?", ((now-timedelta(days=90)).date().isoformat(),))
        db.execute("INSERT OR IGNORE INTO usage_sessions VALUES (?,?,?)", (now.date().isoformat(), session, event))
    return True

def summary(path, days=7):
    since=(datetime.now(timezone.utc)-timedelta(days=days-1)).date().isoformat()
    with closing(sqlite3.connect(path, timeout=5)) as db:
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='usage_sessions'").fetchone()
        if not exists:
            return {event:0 for event in sorted(EVENTS)}
        rows=db.execute("SELECT event,COUNT(DISTINCT session) FROM usage_sessions WHERE day>=? GROUP BY event", (since,)).fetchall()
    return {event:dict(rows).get(event,0) for event in sorted(EVENTS)}

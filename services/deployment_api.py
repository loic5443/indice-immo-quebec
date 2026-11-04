"""Readiness for the colocated deployment; billing endpoints stay unchanged."""
from contextlib import closing
from pathlib import Path
import sqlite3
from urllib.error import URLError
from urllib.request import urlopen

from fastapi.responses import HTMLResponse, JSONResponse, Response
from services.public_seo import guide_html, robots_text, sitemap_xml

from data.database import DATABASE_PATH
from services.billing_api import app


@app.get("/_deployment/ready")
def ready():
    try:
        uri = Path(DATABASE_PATH).resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=1)) as connection:
            for table in ("users", "analyses", "billing_accounts", "schema_migrations"):
                connection.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
        with urlopen("http://127.0.0.1:8501/_stcore/health", timeout=2) as response:
            if response.status != 200:
                raise ValueError("Application unavailable.")
    except (OSError, sqlite3.Error, URLError, ValueError):
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return {"status": "ok"}


@app.get("/valeur-propriete-quebec", response_class=HTMLResponse)
def property_value_guide():
    return HTMLResponse(guide_html(), headers={"Cache-Control": "public, max-age=3600"})


@app.get("/robots.txt", include_in_schema=False)
def public_robots():
    return Response(robots_text(), media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
def public_sitemap():
    return Response(sitemap_xml(), media_type="application/xml")


@app.get("/google3f133c0ebac158cc.html", include_in_schema=False)
def google_site_verification():
    return Response("google-site-verification: google3f133c0ebac158cc.html", media_type="text/html")

"""Admin-only, explicit synchronization of official Quebec assessment territories."""
import os, sqlite3, tempfile, threading, urllib.request
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from services.beta_service import _admin
from services.quebec_role_sync import INDEX_URL, parse_index, validate_xml
from services.quebec_role_importer import import_role_xml

MAX_BYTES=20_000_000; TIMEOUT_SECONDS=45; _LOCK=threading.Lock()
def _now(): return datetime.now(timezone.utc).isoformat()
def _log(c,code,action,outcome,detail="",checksum=None,units=None): c.execute("INSERT INTO role_sync_history(territory_code,action,outcome,checksum,imported_units,detail) VALUES(?,?,?,?,?,?)",(code,action,outcome,checksum,units,detail[:240]))
def _download(url, maximum=MAX_BYTES):
 request=urllib.request.Request(url,headers={"User-Agent":"ImmoRadar/1.0 official-data"})
 with urllib.request.urlopen(request,timeout=TIMEOUT_SECONDS) as response:
  chunks=[]; size=0
  while True:
   chunk=response.read(1024*1024)
   if not chunk: break
   size+=len(chunk)
   if size>maximum: raise ValueError("Fichier officiel trop volumineux.")
   chunks.append(chunk)
 return b"".join(chunks)
def refresh_index(actor,database_path,fetcher=_download):
 _admin(actor,database_path); rows=parse_index(fetcher(INDEX_URL)); now=_now()
 with closing(sqlite3.connect(database_path)) as c,c:
  c.execute("BEGIN IMMEDIATE")
  c.execute("CREATE TEMP TABLE incoming_index AS SELECT * FROM role_index_entries WHERE 0")
  c.executemany("INSERT INTO incoming_index VALUES(?,?,?,?,?)",[(r['territory_code'],r['municipality'],r['url'],r['updated_at'],now) for r in rows])
  c.execute("DELETE FROM role_index_entries")
  c.execute("INSERT INTO role_index_entries SELECT * FROM incoming_index")
  _log(c,"*","index_refresh","success",f"{len(rows)} territoires")
 return {"territories":len(rows),"synced_at":now}
def territories(actor,database_path,query="",state="",page=1,size=20):
 _admin(actor,database_path); q=f"%{query.strip()}%"; where="WHERE (i.municipality LIKE ? OR i.territory_code LIKE ?)"; params=[q,q]
 if state=="synchronized": where+=" AND r.territory_code IS NOT NULL"
 if state=="not_synchronized": where+=" AND r.territory_code IS NULL"
 sql="SELECT i.*,COALESCE(s.enabled,1) enabled,r.source_version,r.role_year,r.imported_units,r.synced_at FROM role_index_entries i LEFT JOIN role_territory_settings s ON s.territory_code=i.territory_code LEFT JOIN role_territory_imports r ON r.territory_code=i.territory_code "+where+" ORDER BY i.municipality LIMIT ? OFFSET ?"
 with closing(sqlite3.connect(database_path)) as c:
  c.row_factory=sqlite3.Row; total=c.execute("SELECT COUNT(*) FROM role_index_entries i LEFT JOIN role_territory_imports r ON r.territory_code=i.territory_code "+where,params).fetchone()[0]; rows=c.execute(sql,params+[size,(page-1)*size]).fetchall()
 return {"total":total,"items":[dict(r) for r in rows]}
def import_territory(actor,database_path,territory_code,fetcher=_download):
 _admin(actor,database_path)
 if not _LOCK.acquire(blocking=False): raise RuntimeError("Une synchronisation est déjà en cours.")
 try:
  with closing(sqlite3.connect(database_path)) as c:
   row=c.execute("SELECT source_url FROM role_index_entries WHERE territory_code=?",(territory_code,)).fetchone()
   if not row: raise ValueError("Territoire absent de l’index officiel.")
   enabled=c.execute("SELECT enabled FROM role_territory_settings WHERE territory_code=?",(territory_code,)).fetchone()
   if enabled and not enabled[0]: raise ValueError("Territoire désactivé.")
  content=fetcher(row[0]); checksum=validate_xml(content)
  with tempfile.NamedTemporaryFile(suffix=".xml",delete=False) as temp: temp.write(content); path=temp.name
  try: summary=import_role_xml(path,database_path,territory_code)
  finally: os.unlink(path)
  with closing(sqlite3.connect(database_path)) as c,c: _log(c,territory_code,"import","success","XML officiel validé",checksum,summary["imported_units"])
  return summary
 except Exception as error:
  with closing(sqlite3.connect(database_path)) as c,c: _log(c,territory_code,"import","failed",type(error).__name__)
  raise
 finally: _LOCK.release()
def set_territory_enabled(actor,database_path,territory_code,enabled):
 _admin(actor,database_path)
 with closing(sqlite3.connect(database_path)) as c,c:
  c.execute("INSERT INTO role_territory_settings(territory_code,enabled,updated_at) VALUES(?,?,?) ON CONFLICT(territory_code) DO UPDATE SET enabled=excluded.enabled,updated_at=excluded.updated_at",(territory_code,int(enabled),_now()));_log(c,territory_code,"enabled" if enabled else "disabled","success")
def remove_local_cache(actor,database_path,territory_code):
 _admin(actor,database_path)
 with closing(sqlite3.connect(database_path)) as c,c:
  c.execute("DELETE FROM role_assessment_units WHERE territory_code=?",(territory_code,));c.execute("DELETE FROM role_territory_imports WHERE territory_code=?",(territory_code,));_log(c,territory_code,"cache_removed","success")
def territory_for_municipality(database_path, municipality):
 with closing(sqlite3.connect(database_path)) as c:
  row=c.execute("SELECT i.territory_code FROM role_index_entries i JOIN role_territory_imports r ON r.territory_code=i.territory_code LEFT JOIN role_territory_settings s ON s.territory_code=i.territory_code WHERE lower(i.municipality)=lower(?) AND COALESCE(s.enabled,1)=1",(municipality.strip(),)).fetchone()
 return row[0] if row else None
def coverage_summary(actor,database_path):
 _admin(actor,database_path)
 with closing(sqlite3.connect(database_path)) as c:
  indexed=c.execute("SELECT COUNT(*) FROM role_index_entries").fetchone()[0]; synced=c.execute("SELECT COUNT(*) FROM role_territory_imports").fetchone()[0]; units=c.execute("SELECT COUNT(*) FROM role_assessment_units").fetchone()[0]; last=c.execute("SELECT MAX(synced_at) FROM role_territory_imports").fetchone()[0]
 return {"indexed":indexed,"synced":synced,"units":units,"last_success":last}

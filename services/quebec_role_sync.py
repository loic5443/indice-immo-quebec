"""Controlled official role index parsing; downloads are explicit admin operations only."""
import csv,hashlib,io
from datetime import datetime
INDEX_URL="https://mamh.gouv.qc.ca/role/indexRole.csv"
REQUIRED={"code géographique","nom du territoire","lien","date de modification"}
def parse_index(content:bytes):
 rows=list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
 if not rows or not REQUIRED.issubset(rows[0]): raise ValueError("Index officiel incompatible.")
 result=[]
 for row in rows:
  if not row["lien"].startswith("https://mamh.gouv.qc.ca/role/") or not row["lien"].endswith(".xml"): continue
  result.append({"territory_code":row["code géographique"],"municipality":row["nom du territoire"],"url":row["lien"],"updated_at":row["date de modification"]})
 return result
def validate_xml(content:bytes,max_size=20_000_000):
 if not content.startswith(b"\xef\xbb\xbf<?xml") or len(content)>max_size: raise ValueError("XML territorial invalide ou trop volumineux.")
 return hashlib.sha256(content).hexdigest()

"""Streaming importer for the documented public fields of Quebec assessment rolls."""
import hashlib, json, re, sqlite3, unicodedata, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

PUBLIC_FIELDS={"RL0101Ax","RL0101Gx","RL0101Ix","RL0104A","RL0104B","RL0104C","RL0104D","RL0104E","RL0104F","RL0104G","RL0104H","RL0105A","RL0302A","RL0306A","RL0307A","RL0401A","RL0402A","RL0403A","RL0404A"}
FORBIDDEN_FIELDS={"owner","proprietaire","courriel","email","telephone","postal","lot","cadastre"}

def inspect_role_xml(path, territory="01023"):
 """Compatibility inspection that never exposes an evaluation-unit payload."""
 version=year=None; units=0
 for _, element in ET.iterparse(path, events=("end",)):
  if element.tag=="VERSION": version=(element.text or "").strip()
  elif element.tag=="RLM01A" and (element.text or "").strip()!=territory: raise ValueError("Territoire XML inattendu.")
  elif element.tag=="RLM02A": year=int((element.text or "").strip())
  elif element.tag=="RLUEx": units+=1; element.clear()
 if version!="2.9" or not year: raise ValueError("Version ou année XML invalide.")
 return {"territory_code":territory,"version":version,"year":year,"units":units,"ingested_fields":sorted(PUBLIC_FIELDS)}

def _text(element, tag): return (element.findtext('.//'+tag) or '').strip() or None
def _num(element, tag, integer=False):
 value=_text(element,tag)
 if value is None:return None
 try:
  n=int(value) if integer else float(value)
  if n<0: raise ValueError
  return n
 except ValueError: raise ValueError(f"Valeur impossible pour {tag}.")
def _unit(element, sequence, territory, year, checksum, source_version):
 parts=[_text(element,t) for t in ("RL0104A","RL0104B","RL0104C","RL0104D","RL0104E","RL0104F","RL0104G","RL0104H")]
 matricule=''.join(x for x in parts if x) or None
 civic,street,local=_text(element,"RL0101Ax"),_text(element,"RL0101Gx"),_text(element,"RL0101Ix")
 address=' '.join(x for x in (civic,street,local) if x) or None
 provenance={key:{"source":f"MAMH rôle {territory} XML {source_version}","xml":key} for key in PUBLIC_FIELDS if _text(element,key) is not None}
 return (territory,checksum,matricule or f"unit-{sequence}",matricule,civic,street,local,address,_text(element,"RL0105A"),_num(element,"RL0302A"),_num(element,"RL0306A"),_num(element,"RL0307A",True),_num(element,"RL0402A"),_num(element,"RL0403A"),_num(element,"RL0404A"),year,_text(element,"RL0401A"),json.dumps(provenance,ensure_ascii=False),_role_key(' '.join(x for x in (civic,street) if x)),_role_key(street or ''))

def import_role_xml(path, database_path, territory="01023"):
 """Atomically replace one territory after a complete, streaming validation."""
 path=Path(path); digest=hashlib.sha256()
 with path.open("rb") as stream:
  for block in iter(lambda:stream.read(1024*1024),b""): digest.update(block)
 checksum=digest.hexdigest(); version=year=None; rows=[]; rejected=0; sequence=0
 for _,element in ET.iterparse(path,events=("end",)):
  if element.tag=="VERSION": version=(element.text or '').strip()
  elif element.tag=="RLM01A" and (element.text or '').strip()!=territory: raise ValueError("Territoire XML inattendu.")
  elif element.tag=="RLM02A": year=int((element.text or '').strip())
  elif element.tag=="RLUEx":
   sequence+=1
   try: rows.append(_unit(element,sequence,territory,year or 0,checksum,version or "inconnue"))
   except ValueError: rejected+=1
   element.clear()
 if version!="2.9" or not year: raise ValueError("Version ou année XML invalide.")
 c=sqlite3.connect(database_path)
 try:
  c.execute("BEGIN IMMEDIATE")
  c.execute("DELETE FROM role_assessment_units WHERE territory_code=?",(territory,))
  c.executemany("INSERT INTO role_assessment_units (territory_code,import_checksum,unit_key,matricule,civic_number,street_name,address_unit,address_text,use_code,land_area_m2,building_floors,construction_year,land_value,building_value,total_value,role_year,market_reference_date,field_provenance,address_search_key,street_search_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",rows)
  c.execute("INSERT OR REPLACE INTO role_territory_imports (territory_code,source_version,role_year,checksum,imported_units,rejected_units,synced_at) VALUES (?,?,?,?,?,?,?)",(territory,version,year,checksum,len(rows),rejected,datetime.now(timezone.utc).isoformat()))
  c.commit()
 except Exception:
  c.rollback();raise
 finally:
  c.close()
 return {"territory_code":territory,"version":version,"year":year,"imported_units":len(rows),"rejected_units":rejected,"checksum":checksum}

def _role_key(value):
 """Compare public street labels without stripping meaningful civic information."""
 value=unicodedata.normalize("NFD",value.casefold())
 value="".join(character for character in value if not unicodedata.combining(character))
 value=value.translate(str.maketrans("’‘‐‑–—", "''----"))
 value=re.sub(r"\b(rue|avenue|av\.?|boulevard|boul\.?|chemin|route|rang|place|montee|montee)\b", " ", value)
 return "".join(character for character in value if character.isalnum())


def display_role_address(value):
 """Return a readable label without changing raw official XML fields.

 Municipal role XML often capitalizes road names. This is presentation-only:
 searches and stored records continue to use the untouched public values.
 """
 text=' '.join(str(value or '').split())
 if not text or text != text.upper(): return text
 label=text.lower().title()
 # Keep common French joining words lower-case when they are not leading.
 return re.sub(r"(?<!^)\b(De|Du|Des|La|Le|Les|Et)\b",lambda match:match.group(1).lower(),label)


def _structured_query(query):
 match=re.match(r"^\s*(\d+(?:\s*[-–—]\s*\d+)?[A-Za-zÀ-ÖØ-öø-ÿ]?)\s*,?\s*(.+?)\s*$",query)
 return (match.group(1),_role_key(match.group(2))) if match else (None,None)


def search_role_units(database_path, territory, query, limit=20):
 """Find an official unit by matricule or an exact normalized civic/street pair.

 The municipal XML commonly stores a road label without its French road type
 (for example ``RUE-EXEMPLE`` rather than ``Rue Exemple``).  This narrow
 normalization handles that public formatting difference; it never selects a
 neighbouring civic number or an approximate street name.
 """
 query=' '.join(query.split())
 if not query or not territory:return []
 civic,street_key=_structured_query(query)
 c=sqlite3.connect(database_path)
 try:
  c.row_factory=sqlite3.Row
  fields="matricule,civic_number,street_name,address_unit,address_text,use_code,land_value,building_value,total_value,role_year,market_reference_date,field_provenance"
  if civic and street_key:
   cursor=c.execute(f"SELECT {fields} FROM role_assessment_units WHERE territory_code=? AND civic_number=? ORDER BY address_text LIMIT ?",(territory,civic,100))
   rows=[dict(row) for row in cursor.fetchall() if _role_key(row["street_name"] or "")==street_key][:limit]
  else:
   cursor=c.execute(f"SELECT {fields} FROM role_assessment_units WHERE territory_code=? AND (matricule=? OR address_text LIKE ?) ORDER BY address_text LIMIT ?",(territory,query,f"%{query}%",limit))
   rows=[dict(r) for r in cursor.fetchall()]
  cursor.close()
  return rows
 finally:
  c.close()


def suggest_role_units(database_path, query, limit=8):
 """Return a bounded, SQL-filtered list of public addresses from active roles.

 Only imported territories that remain enabled are searched.  The normalized
 keys are populated at import time and indexed, so the fallback never loads an
 entire municipal role into memory.
 """
 query=' '.join(query.split())
 if not query:return []
 civic,street_key=_structured_query(query)
 if not street_key:return []
 c=sqlite3.connect(database_path)
 try:
  c.row_factory=sqlite3.Row
  where="r.street_search_key LIKE ?"
  params=[f"{street_key}%"]
  if civic:
   where+=" AND r.civic_number LIKE ?";params.append(f"{civic}%")
  sql=("SELECT r.civic_number,r.street_name,r.address_unit,i.municipality "
       "FROM role_assessment_units r "
       "JOIN role_territory_imports imported ON imported.territory_code=r.territory_code "
       "JOIN role_index_entries i ON i.territory_code=r.territory_code "
       "LEFT JOIN role_territory_settings settings ON settings.territory_code=r.territory_code "
       f"WHERE COALESCE(settings.enabled,1)=1 AND {where} "
       "ORDER BY i.municipality,r.street_name,r.civic_number LIMIT ?")
  rows=c.execute(sql,params+[max(1,min(limit*4,32))]).fetchall()
  suggestions=[];seen=set()
  for row in rows:
   street=' '.join(part for part in (row['civic_number'],row['street_name']) if part)
   if row['address_unit']: street=f"{street}, {row['address_unit']}"
   street=display_role_address(street)
   signature=(_role_key(street),_role_key(row['municipality'] or ''))
   if street and signature not in seen:
    seen.add(signature);suggestions.append({'street':street,'city':row['municipality'] or '', 'postal_code':'','unit':'','source':'role'})
   if len(suggestions)>=limit:break
  return suggestions
 finally:
  c.close()


def role_street_variants(database_path, territory, query, limit=5):
 """Return only public road labels matching the normalized requested road."""
 _,street_key=_structured_query(query)
 if not street_key or not territory:return []
 c=sqlite3.connect(database_path)
 try:
  rows=c.execute("SELECT DISTINCT street_name FROM role_assessment_units WHERE territory_code=? AND street_name IS NOT NULL ORDER BY street_name",(territory,)).fetchall()
  return [row[0] for row in rows if _role_key(row[0])==street_key][:limit]
 finally:
  c.close()

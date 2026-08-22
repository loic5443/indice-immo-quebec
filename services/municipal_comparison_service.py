"""Official, attributed municipal comparison; never estimates sale prices or returns."""
import csv,io,sqlite3,urllib.request
from contextlib import closing
from datetime import datetime,timezone
from services.beta_service import _admin

SOURCE_ID="mamh_financial_profile"; SOURCE_URL="https://mamh.gouv.qc.ca/fichiersdonneesouvertes/PF-2024-2025.csv"
INDICATORS={"population":("population","habitants"),"FIALX02009":("uniformized_residential_assessment_average","CAD"),"FIALX01959":("uniformized_property_wealth","CAD"),"FIALX02011":("uniformized_property_wealth_per_unit","CAD par unité")}
def _now():return datetime.now(timezone.utc).isoformat()

def normalize_selection(values, maximum=4):
 """Keep the user's ordered selection, without duplicates or filter side effects."""
 selected=[]
 for value in values or []:
  if isinstance(value,str) and value and value not in selected:
   selected.append(value)
 return selected[:maximum]

def selection_options(selected, search_results):
 """A search may narrow suggestions, never remove a municipality already chosen."""
 return sorted(set(normalize_selection(selected))|set(search_results or []),key=str.casefold)
def fetch_profile(url=SOURCE_URL):
 with urllib.request.urlopen(url,timeout=45) as r:return r.read()
def import_profile(actor,database_path,content=None):
 _admin(actor,database_path); text=(content or fetch_profile()).decode("utf-8-sig"); rows=list(csv.DictReader(io.StringIO(text)))
 required={"an_donnee","cod_geo","nom_organisme","type_org"}|set(INDICATORS)
 if not rows or not required.issubset(rows[0]):raise ValueError("Schéma officiel du profil financier incompatible.")
 inserted=[]; invalid=0
 for row in rows:
  if row.get("type_org")!="Municipalité locale":continue
  try: year=int(row["an_donnee"])
  except (TypeError,ValueError):invalid+=1;continue
  for field,(code,unit) in INDICATORS.items():
   try:value=float(row[field].replace(" ","").replace(",","."))
   except (AttributeError,ValueError):invalid+=1;continue
   if value<0:invalid+=1;continue
   inserted.append((row["cod_geo"],row["nom_organisme"],year,code,value,unit,SOURCE_ID,SOURCE_URL,_now(),"official"))
 if not inserted:raise ValueError("Aucune ligne municipale valide.")
 with closing(sqlite3.connect(database_path)) as c,c:
  c.execute("BEGIN IMMEDIATE"); years={r[2] for r in inserted}
  for year in years:c.execute("DELETE FROM municipal_indicators WHERE source_id=? AND year=?",(SOURCE_ID,year))
  c.executemany("INSERT INTO municipal_indicators VALUES(?,?,?,?,?,?,?,?,?,?)",inserted)
 return {"municipalities":len({r[0] for r in inserted}),"indicators":len(inserted),"year":max(r[2] for r in inserted),"invalid":invalid}
def comparison(database_path,names,year=None):
 names=normalize_selection(names)
 if len(names)<2:return {"year":None,"rows":[],"available":False,"missing":[]}
 with closing(sqlite3.connect(database_path)) as c:
  c.row_factory=sqlite3.Row
  if year is None:
   common=c.execute("SELECT year FROM municipal_indicators WHERE municipality_name IN (%s) GROUP BY year HAVING COUNT(DISTINCT municipality_name)=? ORDER BY year DESC LIMIT 1" % ",".join("?"*len(names)),names+[len(names)]).fetchone()
   if not common:return {"year":None,"rows":[],"available":False,"missing":names}
   year=common[0]
  rows=c.execute("SELECT * FROM municipal_indicators WHERE year=? AND municipality_name IN (%s) ORDER BY municipality_name,indicator_code" % ",".join("?"*len(names)),[year]+names).fetchall()
 rows=[dict(row) for row in rows]
 expected=set(INDICATORS.values())
 expected_codes={code for code,_unit in expected}
 present={name:{row["indicator_code"] for row in rows if row["municipality_name"]==name} for name in names}
 missing=[name for name in names if present.get(name,set())!=expected_codes]
 return {"year":year,"rows":rows,"available":not missing,"missing":missing}
def municipalities(database_path,query=""):
 with closing(sqlite3.connect(database_path)) as c:return [r[0] for r in c.execute("SELECT DISTINCT municipality_name FROM municipal_indicators WHERE municipality_name LIKE ? ORDER BY municipality_name",(f"%{query}%",)).fetchall()]

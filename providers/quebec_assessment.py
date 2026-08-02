"""Official MAMH/Données Québec assessment metadata provider; no owner fields are accepted."""
from dataclasses import dataclass
SOURCE_ID="061c8cb7-ca4e-45be-a990-61fce7e7d2dc"
OFFICIAL_URL="https://www.donneesquebec.ca/recherche/dataset/roles-d-evaluation-fonciere-du-quebec"
ALLOWED_FIELDS={"municipality","assessment_unit_id","physical_address","land_value","building_value","total_value","assessment_year","reference_date"}
FORBIDDEN_FIELDS={"owner","owner_name","mailing_address","email"}
@dataclass(frozen=True)
class AssessmentRecord:
 municipality:str;assessment_unit_id:str;land_value:float|None=None;building_value:float|None=None;total_value:float|None=None;assessment_year:int|None=None
def filter_public_fields(row):
 if any(key.lower() in FORBIDDEN_FIELDS for key in row): raise ValueError("Champ caviardé ou propriétaire refusé.")
 return {key:value for key,value in row.items() if key in ALLOWED_FIELDS}

"""Unicode-safe Québec address validation, isolated from telemetry and financial engines."""
from dataclasses import dataclass
import re
import unicodedata

POSTAL_RE=re.compile(r"^[ABCEGHJKLMNPRSTVXY]\d[ABCEGHJKLMNPRSTVWXYZ]\d[ABCEGHJKLMNPRSTVWXYZ]\d$")
STREET_RE=re.compile(r"^\d+(?:\s*[-–—]\s*\d+)?[A-Za-zÀ-ÖØ-öø-ÿ]?(?:\s*,\s*|\s+).*[A-Za-zÀ-ÖØ-öø-ÿ].*$")
CITY_RE=re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ '\-‐‑–—]*[A-Za-zÀ-ÖØ-öø-ÿ]$")
FORBIDDEN_RE=re.compile(r"[<>\[\]{};\\]|[\x00-\x1f]")

class AddressValidationError(ValueError):
 def __init__(self,field,message): super().__init__(message);self.field=field

@dataclass(frozen=True)
class QuebecAddress:
 original:str; street:str; city:str; postal_code:str; unit:str=""; normalized_street:str=""; normalized_city:str=""; original_city:str=""

def _compact(value,field,maximum):
 if not isinstance(value,str): raise AddressValidationError(field,"Valeur invalide.")
 value=unicodedata.normalize("NFC",value)
 value=re.sub(r"\s+"," ",value).strip()
 if not value: raise AddressValidationError(field,"Ce champ est requis.")
 if len(value)>maximum or FORBIDDEN_RE.search(value): raise AddressValidationError(field,"Contenu invalide ou trop long.")
 return value
def _search(value):
 return value.translate(str.maketrans("’‘‛‐‑–—","'''----")).casefold()
def normalize_address(street,city,postal,unit=""):
 street=_compact(street,"street",160)
 city=_compact(city,"city",100)
 if not STREET_RE.fullmatch(street): raise AddressValidationError("street","Vérifiez le numéro et le nom de rue.")
 if not CITY_RE.fullmatch(city): raise AddressValidationError("city","Vérifiez le nom de la ville.")
 raw_postal=_compact(postal,"postal",12).replace(" ","").upper()
 if not POSTAL_RE.fullmatch(raw_postal): raise AddressValidationError("postal","Le code postal doit ressembler à A1A 1A1.")
 if unit:
  unit=_compact(unit,"unit",30)
  if not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]",unit): raise AddressValidationError("unit","Vérifiez l’appartement ou le local.")
 formatted=f"{raw_postal[:3]} {raw_postal[3:]}"
 return QuebecAddress(f"{street}, {city}, QC {formatted}",street,city,formatted,unit,_search(street),_search(city),city)

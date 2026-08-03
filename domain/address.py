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
 original:str; street:str; city:str; postal_code:str; unit:str=""; normalized_street:str=""; normalized_city:str=""; original_city:str=""; original_street:str=""

def _compact(value,field,maximum):
 if not isinstance(value,str): raise AddressValidationError(field,"Valeur invalide.")
 value=unicodedata.normalize("NFC",value)
 value=re.sub(r"\s+"," ",value).strip()
 if not value: raise AddressValidationError(field,"Ce champ est requis.")
 if len(value)>maximum or FORBIDDEN_RE.search(value): raise AddressValidationError(field,"Contenu invalide ou trop long.")
 return value
def _search(value):
 return value.translate(str.maketrans("’‘‛‐‑–—","'''----")).casefold()
def _token(value):
 return "".join(char for char in unicodedata.normalize("NFD",_search(value)) if not unicodedata.combining(char)).replace(" ","")
def _postal(value):
 value=re.sub(r"\s+","",value).upper()
 return value if POSTAL_RE.fullmatch(value) else None
def _parse_street_input(value, field_city, field_postal):
 """Accept a street alone or a map-style address without guessing conflicting cities."""
 original=_compact(value,"street",160); postal_in_address=None
 match=re.search(r"\b([ABCEGHJKLMNPRSTVXY]\s*\d\s*[ABCEGHJKLMNPRSTVWXYZ]\s*\d\s*[ABCEGHJKLMNPRSTVWXYZ]\s*\d)\b",original,re.I)
 if match:
  postal_in_address=_postal(match.group(1));original=(original[:match.start()]+original[match.end():]).strip(" ,")
 parts=[part.strip() for part in original.split(",") if part.strip()]
 street=parts[0] if parts else original
 remainder=parts[1:]
 if len(parts)>1 and re.fullmatch(r"\d+(?:\s*[-–—]\s*\d+)?[A-Za-zÀ-ÖØ-öø-ÿ]?",parts[0]):
  street=f"{parts[0]}, {parts[1]}";remainder=parts[2:]
 extracted=None
 if len(parts)>1:
  candidates=[]
  for part in remainder:
   token=_token(part)
   if token in {"qc","quebec","canada"}: continue
   candidates.append(part)
  if candidates:
   extracted=candidates[0]
   if any(_search(candidate)!=_search(extracted) for candidate in candidates[1:]): raise AddressValidationError("city","La ville extraite contredit le champ Ville; vérifiez laquelle est correcte.")
 field_postal=_compact(field_postal,"postal",12) if field_postal else ""
 field_normalized=_postal(field_postal) if field_postal else None
 if field_postal and not field_normalized: raise AddressValidationError("postal","Le code postal doit ressembler à A1A 1A1.")
 if field_normalized and postal_in_address and field_normalized!=postal_in_address: raise AddressValidationError("postal","Le code postal de l’adresse contredit le champ Code postal.")
 if not field_normalized and not postal_in_address: raise AddressValidationError("postal","Le code postal doit ressembler à A1A 1A1.")
 city=field_city
 if extracted and _search(extracted)!=_search(field_city): raise AddressValidationError("city","La ville extraite contredit le champ Ville; vérifiez laquelle est correcte.")
 return street,city,field_normalized or postal_in_address,original
def normalize_address(street,city,postal,unit=""):
 city=_compact(city,"city",100)
 street,city,raw_postal,original_street=_parse_street_input(street,city,postal)
 if not STREET_RE.fullmatch(street): raise AddressValidationError("street","Vérifiez le numéro et le nom de rue.")
 if not CITY_RE.fullmatch(city): raise AddressValidationError("city","Vérifiez le nom de la ville.")
 if unit:
  unit=_compact(unit,"unit",30)
  if not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]",unit): raise AddressValidationError("unit","Vérifiez l’appartement ou le local.")
 formatted=f"{raw_postal[:3]} {raw_postal[3:]}"
 return QuebecAddress(f"{street}, {city}, QC {formatted}",street,city,formatted,unit,_search(street),_search(city),city,original_street)

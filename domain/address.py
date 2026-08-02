"""Address input kept separate from external providers and financial engines."""
from dataclasses import dataclass
import re
@dataclass(frozen=True)
class QuebecAddress:
 original:str; street:str; city:str; postal_code:str; unit:str=""
def normalize_address(street,city,postal,unit=""):
 street=" ".join(street.strip().split());city=" ".join(city.strip().split()).title();postal=postal.replace(" ","").upper()
 if len(street)<4 or len(city)<2 or not re.fullmatch(r"[A-Z]\d[A-Z]\d[A-Z]\d",postal): raise ValueError("Adresse, ville ou code postal québécois invalide.")
 return QuebecAddress(f"{street}, {city}, QC {postal}",street,city,postal,unit.strip())

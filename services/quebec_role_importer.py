"""Streaming role importer: only documented root metadata is accepted until field guide is verified."""
import xml.etree.ElementTree as ET
from services.quebec_role_sync import validate_xml
def inspect_role_xml(path,territory):
 version=year=None;units=0
 for _,element in ET.iterparse(path,events=("end",)):
  if element.tag=="VERSION": version=element.text
  elif element.tag=="RLM01A" and element.text!=territory: raise ValueError("Territoire XML inattendu.")
  elif element.tag=="RLM02A": year=int(element.text)
  elif element.tag=="RLUEx": units+=1
  element.clear()
 if version!="2.9" or not year: raise ValueError("Version ou année XML invalide.")
 return {"territory_code":territory,"version":version,"year":year,"units":units,"ingested_fields":[],"excluded_reason":"Les codes métier XML ne sont pas ingérés sans guide officiel de correspondance."}

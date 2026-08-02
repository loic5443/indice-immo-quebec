"""Consent-first address lookup foundation. No public provider is enabled in this release."""
from domain.address import QuebecAddress
def lookup(address:QuebecAddress,consent:bool):
 if not consent:return {"status":"manual","message":"Vous pouvez poursuivre manuellement sans recherche externe.","found":[],"missing":["Renseignements publics"],"provenance":[]}
 return {"status":"unavailable","message":"Renseignements indisponibles automatiquement pour cette municipalité. Continuez manuellement.","found":[],"missing":["Évaluation municipale","Taxes","Zonage"],"provenance":[]}

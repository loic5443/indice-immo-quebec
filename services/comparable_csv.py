"""Local-only CSV import with explicit rights confirmation."""
import csv
from io import StringIO

CSV_COLUMNS = ["address", "property_type", "sale_date", "sale_price", "living_area", "land_area", "year_built", "units", "bedrooms", "bathrooms", "distance_km", "condition", "source_declared", "reference", "notes", "declared_closed_sale", "usage_right_confirmed"]

def csv_template() -> str:
    return ",".join(CSV_COLUMNS) + "\n"

def parse_comparables_csv(text: str, usage_right_confirmed: bool) -> list[dict]:
    if not usage_right_confirmed: raise ValueError("Confirmez votre droit d'utilisation avant l'import local.")
    rows = list(csv.DictReader(StringIO(text)))
    if not rows or set(CSV_COLUMNS) - set(rows[0]): raise ValueError("Colonnes CSV invalides ou manquantes.")
    result=[]
    for row in rows:
        row["usage_right_confirmed"] = True
        row["declared_closed_sale"] = str(row["declared_closed_sale"]).lower() in ("true", "1", "oui")
        for key in ("sale_price", "living_area", "land_area", "year_built", "units", "bedrooms", "bathrooms", "distance_km"):
            if row[key]: row[key] = float(row[key])
        result.append(row)
    return result

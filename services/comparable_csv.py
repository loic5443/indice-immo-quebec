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

def validate_csv_rows(text: str, usage_right_confirmed: bool, sales_confirmed: bool) -> tuple[list[dict], list[dict]]:
    """Return valid rows and explicit line errors; processing remains entirely local."""
    if not usage_right_confirmed or not sales_confirmed:
        return [], [{"line": 0, "error": "Confirmez les ventes conclues et votre droit d'utilisation."}]
    try: rows = parse_comparables_csv(text, True)
    except (ValueError, csv.Error) as error: return [], [{"line": 0, "error": str(error)}]
    valid, errors, seen = [], [], set()
    for line, row in enumerate(rows, start=2):
        key=(str(row.get("address", "")).strip().lower(), str(row.get("sale_date", "")), row.get("sale_price"))
        if key in seen: errors.append({"line":line,"error":"Doublon détecté dans le fichier."}); continue
        seen.add(key)
        if not row["declared_closed_sale"]: errors.append({"line":line,"error":"Une annonce active ne peut pas être importée."}); continue
        if row.get("sale_price",0)<=0 or row.get("living_area",0)<=0: errors.append({"line":line,"error":"Prix de vente et superficie doivent être supérieurs à zéro."}); continue
        valid.append(row)
    return valid, errors

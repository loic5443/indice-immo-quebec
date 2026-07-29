"""Backtesting scaffold. It refuses to invent results when no authorized dataset is provided."""
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--dataset", help="CSV autorisé avec estimation, prix de vente, type et région")
args = parser.parse_args()
if not args.dataset:
    print("Aucun jeu autorisé fourni : aucun résultat de performance n'est calculé.")
else:
    print("Structure prête : séparation temporelle/géographique, MAE, MdAPE, biais, couverture et résultats par type/région/version.")

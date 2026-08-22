"""Local, interactive password reset for a known ImmoRadar account.

The new password is read with getpass, so it is never echoed, printed, or
passed on the command line.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.database import DATABASE_PATH
from services.auth_service import reset_user_password


parser = argparse.ArgumentParser(description="Réinitialiser un mot de passe ImmoRadar local.")
parser.add_argument("--email", required=True, help="Adresse courriel du compte à réinitialiser.")
arguments = parser.parse_args()

new_password = getpass.getpass("Nouveau mot de passe (au moins 12 caractères) : ")
confirmation = getpass.getpass("Confirmez le nouveau mot de passe : ")
updated, message = reset_user_password(arguments.email, new_password, confirmation, DATABASE_PATH)
print(message)
raise SystemExit(0 if updated else 1)

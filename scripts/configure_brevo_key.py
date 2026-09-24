"""Store a Brevo API key locally without echoing it or putting it in shell history."""

from __future__ import annotations

import ctypes
import getpass
import sys
import tkinter as tk
from tkinter import messagebox


def valid_key(value: str) -> bool:
    """Reject accidental empty, truncated, or whitespace-padded input."""

    return len(value) >= 20 and value == value.strip()


def save_user_environment_variable(name: str, value: str) -> None:
    if sys.platform != "win32":
        raise OSError("La configuration locale de Brevo est disponible sur Windows seulement.")
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    # Notify future Windows processes without exposing the value.
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0, 1000, None)


def save_key_from_clipboard(root: tk.Tk) -> None:
    """Store the current clipboard key locally without displaying its value."""

    try:
        api_key = root.clipboard_get()
    except tk.TclError:
        messagebox.showerror("Clé absente", "Copiez d'abord la clé API dans Brevo, puis réessayez.")
        return

    if not valid_key(api_key):
        messagebox.showerror(
            "Clé incomplète",
            "La clé copiée semble incomplète. Rien n'a été enregistré.",
        )
        return

    save_user_environment_variable("BREVO_API_KEY", api_key)
    # Do not print or render the key. Clear it only after successful local storage.
    root.clipboard_clear()
    root.update()
    messagebox.showinfo("ImmoRadar", "Clé Brevo enregistrée localement. Vous pouvez fermer cette fenêtre.")


def show_clipboard_installer() -> int:
    """Offer a one-click, local-only installer for users who copied an API key."""

    root = tk.Tk()
    root.title("Configurer Brevo pour ImmoRadar")
    root.resizable(False, False)
    frame = tk.Frame(root, padx=24, pady=20)
    frame.pack()
    tk.Label(
        frame,
        text="1. Dans Brevo, créez puis copiez une nouvelle clé API.\n"
        "2. Revenez ici et cliquez sur le bouton ci-dessous.",
        justify="left",
    ).pack(anchor="w", pady=(0, 14))
    tk.Button(
        frame,
        text="Enregistrer la clé copiée",
        command=lambda: save_key_from_clipboard(root),
        padx=12,
        pady=6,
    ).pack(anchor="w")
    tk.Label(
        frame,
        text="La clé reste seulement sur cet ordinateur et n'est jamais affichée par ImmoRadar.",
        wraplength=410,
        justify="left",
    ).pack(anchor="w", pady=(14, 0))
    root.mainloop()
    return 0


def main() -> int:
    if "--clipboard" in sys.argv:
        return show_clipboard_installer()

    api_key = getpass.getpass("Collez la clé API Brevo, puis appuyez sur Entrée : ")
    if not valid_key(api_key):
        print("La clé semble incomplète. Rien n’a été enregistré.")
        return 1
    save_user_environment_variable("BREVO_API_KEY", api_key)
    print("Clé Brevo enregistrée localement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

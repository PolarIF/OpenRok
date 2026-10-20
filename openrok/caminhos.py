import os
import shutil
import sys
from pathlib import Path


# ==========================================================
# PATHS
# ==========================================================
# The base databases live in data/ next to the script, or
# next to the .exe when running from a PyInstaller build.
# The .exe carries a copy of the databases and extracts it
# on first run. What the user learns goes to pasta_dados().
# ==========================================================

def pasta_base():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def caminho_csv(nome):
    caminho = pasta_base() / "data" / nome
    embutido = Path(getattr(sys, "_MEIPASS", "")) / "data" / nome
    if not caminho.exists() and embutido.exists():
        caminho.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(embutido, caminho)
    return caminho


def pasta_dados():
    if sys.platform == "win32":
        raiz = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        raiz = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")

    pasta = raiz / "OpenRok"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def pasta_tessdata():
    # Tesseract wants the trailing separator
    if getattr(sys, "frozen", False):
        return str(Path(sys._MEIPASS) / "openrok" / "tessdata") + os.sep
    return str(Path(__file__).resolve().parent / "tessdata") + os.sep

import os
import shlex
import subprocess
import sys
from pathlib import Path


# ==========================================================
# START WITH THE SYSTEM
# ==========================================================
# Linux: a .desktop file in ~/.config/autostart.
# Windows: the per-user "Run" registry key (not validated yet).
# ==========================================================

def comando_inicio():
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "openrok"]


def _arquivo_linux():
    raiz = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return raiz / "autostart" / "openrok.desktop"


def ativar_inicio(ativo):
    if sys.platform == "win32":
        import winreg

        chave = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run",
                               0, winreg.KEY_SET_VALUE)
        with chave:
            if ativo:
                winreg.SetValueEx(chave, "OpenRok", 0, winreg.REG_SZ, subprocess.list2cmdline(comando_inicio()))
            else:
                try:
                    winreg.DeleteValue(chave, "OpenRok")
                except FileNotFoundError:
                    pass
        return

    arquivo = _arquivo_linux()
    if ativo:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(
            "[Desktop Entry]\nType=Application\nName=OpenRok\n"
            f"Exec={shlex.join(comando_inicio())}\nX-GNOME-Autostart-enabled=true\n",
            encoding="utf-8"
        )
    elif arquivo.exists():
        arquivo.unlink()

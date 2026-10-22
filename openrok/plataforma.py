import sys

from openrok.captura import CapturaMss, CapturaPortal, CapturaX11
from openrok.janela_jogo import JanelaWindows, JanelaX11


# ==========================================================
# PLATFORM CHOICE
# ==========================================================

def plataforma(portal=False):
    """(game window, capture) for this operating system.

    portal: on Linux, capture through the Wayland desktop portal instead of
    reading the game window (needs a running QApplication).
    """
    if sys.platform == "win32":
        return JanelaWindows(), CapturaMss()

    janela = JanelaX11()
    return janela, CapturaPortal() if portal else CapturaX11(janela)

import sys

from openrok.captura import CapturaMss, CapturaX11
from openrok.janela_jogo import JanelaWindows, JanelaX11


# ==========================================================
# PLATFORM CHOICE
# ==========================================================

def plataforma():
    """(game window, capture) for this operating system."""
    if sys.platform == "win32":
        return JanelaWindows(), CapturaMss()

    janela = JanelaX11()
    return janela, CapturaX11(janela)

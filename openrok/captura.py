import threading
from typing import Protocol

import mss
from PIL import Image


# ==========================================================
# SCREEN CAPTURE
# ==========================================================

class Captura(Protocol):

    def capturar(self, ret) -> Image.Image:
        """RGB image of a screen rectangle."""


class CapturaMss:
    """Fast capture (~0.3 ms for the question area) with mss.

    mss handles are not shareable between threads, so each
    thread gets its own.
    """

    def __init__(self):
        self._local = threading.local()

    def capturar(self, ret):
        if not hasattr(self._local, "mss"):
            self._local.mss = mss.MSS()

        foto = self._local.mss.grab({"left": ret.x, "top": ret.y, "width": ret.w, "height": ret.h})
        return Image.frombytes("RGB", foto.size, foto.bgra, "raw", "BGRX")


class CapturaDeQuadro:
    """Captures from a full-screen image instead of the screen (replay and tests)."""

    def __init__(self, quadro=None):
        self.quadro = quadro

    def capturar(self, ret):
        return self.quadro.crop((ret.x, ret.y, ret.x + ret.w, ret.y + ret.h))


class CapturaX11:
    """Reads the game window's own pixels (XGetImage).

    On XWayland a capture of the root window comes back black, but each X11
    window still has its content: ~6 ms for the watcher's area.
    """

    def __init__(self, janela):
        self.janela = janela

    def capturar(self, ret):
        from Xlib import X

        x0, y0 = self.janela.origem or (0, 0)
        bruto = self.janela.janela().get_image(ret.x - x0, ret.y - y0, ret.w, ret.h, X.ZPixmap, 0xFFFFFFFF)
        return Image.frombytes("RGB", (ret.w, ret.h), bruto.data, "raw", "BGRX")

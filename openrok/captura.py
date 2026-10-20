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

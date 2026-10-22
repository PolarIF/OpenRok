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


class CapturaPortal:
    """Screen capture through the desktop portal (Wayland ScreenCast + PipeWire).

    XGetImage on the game window sometimes keeps returning the same frame for
    seconds on XWayland, and the game's green/red answer is missed. The portal
    streams what the compositor shows. It needs a running QApplication, and
    the desktop asks the user which screen to share on start.

    It captures the screen, our own overlay included: the outline is drawn
    outside the option boxes, and the watcher reads colors inside them.
    """

    def __init__(self, iniciar=True):
        self._trava = threading.Lock()
        self._quadro = None

        if iniciar:
            from PySide6.QtGui import QGuiApplication
            from PySide6.QtMultimedia import QMediaCaptureSession, QScreenCapture, QVideoSink

            self._tela = QScreenCapture()
            self._sessao = QMediaCaptureSession()
            self._sink = QVideoSink()
            self._sessao.setScreenCapture(self._tela)
            self._sessao.setVideoSink(self._sink)
            self._sink.videoFrameChanged.connect(self._receber)
            self._tela.setScreen(QGuiApplication.primaryScreen())
            self._tela.start()

    def _receber(self, quadro):
        # Called on the Qt thread for each new frame: only keep it, the watcher converts on demand
        with self._trava:
            self._quadro = quadro

    def capturar(self, ret):
        from PySide6.QtCore import QRect
        from PySide6.QtGui import QImage

        with self._trava:
            quadro = self._quadro

        if quadro is None:
            return Image.new("RGB", (ret.w, ret.h))

        recorte = quadro.toImage().copy(QRect(ret.x, ret.y, ret.w, ret.h)).convertToFormat(QImage.Format_RGB888)
        return Image.frombuffer("RGB", (ret.w, ret.h), bytes(recorte.constBits()), "raw", "RGB",
                                recorte.bytesPerLine(), 1).copy()


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

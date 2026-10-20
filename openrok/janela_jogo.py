from typing import Protocol

from openrok.geometria import Ret


# ==========================================================
# THE GAME WINDOW
# ==========================================================
# Platform implementations (Windows, X11) come with the
# interface milestones; JanelaFixa covers a fixed area.
# ==========================================================

class JanelaJogo(Protocol):

    def localizar(self) -> Ret | None:
        """Client rectangle in screen coordinates, or None."""

    def ativa(self) -> bool:
        """True when the game is the foreground window."""


class JanelaFixa:

    def __init__(self, ret):
        self.ret = ret

    def localizar(self):
        return self.ret

    def ativa(self):
        return True


TITULO_JOGO = "Rise of Kingdoms"


# ==========================================================
# LINUX: X11 / XWAYLAND
# ==========================================================
# The game runs under Wine, which is an X11 client even on a
# Wayland desktop. Its window is found by title in the window
# manager's client list; "active" is _NET_ACTIVE_WINDOW.
# Any X error (window closed meanwhile) means "not found".
# ==========================================================

class JanelaX11:

    def __init__(self, titulo=TITULO_JOGO):
        from Xlib import display

        self.titulo = titulo
        self.display = display.Display()
        self.raiz = self.display.screen().root
        self.xid = None
        self.origem = None  # (x, y) of the window on screen, from the last localizar()
        self._atomos = {nome: self.display.intern_atom(nome)
                        for nome in ("_NET_CLIENT_LIST", "_NET_ACTIVE_WINDOW", "_NET_WM_NAME")}

    def janela(self):
        return self.display.create_resource_object("window", self.xid)

    def _nome(self, janela):
        from Xlib import X

        nome = janela.get_full_property(self._atomos["_NET_WM_NAME"], X.AnyPropertyType)
        if nome and nome.value:
            valor = nome.value
            return valor.decode("utf-8", "replace") if isinstance(valor, bytes) else str(valor)
        return janela.get_wm_name() or ""

    def _procurar(self):
        from Xlib import X

        lista = self.raiz.get_full_property(self._atomos["_NET_CLIENT_LIST"], X.AnyPropertyType)
        for xid in (lista.value if lista else []):
            try:
                if self._nome(self.display.create_resource_object("window", xid)) == self.titulo:
                    return xid
            except Exception:
                continue
        return None

    def localizar(self):
        try:
            if self.xid is not None:
                janela = self.janela()
                if self._nome(janela) != self.titulo:
                    self.xid = None

            if self.xid is None:
                self.xid = self._procurar()
                if self.xid is None:
                    return None

            janela = self.janela()
            geometria = janela.get_geometry()
            posicao = janela.translate_coords(self.raiz, 0, 0)
            self.origem = (-posicao.x, -posicao.y)
            return Ret(-posicao.x, -posicao.y, geometria.width, geometria.height)
        except Exception:
            self.xid = None
            return None

    def ativa(self):
        from Xlib import X

        try:
            ativa = self.raiz.get_full_property(self._atomos["_NET_ACTIVE_WINDOW"], X.AnyPropertyType)
            return bool(ativa and self.xid is not None and ativa.value[0] == self.xid)
        except Exception:
            return False


# ==========================================================
# WINDOWS: WIN32 (ctypes)
# ==========================================================
# Not validated yet (no Windows machine to test on).
# Coordinates are physical pixels: Qt makes the process
# DPI-aware, and the overlay divides by the screen scale.
# ==========================================================

class JanelaWindows:

    def __init__(self, titulo=TITULO_JOGO):
        import ctypes
        from ctypes import wintypes

        self.titulo = titulo
        self.hwnd = None
        self._user32 = ctypes.windll.user32
        self._wintypes = wintypes
        self._ctypes = ctypes

    def _procurar(self):
        achadas = []
        ctypes, wintypes, user32 = self._ctypes, self._wintypes, self._user32

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def visitar(hwnd, _):
            tamanho = user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(tamanho + 1)
            user32.GetWindowTextW(hwnd, buffer, tamanho + 1)
            if buffer.value == self.titulo and user32.IsWindowVisible(hwnd):
                achadas.append(hwnd)
                return False
            return True

        user32.EnumWindows(visitar, 0)
        return achadas[0] if achadas else None

    def localizar(self):
        user32, wintypes, ctypes = self._user32, self._wintypes, self._ctypes

        if self.hwnd is None or not user32.IsWindow(self.hwnd):
            self.hwnd = self._procurar()
            if self.hwnd is None:
                return None

        retangulo = wintypes.RECT()
        ponto = wintypes.POINT(0, 0)
        if not user32.GetClientRect(self.hwnd, ctypes.byref(retangulo)) or \
                not user32.ClientToScreen(self.hwnd, ctypes.byref(ponto)):
            self.hwnd = None
            return None

        return Ret(ponto.x, ponto.y, retangulo.right - retangulo.left, retangulo.bottom - retangulo.top)

    def ativa(self):
        user32 = self._user32
        return self.hwnd is not None and user32.GetForegroundWindow() == self.hwnd and not user32.IsIconic(self.hwnd)

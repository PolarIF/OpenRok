import sys

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

from openrok.eventos import Sugestao
from openrok.ui.tema import AMARELO, VERDE


# ==========================================================
# OVERLAY ON TOP OF THE GAME
# ==========================================================
# A transparent, always-on-top window over the game that
# lets every click through. It draws a glowing outline just
# OUTSIDE the right option box: the box interior is where the
# watcher reads the game's own green, so it is never touched.
#
# Window systems report physical pixels; Qt places windows in
# logical ones, hence the division by the screen scale.
# ==========================================================

ESPESSURA = 4
MARGEM = 4  # from the box edge to the middle of the stroke: the stroke covers 2-6 px outside


def para_logico(ret, dpr):
    return QRect(round(ret.x / dpr), round(ret.y / dpr), round(ret.w / dpr), round(ret.h / dpr))


class Overlay(QWidget):

    def __init__(self, textos):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                         | Qt.WindowTransparentForInput | Qt.X11BypassWindowManagerHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.textos = textos
        self.marcada = None
        self._geometria = None
        self._tempo_ms = 0.0

    def definir_opacidade(self, valor):
        self.setWindowOpacity(valor)

    def aplicar(self, evento, geometria):
        if isinstance(evento, Sugestao):
            if geometria is None:
                return
            self._mostrar(evento, geometria)
        else:
            # Any other event means the suggestion no longer applies:
            # a new question, an answer given, the result, or the game left
            self.esconder()

    def esconder(self):
        self.marcada = None
        self.hide()

    def _mostrar(self, sugestao, geometria):
        cliente, _ = geometria
        self.marcada = (sugestao.letra, sugestao.origem)
        self._geometria = geometria
        self._tempo_ms = sugestao.tempo_ms

        tela = QApplication.screenAt(para_logico(cliente, 1).center()) or QApplication.primaryScreen()
        self._dpr = tela.devicePixelRatio()
        self.setGeometry(para_logico(cliente, self._dpr))

        self.show()
        self.raise_()
        self._excluir_da_captura()
        self.update()

    def _excluir_da_captura(self):
        # Windows 10 2004+: keep our own green outline out of the watcher's capture
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 0x11)
            except Exception:
                pass

    def paintEvent(self, _):
        if self.marcada is None or self._geometria is None:
            return

        cliente, areas = self._geometria
        letra, origem = self.marcada
        cor = QColor(AMARELO if origem == "ia" else VERDE)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(1 / self._dpr, 1 / self._dpr)  # draw in physical pixels, relative to the game window

        caixa = areas.caixas[letra]
        contorno = QRectF(caixa.x - cliente.x - MARGEM, caixa.y - cliente.y - MARGEM,
                          caixa.w + 2 * MARGEM, caixa.h + 2 * MARGEM)

        brilho = QColor(cor)
        brilho.setAlpha(90)
        p.setPen(QPen(brilho, ESPESSURA + 6))
        p.drawRoundedRect(contorno.adjusted(-3, -3, 3, 3), 10, 10)

        p.setPen(QPen(cor, ESPESSURA))
        p.drawRoundedRect(contorno, 8, 8)

        self._desenhar_selo(p, areas.pergunta, cliente, cor, origem)

    def _desenhar_selo(self, p, pergunta, cliente, cor, origem):
        chave = {"ia": "selo_ia", "cache": "selo_banco"}.get(origem, "selo_banco")
        texto = self.textos[chave].format(tempo=f"{self._tempo_ms / 1000:.2f}".replace(".", ","))

        fonte = QFont()
        fonte.setPixelSize(14)
        fonte.setBold(True)
        p.setFont(fonte)

        largura = p.fontMetrics().horizontalAdvance(texto) + 20
        selo = QRectF(pergunta.x - cliente.x + pergunta.w - largura, pergunta.y - cliente.y - 30, largura, 24)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(15, 20, 15, 210))
        p.drawRoundedRect(selo, 12, 12)
        p.setPen(cor)
        p.drawText(selo, Qt.AlignCenter, texto)

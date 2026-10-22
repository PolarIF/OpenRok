from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPolygonF
from PySide6.QtWidgets import QApplication, QWidget

from openrok.eventos import ErroIA, JogoEncontrado, JogoPerdido, PerguntaDetectada, SemResposta, Sugestao
from openrok.idiomas import LETRAS
from openrok.ui.aba_inicio import MOTIVO_OPCOES
from openrok.ui.logo import pixmap_logo
from openrok.ui.overlay import para_logico
from openrok.ui.tema import AMARELO, BORDA, FUNDO, SECUNDARIO, VERDE


# ==========================================================
# ANSWER PILL OVER THE GAME
# ==========================================================
# A fullscreen game sits above every "always on top" window,
# so the pill lives in the same layer as the overlay
# (bypassing the window manager). Unlike the overlay it takes
# the mouse, so it can be dragged, but it never takes the
# keyboard focus: clicking it leaves the game the active
# window and the watcher keeps watching.
# ==========================================================

POSICAO_PADRAO = (0.5, 0.02)  # center-top, as fractions of the game window
ALTURA = 34
BOTAO = 30  # the play/pause button at the right end
CLIQUE = 4  # a press that moves less than this (px) is a click, not a drag


class Painel(QWidget):

    movido = Signal(float, float)
    vigia_alternado = Signal(bool)  # True: watching, False: paused

    def __init__(self, textos, posicao):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                         | Qt.X11BypassWindowManagerHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setCursor(Qt.OpenHandCursor)

        self.textos = textos
        self.posicao = list(posicao) if posicao else list(POSICAO_PADRAO)
        self.texto = self._principal = textos["painel_vigiando"]
        self.detalhe = self._secundario = ""
        self.cor = SECUNDARIO
        self._opcoes = []
        self._cliente = None
        self._dpr = 1.0
        self._arraste = None
        self.pausado = False

        fonte = QFont()
        fonte.setPixelSize(14)
        fonte.setBold(True)
        self.setFont(fonte)

    # ------------------------------------------------------
    # Content
    # ------------------------------------------------------
    def aplicar(self, evento, geometria):
        if isinstance(evento, JogoPerdido):
            self.hide()
            return

        if isinstance(evento, JogoEncontrado):
            self._mostrar_estado()
        elif isinstance(evento, PerguntaDetectada):
            self._opcoes = evento.opcoes
            self._mostrar_texto("…", "", SECUNDARIO)
        elif isinstance(evento, Sugestao):
            indice = LETRAS.index(evento.letra)
            opcao = self._opcoes[indice] if indice < len(self._opcoes) else ""
            chave = "selo_ia" if evento.origem == "ia" else "selo_banco"
            tempo = f"{evento.tempo_ms / 1000:.2f}".replace(".", ",")
            self._mostrar_texto(f"{evento.letra} · {opcao}".strip(" ·"), self.textos[chave].format(tempo=tempo),
                                AMARELO if evento.origem == "ia" else VERDE)
        elif isinstance(evento, SemResposta):
            if evento.motivo.startswith(MOTIVO_OPCOES):
                texto = self.textos["sem_resposta_opcoes"].format(resposta=evento.motivo[len(MOTIVO_OPCOES):])
            else:
                texto = self.textos["sem_resposta_fora"]
            self._mostrar_texto(texto, "", SECUNDARIO)
        elif isinstance(evento, ErroIA):
            self._mostrar_texto(self.textos["erro_ia"].format(erro=evento.mensagem), "", SECUNDARIO)
        else:
            return

        if geometria is not None:
            self._cliente = geometria[0]
            self._posicionar()
            self.show()
            self.raise_()

    def definir_pausado(self, pausado):
        self.pausado = pausado
        self._mostrar_estado()
        if self._cliente is not None and self.isVisible():
            self._posicionar()

    def _mostrar_estado(self):
        chave = "painel_pausado" if self.pausado else "painel_vigiando"
        self._mostrar_texto(self.textos[chave], "", SECUNDARIO)

    def _mostrar_texto(self, texto, detalhe, cor):
        self.texto, self.detalhe, self.cor = texto, detalhe, cor
        if self.detalhe:
            self.texto = f"{texto}  {detalhe}"
        self._principal, self._secundario = texto, detalhe
        self.update()

    # ------------------------------------------------------
    # Size and position (game window in physical pixels)
    # ------------------------------------------------------
    def _posicionar(self):
        tela = QApplication.screenAt(para_logico(self._cliente, 1).center()) or QApplication.primaryScreen()
        self._dpr = tela.devicePixelRatio()
        cliente = para_logico(self._cliente, self._dpr)

        metricas = self.fontMetrics()
        largura = 46 + BOTAO + metricas.horizontalAdvance(self._principal)
        if self._secundario:
            largura += 14 + metricas.horizontalAdvance(self._secundario)
        self.resize(largura, ALTURA)

        fx, fy = self.posicao
        self.move(round(cliente.x() + fx * cliente.width() - largura / 2), round(cliente.y() + fy * cliente.height()))

    def area_botao(self):
        return QRect(self.width() - BOTAO - 4, (ALTURA - 24) // 2, 24, 24)

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            self._arraste = (evento.globalPosition().toPoint(), self.pos(), evento.position().toPoint())
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, evento):
        if self._arraste is not None:
            inicio_mouse, inicio_janela, _ = self._arraste
            self.move(inicio_janela + (evento.globalPosition().toPoint() - inicio_mouse))

    def mouseReleaseEvent(self, evento):
        if self._arraste is None:
            return
        inicio_mouse, inicio_janela, local = self._arraste
        self._arraste = None
        self.setCursor(Qt.OpenHandCursor)

        if (evento.globalPosition().toPoint() - inicio_mouse).manhattanLength() < CLIQUE:
            self.move(inicio_janela)
            if self.area_botao().contains(local):
                self.definir_pausado(not self.pausado)
                self.vigia_alternado.emit(not self.pausado)
            return

        if self._cliente is not None:
            cliente = para_logico(self._cliente, self._dpr)
            self.posicao = [(self.x() + self.width() / 2 - cliente.x()) / cliente.width(),
                            (self.y() - cliente.y()) / cliente.height()]
            self.movido.emit(*self.posicao)

    # ------------------------------------------------------
    # Drawing
    # ------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        fundo = QColor(FUNDO)
        fundo.setAlpha(240)
        p.setPen(QColor(BORDA))
        p.setBrush(fundo)
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), ALTURA / 2, ALTURA / 2)

        p.drawPixmap(QPoint(10, (ALTURA - 20) // 2), pixmap_logo(20))

        metricas = self.fontMetrics()
        x = 36
        p.setPen(QColor(self.cor))
        p.drawText(QRectF(x, 0, self.width(), ALTURA), Qt.AlignLeft | Qt.AlignVCenter, self._principal)

        if self._secundario:
            x += metricas.horizontalAdvance(self._principal) + 14
            fonte = QFont(self.font())
            fonte.setBold(False)
            p.setFont(fonte)
            p.setPen(QColor(SECUNDARIO))
            p.drawText(QRectF(x, 0, self.width(), ALTURA), Qt.AlignLeft | Qt.AlignVCenter, self._secundario)

        self._desenhar_botao(p)

    def _desenhar_botao(self, p):
        # Paused: a green "play" to start watching. Watching: a gray "pause"
        botao = QRectF(self.area_botao())
        cor = QColor(VERDE if self.pausado else SECUNDARIO)
        p.setPen(Qt.NoPen)
        fundo = QColor(cor)
        fundo.setAlpha(45)
        p.setBrush(fundo)
        p.drawEllipse(botao)

        p.setBrush(cor)
        c = botao.center()
        if self.pausado:
            p.drawPolygon(QPolygonF([QPointF(c.x() - 3.5, c.y() - 6), QPointF(c.x() - 3.5, c.y() + 6),
                                     QPointF(c.x() + 6, c.y())]))
        else:
            p.drawRect(QRectF(c.x() - 5, c.y() - 5.5, 3.5, 11))
            p.drawRect(QRectF(c.x() + 1.5, c.y() - 5.5, 3.5, 11))

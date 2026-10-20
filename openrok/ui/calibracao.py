from PIL.ImageQt import ImageQt
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from openrok.geometria import Ret, areas_para
from openrok.ui.tema import AMARELO, QSS, VERDE


# ==========================================================
# AREA CALIBRATION
# ==========================================================
# For windows whose layout doesn't match the 1920x1080
# reference: the user drags a rectangle around the question
# and the four options on a capture of the game, and the
# reference layout is stretched onto it. A live preview shows
# where every area will be read.
# ==========================================================

def retangulo_para_fracoes(ret, tamanho):
    return [ret.x() / tamanho.width(), ret.y() / tamanho.height(),
            ret.width() / tamanho.width(), ret.height() / tamanho.height()]


class ImagemCalibracao(QWidget):

    def __init__(self, captura, calibracao):
        super().__init__()
        self.pixmap = QPixmap.fromImage(ImageQt(captura.convert("RGB")))
        self.tamanho_original = self.pixmap.size()
        self.calibracao = calibracao
        self._inicio = None
        self._arraste = None

        largura = min(960, self.tamanho_original.width())
        self.setFixedSize(largura, round(largura * self.tamanho_original.height() / self.tamanho_original.width()))
        self.setCursor(Qt.CrossCursor)

    def _escala(self):
        return self.tamanho_original.width() / self.width(), self.tamanho_original.height() / self.height()

    def mousePressEvent(self, evento):
        self._inicio = evento.position().toPoint()
        self._arraste = QRect(self._inicio, self._inicio)

    def mouseMoveEvent(self, evento):
        if self._inicio is not None:
            self._arraste = QRect(self._inicio, evento.position().toPoint()).normalized()
            self.update()

    def mouseReleaseEvent(self, evento):
        if self._inicio is None:
            return
        self._arraste = QRect(self._inicio, evento.position().toPoint()).normalized()
        self._inicio = None

        if self._arraste.width() > 10 and self._arraste.height() > 10:
            ex, ey = self._escala()
            original = QRect(round(self._arraste.x() * ex), round(self._arraste.y() * ey),
                             round(self._arraste.width() * ex), round(self._arraste.height() * ey))
            self.calibracao = retangulo_para_fracoes(original, self.tamanho_original)
        self._arraste = None
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self.pixmap)

        ex, ey = self._escala()
        areas = areas_para(Ret(0, 0, self.tamanho_original.width(), self.tamanho_original.height()), self.calibracao)

        p.setPen(QPen(QColor(VERDE), 2))
        for r in (areas.pergunta, *areas.caixas.values()):
            p.drawRect(QRectF(r.x / ex, r.y / ey, r.w / ex, r.h / ey))

        if self._arraste is not None:
            p.setPen(QPen(QColor(AMARELO), 2, Qt.DashLine))
            p.drawRect(self._arraste)


class DialogoCalibracao(QDialog):

    def __init__(self, captura_cliente, atual, textos):
        super().__init__()
        self.setWindowTitle("OpenRok")
        self.setStyleSheet(QSS)

        self.imagem = ImagemCalibracao(captura_cliente, atual)

        ajuda = QLabel(textos["calibrar_ajuda"])
        self.padrao = QPushButton(textos["calibrar_padrao"])
        self.padrao.clicked.connect(self._restaurar)
        ok = QPushButton("OK")
        ok.setObjectName("principal")
        ok.clicked.connect(self.accept)
        cancelar = QPushButton("✕")
        cancelar.clicked.connect(self.reject)

        botoes = QHBoxLayout()
        botoes.addWidget(self.padrao)
        botoes.addStretch()
        botoes.addWidget(cancelar)
        botoes.addWidget(ok)

        layout = QVBoxLayout(self)
        layout.addWidget(ajuda)
        layout.addWidget(self.imagem)
        layout.addLayout(botoes)

    def _restaurar(self):
        self.imagem.calibracao = None
        self.imagem.update()

    def resultado(self):
        return self.imagem.calibracao


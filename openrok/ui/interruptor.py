from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QAbstractButton, QSizePolicy

from openrok.ui.tema import SECUNDARIO, TEXTO, VERDE


# ==========================================================
# ON/OFF SWITCH
# ==========================================================
# Replaces check boxes: label on the left, then "ON"/"OFF"
# and a sliding knob on a green (on) or gray (off) track, so
# the state is obvious at a glance.
# ==========================================================

TRILHO_DESLIGADO = "#3A424D"


class Interruptor(QAbstractButton):

    def __init__(self, texto, parent=None):
        super().__init__(parent)
        self.setText(texto)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def texto_estado(self):
        return "ON" if self.isChecked() else "OFF"

    def sizeHint(self):
        largura = self.fontMetrics().horizontalAdvance(self.text()) + 110
        return QSize(largura, 30)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        ligado = self.isChecked()

        trilho = QRectF(self.width() - 42, (self.height() - 22) / 2, 38, 22)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(VERDE if ligado else TRILHO_DESLIGADO))
        p.drawRoundedRect(trilho, 11, 11)

        bolinha = QRectF(trilho.x() + (19 if ligado else 3), trilho.y() + 3, 16, 16)
        p.setBrush(QColor("#FFFFFF" if ligado else "#C9CED6"))
        p.drawEllipse(bolinha)

        fonte = QFont(self.font())
        fonte.setPixelSize(11)
        fonte.setBold(True)
        p.setFont(fonte)
        p.setPen(QColor(VERDE if ligado else SECUNDARIO))
        estado = QRectF(trilho.x() - 40, 0, 34, self.height())
        p.drawText(estado, Qt.AlignRight | Qt.AlignVCenter, self.texto_estado())

        p.setFont(self.font())
        p.setPen(QColor(TEXTO))
        p.drawText(QRectF(0, 0, estado.x() - 6, self.height()), Qt.AlignLeft | Qt.AlignVCenter, self.text())

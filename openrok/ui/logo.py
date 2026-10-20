from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# The owl: the classic symbol of wisdom, one eye drawn as a check mark
ARQUIVO = Path(__file__).resolve().parent / "logo.svg"


def pixmap_logo(tamanho):
    pixmap = QPixmap(tamanho, tamanho)
    pixmap.fill(Qt.transparent)
    pintor = QPainter(pixmap)
    QSvgRenderer(str(ARQUIVO)).render(pintor)
    pintor.end()
    return pixmap


def icone():
    icone = QIcon()
    for tamanho in (16, 24, 32, 48, 64, 128, 256):
        icone.addPixmap(pixmap_logo(tamanho))
    return icone

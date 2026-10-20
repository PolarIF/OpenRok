from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QPushButton, QSlider, QWidget

from openrok.idiomas import IDIOMAS
from openrok.ui.interruptor import Interruptor


# ==========================================================
# SETTINGS TAB
# ==========================================================

class AbaAjustes(QWidget):

    idioma_mudou = Signal(str)
    opacidade_mudou = Signal(float)
    fixar_mudou = Signal(bool)
    painel_mudou = Signal(bool)
    iniciar_mudou = Signal(bool)
    calibrar_pedido = Signal()

    def __init__(self, textos, config):
        super().__init__()

        self.idioma = QComboBox()
        for codigo, dados in IDIOMAS.items():
            self.idioma.addItem(dados["nome"], codigo)
        self.idioma.setCurrentIndex(self.idioma.findData(config.idioma))
        self.idioma.currentIndexChanged.connect(lambda i: self.idioma_mudou.emit(self.idioma.itemData(i)))

        self.opacidade = QSlider(Qt.Horizontal)
        self.opacidade.setRange(30, 100)
        self.opacidade.setValue(round(config.opacidade * 100))
        self.opacidade.valueChanged.connect(lambda v: self.opacidade_mudou.emit(v / 100))

        self.painel = Interruptor(textos["painel_no_jogo"])
        self.painel.setChecked(config.painel_no_jogo)
        self.painel.toggled.connect(self.painel_mudou)

        self.fixar = Interruptor(textos["fixar_topo"])
        self.fixar.setChecked(config.fixar_no_topo)
        self.fixar.toggled.connect(self.fixar_mudou)

        self.iniciar = Interruptor(textos["iniciar_sistema"])
        self.iniciar.setChecked(config.iniciar_com_sistema)
        self.iniciar.toggled.connect(self.iniciar_mudou)

        self.calibrar = QPushButton(textos["calibrar"])
        self.calibrar.clicked.connect(self.calibrar_pedido)

        layout = QFormLayout(self)
        layout.addRow(textos["idioma"], self.idioma)
        layout.addRow(textos["opacidade"], self.opacidade)
        layout.addRow(self.painel)
        layout.addRow(self.fixar)
        layout.addRow(self.iniciar)
        layout.addRow(self.calibrar)

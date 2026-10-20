from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QSystemTrayIcon, QTabWidget

from openrok.idiomas import IDIOMAS
from openrok.ui.aba_ajustes import AbaAjustes
from openrok.ui.aba_banco import AbaBanco
from openrok.ui.aba_inicio import AbaInicio
from openrok.ui.logo import icone
from openrok.ui.tema import QSS


# ==========================================================
# MAIN WINDOW
# ==========================================================
# Tabs Home / Database / Settings plus a tray icon. Closing
# the window keeps OpenRok running in the tray; "Quit" ends it.
# Every settings change is written to config right away.
# ==========================================================

class JanelaPrincipal(QMainWindow):

    idioma_mudou = Signal(str)
    opacidade_mudou = Signal(float)
    usar_ia_mudou = Signal(bool)
    marcar_no_jogo_mudou = Signal(bool)
    iniciar_mudou = Signal(bool)
    painel_no_jogo_mudou = Signal(bool)
    calibrar_pedido = Signal()
    sair_pedido = Signal()

    def __init__(self, config, conhecimento, salvar_config):
        super().__init__()
        self.config = config
        self.conhecimento = conhecimento
        self.salvar_config = salvar_config
        self._saindo = False

        self.setWindowTitle("OpenRok")
        self.setWindowIcon(icone())
        self.setStyleSheet(QSS)
        self.resize(400, 560)
        self._aplicar_fixar(config.fixar_no_topo)

        self._montar_abas()
        self._montar_bandeja()

    @property
    def textos(self):
        return IDIOMAS[self.config.idioma]["textos"]

    def _montar_abas(self):
        t = self.textos
        self.inicio = AbaInicio(t, self.config, len(self.conhecimento))
        self.banco = AbaBanco(t, self.conhecimento, lambda: self.inicio.atualizar_total(len(self.conhecimento)))
        self.ajustes = AbaAjustes(t, self.config)

        self.inicio.marcar_no_jogo_mudou.connect(lambda v: self._mudar("marcar_no_jogo", v, self.marcar_no_jogo_mudou))
        self.inicio.usar_ia_mudou.connect(lambda v: self._mudar("usar_ia", v, self.usar_ia_mudou))
        self.ajustes.idioma_mudou.connect(lambda v: self._mudar("idioma", v, self.idioma_mudou))
        self.ajustes.opacidade_mudou.connect(lambda v: self._mudar("opacidade", v, self.opacidade_mudou))
        self.ajustes.painel_mudou.connect(lambda v: self._mudar("painel_no_jogo", v, self.painel_no_jogo_mudou))
        self.ajustes.fixar_mudou.connect(self._fixar)
        self.ajustes.iniciar_mudou.connect(lambda v: self._mudar("iniciar_com_sistema", v, self.iniciar_mudou))
        self.ajustes.calibrar_pedido.connect(self.calibrar_pedido)

        abas = QTabWidget()
        abas.addTab(self.inicio, t["aba_inicio"])
        abas.addTab(self.banco, t["aba_banco"])
        abas.addTab(self.ajustes, t["aba_ajustes"])
        self.setCentralWidget(abas)

    def _montar_bandeja(self):
        self.bandeja = QSystemTrayIcon(icone(), self)
        self._menu_bandeja()
        self.bandeja.activated.connect(lambda motivo: motivo == QSystemTrayIcon.Trigger and self._mostrar())
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.bandeja.show()

    def _menu_bandeja(self):
        menu = QMenu(self)
        mostrar = QAction(self.textos["mostrar"], menu)
        mostrar.triggered.connect(self._mostrar)
        sair = QAction(self.textos["sair"], menu)
        sair.triggered.connect(self.sair)
        menu.addAction(mostrar)
        menu.addAction(sair)
        self.bandeja.setContextMenu(menu)

    def _mudar(self, campo, valor, sinal):
        setattr(self.config, campo, valor)
        self.salvar_config()
        sinal.emit(valor)

    def _fixar(self, valor):
        self.config.fixar_no_topo = valor
        self.salvar_config()
        self._aplicar_fixar(valor)
        self.show()

    def _aplicar_fixar(self, valor):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, valor)

    def _mostrar(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def aplicar(self, evento):
        self.inicio.aplicar(evento)

    def trocar_conhecimento(self, conhecimento):
        """New language: new database and every text redone."""
        self.conhecimento = conhecimento
        self._montar_abas()
        self._menu_bandeja()

    def sair(self):
        self._saindo = True
        self.sair_pedido.emit()
        QApplication.quit()

    def closeEvent(self, evento):
        if self._saindo or not QSystemTrayIcon.isSystemTrayAvailable():
            evento.accept()
            self.sair_pedido.emit()
            return
        evento.ignore()
        self.hide()

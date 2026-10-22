import logging
import os
import sys
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from openrok.armazem import Armazem
from openrok.autostart import ativar_inicio
from openrok.caminhos import caminho_csv, pasta_dados
from openrok.config import Config
from openrok.conhecimento import Conhecimento
from openrok.eventos import Aprendido
from openrok.idiomas import IDIOMAS
from openrok.ocr import MotorOCR
from openrok.plataforma import plataforma
from openrok.ui.calibracao import DialogoCalibracao
from openrok.ui.janela import JanelaPrincipal
from openrok.ui.overlay import Overlay
from openrok.ui.painel import Painel
from openrok.ui.ponte import Ponte
from openrok.vigia import Vigia


# ==========================================================
# THE APPLICATION
# ==========================================================
# Wires the watcher (its own thread) to the window and the
# overlay (interface thread) through a Ponte, and reacts to
# settings. Changing the language rebuilds the watcher with a
# new database, OCR model and bridge; the old bridge is
# disconnected first so nothing from the old watcher arrives
# after the switch.
# ==========================================================

class Aplicacao:

    def __init__(self, config, janela_jogo, captura, armazem, caminho_config, ia_fabrica, sem_banco=False):
        self.config = config
        self.janela_jogo = janela_jogo
        self.captura = captura
        # Diagnostic mode: no base database and a throwaway store, so every
        # question is unknown and nothing reaches the real database
        self.sem_banco = sem_banco
        self.armazem = Armazem(":memory:") if sem_banco else armazem
        self.caminho_config = caminho_config
        self.ia_fabrica = ia_fabrica

        self.vigia = None
        self.ponte = None
        self.ocr = None

    # ------------------------------------------------------
    # Start / stop
    # ------------------------------------------------------
    def iniciar(self):
        self.conhecimento, self.ocr, self._ia = self._carregar_idioma(self.config.idioma)

        self.janela = JanelaPrincipal(self.config, self.conhecimento, self.salvar_config)
        if self.sem_banco:
            self.janela.setWindowTitle("OpenRok [diagnóstico: sem banco]")
        self.overlay = Overlay(IDIOMAS[self.config.idioma]["textos"])
        self.overlay.definir_opacidade(self.config.opacidade)
        self.painel = Painel(IDIOMAS[self.config.idioma]["textos"], self.config.painel_posicao)
        self.painel.movido.connect(self._painel_movido)

        self.janela.idioma_mudou.connect(self.trocar_idioma)
        self.janela.opacidade_mudou.connect(self.overlay.definir_opacidade)
        self.janela.usar_ia_mudou.connect(self._usar_ia)
        self.janela.marcar_no_jogo_mudou.connect(lambda ativo: ativo or self.overlay.esconder())
        self.janela.iniciar_mudou.connect(self._iniciar_com_sistema)
        self.janela.painel_no_jogo_mudou.connect(lambda ativo: ativo or self.painel.hide())
        self.janela.calibrar_pedido.connect(self.calibrar)
        self.janela.sair_pedido.connect(self.encerrar)

        self._iniciar_vigia()

    def _carregar_idioma(self, idioma):
        if self.sem_banco:
            vazio = Path(tempfile.gettempdir()) / "openrok-sem-banco.csv"
            vazio.write_text("pergunta,resposta\n", encoding="utf-8")
            csv = vazio
        else:
            csv = caminho_csv(IDIOMAS[idioma]["csv"])
        conhecimento = Conhecimento(idioma, csv, self.armazem)
        return conhecimento, MotorOCR(IDIOMAS[idioma]["ocr"]), self.ia_fabrica(idioma)

    def _iniciar_vigia(self):
        self.ponte = Ponte()
        self.ponte.evento.connect(self._evento)
        self.vigia = Vigia(self.janela_jogo, self.captura, self.ocr, self.conhecimento, self.ponte.emitir,
                           ia=self._ia if self.config.usar_ia else None)
        self.vigia.calibracao = self.config.calibracao
        if os.environ.get("OPENROK_DEBUG"):
            self.vigia.pasta_quadros = pasta_dados() / "quadros"
        self.vigia.iniciar()

    def _parar_vigia(self):
        if self.ponte is not None:
            self.ponte.evento.disconnect(self._evento)
            self.ponte = None
        if self.vigia is not None:
            self.vigia.parar()

    def encerrar(self):
        self._parar_vigia()
        if self.ocr is not None:
            self.ocr.fechar()
            self.ocr = None
        self.overlay.esconder()
        self.painel.hide()

    # ------------------------------------------------------
    # Events and settings
    # ------------------------------------------------------
    def _evento(self, evento):
        self.janela.aplicar(evento)

        if self.config.marcar_no_jogo:
            self.overlay.aplicar(evento, self.vigia.geometria)

        if self.config.painel_no_jogo:
            self.painel.aplicar(evento, self.vigia.geometria)

        if isinstance(evento, Aprendido):
            self.janela.inicio.atualizar_total(len(self.conhecimento))

    def salvar_config(self):
        try:
            self.config.salvar(self.caminho_config)
        except OSError:
            pass  # settings still apply for this session

    def _painel_movido(self, fx, fy):
        self.config.painel_posicao = [fx, fy]
        self.salvar_config()

    def _usar_ia(self, ativo):
        self.vigia.ia = self._ia if ativo else None

    def _iniciar_com_sistema(self, ativo):
        try:
            ativar_inicio(ativo)
        except OSError:
            pass

    def trocar_idioma(self, idioma):
        self._parar_vigia()
        self.ocr.fechar()
        self.overlay.esconder()

        self.config.idioma = idioma
        self.conhecimento, self.ocr, self._ia = self._carregar_idioma(idioma)
        self.overlay.textos = IDIOMAS[idioma]["textos"]
        self.painel.textos = IDIOMAS[idioma]["textos"]
        self.painel.hide()
        self.janela.trocar_conhecimento(self.conhecimento)

        self._iniciar_vigia()

    def calibrar(self):
        textos = IDIOMAS[self.config.idioma]["textos"]
        cliente = self.janela_jogo.localizar()
        if cliente is None:
            QMessageBox.information(self.janela, "OpenRok", textos["calibrar_sem_jogo"])
            return

        dialogo = DialogoCalibracao(self.captura.capturar(cliente), self.config.calibracao, textos)
        if dialogo.exec():
            self.config.calibracao = dialogo.resultado()
            self.vigia.calibracao = self.config.calibracao
            self.salvar_config()


# ==========================================================
# ENTRY POINT
# ==========================================================

def fabrica_ia(idioma):
    return None  # replaced by ia_de_config once the key vault exists


def main():
    if sys.platform.startswith("linux"):
        # The game runs on XWayland: the overlay must live there too,
        # in the same coordinate system
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    pasta = pasta_dados()
    arquivo_log = RotatingFileHandler(pasta / "openrok.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    arquivo_log.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.DEBUG if os.environ.get("OPENROK_DEBUG") else logging.INFO,
                        handlers=[arquivo_log])

    config = Config.carregar(pasta / "config.json")
    # On Wayland the game window's own pixels sometimes freeze for seconds
    # (XWayland + Wine); the portal shows what is really on screen.
    # OPENROK_CAPTURA=x11 goes back to reading the window, for diagnosis.
    portal = os.environ.get("XDG_SESSION_TYPE") == "wayland" and os.environ.get("OPENROK_CAPTURA") != "x11"
    logging.getLogger("openrok.app").info("captura: %s", "portal" if portal else "janela")
    janela_jogo, captura = plataforma(portal=portal)

    aplicacao = Aplicacao(config, janela_jogo, captura, Armazem(pasta / "openrok.db"), pasta / "config.json", fabrica_ia,
                          sem_banco=bool(os.environ.get("OPENROK_SEM_BANCO")))
    aplicacao.iniciar()
    aplicacao.janela.show()

    sys.exit(app.exec())

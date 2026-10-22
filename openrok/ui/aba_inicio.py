from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from openrok.eventos import (Aprendido, ErroIA, JogoEncontrado, JogoPerdido, OutraTela, PerguntaDetectada, Resultado,
                             SemResposta, Sugestao)
from openrok.idiomas import LETRAS
from openrok.ui.interruptor import Interruptor

# The watcher reports these reasons in Portuguese; the tab translates them
MOTIVO_FORA = "fora do banco"
MOTIVO_OPCOES = "resposta do banco não está entre as opções: "


# ==========================================================
# HOME TAB
# ==========================================================
# Watcher status, the last question with its answer (letter,
# text, source and time) and the session counters.
# ==========================================================

class AbaInicio(QWidget):

    vigiar_mudou = Signal(bool)
    marcar_no_jogo_mudou = Signal(bool)
    usar_ia_mudou = Signal(bool)

    def __init__(self, textos, config, total):
        super().__init__()
        self.textos = textos
        self._opcoes = []
        self._aprendidas = 0
        self._acertos = 0
        self._resultados = 0

        self.status = QLabel(textos["status_aguardando"])
        self.status.setObjectName("secundario")

        cartao = QFrame()
        cartao.setObjectName("cartao")
        self.pergunta = QLabel(textos["sem_pergunta"])
        self.pergunta.setObjectName("secundario")
        self.pergunta.setWordWrap(True)
        self.resposta = QLabel("")
        self.resposta.setObjectName("resposta")
        self.resposta.setWordWrap(True)
        self.origem = QLabel("")
        self.origem.setObjectName("secundario")
        layout_cartao = QVBoxLayout(cartao)
        for widget in (self.pergunta, self.resposta, self.origem):
            layout_cartao.addWidget(widget)

        self.total = QLabel(str(total))
        self.aprendidas = QLabel("0")
        self.acertos = QLabel("0/0")
        estatisticas = QGridLayout()
        for coluna, (valor, rotulo) in enumerate(((self.total, "stat_banco"), (self.aprendidas, "stat_aprendidas"),
                                                  (self.acertos, "stat_acertos"))):
            caixa = QFrame()
            caixa.setObjectName("estatistica")
            interno = QVBoxLayout(caixa)
            valor.setObjectName("numero")
            legenda = QLabel(textos[rotulo])
            legenda.setObjectName("secundario")
            interno.addWidget(valor)
            interno.addWidget(legenda)
            estatisticas.addWidget(caixa, 0, coluna)

        self.vigiar = Interruptor(textos["vigiar"])  # the app always opens paused
        self.vigiar.toggled.connect(self.vigiar_mudou)
        self.marcar_no_jogo = Interruptor(textos["marcar_no_jogo"])
        self.marcar_no_jogo.setChecked(config.marcar_no_jogo)
        self.marcar_no_jogo.toggled.connect(self.marcar_no_jogo_mudou)
        self.usar_ia = Interruptor(textos["usar_ia"])
        self.usar_ia.setChecked(config.usar_ia)
        self.usar_ia.toggled.connect(self.usar_ia_mudou)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(cartao)
        layout.addLayout(estatisticas)
        layout.addWidget(self.vigiar)
        layout.addWidget(self.marcar_no_jogo)
        layout.addWidget(self.usar_ia)
        layout.addStretch()

    def aplicar(self, evento):
        t = self.textos

        if isinstance(evento, JogoEncontrado):
            self.status.setText(t["status_vigiando"])
        elif isinstance(evento, JogoPerdido):
            self.status.setText(t["status_aguardando"])
        elif isinstance(evento, OutraTela):
            self.status.setText(t["status_outra_tela"])
        elif isinstance(evento, PerguntaDetectada):
            self.status.setText(t["status_vigiando"])
            self._opcoes = evento.opcoes
            self.pergunta.setText(evento.texto)
            self.resposta.setText("…")
            self.origem.setText("")
        elif isinstance(evento, Sugestao):
            indice = LETRAS.index(evento.letra)
            texto = self._opcoes[indice] if indice < len(self._opcoes) else ""
            self.resposta.setText(f"{evento.letra} · {texto}".strip(" ·"))
            chave = "selo_ia" if evento.origem == "ia" else "selo_banco"
            self.origem.setText(t[chave].format(tempo=f"{evento.tempo_ms / 1000:.2f}".replace(".", ",")))
        elif isinstance(evento, SemResposta):
            if evento.motivo.startswith(MOTIVO_OPCOES):
                self.resposta.setText(t["sem_resposta_opcoes"].format(resposta=evento.motivo[len(MOTIVO_OPCOES):]))
            else:
                self.resposta.setText(t["sem_resposta_fora"])
        elif isinstance(evento, ErroIA):
            self.resposta.setText(t["erro_ia"].format(erro=evento.mensagem))
        elif isinstance(evento, Resultado):
            self._resultados += 1
            self._acertos += evento.correta == evento.marcada
            self.acertos.setText(f"{self._acertos}/{self._resultados}")
        elif isinstance(evento, Aprendido):
            self._aprendidas += 1
            self.aprendidas.setText(str(self._aprendidas))

    def atualizar_total(self, total):
        self.total.setText(str(total))

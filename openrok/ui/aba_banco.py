from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout, QWidget)

FILTROS = ("todas", "aprendidas", "corrigidas", "nao_confirmadas")
LIMITE_LISTA = 500  # the full database has ~1300 rows; searching narrows it down


# ==========================================================
# DATABASE TAB
# ==========================================================
# Search, filter chips and every question with its status:
# confirmed by the game, corrected by the game (with the old
# answer) or still only in the original database.
# ==========================================================

class AbaBanco(QWidget):

    def __init__(self, textos, conhecimento, ao_mudar):
        super().__init__()
        self.textos = textos
        self.conhecimento = conhecimento
        self.ao_mudar = ao_mudar
        self.filtro = "todas"

        self.busca = QLineEdit()
        self.busca.setPlaceholderText(textos["busca"])
        self.busca.textChanged.connect(self.atualizar)

        self.filtros = {}
        grupo = QButtonGroup(self)
        chips = QHBoxLayout()
        for nome in FILTROS:
            botao = QPushButton(textos[f"filtro_{nome}"])
            botao.setCheckable(True)
            botao.setChecked(nome == "todas")
            botao.clicked.connect(lambda _=False, n=nome: self._filtrar(n))
            grupo.addButton(botao)
            chips.addWidget(botao)
            self.filtros[nome] = botao

        self.lista = QListWidget()
        self.lista.setWordWrap(True)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.mensagem = QLabel("")
        self.mensagem.setObjectName("secundario")

        self.exportar = QPushButton(textos["exportar"])
        self.exportar.clicked.connect(self._exportar)
        self.importar = QPushButton(textos["importar"])
        self.importar.clicked.connect(self._importar)
        self.desfazer = QPushButton(textos["desfazer"])
        self.desfazer.clicked.connect(self._desfazer)
        acoes = QHBoxLayout()
        for botao in (self.exportar, self.importar, self.desfazer):
            acoes.addWidget(botao)

        layout = QVBoxLayout(self)
        layout.addWidget(self.busca)
        layout.addLayout(chips)
        layout.addWidget(self.lista)
        layout.addWidget(self.mensagem)
        layout.addLayout(acoes)

        self.atualizar()

    def _filtrar(self, nome):
        self.filtro = nome
        self.atualizar()

    def atualizar(self):
        self.lista.clear()
        for item in self.conhecimento.listar(self.busca.text(), self.filtro)[:LIMITE_LISTA]:
            if item["corrigida_de"] is not None:
                situacao = self.textos["item_corrigida"].format(antiga=item["corrigida_de"])
            elif item["confirmada"]:
                situacao = self.textos["item_confirmada"]
            else:
                situacao = self.textos["item_base"]
            QListWidgetItem(f"{item['pergunta']}\n{item['resposta']}\n{situacao}", self.lista)

    def _exportar(self):
        caminho, _ = QFileDialog.getSaveFileName(self, self.textos["exportar"], "openrok.csv", "CSV (*.csv)")
        if caminho:
            n = self.conhecimento.exportar_confirmadas(caminho)
            self.mensagem.setText(self.textos["exportadas"].format(n=n))

    def _importar(self):
        caminho, _ = QFileDialog.getOpenFileName(self, self.textos["importar"], "", "CSV (*.csv)")
        if caminho:
            n = self.conhecimento.importar_csv(caminho)
            self.mensagem.setText(self.textos["importadas"].format(n=n))
            self.atualizar()
            self.ao_mudar()

    def _desfazer(self):
        desfeita = self.conhecimento.desfazer_ultima_correcao()
        if desfeita is None:
            self.mensagem.setText(self.textos["nada_a_desfazer"])
        else:
            self.mensagem.setText(self.textos["desfeita"].format(pergunta=desfeita[0], resposta=desfeita[1]))
        self.atualizar()

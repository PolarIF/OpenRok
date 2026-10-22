import random
import threading

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QPushButton, QWidget

from openrok.ia import PRESETS, FalhaIA, ia_de_config, pergunta_de_teste, preset


# ==========================================================
# AI TAB
# ==========================================================
# Provider, key (in the system vault), model and a Test
# button that asks a known question from the database.
# ==========================================================

class AbaIA(QWidget):

    ia_mudou = Signal()
    teste_pronto = Signal(str)

    def __init__(self, textos, config, cofre, conhecimento, salvar_config):
        super().__init__()
        self.textos = textos
        self.config = config
        self.cofre = cofre
        self.conhecimento = conhecimento
        self.salvar_config = salvar_config

        self.provedor = QComboBox()
        for p in PRESETS:
            self.provedor.addItem(f"{p.nome} · {textos['ia_gratis']}" if p.gratis else p.nome, p.id)
        self.provedor.setCurrentIndex(self.provedor.findData(preset(config.ia_provedor).id))

        self.chave = QLineEdit()
        self.chave.setEchoMode(QLineEdit.Password)
        self.modelo = QLineEdit(config.ia_modelo)
        self.base_url = QLineEdit(config.ia_base_url)
        self.base_url.setPlaceholderText("http://localhost:8080/v1")

        self.link = QLabel()
        self.link.setOpenExternalLinks(True)

        self.testar = QPushButton(textos["ia_testar"])
        self.resultado = QLabel()
        self.resultado.setWordWrap(True)

        self.aviso_cofre = QLabel(textos["ia_cofre_indisponivel"])
        self.aviso_cofre.setWordWrap(True)

        self._layout = QFormLayout(self)
        self._layout.addRow(textos["ia_provedor"], self.provedor)
        self._layout.addRow(textos["ia_chave"], self.chave)
        self._layout.addRow(self.link)
        self._layout.addRow(textos["ia_modelo"], self.modelo)
        self._layout.addRow(textos["ia_base_url"], self.base_url)
        self._layout.addRow(self.testar)
        self._layout.addRow(self.resultado)
        self._layout.addRow(self.aviso_cofre)

        self._mostrar_provedor()

        self.provedor.currentIndexChanged.connect(self._trocar_provedor)
        self.chave.editingFinished.connect(self._gravar_chave)
        self.modelo.editingFinished.connect(lambda: self._gravar("ia_modelo", self.modelo.text().strip()))
        self.base_url.editingFinished.connect(lambda: self._gravar("ia_base_url", self.base_url.text().strip()))
        self.testar.clicked.connect(self._testar)
        self.teste_pronto.connect(self._mostrar_teste)

    def _preset(self):
        return preset(self.provedor.currentData())

    def _mostrar_provedor(self):
        p = self._preset()
        self.chave.setEnabled(p.exige_chave or p.id == "personalizado")
        self.chave.setText(self.cofre.ler(p.id) or "")
        self.modelo.setPlaceholderText(p.modelo)
        self._layout.setRowVisible(self.base_url, p.id == "personalizado")

        if p.link_chave:
            texto = self.textos["ia_link_gratis"] if p.gratis else self.textos["ia_link_pago"]
            self.link.setText(f'<a href="{p.link_chave}">{texto}</a>')
        self.link.setVisible(bool(p.link_chave))
        self.aviso_cofre.setVisible(not self.cofre.disponivel)
        self.resultado.clear()

    def _avisar(self):
        self.salvar_config()
        self.ia_mudou.emit()

    def _trocar_provedor(self, _):
        self.config.ia_provedor = self._preset().id
        self.config.ia_modelo = ""
        self.modelo.clear()
        self._mostrar_provedor()
        self._avisar()

    def _gravar_chave(self):
        self.cofre.gravar(self._preset().id, self.chave.text().strip())
        self.aviso_cofre.setVisible(not self.cofre.disponivel)
        self._avisar()

    def _gravar(self, campo, valor):
        setattr(self.config, campo, valor)
        self._avisar()

    # ------------------------------------------------------
    # Test with a known question
    # ------------------------------------------------------
    def _testar(self):
        cliente = ia_de_config(self.config, self.config.idioma, self.cofre)
        if cliente is None:
            sem = "ia_informe_url" if self._preset().id == "personalizado" else "ia_informe_chave"
            self.resultado.setText(self.textos[sem])
            return

        banco = self.conhecimento.banco
        pergunta, opcoes, correta = pergunta_de_teste(banco.perguntas, banco.respostas, random.Random())
        self.testar.setEnabled(False)
        self.resultado.setText(self.textos["ia_testando"])

        def trabalho():
            # Off the UI thread: a slow or unreachable provider must not freeze the window
            try:
                r = cliente.testar(pergunta, opcoes, correta)
            except FalhaIA as erro:
                self.teste_pronto.emit(str(erro))
                return

            tempo = f"{r.tempo_ms / 1000:.2f}".replace(".", ",")
            if r.acertou:
                texto = self.textos["ia_teste_acertou"].format(tempo=tempo)
            elif r.letra:
                texto = self.textos["ia_teste_errou"].format(letra=r.letra, correta=r.correta, tempo=tempo)
            else:
                texto = self.textos["ia_teste_sem_letra"].format(tempo=tempo)
            self.teste_pronto.emit(texto)

        threading.Thread(target=trabalho, daemon=True).start()

    def _mostrar_teste(self, texto):
        self.resultado.setText(texto)
        self.testar.setEnabled(True)

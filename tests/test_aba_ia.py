import csv

import pytest

from openrok.armazem import Armazem
from openrok.cofre import CofreMemoria
from openrok.config import Config
from openrok.conhecimento import Conhecimento
from openrok.ia import FalhaIA, ResultadoTeste
from openrok.idiomas import IDIOMAS
from openrok.ui.aba_ia import AbaIA

T = IDIOMAS["pt"]["textos"]


@pytest.fixture
def conhecimento(tmp_path):
    caminho = tmp_path / "db.csv"
    with open(caminho, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["pergunta", "resposta"])
        writer.writerows([(f"Qual foi o nome do herói número {i} da lenda antiga?", f"Resposta {i}") for i in range(6)])
    return Conhecimento("pt", caminho, Armazem(":memory:"))


@pytest.fixture
def aba(qtbot, conhecimento):
    def criar(config=None, cofre=None):
        salvos = []
        widget = AbaIA(T, config or Config(idioma="pt"), cofre or CofreMemoria(), conhecimento,
                       lambda: salvos.append(True))
        widget.salvos = salvos
        qtbot.addWidget(widget)
        widget.show()
        return widget
    return criar


def escolher(aba, id_provedor):
    aba.provedor.setCurrentIndex(aba.provedor.findData(id_provedor))


def test_lista_presets_na_ordem_com_selo_gratis(aba):
    widget = aba()

    ids = [widget.provedor.itemData(i) for i in range(widget.provedor.count())]
    assert len(ids) == 9 and ids[0] == "gemini" and ids[-1] == "personalizado"
    assert T["ia_gratis"] in widget.provedor.itemText(ids.index("groq"))
    assert T["ia_gratis"] not in widget.provedor.itemText(ids.index("openai"))


def test_trocar_provedor_grava_e_avisa(qtbot, aba):
    widget = aba(Config(idioma="pt", ia_modelo="velho"))

    with qtbot.waitSignal(widget.ia_mudou):
        escolher(widget, "groq")

    assert widget.config.ia_provedor == "groq" and widget.config.ia_modelo == ""
    assert widget.modelo.placeholderText() == "openai/gpt-oss-20b"
    assert widget.salvos


def test_chave_vai_para_o_cofre(qtbot, aba):
    cofre = CofreMemoria()
    widget = aba(cofre=cofre)
    escolher(widget, "groq")

    widget.chave.setText("k")
    with qtbot.waitSignal(widget.ia_mudou):
        widget.chave.editingFinished.emit()

    assert cofre.ler("groq") == "k"
    escolher(widget, "ollama")
    assert not widget.chave.isEnabled()
    escolher(widget, "groq")
    assert widget.chave.text() == "k"


def test_modelo_vai_para_a_config(qtbot, aba):
    widget = aba()

    widget.modelo.setText("outro")
    with qtbot.waitSignal(widget.ia_mudou):
        widget.modelo.editingFinished.emit()

    assert widget.config.ia_modelo == "outro"


def test_base_url_so_no_personalizado(aba):
    widget = aba()
    assert not widget.base_url.isVisible()

    escolher(widget, "personalizado")
    assert widget.base_url.isVisible()


def test_link_da_chave(aba):
    widget = aba()
    assert widget.link.isVisible() and "aistudio.google.com" in widget.link.text()

    escolher(widget, "ollama")
    assert not widget.link.isVisible()


def test_testar_sem_chave_nao_usa_rede(aba):
    widget = aba()
    escolher(widget, "groq")

    widget.testar.click()

    assert widget.resultado.text() == T["ia_informe_chave"]


def test_testar_personalizado_sem_url(aba):
    widget = aba()
    escolher(widget, "personalizado")

    widget.testar.click()

    assert widget.resultado.text() == T["ia_informe_url"]


class ClienteFalso:
    def __init__(self, resultado=None, erro=None):
        self.resultado, self.erro = resultado, erro

    def testar(self, pergunta, opcoes, correta):
        if self.erro:
            raise self.erro
        return self.resultado


@pytest.mark.parametrize("cliente, trechos", [
    (ClienteFalso(ResultadoTeste("C", "C", 1200.0)), ["✓", "1,2"]),
    (ClienteFalso(ResultadoTeste("A", "C", 800.0)), ["✗", "A", "C", "0,8"]),
    (ClienteFalso(ResultadoTeste(None, "C", 500.0)), ["✗", "0,5"]),
    (ClienteFalso(erro=FalhaIA("chave inválida")), ["chave inválida"]),
])
def test_testar_mostra_resultado(qtbot, monkeypatch, aba, cliente, trechos):
    monkeypatch.setattr("openrok.ui.aba_ia.ia_de_config", lambda config, idioma, cofre: cliente)
    widget = aba()

    widget.testar.click()

    qtbot.waitUntil(lambda: widget.testar.isEnabled() and widget.resultado.text() != T["ia_testando"], timeout=3000)
    assert all(trecho in widget.resultado.text() for trecho in trechos)


def test_aviso_cofre(aba):
    cofre = CofreMemoria()
    cofre.disponivel = False

    widget = aba(cofre=cofre)

    assert widget.aviso_cofre.isVisible()
    assert not aba().aviso_cofre.isVisible()


def test_testar_com_banco_pequeno(qtbot, tmp_path):
    caminho = tmp_path / "pequeno.csv"
    caminho.write_text("pergunta,resposta\n", encoding="utf-8")
    cofre = CofreMemoria()
    cofre.gravar("groq", "k")
    widget = AbaIA(T, Config(idioma="pt", ia_provedor="groq"), cofre, Conhecimento("pt", caminho, Armazem(":memory:")),
                   lambda: None)
    qtbot.addWidget(widget)

    widget.testar.click()

    assert widget.resultado.text() == T["ia_teste_sem_banco"]
    assert widget.testar.isEnabled()


@pytest.mark.parametrize("campo", ["chave", "modelo", "base_url"])
def test_sair_do_campo_sem_mudar_nao_salva(qtbot, aba, campo):
    widget = aba()
    escolher(widget, "personalizado")
    widget.salvos.clear()
    emitidos = []
    widget.ia_mudou.connect(lambda: emitidos.append(True))

    getattr(widget, campo).editingFinished.emit()

    assert emitidos == [] and widget.salvos == []

import csv

import pytest
from PySide6.QtCore import Qt

from openrok.armazem import Armazem
from openrok.config import Config
from openrok.conhecimento import Conhecimento
from openrok.eventos import JogoEncontrado, JogoPerdido, PerguntaDetectada, Resultado, SemResposta, Sugestao
from openrok.idiomas import IDIOMAS
from openrok.ui.janela import JanelaPrincipal


@pytest.fixture
def conhecimento(tmp_path):
    caminho = tmp_path / "db.csv"
    with open(caminho, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["pergunta", "resposta"])
        writer.writerows([
            ("Antes de liderar a maior rebelião, o que foi Espártaco?", "Um gladiador"),
            ("Qual orgao faz parte do sistema respiratorio humano?", "chave de impacto"),
            ("Quem pintou a Mona Lisa original?", "Leonardo da Vinci"),
        ])
    conhecimento = Conhecimento("pt", caminho, Armazem(":memory:"))
    conhecimento.aprender("Qual orgao faz parte do sistema respiratorio humano?", ["Pulmões", "Fígado", "", ""], "A", None)
    return conhecimento


@pytest.fixture
def janela(qtbot, conhecimento):
    salvos = []
    widget = JanelaPrincipal(Config(idioma="pt"), conhecimento, lambda: salvos.append(True))
    widget.salvos = salvos
    qtbot.addWidget(widget)
    return widget


def test_textos_mesmas_chaves():
    assert IDIOMAS["en"]["textos"].keys() == IDIOMAS["pt"]["textos"].keys()


def test_inicio_status(janela):
    janela.aplicar(JogoEncontrado())
    assert "Vigiando" in janela.inicio.status.text()

    janela.aplicar(JogoPerdido())
    assert "Aguardando" in janela.inicio.status.text()


def test_inicio_mostra_sugestao(janela):
    janela.aplicar(JogoEncontrado())
    janela.aplicar(PerguntaDetectada("Quem pintou a Mona Lisa?", ["Da Vinci", "Rafael", "", ""]))
    janela.aplicar(Sugestao("A", "banco", 60))

    assert janela.inicio.pergunta.text() == "Quem pintou a Mona Lisa?"
    assert "A" in janela.inicio.resposta.text() and "Da Vinci" in janela.inicio.resposta.text()
    assert "0,06" in janela.inicio.origem.text()


def test_inicio_sem_resposta_traduzida(janela):
    janela.aplicar(PerguntaDetectada("Pergunta nova?", ["a", "b", "c", "d"]))
    janela.aplicar(SemResposta("fora do banco"))

    assert janela.inicio.resposta.text() == IDIOMAS["pt"]["textos"]["sem_resposta_fora"]


def test_inicio_estatisticas(janela):
    janela.aplicar(Resultado("D", "C"))
    janela.aplicar(Resultado("B", "B"))

    assert "1/2" in janela.inicio.acertos.text()
    assert janela.inicio.total.text() == "3"


def test_banco_filtro_e_busca(janela, qtbot):
    banco = janela.banco
    assert banco.lista.count() == 3

    qtbot.mouseClick(banco.filtros["corrigidas"], Qt.LeftButton)
    assert banco.lista.count() == 1
    assert "chave de impacto" in banco.lista.item(0).text()

    qtbot.mouseClick(banco.filtros["todas"], Qt.LeftButton)
    banco.busca.setText("espartaco")
    assert banco.lista.count() == 1


def test_banco_desfazer(janela, qtbot, conhecimento):
    qtbot.mouseClick(janela.banco.desfazer, Qt.LeftButton)
    assert conhecimento.buscar("Qual orgao faz parte do sistema respiratorio humano?")[1] == "chave de impacto"


def test_ajustes_salva_config(janela, qtbot):
    with qtbot.waitSignal(janela.opacidade_mudou) as sinal:
        janela.ajustes.opacidade.setValue(50)

    assert sinal.args == [0.5]
    assert janela.config.opacidade == 0.5
    assert janela.salvos


def test_trocar_idioma_emite(janela, qtbot):
    with qtbot.waitSignal(janela.idioma_mudou) as sinal:
        janela.ajustes.idioma.setCurrentIndex(janela.ajustes.idioma.findData("en"))

    assert sinal.args == ["en"]
    assert janela.config.idioma == "en"


def test_interruptores_do_inicio_mudam_config(janela, qtbot):
    with qtbot.waitSignal(janela.usar_ia_mudou) as sinal:
        janela.inicio.usar_ia.setChecked(False)

    assert sinal.args == [False]
    assert janela.config.usar_ia is False

    janela.inicio.marcar_no_jogo.setChecked(False)
    assert janela.config.marcar_no_jogo is False


def test_interruptores_no_lugar_das_caixas(janela):
    from openrok.ui.interruptor import Interruptor

    assert isinstance(janela.inicio.usar_ia, Interruptor)
    assert isinstance(janela.ajustes.painel, Interruptor)


def test_desligar_painel(janela, qtbot):
    with qtbot.waitSignal(janela.painel_no_jogo_mudou) as sinal:
        janela.ajustes.painel.setChecked(False)

    assert sinal.args == [False]
    assert janela.config.painel_no_jogo is False


def test_ordem_das_abas(janela):
    abas = janela.centralWidget()
    nomes = [abas.tabText(i) for i in range(abas.count())]
    t = IDIOMAS["pt"]["textos"]
    assert nomes == [t["aba_inicio"], t["aba_ia"], t["aba_banco"], t["aba_ajustes"]]

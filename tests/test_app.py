import pytest

from openrok.app import Aplicacao
from openrok.armazem import Armazem
from openrok.captura import CapturaDeQuadro
from openrok.config import Config
from openrok.eventos import Sugestao
from openrok.geometria import Ret
from openrok.janela_jogo import JanelaFixa
from tests.fixtures import carregar_print


@pytest.fixture
def montar(qtbot, tmp_path):
    criadas = []

    def criar(**config):
        app = Aplicacao(Config(idioma="pt", **config), JanelaFixa(Ret(0, 0, 1920, 1080)),
                        CapturaDeQuadro(carregar_print("q1_go")), Armazem(":memory:"),
                        tmp_path / "config.json", lambda idioma: None)
        app.iniciar()
        qtbot.addWidget(app.janela)
        qtbot.addWidget(app.overlay)
        qtbot.addWidget(app.painel)
        criadas.append(app)
        return app

    yield criar

    for app in criadas:
        app.encerrar()


def test_app_de_ponta_a_ponta(montar, qtbot):
    app = montar()

    qtbot.waitUntil(lambda: app.overlay.marcada == ("A", "banco"), timeout=8000)
    assert app.janela.inicio.resposta.text().startswith("A")


def test_marcar_no_jogo_desligado(montar, qtbot):
    app = montar(marcar_no_jogo=False)

    qtbot.waitUntil(lambda: app.janela.inicio.resposta.text().startswith("A"), timeout=8000)
    assert app.overlay.marcada is None


def test_trocar_idioma_sem_eventos_velhos(montar, qtbot):
    app = montar()
    qtbot.waitUntil(lambda: app.overlay.marcada is not None, timeout=8000)
    vigia_antigo, ponte_antiga = app.vigia, app.ponte

    app.trocar_idioma("en")

    assert app.vigia is not vigia_antigo
    assert not vigia_antigo._thread.is_alive()

    texto_antes = app.janela.inicio.resposta.text()
    ponte_antiga.emitir(Sugestao("D", "banco", 1))
    qtbot.wait(100)
    assert app.janela.inicio.resposta.text() == texto_antes
    assert app.janela.ajustes.idioma.currentData() == "en"


def test_calibracao_chega_ao_vigia(montar, qtbot):
    calibracao = [0.3, 0.3, 0.5, 0.3]
    app = montar(calibracao=calibracao)
    assert app.vigia.calibracao == calibracao


def test_painel_mostra_a_resposta(montar, qtbot):
    app = montar()
    qtbot.waitUntil(lambda: "A · 2" in app.painel.texto, timeout=8000)
    assert app.painel.isVisible()


def test_mover_painel_salva_config(montar):
    app = montar()
    app.painel.movido.emit(0.3, 0.1)
    assert app.config.painel_posicao == [0.3, 0.1]


def test_modo_sem_banco(qtbot, tmp_path):
    armazem_real = Armazem(":memory:")
    app = Aplicacao(Config(idioma="pt"), JanelaFixa(Ret(0, 0, 1920, 1080)),
                    CapturaDeQuadro(carregar_print("q1_go")), armazem_real,
                    tmp_path / "config.json", lambda idioma: None, sem_banco=True)
    app.iniciar()
    qtbot.addWidget(app.janela)
    qtbot.addWidget(app.overlay)
    qtbot.addWidget(app.painel)

    try:
        assert len(app.conhecimento) == 0
        qtbot.waitUntil(lambda: app.janela.inicio.resposta.text() == "Fora do banco", timeout=8000)
        assert app.conhecimento.armazem is not armazem_real
    finally:
        app.encerrar()

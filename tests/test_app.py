import threading

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

    def criar(ia_fabrica=lambda idioma: None, sem_banco=False, **config):
        app = Aplicacao(Config(idioma="pt", **config), JanelaFixa(Ret(0, 0, 1920, 1080)),
                        CapturaDeQuadro(carregar_print("q1_go")), Armazem(":memory:"),
                        tmp_path / "config.json", ia_fabrica, sem_banco=sem_banco)
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


def outra_pergunta():
    """q1 with other text in the question area: a new question with no colors."""
    from PIL import ImageDraw

    from openrok.geometria import areas_para

    quadro = carregar_print("q1_go").copy()
    pergunta = areas_para(Ret(0, 0, 1920, 1080)).pergunta
    desenho = ImageDraw.Draw(quadro)
    desenho.rectangle((pergunta.x, pergunta.y, pergunta.x + pergunta.w, pergunta.y + pergunta.h), fill=(222, 190, 140))
    desenho.text((pergunta.x + 20, pergunta.y + 20), "Qual foi o primeiro imperador romano?", fill=(40, 30, 20))
    return quadro


class IAFalsa:
    def __init__(self, letra=None, liberar=None):
        self.letra, self.liberar, self.chamadas = letra, liberar, 0

    def escolher(self, pergunta, opcoes):
        self.chamadas += 1
        if self.liberar is not None:
            self.liberar.wait(5)
        return self.letra


def test_ia_mudou_troca_o_cliente_sem_reiniciar(montar):
    criadas = []

    def fabrica(idioma):
        criadas.append(IAFalsa())
        return criadas[-1]

    app = montar(ia_fabrica=fabrica)
    vigia = app.vigia

    app.janela.ia_mudou.emit()

    assert app.vigia is vigia
    assert app.vigia.ia is criadas[-1] and len(criadas) == 2


def test_ia_mudou_com_ia_desligada(montar):
    app = montar(ia_fabrica=lambda idioma: IAFalsa(), usar_ia=False)

    app.janela.ia_mudou.emit()

    assert app.vigia.ia is None
    assert app._ia is not None


def test_resposta_atrasada_da_ia_antiga_e_descartada(montar, qtbot):
    liberar = threading.Event()
    antiga, nova = IAFalsa("D", liberar), IAFalsa(None)
    fabricas = iter([antiga, nova])
    app = montar(ia_fabrica=lambda idioma: next(fabricas), sem_banco=True)
    sugestoes = []
    app.ponte.evento.connect(lambda e: isinstance(e, Sugestao) and sugestoes.append(e))
    qtbot.waitUntil(lambda: antiga.chamadas == 1, timeout=8000)

    app.janela.ia_mudou.emit()
    app.captura.quadro = outra_pergunta()
    qtbot.waitUntil(lambda: app.vigia._numero == 2, timeout=8000)
    liberar.set()
    qtbot.waitUntil(lambda: nova.chamadas == 1, timeout=8000)
    qtbot.wait(200)

    assert sugestoes == []

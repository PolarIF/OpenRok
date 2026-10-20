import pytest
from PySide6.QtCore import QPoint, Qt

from openrok.eventos import JogoEncontrado, JogoPerdido, PerguntaDetectada, SemResposta, Sugestao
from openrok.geometria import Ret, areas_para
from openrok.idiomas import IDIOMAS
from openrok.ui.painel import Painel

CLIENTE = Ret(0, 0, 1920, 1080)
GEOMETRIA = (CLIENTE, areas_para(CLIENTE))


@pytest.fixture
def painel(qtbot):
    widget = Painel(IDIOMAS["pt"]["textos"], None)
    qtbot.addWidget(widget)
    return widget


def test_nao_rouba_foco_e_recebe_mouse(painel):
    flags = painel.windowFlags()
    assert flags & Qt.WindowDoesNotAcceptFocus
    assert flags & Qt.X11BypassWindowManagerHint
    assert flags & Qt.WindowStaysOnTopHint
    assert not flags & Qt.WindowTransparentForInput


def test_aparece_com_o_jogo_e_some_sem_ele(painel):
    painel.aplicar(JogoEncontrado(), GEOMETRIA)
    assert painel.isVisible()
    assert "Vigiando" in painel.texto

    painel.aplicar(JogoPerdido(), GEOMETRIA)
    assert not painel.isVisible()


def test_mostra_sugestao(painel):
    painel.aplicar(JogoEncontrado(), GEOMETRIA)
    painel.aplicar(PerguntaDetectada("Quantas tropas?", ["5", "4", "2", "3"]), GEOMETRIA)
    painel.aplicar(Sugestao("B", "banco", 60), GEOMETRIA)

    assert "B · 4" in painel.texto and "0,06" in painel.texto
    assert painel.cor == "#21E05A"

    painel.aplicar(Sugestao("B", "ia", 1200), GEOMETRIA)
    assert painel.cor == "#FFC928"


def test_sem_resposta(painel):
    painel.aplicar(PerguntaDetectada("Nova?", ["a", "b", "c", "d"]), GEOMETRIA)
    painel.aplicar(SemResposta("fora do banco"), GEOMETRIA)
    assert IDIOMAS["pt"]["textos"]["sem_resposta_fora"] in painel.texto


def test_posicao_padrao_centro_do_topo(painel):
    painel.aplicar(JogoEncontrado(), GEOMETRIA)
    assert abs(painel.x() + painel.width() / 2 - 960) <= 1
    assert painel.y() == round(0.02 * 1080)


def test_arrastar_salva_posicao(painel, qtbot):
    painel.aplicar(JogoEncontrado(), GEOMETRIA)
    inicio = painel.pos()

    with qtbot.waitSignal(painel.movido) as sinal:
        qtbot.mousePress(painel, Qt.LeftButton, pos=QPoint(10, 10))
        qtbot.mouseMove(painel, QPoint(110, 60))
        qtbot.mouseRelease(painel, Qt.LeftButton, pos=QPoint(110, 60))

    assert painel.pos() == inicio + QPoint(100, 50)
    fx, fy = sinal.args
    assert abs(fx - (painel.x() + painel.width() / 2) / 1920) < 0.002
    assert abs(fy - painel.y() / 1080) < 0.002


def test_posicao_salva_e_usada(qtbot):
    widget = Painel(IDIOMAS["pt"]["textos"], [0.25, 0.5])
    qtbot.addWidget(widget)
    widget.aplicar(JogoEncontrado(), GEOMETRIA)

    assert abs(widget.x() + widget.width() / 2 - 480) <= 1
    assert widget.y() == 540

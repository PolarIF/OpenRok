import threading

import pytest
from PySide6.QtCore import QObject, QRect, Signal

from openrok.eventos import JogoPerdido, OutraTela, PerguntaDetectada, Respondida, Resultado, Sugestao
from openrok.geometria import Ret, areas_para
from openrok.idiomas import IDIOMAS
from openrok.ui.overlay import Overlay, para_logico
from openrok.ui.ponte import Ponte

CLIENTE = Ret(0, 0, 1920, 1080)
GEOMETRIA = (CLIENTE, areas_para(CLIENTE))


@pytest.fixture
def overlay(qtbot):
    widget = Overlay(IDIOMAS["pt"]["textos"])
    qtbot.addWidget(widget)
    return widget


def cor_ao_lado_de_a(overlay):
    caixa = GEOMETRIA[1].caixas["A"]
    return overlay.grab().toImage().pixelColor(caixa.x - 3, caixa.y + caixa.h // 2)


def test_para_logico():
    assert para_logico(Ret(0, 0, 1920, 1080), 1.25) == QRect(0, 0, 1536, 864)
    assert para_logico(Ret(300, 150, 900, 450), 1.5) == QRect(200, 100, 600, 300)


def test_sugestao_banco_desenha_verde(overlay):
    overlay.aplicar(Sugestao("A", "banco", 60), GEOMETRIA)

    assert overlay.isVisible() and overlay.marcada == ("A", "banco")
    cor = cor_ao_lado_de_a(overlay)
    assert cor.green() > 180 and cor.red() < 120


def test_sugestao_ia_desenha_amarelo(overlay):
    overlay.aplicar(Sugestao("A", "ia", 1200), GEOMETRIA)

    cor = cor_ao_lado_de_a(overlay)
    assert cor.red() > 200 and cor.green() > 160 and cor.blue() < 100


def test_contorno_nao_invade_a_caixa(overlay):
    overlay.aplicar(Sugestao("A", "banco", 60), GEOMETRIA)
    caixa = GEOMETRIA[1].caixas["A"]

    assert cor_ao_lado_de_a(overlay).alpha() > 0
    assert overlay.grab().toImage().pixelColor(caixa.x + 2, caixa.y + caixa.h // 2).alpha() == 0


@pytest.mark.parametrize("evento", [Respondida(), Resultado("A", "A"), OutraTela(), JogoPerdido(),
                                    PerguntaDetectada("x", [])])
def test_eventos_que_escondem(overlay, evento):
    overlay.aplicar(Sugestao("A", "banco", 60), GEOMETRIA)
    overlay.aplicar(evento, GEOMETRIA)

    assert not overlay.isVisible() and overlay.marcada is None


def test_sugestao_sem_geometria_nao_quebra(overlay):
    overlay.aplicar(Sugestao("A", "banco", 60), None)
    assert not overlay.isVisible()


def test_ponte_entre_threads(qtbot):
    ponte = Ponte()
    recebidos = []

    class Receptor(QObject):
        pronto = Signal()

        def receber(self, evento):
            recebidos.append((evento, threading.current_thread() is threading.main_thread()))
            self.pronto.emit()

    receptor = Receptor()
    ponte.evento.connect(receptor.receber)

    with qtbot.waitSignal(receptor.pronto, timeout=2000):
        threading.Thread(target=ponte.emitir, args=(Respondida(),)).start()

    assert recebidos == [(Respondida(), True)]

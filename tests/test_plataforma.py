import os
import sys
import time

import pytest

from openrok.geometria import Ret

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux") or not os.environ.get("DISPLAY"),
    reason="needs an X11 (or XWayland) display"
)

VERMELHO = (220, 30, 40)
# Not "Rise of Kingdoms": the real game may be open while tests run
TITULO = f"OpenRok teste {os.getpid()}"


@pytest.fixture
def x11():
    from Xlib import X, display

    d = display.Display()
    criadas = []

    def criar(titulo, largura=400, altura=300):
        tela = d.screen()
        cor = tela.default_colormap.alloc_color(*(c * 257 for c in VERMELHO)).pixel
        janela = tela.root.create_window(100, 100, largura, altura, 0, tela.root_depth,
                                         X.InputOutput, X.CopyFromParent, background_pixel=cor)
        janela.set_wm_name(titulo)
        janela.change_property(d.intern_atom("_NET_WM_NAME"), d.intern_atom("UTF8_STRING"), 8, titulo.encode())
        janela.map()
        d.sync()
        criadas.append(janela)
        return janela

    def destruir(janela):
        janela.destroy()
        d.sync()
        criadas.remove(janela)

    yield criar, destruir

    for janela in criadas:
        janela.destroy()
    d.sync()


def esperar(condicao, segundos=3.0):
    limite = time.time() + segundos
    while time.time() < limite:
        valor = condicao()
        if valor:
            return valor
        time.sleep(0.05)
    return condicao()


def test_acha_janela_x11(x11):
    from openrok.janela_jogo import JanelaX11

    criar, _ = x11
    criar(TITULO)
    ret = esperar(JanelaX11(TITULO).localizar)

    assert ret is not None
    assert (ret.w, ret.h) == (400, 300)


def test_captura_x11_le_conteudo(x11):
    from openrok.captura import CapturaX11
    from openrok.janela_jogo import JanelaX11

    criar, _ = x11
    criar(TITULO)
    janela = JanelaX11(TITULO)
    ret = esperar(janela.localizar)

    def capturou_vermelho():
        imagem = CapturaX11(janela).capturar(Ret(ret.x + 10, ret.y + 10, 50, 40))
        return imagem if imagem.getpixel((25, 20)) == VERMELHO else None

    imagem = esperar(capturou_vermelho)
    assert imagem is not None and imagem.size == (50, 40)


def test_janela_fechada_e_reaberta(x11):
    from openrok.janela_jogo import JanelaX11

    criar, destruir = x11
    primeira = criar(TITULO)
    janela = JanelaX11(TITULO)
    assert esperar(janela.localizar) is not None

    destruir(primeira)
    assert esperar(lambda: janela.localizar() is None)

    criar(TITULO)  # the X server may hand out the same id again: only finding it matters
    assert esperar(janela.localizar) is not None


def test_titulo_diferente_nao_casa(x11):
    from openrok.janela_jogo import JanelaX11

    criar, _ = x11
    criar(TITULO + " - Wiki")
    time.sleep(0.5)

    assert JanelaX11(TITULO).localizar() is None


def test_plataforma_no_linux():
    from openrok.captura import CapturaX11
    from openrok.janela_jogo import JanelaX11
    from openrok.plataforma import plataforma

    janela, captura = plataforma()
    assert isinstance(janela, JanelaX11) and isinstance(captura, CapturaX11)

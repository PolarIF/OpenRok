from PySide6.QtGui import QColor, QImage
from PySide6.QtMultimedia import QVideoFrame

from openrok.captura import CapturaPortal
from openrok.geometria import Ret


def quadro_com_quadrado(cor, ret, tamanho=(200, 100)):
    imagem = QImage(*tamanho, QImage.Format_RGB32)
    imagem.fill(QColor(10, 10, 10))
    for x in range(ret.x, ret.x + ret.w):
        for y in range(ret.y, ret.y + ret.h):
            imagem.setPixelColor(x, y, QColor(*cor))
    return QVideoFrame(imagem)


def test_recorta_o_quadro_mais_recente(qapp):
    captura = CapturaPortal(iniciar=False)
    captura._receber(quadro_com_quadrado((200, 30, 40), Ret(50, 20, 10, 10)))
    captura._receber(quadro_com_quadrado((30, 200, 40), Ret(50, 20, 10, 10)))

    recorte = captura.capturar(Ret(45, 15, 20, 20))

    assert recorte.mode == "RGB" and recorte.size == (20, 20)
    assert recorte.getpixel((10, 10)) == (30, 200, 40)
    assert recorte.getpixel((0, 0)) == (10, 10, 10)


def test_sem_quadro_ainda_devolve_preto(qapp):
    captura = CapturaPortal(iniciar=False)

    recorte = captura.capturar(Ret(0, 0, 30, 20))

    assert recorte.size == (30, 20)
    assert recorte.getextrema() == ((0, 0), (0, 0), (0, 0))


def test_area_fora_do_quadro_vem_preta(qapp):
    captura = CapturaPortal(iniciar=False)
    captura._receber(quadro_com_quadrado((200, 30, 40), Ret(190, 90, 10, 10)))

    recorte = captura.capturar(Ret(190, 90, 20, 20))

    assert recorte.size == (20, 20)
    assert recorte.getpixel((5, 5)) == (200, 30, 40)
    assert recorte.getpixel((15, 15)) == (0, 0, 0)

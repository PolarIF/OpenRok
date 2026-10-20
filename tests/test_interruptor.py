from PySide6.QtCore import Qt

from openrok.ui.interruptor import Interruptor
from openrok.ui.logo import icone, pixmap_logo


def test_logo_carrega(qapp):
    assert not icone().isNull()
    imagem = pixmap_logo(64).toImage()
    assert imagem.width() == 64
    cor = imagem.pixelColor(20, 42)  # owl body, below the left eye
    assert cor.green() > 180 and cor.red() < 100


def test_interruptor_alterna_e_emite(qtbot):
    botao = Interruptor("Usar IA")
    qtbot.addWidget(botao)
    botao.resize(botao.sizeHint())

    assert not botao.isChecked()
    with qtbot.waitSignal(botao.toggled) as sinal:
        qtbot.mouseClick(botao, Qt.LeftButton)

    assert sinal.args == [True]
    assert botao.isChecked()


def test_interruptor_desenha_on_e_off(qtbot):
    botao = Interruptor("Usar IA")
    qtbot.addWidget(botao)
    botao.resize(botao.sizeHint())

    def cor_do_trilho():
        # the track just above the knob, in the middle of the switch
        imagem = botao.grab().toImage()
        return imagem.pixelColor(imagem.width() - 23, (imagem.height() - 22) // 2 + 2)

    desligado = cor_do_trilho()
    botao.setChecked(True)
    ligado = cor_do_trilho()

    assert ligado.green() > 180 and ligado.red() < 100
    assert desligado.green() < 120
    assert botao.texto_estado() == "ON"
    botao.setChecked(False)
    assert botao.texto_estado() == "OFF"

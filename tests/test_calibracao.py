import sys

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, QRect, QSize, Qt

from openrok.autostart import ativar_inicio, comando_inicio
from openrok.idiomas import IDIOMAS
from openrok.ui.calibracao import DialogoCalibracao, retangulo_para_fracoes


def test_fracoes():
    fracoes = retangulo_para_fracoes(QRect(592, 335, 899, 316), QSize(1920, 1080))
    assert [round(f, 4) for f in fracoes] == [0.3083, 0.3102, 0.4682, 0.2926]


def test_dialogo_arrastar(qtbot):
    dialogo = DialogoCalibracao(Image.new("RGB", (1920, 1080), (200, 160, 110)), None, IDIOMAS["pt"]["textos"])
    qtbot.addWidget(dialogo)
    imagem = dialogo.imagem
    imagem.setFixedSize(960, 540)

    qtbot.mousePress(imagem, Qt.LeftButton, pos=QPoint(296, 167))
    qtbot.mouseMove(imagem, QPoint(500, 250))
    qtbot.mouseMove(imagem, QPoint(746, 325))
    qtbot.mouseRelease(imagem, Qt.LeftButton, pos=QPoint(746, 325))

    esperado = [0.3083, 0.3093, 0.4687, 0.2926]
    assert all(abs(a - b) <= 0.002 for a, b in zip(dialogo.resultado(), esperado))


def test_dialogo_restaurar_padrao(qtbot):
    dialogo = DialogoCalibracao(Image.new("RGB", (1920, 1080)), [0.1, 0.1, 0.5, 0.5], IDIOMAS["pt"]["textos"])
    qtbot.addWidget(dialogo)

    qtbot.mouseClick(dialogo.padrao, Qt.LeftButton)
    assert dialogo.resultado() is None


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux autostart")
def test_autostart_linux(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    arquivo = tmp_path / "autostart" / "openrok.desktop"

    ativar_inicio(True)
    conteudo = arquivo.read_text(encoding="utf-8")
    assert "Exec=" in conteudo and "-m openrok" in conteudo

    ativar_inicio(False)
    assert not arquivo.exists()


def test_comando_inicio_fora_do_executavel():
    assert comando_inicio() == [sys.executable, "-m", "openrok"]

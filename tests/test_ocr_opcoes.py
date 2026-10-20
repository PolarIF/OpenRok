import pytest

from openrok.geometria import Ret, areas_para
from openrok.ocr import MotorOCR
from openrok.texto import normalizar
from tests.fixtures import carregar_print, quadros_video

AREAS = areas_para(Ret(0, 0, 1920, 1080))
TELA = Ret(0, 0, 1920, 1080)


@pytest.fixture(scope="module")
def ocr():
    motor = MotorOCR("por")
    yield motor
    motor.fechar()


def ler_opcoes(ocr, imagem):
    return ocr.ler_opcoes([AREAS.texto_opcao(letra).recortar(imagem, TELA) for letra in "ABCD"])


def confere(lidas, esperadas):
    for lida, esperada in zip(lidas, esperadas):
        assert normalizar(lida).startswith(esperada), (lidas, esperadas)


@pytest.mark.parametrize("nome, esperadas", [
    ("q1_go", ["2", "1", "4", "3"]),
    ("q4_einstein", ["1915", "1879", "1921", "1905"]),
    ("q6_cometa", ["cometa halley", "cometa faye", "cometa brorsen", "cometa biela"]),
])
def test_le_opcoes_dos_prints(ocr, nome, esperadas):
    confere(ler_opcoes(ocr, carregar_print(nome)), esperadas)


def test_le_opcoes_com_bau_por_cima(ocr):
    # q5 was taken at result time, with the reward chest drawn over option A;
    # the watcher reads options when the question shows up, before the chest
    lidas = ler_opcoes(ocr, carregar_print("q5_nobel"))

    assert "marie curie" in normalizar(lidas[0])
    confere(lidas[1:], ["bertha von suttner", "aung san suu kyi", "pearl s buck"])


def test_le_opcoes_do_video(ocr):
    quadro = next(q for t, q in quadros_video() if t >= 1.0)
    confere(ler_opcoes(ocr, quadro), ["1286", "1360", "1083", "1192"])


def test_ler_tudo(ocr):
    imagem = carregar_print("q6_cometa")
    pergunta, opcoes = ocr.ler_tudo(
        AREAS.pergunta.recortar(imagem, TELA),
        [AREAS.texto_opcao(letra).recortar(imagem, TELA) for letra in "ABCD"]
    )

    assert "cometa" in normalizar(pergunta)
    confere(opcoes, ["cometa halley", "cometa faye", "cometa brorsen", "cometa biela"])

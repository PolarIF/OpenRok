import io

import pytest
from PIL import Image

from openrok.geometria import Ret, areas_para
from openrok.tela import EstadoOpcao, distancia, dhash, eh_tela_de_perguntas, estado_opcao
from tests.fixtures import carregar_print

AREAS = areas_para(Ret(0, 0, 1920, 1080))
TELA = Ret(0, 0, 1920, 1080)
N, VD, VM = EstadoOpcao.NEUTRA, EstadoOpcao.VERDE, EstadoOpcao.VERMELHA


@pytest.mark.parametrize("nome, esperado", [
    ("q1_go", [N, N, N, N]),
    ("q4_einstein", [VM, N, N, VD]),
    ("q5_nobel", [VD, N, N, N]),  # reward chest drawn over the green box
    ("q6_cometa", [VD, N, N, N]),
])
def test_estado_das_opcoes_nos_prints(nome, esperado):
    imagem = carregar_print(nome)
    estados = [estado_opcao(AREAS.interior(letra).recortar(imagem, TELA)) for letra in "ABCD"]
    assert estados == esperado


def test_estado_colorido():
    assert estado_opcao(Image.new("RGB", (100, 50), (40, 110, 230))) == EstadoOpcao.COLORIDA


@pytest.mark.parametrize("nome", ["q1_go", "q4_einstein", "q5_nobel", "q6_cometa"])
def test_assinatura_reconhece_tela_de_perguntas(nome):
    imagem = carregar_print(nome)
    assert eh_tela_de_perguntas([s.recortar(imagem, TELA) for s in AREAS.sondas])


def test_assinatura_rejeita_outra_tela():
    imagem = Image.new("RGB", (1920, 1080), (30, 30, 35))
    assert not eh_tela_de_perguntas([s.recortar(imagem, TELA) for s in AREAS.sondas])


def test_dhash_estavel():
    pergunta = AREAS.pergunta.recortar(carregar_print("q1_go"), TELA)

    buffer = io.BytesIO()
    pergunta.save(buffer, "JPEG", quality=70)
    comprimida = Image.open(io.BytesIO(buffer.getvalue()))

    outra = AREAS.pergunta.recortar(carregar_print("q4_einstein"), TELA)

    assert distancia(dhash(pergunta), dhash(comprimida)) <= 4
    assert distancia(dhash(pergunta), dhash(outra)) > 6
    assert 0 <= dhash(pergunta) < 2 ** 64

import io

import pytest
from PIL import Image

from openrok.geometria import Ret, areas_para
from openrok.tela import LIMITE_MESMA, EstadoOpcao, distancia, eh_tela_de_perguntas, estado_opcao, impressao
from tests.fixtures import carregar_print, quadros_video

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


def test_impressao_estavel_com_compressao():
    pergunta = AREAS.pergunta.recortar(carregar_print("q1_go"), TELA)

    buffer = io.BytesIO()
    pergunta.save(buffer, "JPEG", quality=70)
    comprimida = Image.open(io.BytesIO(buffer.getvalue()))

    assert distancia(impressao(pergunta), impressao(comprimida)) <= LIMITE_MESMA
    assert isinstance(impressao(pergunta), bytes)


def test_impressao_separa_perguntas_parecidas_do_video():
    # Q1 (Saladino) and Q3 (Shakespeare) are both one-line questions of similar
    # length: a 64-bit dHash put them 2 bits apart and mixed up their answers
    quadros = list(quadros_video())
    q1 = [impressao(AREAS.pergunta.recortar(q, TELA)) for t, q in quadros if 0.5 <= t <= 3.0]
    q3 = [impressao(AREAS.pergunta.recortar(q, TELA)) for t, q in quadros if 11.2 <= t <= 11.9]

    assert max(distancia(a, b) for a in q1 for b in q1) <= LIMITE_MESMA
    assert max(distancia(a, b) for a in q3 for b in q3) <= LIMITE_MESMA
    assert min(distancia(a, b) for a in q1 for b in q3) > 1.5 * LIMITE_MESMA

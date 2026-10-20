import sqlite3
import threading

import pytest
from PIL import Image, ImageDraw, ImageFont

from openrok.armazem import Armazem
from openrok.captura import CapturaDeQuadro
from openrok.caminhos import pasta_base
from openrok.conhecimento import Conhecimento
from openrok.eventos import (Aprendido, JogoEncontrado, JogoPerdido, OutraTela, PerguntaDetectada, Respondida,
                             Resultado, SemResposta, Sugestao)
from openrok.geometria import Ret, areas_para
from openrok.ocr import MotorOCR
from openrok.tela import EstadoOpcao, estado_opcao
from openrok.vigia import Estado, Vigia
from tests.fixtures import carregar_print

TELA = Ret(0, 0, 1920, 1080)
AREAS = areas_para(TELA)
CSV_PT = pasta_base() / "data" / "perguntas_respostas_pt.csv"


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

class JanelaFake:
    def __init__(self):
        self.ativa_agora = True

    def localizar(self):
        return TELA

    def ativa(self):
        return self.ativa_agora


@pytest.fixture(scope="module")
def ocr():
    motor = MotorOCR("por")
    yield motor
    motor.fechar()


@pytest.fixture
def conhecimento():
    return Conhecimento("pt", CSV_PT, Armazem(":memory:"))


def montar(ocr, conhecimento, ia=None):
    eventos = []
    captura = CapturaDeQuadro()
    janela = JanelaFake()
    vigia = Vigia(janela, captura, ocr, conhecimento, eventos.append, ia=ia)
    return vigia, captura, janela, eventos


def rodar(vigia, captura, quadro, ciclos=1):
    captura.quadro = quadro
    for _ in range(ciclos):
        vigia.ciclo()


def tipos(eventos):
    return [type(e) for e in eventos]


def neutralizar(imagem, textos):
    """Redraws result boxes as neutral ones: game beige with the white option text."""
    imagem = imagem.copy()
    desenho = ImageDraw.Draw(imagem)
    for letra, texto in textos.items():
        c = AREAS.caixas[letra]
        desenho.rectangle((c.x, c.y, c.x + c.w, c.y + c.h), fill=(197, 145, 92))
        desenho.text((c.x + 50, c.y + 26), texto, fill=(250, 245, 235), font=ImageFont.load_default(size=26))
    return imagem


def pintar_caixa(imagem, letra, cor):
    imagem = imagem.copy()
    c = AREAS.caixas[letra]
    ImageDraw.Draw(imagem).rectangle((c.x, c.y, c.x + c.w, c.y + c.h), fill=cor)
    return imagem


def pergunta_inexistente():
    imagem = carregar_print("q1_go")
    p = AREAS.pergunta
    desenho = ImageDraw.Draw(imagem)
    desenho.rectangle((p.x, p.y, p.x + p.w, p.y + p.h), fill=(232, 205, 160))
    desenho.text((p.x + 10, p.y + 30), "Pergunta inexistente de teste qualquer?", fill=(40, 30, 20),
                 font=ImageFont.load_default(size=28))
    return imagem


# ----------------------------------------------------------
# Tests
# ----------------------------------------------------------

def test_neutro_de_teste_esta_neutro():
    q4_neutro = neutralizar(carregar_print("q4_einstein"), {"A": "1915", "D": "1905"})
    for letra in "AD":
        assert estado_opcao(AREAS.interior(letra).recortar(q4_neutro, TELA)) == EstadoOpcao.NEUTRA


def test_pergunta_do_banco(ocr, conhecimento):
    vigia, captura, _, eventos = montar(ocr, conhecimento)
    rodar(vigia, captura, carregar_print("q1_go"), ciclos=2)

    assert tipos(eventos) == [JogoEncontrado, PerguntaDetectada, Sugestao]
    assert "Go" in eventos[1].texto
    assert (eventos[2].letra, eventos[2].origem) == ("A", "banco")
    assert vigia.estado == Estado.PERGUNTA


def test_resultado_aprende(ocr, conhecimento):
    vigia, captura, _, eventos = montar(ocr, conhecimento)
    original = carregar_print("q4_einstein")

    rodar(vigia, captura, neutralizar(original, {"A": "1915", "D": "1905"}), ciclos=2)
    assert eventos[-1] == Sugestao("D", "banco", eventos[-1].tempo_ms)

    rodar(vigia, captura, original, ciclos=3)
    assert eventos[-2:] == [Resultado("D", "A"), Aprendido("confirmada")]
    assert vigia.estado == Estado.RESULTADO


def test_colorida_vira_respondida(ocr, conhecimento):
    vigia, captura, _, eventos = montar(ocr, conhecimento)
    q1 = carregar_print("q1_go")

    rodar(vigia, captura, q1, ciclos=2)
    rodar(vigia, captura, pintar_caixa(q1, "B", (40, 110, 230)), ciclos=2)

    assert eventos[-1] == Respondida()
    assert Aprendido not in tipos(eventos)
    assert vigia.estado == Estado.RESPONDIDA


def test_outra_tela(ocr, conhecimento):
    vigia, captura, _, eventos = montar(ocr, conhecimento)
    rodar(vigia, captura, Image.new("RGB", (1920, 1080), (30, 30, 35)), ciclos=3)

    assert tipos(eventos) == [JogoEncontrado, OutraTela]
    assert vigia.estado == Estado.OUTRA_TELA


def test_jogo_inativo_e_volta(ocr, conhecimento):
    vigia, captura, janela, eventos = montar(ocr, conhecimento)
    q1 = carregar_print("q1_go")
    rodar(vigia, captura, q1, ciclos=2)

    janela.ativa_agora = False
    rodar(vigia, captura, q1, ciclos=2)
    assert eventos[-1] == JogoPerdido()
    assert vigia.estado == Estado.AGUARDANDO_JOGO

    janela.ativa_agora = True
    del eventos[:]
    rodar(vigia, captura, q1, ciclos=2)
    assert tipos(eventos) == [JogoEncontrado, PerguntaDetectada, Sugestao]
    assert eventos[-1].letra == "A"


def test_ia_atrasada_descartada(ocr, conhecimento):
    liberar = threading.Event()

    class IALenta:
        def escolher(self, pergunta, opcoes):
            liberar.wait(5)
            return "A"

    vigia, captura, _, eventos = montar(ocr, conhecimento, ia=IALenta())

    rodar(vigia, captura, pergunta_inexistente(), ciclos=2)
    rodar(vigia, captura, carregar_print("q1_go"), ciclos=2)
    liberar.set()
    vigia.parar()

    assert [e.origem for e in eventos if isinstance(e, Sugestao)] == ["banco"]


def test_ia_responde_pergunta_fora_do_banco(ocr, conhecimento):
    class IAFixa:
        def escolher(self, pergunta, opcoes):
            return "C"

    vigia, captura, _, eventos = montar(ocr, conhecimento, ia=IAFixa())
    rodar(vigia, captura, pergunta_inexistente(), ciclos=2)
    vigia.parar()

    assert eventos[-1].letra == "C" and eventos[-1].origem == "ia"


def test_sem_ia_avisa(ocr, conhecimento):
    vigia, captura, _, eventos = montar(ocr, conhecimento)
    rodar(vigia, captura, pergunta_inexistente(), ciclos=2)

    assert eventos[-1] == SemResposta("fora do banco")


def test_falha_ao_gravar(ocr, conhecimento):
    def explode(*args):
        raise sqlite3.OperationalError("database is locked")

    conhecimento.aprender = explode
    vigia, captura, _, eventos = montar(ocr, conhecimento)
    original = carregar_print("q4_einstein")

    rodar(vigia, captura, neutralizar(original, {"A": "1915", "D": "1905"}), ciclos=2)
    rodar(vigia, captura, original, ciclos=1)

    assert eventos[-1] == Resultado("D", "A")
    rodar(vigia, captura, carregar_print("q1_go"), ciclos=2)
    assert eventos[-1].letra == "A"


def test_opcao_verde_vazia(conhecimento):
    class OCRFalso:
        def ler(self, imagem):
            return "Em que ano Einstein publicou seus quatro Annus Mirabilis (\"Artigos Miraculosos\")?"

        def ler_opcoes(self, imagens):
            return ["1915", "1879", "1921", ""]

        def ler_tudo(self, pergunta, opcoes):
            return self.ler(pergunta), self.ler_opcoes(opcoes)

    vigia, captura, _, eventos = montar(OCRFalso(), conhecimento)
    original = carregar_print("q4_einstein")

    rodar(vigia, captura, neutralizar(original, {"A": "1915", "D": "1905"}), ciclos=2)
    rodar(vigia, captura, original, ciclos=2)

    assert Resultado("D", "A") in eventos
    assert Aprendido not in tipos(eventos)


def test_cache_errado_cai_para_o_banco(ocr, conhecimento):
    conhecimento.por_hash = lambda h: ("Pergunta parecida de outra rodada?", "1192")

    vigia, captura, _, eventos = montar(ocr, conhecimento)
    rodar(vigia, captura, carregar_print("q1_go"), ciclos=2)

    assert "Go" in eventos[-2].texto
    assert (eventos[-1].letra, eventos[-1].origem) == ("A", "banco")


class OCRContado:
    def __init__(self, ocr):
        self.ocr, self.leituras = ocr, 0

    def ler_opcoes(self, imagens):
        self.leituras += 1
        return self.ocr.ler_opcoes(imagens)

    def ler_tudo(self, pergunta, opcoes):
        self.leituras += 1
        return self.ocr.ler_tudo(pergunta, opcoes)


def test_volta_ao_jogo_reemite_sem_novo_ocr(ocr, conhecimento):
    contado = OCRContado(ocr)
    vigia, captura, janela, eventos = montar(contado, conhecimento)
    q1 = carregar_print("q1_go")
    rodar(vigia, captura, q1, ciclos=2)

    janela.ativa_agora = False
    rodar(vigia, captura, q1, ciclos=1)
    janela.ativa_agora = True
    del eventos[:]
    rodar(vigia, captura, q1, ciclos=1)

    assert tipos(eventos) == [JogoEncontrado, PerguntaDetectada, Sugestao]
    assert contado.leituras == 1


def test_trocar_de_janela_depois_de_responder_ainda_aprende(ocr, conhecimento):
    vigia, captura, janela, eventos = montar(ocr, conhecimento)
    original = carregar_print("q4_einstein")
    rodar(vigia, captura, neutralizar(original, {"A": "1915", "D": "1905"}), ciclos=2)

    janela.ativa_agora = False
    rodar(vigia, captura, original, ciclos=1)
    janela.ativa_agora = True
    rodar(vigia, captura, original, ciclos=1)

    assert eventos[-2:] == [Resultado("D", "A"), Aprendido("confirmada")]


def test_alternar_janela_no_verde_nao_aprende_duas_vezes(ocr, conhecimento):
    vigia, captura, janela, eventos = montar(ocr, conhecimento)
    original = carregar_print("q4_einstein")
    rodar(vigia, captura, neutralizar(original, {"A": "1915", "D": "1905"}), ciclos=2)
    rodar(vigia, captura, original, ciclos=1)

    janela.ativa_agora = False
    rodar(vigia, captura, original, ciclos=1)
    janela.ativa_agora = True
    rodar(vigia, captura, original, ciclos=2)

    assert tipos(eventos).count(Aprendido) == 1
    assert tipos(eventos).count(Resultado) == 1


def test_geometria_do_ultimo_ciclo(ocr, conhecimento):
    vigia, captura, _, _ = montar(ocr, conhecimento)
    assert vigia.geometria is None

    rodar(vigia, captura, carregar_print("q1_go"))
    assert vigia.geometria == (TELA, AREAS)

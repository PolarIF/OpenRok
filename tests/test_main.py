import csv

import pytest

from openrok.banco import BancoPerguntas
from openrok.caminhos import pasta_base
from openrok.ia import extrair_letra
from openrok.idiomas import IDIOMAS
from openrok.texto import normalizar


def criar_csv(caminho, linhas, cabecalho=("question", "response")):
    with open(caminho, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(cabecalho)
        writer.writerows(linhas)
    return caminho


@pytest.fixture
def banco(tmp_path):
    return BancoPerguntas(criar_csv(tmp_path / "db.csv", [
        ("During the Trojan War, which Greek warrior killed Hector?", "Achilles"),
        ("Which of the following is NOT one of Mulan's abilities?", "Indomitable Army"),
        ("Which of the following is NOT one of Osman I's abilities?", "Oblique Tactics"),
        ("Antes de liderar a maior rebelião de escravos da Roma Antiga, o que foi Espártaco?", "Um gladiador"),
        ("", "empty question"),
        ("#VALUE!", "excel garbage"),
        ("During the Trojan War, which Greek warrior killed Hector?", "duplicate"),
        ("A question without an answer here", ""),
    ]))


# ----------------------------------------------------------
# Normalization and database loading
# ----------------------------------------------------------

def test_normalizar_remove_acentos_pontuacao_e_quebras():
    assert normalizar("  O que foi\nEspártaco?! ") == "o que foi espartaco"
    assert normalizar("Mulan's") == "mulan s"


def test_carrega_ignorando_cabecalho_lixo_e_duplicadas(banco):
    assert len(banco) == 4
    assert "question" not in banco.perguntas
    assert banco.buscar("During the Trojan War, which Greek warrior killed Hector?")[1] == "Achilles"


# ----------------------------------------------------------
# Matching
# ----------------------------------------------------------

def test_tolera_ruido_de_ocr(banco):
    texto = "| During the Tr0jan War, which Greek\nwarrior kil1ed Hector?"
    assert banco.buscar(texto)[1] == "Achilles"


def test_tolera_acentos_perdidos_no_ocr(banco):
    texto = "Antes de liderar a maior rebeliao de escravos da Roma\nAntiga, o que foi Espartaco?"
    assert banco.buscar(texto)[1] == "Um gladiador"


def test_nao_confunde_perguntas_do_mesmo_modelo(banco):
    # Same template, different commander: must not return Mulan's or Osman's answer
    assert banco.buscar("Which of the following is NOT one of Belisarius' abilities?") is None
    assert banco.buscar("Which of the following is NOT one of Mulan's abilities?")[1] == "Indomitable Army"


def test_fragmento_curto_nao_casa(banco):
    assert banco.buscar("Which of") is None
    assert banco.buscar("") is None


def test_salvar_persiste_e_nao_duplica(banco):
    pergunta = "Who was the first emperor\nof the Roman Empire?"

    assert banco.salvar(pergunta, "Augustus")
    assert not banco.salvar(pergunta, "Augustus")
    assert BancoPerguntas(banco.caminho).buscar(pergunta)[1] == "Augustus"

    with open(banco.caminho, encoding="utf-8") as file:
        assert "Who was the first emperor of the Roman Empire?,Augustus" in file.read()


# ----------------------------------------------------------
# AI reply parsing
# ----------------------------------------------------------

OPCOES = ["A slave", "A gladiator", "Achilles", "A senator"]


@pytest.mark.parametrize("resposta, esperado", [
    ("B", "B"),
    ("b", "B"),
    ("B)", "B"),
    ("**C**", "C"),
    ("Answer: B", "B"),
    ("The correct answer is B) A gladiator", "B"),
    ("I think it is D.", "D"),
    ("Achilles", "C"),       # option text instead of the letter
    ("A gladiator", "B"),    # starts with the article "A", but it's option B
    ("A or B", None),        # ambiguous
    ("I don't know", None),
    ("", None),
    (None, None),
])
def test_extrair_letra(resposta, esperado):
    assert extrair_letra(resposta, OPCOES) == esperado


# ----------------------------------------------------------
# AI factory
# ----------------------------------------------------------

def test_sem_chave_nao_cria_ia(monkeypatch):
    from openrok.app import fabrica_ia

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert fabrica_ia("pt") is None


# ----------------------------------------------------------
# Real data files
# ----------------------------------------------------------

@pytest.mark.parametrize("idioma", list(IDIOMAS))
def test_bancos_reais_carregam(idioma):
    banco = BancoPerguntas(pasta_base() / "data" / IDIOMAS[idioma]["csv"])
    assert len(banco) > 1200
    pergunta = banco.perguntas[0]
    assert banco.buscar(pergunta)[1] == banco.respostas[0]

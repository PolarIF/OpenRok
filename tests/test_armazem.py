import csv

from openrok.armazem import Armazem
from openrok.conhecimento import Conhecimento

PERGUNTA = "Which of the following organs is NOT part of the human respiratory system?"


def criar_csv(caminho, linhas):
    with open(caminho, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["question", "response"])
        writer.writerows(linhas)
    return caminho


def test_nova_confirmada_corrigida():
    armazem = Armazem(":memory:")

    assert armazem.aprender("en", PERGUNTA, "Lungs", None, None) == "nova"
    assert armazem.aprender("en", PERGUNTA, "Lungs", "Lungs", None) == "confirmada"
    assert armazem.aprender("en", PERGUNTA, "Heart", "Lungs", None) == "corrigida"

    assert armazem.perguntas("en") == [(PERGUNTA, "Heart")]
    assert armazem.perguntas("pt") == []


def test_desfazer():
    armazem = Armazem(":memory:")
    armazem.aprender("en", PERGUNTA, "Lungs", None, None)
    armazem.aprender("en", PERGUNTA, "Heart", "Lungs", None)

    assert armazem.desfazer_ultima_correcao("en") == (PERGUNTA, "Lungs")
    assert armazem.perguntas("en") == [(PERGUNTA, "Lungs")]
    assert armazem.desfazer_ultima_correcao("en") is None


def test_hash_64_bits():
    armazem = Armazem(":memory:")
    armazem.aprender("en", PERGUNTA, "Lungs", None, 2 ** 64 - 1)

    assert armazem.hashes("en") == [(2 ** 64 - 1, PERGUNTA, "Lungs")]


def test_conhecimento_usuario_vence(tmp_path):
    caminho = criar_csv(tmp_path / "db.csv", [(PERGUNTA, "impact wrench")])
    armazem = Armazem(":memory:")

    conhecimento = Conhecimento("en", caminho, armazem)
    assert conhecimento.aprender(PERGUNTA, "Lungs", None) == "corrigida"
    assert conhecimento.buscar(PERGUNTA)[1] == "Lungs"

    assert Conhecimento("en", caminho, armazem).buscar(PERGUNTA)[1] == "Lungs"


def test_aprender_usa_pergunta_canonica(tmp_path):
    caminho = criar_csv(tmp_path / "db.csv", [(PERGUNTA, "Lungs")])
    armazem = Armazem(":memory:")
    conhecimento = Conhecimento("en", caminho, armazem)

    lida = "Which of the fol1owing organs is NOT part of the\nhuman respiratory system?"
    assert conhecimento.aprender(lida, "Lungs", None) == "confirmada"
    assert armazem.perguntas("en") == [(PERGUNTA, "Lungs")]


def test_por_hash(tmp_path):
    caminho = criar_csv(tmp_path / "db.csv", [])
    conhecimento = Conhecimento("en", caminho, Armazem(":memory:"))
    h = 0x0123456789ABCDEF

    assert conhecimento.aprender(PERGUNTA, "Lungs", h) == "nova"
    assert conhecimento.por_hash(h ^ 0b1011) == (PERGUNTA, "Lungs")
    assert conhecimento.por_hash(h ^ 0b11111) is None


def test_persistencia_em_arquivo(tmp_path):
    caminho = tmp_path / "openrok.db"
    Armazem(caminho).aprender("pt", "Quem pintou a Mona Lisa?", "Leonardo da Vinci", None, 42)

    reaberto = Armazem(caminho)
    assert reaberto.perguntas("pt") == [("Quem pintou a Mona Lisa?", "Leonardo da Vinci")]
    assert reaberto.hashes("pt") == [(42, "Quem pintou a Mona Lisa?", "Leonardo da Vinci")]

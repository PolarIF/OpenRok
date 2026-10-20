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


def test_impressao_guardada_como_bytes():
    armazem = Armazem(":memory:")
    armazem.aprender("en", PERGUNTA, "Lungs", None, b"\xff" * 144)

    assert armazem.hashes("en") == [(b"\xff" * 144, PERGUNTA, "Lungs")]


def test_conhecimento_usuario_vence(tmp_path):
    caminho = criar_csv(tmp_path / "db.csv", [(PERGUNTA, "impact wrench")])
    armazem = Armazem(":memory:")

    conhecimento = Conhecimento("en", caminho, armazem)
    assert conhecimento.aprender(PERGUNTA, ["Heart", "Lungs", "Liver", "Kidney"], "B", None) == "corrigida"
    assert conhecimento.buscar(PERGUNTA)[1] == "Lungs"

    assert Conhecimento("en", caminho, armazem).buscar(PERGUNTA)[1] == "Lungs"


def test_aprender_usa_pergunta_canonica(tmp_path):
    caminho = criar_csv(tmp_path / "db.csv", [(PERGUNTA, "Lungs")])
    armazem = Armazem(":memory:")
    conhecimento = Conhecimento("en", caminho, armazem)

    lida = "Which of the fol1owing organs is NOT part of the\nhuman respiratory system?"
    assert conhecimento.aprender(lida, ["Lungs", "Heart", "Liver", "Kidney"], "A", None) == "confirmada"
    assert armazem.perguntas("en") == [(PERGUNTA, "Lungs")]


def test_por_hash(tmp_path):
    caminho = criar_csv(tmp_path / "db.csv", [])
    conhecimento = Conhecimento("en", caminho, Armazem(":memory:"))
    h = bytes([0b11110000] * 10) + bytes(134)  # 40 text cells
    perto = bytes([0b11110000] * 9 + [0b11110001]) + bytes(134)  # 1/41 apart
    longe = bytes([0b11110000] * 8 + [0b00001111] * 2) + bytes(134)  # 16/48 apart

    assert conhecimento.aprender(PERGUNTA, ["Lungs", "Heart", "Liver", "Kidney"], "A", h) == "nova"
    assert conhecimento.por_hash(perto) == (PERGUNTA, "Lungs")
    assert conhecimento.por_hash(longe) is None


def test_persistencia_em_arquivo(tmp_path):
    caminho = tmp_path / "openrok.db"
    Armazem(caminho).aprender("pt", "Quem pintou a Mona Lisa?", "Leonardo da Vinci", None, b"\x01\x02")

    reaberto = Armazem(caminho)
    assert reaberto.perguntas("pt") == [("Quem pintou a Mona Lisa?", "Leonardo da Vinci")]
    assert reaberto.hashes("pt") == [(b"\x01\x02", "Quem pintou a Mona Lisa?", "Leonardo da Vinci")]


def test_ocr_sujo_na_opcao_verde_nao_corrompe_resposta_certa(tmp_path):
    pergunta = "Em que ano Einstein publicou seus quatro Annus Mirabilis?"
    caminho = criar_csv(tmp_path / "db.csv", [(pergunta, "1905")])
    armazem = Armazem(":memory:")
    conhecimento = Conhecimento("pt", caminho, armazem)

    assert conhecimento.aprender(pergunta, ["1915 v", "1879", "1921", "1905 4"], "D", None) == "confirmada"
    assert conhecimento.buscar(pergunta)[1] == "1905"
    assert armazem.perguntas("pt") == [(pergunta, "1905")]


def test_pergunta_nova_guarda_texto_da_opcao(tmp_path):
    conhecimento = Conhecimento("en", criar_csv(tmp_path / "db.csv", []), Armazem(":memory:"))

    assert conhecimento.aprender(PERGUNTA, ["Heart", "Lungs\nand trachea", "", ""], "B", None) == "nova"
    assert conhecimento.buscar(PERGUNTA)[1] == "Lungs and trachea"


# ----------------------------------------------------------
# Database tab support
# ----------------------------------------------------------

def conhecimento_com_historia(tmp_path):
    caminho = criar_csv(tmp_path / "db.csv", [
        ("Antes de liderar a maior rebelião, o que foi Espártaco?", "Um gladiador"),
        ("Qual orgao faz parte do sistema respiratorio humano?", "chave de impacto"),
        ("Quem pintou a Mona Lisa original?", "Leonardo da Vinci"),
    ])
    conhecimento = Conhecimento("pt", caminho, Armazem(":memory:"))
    conhecimento.aprender("Antes de liderar a maior rebelião, o que foi Espártaco?",
                          ["Um gladiador", "Um senador", "", ""], "A", None)
    conhecimento.aprender("Qual orgao faz parte do sistema respiratorio humano?",
                          ["Pulmões", "Fígado", "", ""], "A", None)
    return conhecimento


def test_listar_filtros(tmp_path):
    conhecimento = conhecimento_com_historia(tmp_path)

    assert len(conhecimento.listar(filtro="aprendidas")) == 2
    corrigidas = conhecimento.listar(filtro="corrigidas")
    assert [(c["resposta"], c["corrigida_de"]) for c in corrigidas] == [("Pulmões", "chave de impacto")]
    assert [c["pergunta"] for c in conhecimento.listar(filtro="nao_confirmadas")] == ["Quem pintou a Mona Lisa original?"]
    assert len(conhecimento.listar()) == 3


def test_busca_sem_acento(tmp_path):
    conhecimento = conhecimento_com_historia(tmp_path)
    assert [c["resposta"] for c in conhecimento.listar("espartaco")] == ["Um gladiador"]
    assert [c["resposta"] for c in conhecimento.listar("PULMOES")] == ["Pulmões"]


def test_desfazer_atualiza_memoria(tmp_path):
    conhecimento = conhecimento_com_historia(tmp_path)

    assert conhecimento.desfazer_ultima_correcao() == ("Qual orgao faz parte do sistema respiratorio humano?",
                                                       "chave de impacto")
    assert conhecimento.buscar("Qual orgao faz parte do sistema respiratorio humano?")[1] == "chave de impacto"
    assert conhecimento.desfazer_ultima_correcao() is None


def test_exportar_confirmadas(tmp_path):
    conhecimento = conhecimento_com_historia(tmp_path)
    destino = tmp_path / "confirmadas.csv"

    assert conhecimento.exportar_confirmadas(destino) == 2
    with open(destino, encoding="utf-8", newline="") as file:
        linhas = list(csv.reader(file))
    assert linhas[0] == ["pergunta", "resposta"]
    assert sorted(linhas[1:]) == sorted([["Antes de liderar a maior rebelião, o que foi Espártaco?", "Um gladiador"],
                                         ["Qual orgao faz parte do sistema respiratorio humano?", "Pulmões"]])


def test_importar_csv_tolerante(tmp_path):
    conhecimento = conhecimento_com_historia(tmp_path)
    origem = tmp_path / "amigo.csv"
    origem.write_text("Q;A\n\nso uma coluna\nQuem descobriu o caminho maritimo para a India?,Vasco da Gama\n"
                      "Em que ano caiu o Imperio Romano do Ocidente?,476\n", encoding="utf-8")

    assert conhecimento.importar_csv(origem) == 2
    assert conhecimento.buscar("Quem descobriu o caminho maritimo para a India?")[1] == "Vasco da Gama"
    assert conhecimento.buscar("Em que ano caiu o Imperio Romano do Ocidente?")[1] == "476"


def test_importar_nao_sobrescreve_o_que_o_jogo_confirmou(tmp_path):
    conhecimento = conhecimento_com_historia(tmp_path)
    origem = tmp_path / "amigo.csv"
    origem.write_text('"Antes de liderar a maior rebelião, o que foi Espártaco?",Um rei\n', encoding="utf-8")

    assert conhecimento.importar_csv(origem) == 0
    assert conhecimento.buscar("Antes de liderar a maior rebelião, o que foi Espártaco?")[1] == "Um gladiador"

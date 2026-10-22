import json
import random

import httpx
import pytest

from openrok.ia import PRESETS, ClienteIA, FalhaIA, pergunta_de_teste, preset
from openrok.idiomas import IDIOMAS

OPCOES = ["Paris", "Achilles", "Ajax", "Priam"]
T = IDIOMAS["pt"]["textos"]


def resposta_com(texto):
    return {"choices": [{"message": {"role": "assistant", "content": texto}}]}


def cliente(id_preset="openai", resposta=None, status=200, chave="chave", base_url=None, modelo=None,
            excecao=None, corpo=None, modelos=None):
    """ClienteIA over a MockTransport; the requests it got land in .recebidas."""
    recebidas = []
    p = preset(id_preset)

    def responder(requisicao):
        recebidas.append(requisicao)
        if excecao is not None:
            raise excecao("falhou", request=requisicao)
        if requisicao.method == "GET":
            return httpx.Response(200, json={"data": [{"id": m} for m in (modelos or [])]})
        if corpo is not None:
            return httpx.Response(status, content=corpo)
        return httpx.Response(status, json=resposta_com("B") if resposta is None else resposta)

    ia = ClienteIA("pt", p, base_url or p.base_url, p.modelo if modelo is None else modelo, chave,
                   transporte=httpx.MockTransport(responder))
    ia.recebidas = recebidas
    return ia


def test_requisicao_tem_modelo_prompt_e_corpo_do_preset():
    ia = cliente("openai")

    ia.escolher("Quem matou Heitor?", ["Paris", "Achilles", "", "Priam"])

    requisicao = ia.recebidas[0]
    dados = json.loads(requisicao.content)
    assert str(requisicao.url) == "https://api.openai.com/v1/chat/completions"
    assert requisicao.headers["Authorization"] == "Bearer chave"
    assert dados["model"] == "gpt-6-luna"
    assert dados["temperature"] == 0 and dados["reasoning_effort"] == "none"
    assert [m["role"] for m in dados["messages"]] == ["user"]
    prompt = dados["messages"][0]["content"]
    assert "Quem matou Heitor?" in prompt
    assert "A) Paris" in prompt and "B) Achilles" in prompt and "D) Priam" in prompt
    assert "C)" not in prompt


def test_anthropic_sem_temperature():
    ia = cliente("anthropic")

    ia.escolher("Quem matou Heitor?", OPCOES)

    assert "temperature" not in json.loads(ia.recebidas[0].content)


def test_sem_chave_nao_manda_authorization():
    ia = cliente("ollama", chave=None)

    ia.escolher("Quem matou Heitor?", OPCOES)

    assert "Authorization" not in ia.recebidas[0].headers


@pytest.mark.parametrize("texto, opcoes, esperado", [
    ("B", OPCOES, "B"),
    ("Resposta: B", OPCOES, "B"),
    ("não sei", OPCOES, None),
    ("D", ["Paris", "Achilles", "Ajax", ""], None),
])
def test_escolher_devolve_letra(texto, opcoes, esperado):
    assert cliente(resposta=resposta_com(texto)).escolher("Quem matou Heitor?", opcoes) == esperado


@pytest.mark.parametrize("status, corpo, esperado", [
    (401, b"{}", T["ia_chave_invalida"]),
    (403, b"{}", T["ia_chave_invalida"]),
    (400, b'{"error": {"message": "API key not valid"}}', T["ia_chave_invalida"]),
    (429, b"{}", T["ia_limite"]),
    (404, b"{}", T["ia_modelo_nao_encontrado"].format(modelo="gpt-6-luna")),
    (500, b"{}", T["ia_erro_http"].format(status=500)),
])
def test_erros_viram_falha_ia(status, corpo, esperado):
    with pytest.raises(FalhaIA) as erro:
        cliente(status=status, corpo=corpo).escolher("Quem matou Heitor?", OPCOES)

    assert str(erro.value) == esperado


def test_timeout_e_conexao():
    with pytest.raises(FalhaIA) as erro:
        cliente(excecao=httpx.ReadTimeout).escolher("Quem matou Heitor?", OPCOES)
    assert str(erro.value) == T["ia_demorou"]

    with pytest.raises(FalhaIA) as erro:
        cliente("ollama", chave=None, excecao=httpx.ConnectError).escolher("Quem matou Heitor?", OPCOES)
    assert str(erro.value) == T["ia_sem_conexao"].format(base="http://localhost:11434/v1")


@pytest.mark.parametrize("corpo", [
    b"{}",
    b'{"choices": []}',
    b'{"choices": [{"message": {"content": null}}]}',
    b"<html>nada</html>",
])
def test_resposta_invalida(corpo):
    with pytest.raises(FalhaIA) as erro:
        cliente(corpo=corpo).escolher("Quem matou Heitor?", OPCOES)

    assert str(erro.value) == T["ia_resposta_invalida"]


def test_modelo_vazio_usa_o_primeiro_carregado():
    ia = cliente("lmstudio", chave=None, modelo="", modelos=["qwen3-4b", "outro"])

    ia.escolher("Quem matou Heitor?", OPCOES)
    ia.escolher("Quem matou Heitor?", OPCOES)

    metodos = [(r.method, r.url.path) for r in ia.recebidas]
    assert metodos.count(("GET", "/v1/models")) == 1
    assert all(json.loads(r.content)["model"] == "qwen3-4b" for r in ia.recebidas if r.method == "POST")


def test_modelo_vazio_sem_modelos_carregados():
    with pytest.raises(FalhaIA) as erro:
        cliente("lmstudio", chave=None, modelo="", modelos=[]).escolher("Quem matou Heitor?", OPCOES)

    assert str(erro.value) == T["ia_modelo_nao_encontrado"].format(modelo="")


def test_base_url_com_barra_no_fim():
    ia = cliente("personalizado", base_url="http://x/v1/", modelo="m")

    ia.escolher("Quem matou Heitor?", OPCOES)

    assert str(ia.recebidas[0].url) == "http://x/v1/chat/completions"


def test_testar_mede_tempo_e_acerto():
    certo = cliente(resposta=resposta_com("C")).testar("Quem matou Heitor?", OPCOES, "C")
    assert certo.acertou is True and certo.tempo_ms >= 0

    errado = cliente(resposta=resposta_com("A")).testar("Quem matou Heitor?", OPCOES, "C")
    assert errado.acertou is False and errado.letra == "A" and errado.correta == "C"


def test_pergunta_de_teste():
    perguntas = [f"Pergunta {i}?" for i in range(10)]
    respostas = [f"Resposta {i}" for i in range(10)]

    pergunta, opcoes, letra = pergunta_de_teste(perguntas, respostas, random.Random(1))

    indice = perguntas.index(pergunta)
    assert len(opcoes) == 4 and len(set(opcoes)) == 4
    assert opcoes["ABCD".index(letra)] == respostas[indice]
    assert all(o in respostas and o != respostas[indice] for i, o in enumerate(opcoes) if "ABCD"[i] != letra)


def test_presets():
    assert [p.id for p in PRESETS] == ["gemini", "groq", "openrouter", "ollama", "lmstudio", "openai",
                                       "anthropic", "deepseek", "personalizado"]
    assert preset("xyz") is PRESETS[0]
    assert all(p.link_chave.startswith("https://") for p in PRESETS if p.exige_chave)
    assert preset("deepseek").base_url == "https://api.deepseek.com"


@pytest.mark.parametrize("campos, chaves, ambiente, esperado", [
    ({"ia_provedor": "groq"}, {}, {}, None),
    ({"ia_provedor": "groq"}, {"groq": "k"}, {}, ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b", "k")),
    ({"ia_provedor": "groq", "ia_modelo": "outro"}, {"groq": "k"}, {}, ("https://api.groq.com/openai/v1", "outro", "k")),
    ({"ia_provedor": "ollama"}, {}, {}, ("http://localhost:11434/v1", "llama3.2", None)),
    ({"ia_provedor": "personalizado"}, {}, {}, None),
    ({"ia_provedor": "personalizado", "ia_base_url": "http://x/v1", "ia_modelo": "m"}, {}, {}, ("http://x/v1", "m", None)),
    ({"ia_provedor": "gemini"}, {}, {"GEMINI_API_KEY": "g"},
     ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.5-flash-lite", "g")),
])
def test_ia_de_config(monkeypatch, campos, chaves, ambiente, esperado):
    from openrok.cofre import CofreMemoria
    from openrok.config import Config
    from openrok.ia import ia_de_config

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    for nome, valor in ambiente.items():
        monkeypatch.setenv(nome, valor)
    cofre = CofreMemoria()
    for provedor, chave in chaves.items():
        cofre.gravar(provedor, chave)

    ia = ia_de_config(Config(**campos), "pt", cofre)

    if esperado is None:
        assert ia is None
    else:
        assert (ia.base_url, ia.modelo, ia.chave) == esperado
        assert ia.idioma == "pt"


def test_chave_com_caractere_invisivel_e_limpa():
    ia = cliente(chave="  abc\u200b\n")

    ia.escolher("Quem matou Heitor?", OPCOES)

    assert ia.recebidas[0].headers["Authorization"] == "Bearer abc"


def test_chave_com_acento_nao_derruba():
    from openrok.cofre import CofreMemoria
    from openrok.config import Config
    from openrok.ia import ia_de_config

    cofre = CofreMemoria()
    cofre.gravar("groq", "chaveç")

    ia = ia_de_config(Config(ia_provedor="groq"), "pt", cofre)

    with pytest.raises(FalhaIA) as erro:
        ia.escolher("Quem matou Heitor?", OPCOES)
    assert str(erro.value) == T["ia_chave_invalida"]


def test_pergunta_de_teste_com_banco_pequeno():
    with pytest.raises(ValueError):
        pergunta_de_teste([], [], random.Random(1))
    with pytest.raises(ValueError):
        pergunta_de_teste(["a", "b", "c"], ["x", "y", "z"], random.Random(1))


def test_log_tem_o_que_foi_enviado_e_recebido(caplog):
    caplog.set_level("INFO", logger="openrok.ia")
    ia = cliente(resposta=resposta_com("Acho que é a B) Achilles"), chave="segredo-123")

    ia.escolher("Quem matou Heitor?", OPCOES)

    texto = caplog.text
    assert "gpt-6-luna" in texto and "Quem matou Heitor?" in texto and "B) Achilles" in texto
    assert "Acho que é a B) Achilles" in texto
    assert "letra=B" in texto
    assert "segredo-123" not in texto


def test_log_do_erro_tem_status_e_corpo(caplog):
    caplog.set_level("INFO", logger="openrok.ia")

    with pytest.raises(FalhaIA):
        cliente(status=500, corpo=b'{"error": "servidor caiu"}').escolher("Quem matou Heitor?", OPCOES)

    assert "500" in caplog.text and "servidor caiu" in caplog.text


def test_groq_pede_raciocinio_curto():
    ia = cliente("groq")

    ia.escolher("Quem matou Heitor?", OPCOES)

    dados = json.loads(ia.recebidas[0].content)
    assert dados["model"] == "openai/gpt-oss-120b"
    assert dados["reasoning_effort"] == "low" and dados["temperature"] == 0


def test_log_da_resposta_vazia_tem_o_motivo(caplog):
    caplog.set_level("INFO", logger="openrok.ia")
    corpo = {"choices": [{"message": {"content": "", "reasoning": "pensando..."}, "finish_reason": "length"}]}

    assert cliente(resposta=corpo).escolher("Quem matou Heitor?", OPCOES) is None

    assert "finish_reason=length" in caplog.text


@pytest.mark.parametrize("id_preset, modelo", [("groq", "allam-2-7b"), ("openai", "outro-modelo")])
def test_campos_do_preset_so_com_o_modelo_padrao(id_preset, modelo):
    ia = cliente(id_preset, modelo=modelo)

    ia.escolher("Quem matou Heitor?", OPCOES)

    dados = json.loads(ia.recebidas[0].content)
    assert dados["model"] == modelo
    assert "reasoning_effort" not in dados and dados["temperature"] == 0

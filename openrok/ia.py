import os
import re
import time
from dataclasses import dataclass, field

import httpx
from rapidfuzz import fuzz, process

from openrok.idiomas import IDIOMAS, LETRAS
from openrok.texto import normalizar


# ==========================================================
# PROVIDERS
# ==========================================================
# Every provider is reached through the OpenAI-compatible
# POST {base}/chat/completions. Default models checked in the
# providers' docs on 2026-10-21; the user can type any other.
# ==========================================================

@dataclass(frozen=True)
class Preset:
    id: str
    nome: str
    base_url: str
    modelo: str
    exige_chave: bool
    gratis: bool
    link_chave: str = ""
    corpo: dict = field(default_factory=lambda: {"temperature": 0})  # extra request fields


PRESETS = [
    Preset("gemini", "Google Gemini", "https://generativelanguage.googleapis.com/v1beta/openai",
           "gemini-3.5-flash-lite", True, True, "https://aistudio.google.com/apikey"),
    Preset("groq", "Groq", "https://api.groq.com/openai/v1", "llama-3.1-8b-instant", True, True,
           "https://console.groq.com/keys"),
    Preset("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "openrouter/free", True, True,
           "https://openrouter.ai/keys"),
    Preset("ollama", "Ollama", "http://localhost:11434/v1", "llama3.2", False, True),
    Preset("lmstudio", "LM Studio", "http://localhost:1234/v1", "", False, True),
    # temperature is only accepted with reasoning turned off
    Preset("openai", "OpenAI", "https://api.openai.com/v1", "gpt-6-luna", True, False,
           "https://platform.openai.com/api-keys", {"temperature": 0, "reasoning_effort": "none"}),
    # rejects any temperature below 1
    Preset("anthropic", "Anthropic", "https://api.anthropic.com/v1", "claude-haiku-5-5", True, False,
           "https://platform.claude.com/settings/keys", {}),
    Preset("deepseek", "DeepSeek", "https://api.deepseek.com", "deepseek-flash", True, False,
           "https://platform.deepseek.com/api_keys"),
    Preset("personalizado", "Personalizado", "", "", False, False),
]


def preset(id):
    return next((p for p in PRESETS if p.id == id), PRESETS[0])


# ==========================================================
# REPLY PARSING
# ==========================================================

def extrair_letra(texto, opcoes=()):
    """Finds the chosen option in the model reply ("B", "B)", "Answer: B"...).

    Returns None when the reply is ambiguous ("A or B") or doesn't
    point to any option, so a doubtful answer is never saved.
    """
    if not texto:
        return None

    limpo = re.sub(r"[\s*().:]", "", texto)
    if len(limpo) == 1 and limpo.upper() in LETRAS:
        return limpo.upper()

    # The model answered with the option text instead of the letter
    if any(opcoes):
        melhor = process.extractOne(
            normalizar(texto),
            [normalizar(opcao) for opcao in opcoes],
            scorer=fuzz.ratio,
            score_cutoff=90
        )
        if melhor:
            return LETRAS[melhor[2]]

    # The option marker as written in the prompt ("B) A gladiator")
    marcadas = set(re.findall(r"\b([ABCD])\)", texto))
    if len(marcadas) == 1:
        return marcadas.pop()

    # A standalone capital letter not starting a phrase ("A gladiator")
    todas = set(re.findall(r"\b([ABCD])\b", texto))
    soltas = set(re.findall(r"\b([ABCD])\b(?!\s+[a-z])", texto))

    if len(todas) == 1 and len(soltas) == 1:
        return soltas.pop()

    return None


class FalhaIA(Exception):
    """Any AI failure, with a message already in the interface language."""


@dataclass(frozen=True)
class ResultadoTeste:
    letra: str | None
    correta: str
    tempo_ms: float

    @property
    def acertou(self):
        return self.letra == self.correta


class ClienteIA:
    """One OpenAI-compatible chat endpoint.

    A single attempt with a short timeout: the question is on screen
    for seconds, a late answer is worthless.
    """

    def __init__(self, idioma, preset, base_url, modelo, chave, transporte=None, timeout=6.0):
        self.idioma = idioma
        self.preset = preset
        self.base_url = base_url.rstrip("/")
        self.modelo = modelo
        self.chave = chave
        cabecalhos = {"Authorization": f"Bearer {chave}"} if chave else {}
        self._http = httpx.Client(transport=transporte, timeout=timeout, headers=cabecalhos)

    def _texto(self, chave, **valores):
        return IDIOMAS[self.idioma]["textos"][chave].format(**valores)

    def _pedir(self, metodo, caminho, **kwargs):
        try:
            resposta = self._http.request(metodo, f"{self.base_url}{caminho}", **kwargs)
        except httpx.TimeoutException:
            raise FalhaIA(self._texto("ia_demorou")) from None
        except httpx.HTTPError:
            raise FalhaIA(self._texto("ia_sem_conexao", base=self.base_url)) from None

        status = resposta.status_code
        if status in (401, 403) or (status == 400 and "api key" in resposta.text.lower().replace("_", " ")):
            raise FalhaIA(self._texto("ia_chave_invalida"))
        if status == 429:
            raise FalhaIA(self._texto("ia_limite"))
        if status == 404:
            raise FalhaIA(self._texto("ia_modelo_nao_encontrado", modelo=self.modelo))
        if status >= 400:
            raise FalhaIA(self._texto("ia_erro_http", status=status))

        try:
            return resposta.json()
        except ValueError:
            raise FalhaIA(self._texto("ia_resposta_invalida")) from None

    def _modelo(self):
        # No model given (LM Studio): use the first one the server has loaded
        if not self.modelo:
            dados = self._pedir("GET", "/models")
            ids = [item.get("id") for item in dados.get("data", []) if isinstance(item, dict)] \
                if isinstance(dados, dict) else []
            if not ids or not ids[0]:
                raise FalhaIA(self._texto("ia_modelo_nao_encontrado", modelo=self.modelo))
            self.modelo = ids[0]
        return self.modelo

    def _perguntar(self, pergunta, opcoes):
        texto_opcoes = "\n".join(f"{letra}) {opcao}" for letra, opcao in zip(LETRAS, opcoes) if opcao)
        prompt = IDIOMAS[self.idioma]["prompt"].format(pergunta=" ".join(pergunta.split()), opcoes=texto_opcoes)

        dados = self._pedir("POST", "/chat/completions", json={
            "model": self._modelo(),
            "messages": [{"role": "user", "content": prompt}],
            **self.preset.corpo,
        })

        try:
            texto = dados["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            texto = None
        if not isinstance(texto, str):
            raise FalhaIA(self._texto("ia_resposta_invalida"))

        letra = extrair_letra(texto.strip(), opcoes)
        return letra if letra and opcoes[LETRAS.index(letra)] else None

    def escolher(self, pergunta, opcoes):
        """Letter of the option the model picked, or None."""
        return self._perguntar(pergunta, opcoes)

    def testar(self, pergunta, opcoes, correta):
        inicio = time.perf_counter()
        letra = self._perguntar(pergunta, opcoes)
        return ResultadoTeste(letra, correta, (time.perf_counter() - inicio) * 1000)


def pergunta_de_teste(perguntas, respostas, aleatorio):
    """A known question with its answer among three answers of other questions."""
    indice = aleatorio.randrange(len(perguntas))
    certa = respostas[indice]
    outras = list(dict.fromkeys(r for i, r in enumerate(respostas) if i != indice and r != certa))
    opcoes = aleatorio.sample(outras, 3) + [certa]
    aleatorio.shuffle(opcoes)
    return perguntas[indice], opcoes, LETRAS[opcoes.index(certa)]


def ia_de_config(config, idioma, cofre):
    """AI client for the provider chosen in the settings, or None when it can't work yet."""
    escolhido = preset(config.ia_provedor)
    base_url = config.ia_base_url if escolhido.id == "personalizado" else escolhido.base_url
    if not base_url:
        return None

    chave = cofre.ler(escolhido.id)
    if not chave and escolhido.id == "gemini":
        # Users of version 1 set the key in the environment
        chave = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if escolhido.exige_chave and not chave:
        return None

    return ClienteIA(idioma, escolhido, base_url, config.ia_modelo or escolhido.modelo, chave)

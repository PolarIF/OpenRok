import os
import re

from rapidfuzz import fuzz, process

from openrok.idiomas import IDIOMAS, LETRAS
from openrok.texto import normalizar


# ==========================================================
# GEMINI CONFIGURATION
# ==========================================================
# The API key is read from the GEMINI_API_KEY environment
# variable (never hardcode it in the source).
#   Windows:  setx GEMINI_API_KEY "your-key"
# The model can be changed with OPENROK_MODEL.
# ==========================================================

MODELO_GEMINI = os.environ.get("OPENROK_MODEL", "gemini-3.1-flash-lite-preview")


# ==========================================================
# GEMINI (FALLBACK FOR UNKNOWN QUESTIONS)
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


class Gemini:

    def __init__(self, idioma, client=None):
        self.idioma = idioma
        self._client = client

    @property
    def configurado(self):
        return self._client is not None or bool(
            os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        )

    def _cliente(self):
        if self._client is None:
            from google import genai  # imported lazily: slow import, only needed on a miss
            self._client = genai.Client()
        return self._client

    def _perguntar(self, pergunta, opcoes):
        from google.genai import types

        texto_opcoes = "\n".join(f"{letra}) {opcao}" for letra, opcao in zip(LETRAS, opcoes) if opcao)

        response = self._cliente().models.generate_content(
            model=MODELO_GEMINI,
            contents=IDIOMAS[self.idioma]["prompt"].format(
                pergunta=" ".join(pergunta.split()),
                opcoes=texto_opcoes
            ),
            config=types.GenerateContentConfig(temperature=0)
        )

        texto = (response.text or "").strip()
        letra = extrair_letra(texto, opcoes)

        if letra and opcoes[LETRAS.index(letra)]:
            return texto, letra
        return texto, None

    def escolher(self, pergunta, opcoes):
        """Letter of the option the model picked, or None."""
        return self._perguntar(pergunta, opcoes)[1]

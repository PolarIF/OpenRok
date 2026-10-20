import re
import unicodedata

from rapidfuzz import fuzz, process


# ==========================================================
# TEXT NORMALIZATION
# ==========================================================
# Lowercase, no accents, no punctuation, single spaces.
# Used everywhere questions and answers are compared.
# ==========================================================

def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^\w\s]", " ", texto)
    return " ".join(texto.split())


def palavras_batem(origem, destino, minimo=60):
    """Every word (3+ letters) of origem must have a similar word in destino.

    Many questions share a template and differ in a single word
    ("...NOT one of Mulan's abilities?" vs "...NOT one of Osman I's
    abilities?"). A global similarity score barely notices that, while
    OCR noise only damages words, it doesn't swap them for others.
    """
    palavras_destino = destino.split()

    for palavra in origem.split():
        if len(palavra) < 3 or palavra in palavras_destino:
            continue

        if process.extractOne(palavra, palavras_destino, scorer=fuzz.ratio, score_cutoff=minimo) is None:
            return False

    return True

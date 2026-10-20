from enum import Enum

import cv2
import numpy as np


# ==========================================================
# READING THE GAME SCREEN BY COLOR
# ==========================================================
# HSV ranges (OpenCV scale: H 0-180) measured on real
# screenshots: the parchment beige of a neutral option, the
# green of the right answer and the red of a wrong pick.
# Anything else colored (the weekend "answered" blue) is
# reported as COLORIDA without depending on its exact tone.
# ==========================================================

class EstadoOpcao(Enum):
    NEUTRA = "neutra"
    VERDE = "verde"
    VERMELHA = "vermelha"
    COLORIDA = "colorida"


LIMITE_COR = 0.35
LIMITE_BEGE = 0.6


def _hsv(imagem):
    return cv2.cvtColor(np.asarray(imagem.convert("RGB")), cv2.COLOR_RGB2HSV)


def _bege(h, s, v):
    return (h >= 10) & (h <= 22) & (s >= 105) & (s <= 165) & (v >= 165) & (v <= 230)


def fracoes(imagem):
    """Fraction of (beige, green, red) pixels."""
    hsv = _hsv(imagem)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    bege = _bege(h, s, v)
    verde = (h >= 50) & (h <= 75) & (s >= 140) & (v >= 100)
    vermelho = ((h <= 6) | (h >= 174)) & (s >= 170) & (v >= 100)

    return float(bege.mean()), float(verde.mean()), float(vermelho.mean())


def estado_opcao(imagem):
    bege, verde, vermelho = fracoes(imagem)

    if verde > LIMITE_COR:
        return EstadoOpcao.VERDE
    if vermelho > LIMITE_COR:
        return EstadoOpcao.VERMELHA
    if bege >= LIMITE_BEGE:
        return EstadoOpcao.NEUTRA
    return EstadoOpcao.COLORIDA


def eh_tela_de_perguntas(sondas):
    return all(fracoes(sonda)[0] >= LIMITE_BEGE for sonda in sondas)


# ==========================================================
# QUESTION FINGERPRINT
# ==========================================================
# 64-bit difference hash: survives compression and small
# rendering differences, changes completely with the text.
# ==========================================================

def dhash(imagem):
    pequena = np.asarray(imagem.convert("L").resize((9, 8)), dtype=np.int16)
    bits = (pequena[:, 1:] > pequena[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def distancia(a, b):
    return (a ^ b).bit_count()

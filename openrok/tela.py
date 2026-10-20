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
# Where the text ink is, on a 96x12 grid (adaptive threshold,
# so lighting and compression don't matter), compared with
# the Jaccard distance: changed cells / cells with ink.
# Measured on the real video: the same question stays under
# 0.026, different questions start at 0.127. A 64-bit dHash
# could not tell two one-line questions apart.
# ==========================================================

GRADE = (96, 12)
LIMITE_MESMA = 0.06


def impressao(imagem):
    cinza = np.asarray(imagem.convert("L"), dtype=np.uint8)
    tinta = cv2.adaptiveThreshold(cinza, 1, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    grade = cv2.resize(tinta.astype(np.float32), GRADE, interpolation=cv2.INTER_AREA)
    return np.packbits(grade.flatten() > 0.12).tobytes()


def distancia(a, b):
    bits_a = np.unpackbits(np.frombuffer(a, dtype=np.uint8))
    bits_b = np.unpackbits(np.frombuffer(b, dtype=np.uint8))
    tinta = np.count_nonzero(bits_a | bits_b)
    return np.count_nonzero(bits_a ^ bits_b) / tinta if tinta else 0.0

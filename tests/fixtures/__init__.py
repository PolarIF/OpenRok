from pathlib import Path

import cv2
from PIL import Image

PASTA = Path(__file__).resolve().parent

# Top-left corner of the crop inside the original 1920x1080 screenshot
RECORTE = (560, 330)


def carregar_print(nome):
    """Real game screenshot rebuilt at 1920x1080 (black outside the crop)."""
    tela = Image.new("RGB", (1920, 1080))
    tela.paste(Image.open(PASTA / f"{nome}.png").convert("RGB"), RECORTE)
    return tela


def quadros_video(fps=15):
    """Yields (seconds, 1920x1080 RGB frame) sampled at fps."""
    video = cv2.VideoCapture(str(PASTA / "simulado_0-12s.mp4"))
    proximo = 0.0

    try:
        while True:
            ok, quadro = video.read()
            if not ok:
                return

            tempo = video.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if tempo + 1e-6 < proximo:
                continue

            proximo += 1 / fps
            yield tempo, Image.fromarray(cv2.cvtColor(quadro, cv2.COLOR_BGR2RGB))
    finally:
        video.release()

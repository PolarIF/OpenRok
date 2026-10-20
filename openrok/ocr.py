import os
import queue
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import tesserocr
from PIL import Image, ImageEnhance, ImageGrab

from openrok.caminhos import pasta_tessdata


# ==========================================================
# SCREEN CAPTURE AND OCR
# ==========================================================

def preprocessar(imagem):
    # Grayscale -> 2x upscale -> contrast -> blur -> Otsu binarization
    imagem = imagem.convert("L")

    imagem = imagem.resize(
        (imagem.width * 2, imagem.height * 2),
        Image.LANCZOS
    )

    imagem = ImageEnhance.Contrast(imagem).enhance(2.0)

    imagem_np = cv2.GaussianBlur(np.array(imagem), (3, 3), 0)

    _, imagem_processada = cv2.threshold(
        imagem_np,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return Image.fromarray(imagem_processada)


def capturar_tela(areas):
    """Grabs the screen once and crops every area out of it."""
    x1 = min(x for x, y, w, h in areas.values())
    y1 = min(y for x, y, w, h in areas.values())
    x2 = max(x + w for x, y, w, h in areas.values())
    y2 = max(y + h for x, y, w, h in areas.values())

    tela = ImageGrab.grab(bbox=(x1, y1, x2, y2))

    return {
        nome: tela.crop((x - x1, y - y1, x - x1 + w, y - y1 + h))
        for nome, (x, y, w, h) in areas.items()
    }


class MotorOCR:
    """Keeps Tesseract instances loaded instead of creating one per read.

    Loading the language model is the slowest part of a read, so the
    instances are created once. There is one instance per area so
    the question and the four options can be read in parallel
    (tesserocr releases the GIL while recognizing).
    """

    def __init__(self, lang, instancias=5):
        caminho = os.environ.get("TESSDATA_PREFIX") or pasta_tessdata()

        self._livres = queue.Queue()
        for _ in range(instancias):
            self._livres.put(tesserocr.PyTessBaseAPI(path=caminho, lang=lang))

        self._executor = ThreadPoolExecutor(max_workers=instancias)

    def ler(self, imagem):
        api = self._livres.get()
        try:
            api.SetImage(preprocessar(imagem))
            return api.GetUTF8Text().strip()
        finally:
            self._livres.put(api)

    def ler_varias(self, imagens):
        return list(self._executor.map(self.ler, imagens))

    def fechar(self):
        self._executor.shutdown(wait=False)
        while not self._livres.empty():
            self._livres.get().End()

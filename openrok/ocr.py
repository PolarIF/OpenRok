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


def preprocessar_opcao(imagem):
    """Options have light text on a colored box (beige, green, red, blue).

    Plain grayscale + Otsu splits the parchment's lighting gradient
    instead of the text and loses short answers like "2". "Whiteness"
    (value minus saturation) is high only on the text, whatever the
    box color, so Otsu on it isolates the text. Output: dark on light.
    """
    imagem = imagem.convert("RGB")
    imagem = imagem.resize((imagem.width * 2, imagem.height * 2), Image.LANCZOS)

    hsv = cv2.cvtColor(np.asarray(imagem), cv2.COLOR_RGB2HSV).astype(np.int16)
    brancura = np.clip(hsv[..., 2] - hsv[..., 1], 0, 255).astype(np.uint8)

    _, binaria = cv2.threshold(brancura, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return Image.fromarray(binaria)


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

    def ler_opcao(self, imagem):
        # Options are short: a block first (they may wrap to two lines),
        # then a single line, which is what finds lone numbers like "2"
        api = self._livres.get()
        try:
            api.SetImage(preprocessar_opcao(imagem))

            for modo in (tesserocr.PSM.SINGLE_BLOCK, tesserocr.PSM.SINGLE_LINE):
                api.SetPageSegMode(modo)
                texto = " ".join(api.GetUTF8Text().split())
                if texto:
                    return texto

            return ""
        finally:
            api.SetPageSegMode(tesserocr.PSM.AUTO)
            self._livres.put(api)

    def ler_opcoes(self, imagens):
        return list(self._executor.map(self.ler_opcao, imagens))

    def ler_tudo(self, pergunta, opcoes):
        """Reads the question and the options at the same time."""
        futura = self._executor.submit(self.ler, pergunta)
        lidas = self.ler_opcoes(opcoes)
        return futura.result(), lidas

    def fechar(self):
        self._executor.shutdown(wait=False)
        while not self._livres.empty():
            self._livres.get().End()

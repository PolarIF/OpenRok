import argparse
import csv
import os
import queue
import re
import shutil
import sys
import threading
import time
import tkinter as tk
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import ttk

import cv2
import numpy as np
import tesserocr
from PIL import Image, ImageEnhance, ImageGrab
from rapidfuzz import fuzz, process


# ==========================================================
# CAPTURE AREA CONFIGURATION
# ==========================================================
# Coordinates used to capture parts of the screen.
# Format: (x, y, width, height)
#
# Base resolution used in this project:
# 1920x1080 (Full HD)
# ==========================================================

tamanhos = {
    "1920x1080": {
        "Pergunta": (640, 335, 850, 120),
        "A": (623, 470, 405, 83),
        "B": (1085, 470, 405, 83),
        "C": (623, 570, 405, 83),
        "D": (1085, 570, 405, 83)
    }
}

LETRAS = ("A", "B", "C", "D")


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
# LANGUAGES
# ==========================================================
# Everything that changes between the EN and PT versions:
# OCR language, question database, interface text and prompt.
# ==========================================================

IDIOMAS = {
    "en": {
        "nome": "English",
        "ocr": "eng",
        "csv": "perguntas_respostas_en.csv",
        "textos": {
            "pergunta": "Question:",
            "resposta": "Answer:",
            "fixar": "Pin Window",
            "pesquisar": "Search",
            "pesquisando": "Searching...",
            "sem_texto": "No text detected.",
            "fonte_banco": "Source: local database",
            "fonte_ia": "Source: Gemini (saved to database)",
            "fonte_ia_nao_validada": "Source: Gemini (could not match an option, not saved)",
            "sem_chave": "Question not in database and GEMINI_API_KEY is not set.",
            "erro_ia": "Gemini error: {erro}",
        },
        "prompt": (
            "This is a multiple-choice question from the Lyceum of Wisdom event "
            "in Rise of Kingdoms (game lore and world history). The text was read "
            "with OCR and may contain small errors.\n\n"
            "Question: {pergunta}\n{opcoes}\n\n"
            "Reply with only the letter of the correct option: A, B, C or D."
        ),
    },
    "pt": {
        "nome": "Português",
        "ocr": "por",
        "csv": "perguntas_respostas_pt.csv",
        "textos": {
            "pergunta": "Pergunta:",
            "resposta": "Resposta:",
            "fixar": "Fixar Janela",
            "pesquisar": "Pesquisar",
            "pesquisando": "Pesquisando...",
            "sem_texto": "Nenhum texto detectado.",
            "fonte_banco": "Fonte: banco local",
            "fonte_ia": "Fonte: Gemini (salvo no banco)",
            "fonte_ia_nao_validada": "Fonte: Gemini (não bateu com nenhuma opção, não salvo)",
            "sem_chave": "Pergunta fora do banco e GEMINI_API_KEY não está definida.",
            "erro_ia": "Erro no Gemini: {erro}",
        },
        "prompt": (
            "Esta é uma pergunta de múltipla escolha do evento Liceu da Sabedoria "
            "do Rise of Kingdoms (história do jogo e história mundial). O texto foi "
            "lido com OCR e pode conter pequenos erros.\n\n"
            "Pergunta: {pergunta}\n{opcoes}\n\n"
            "Responda apenas com a letra da opção correta: A, B, C ou D."
        ),
    },
}


# ==========================================================
# PATHS
# ==========================================================
# The databases live in data/ next to the script, or next
# to the .exe when running from a PyInstaller build. The
# .exe carries a copy of the databases and extracts it on
# first run, so the self-feeding database keeps growing.
# ==========================================================

def pasta_base():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def caminho_csv(nome):
    caminho = pasta_base() / "data" / nome
    embutido = Path(getattr(sys, "_MEIPASS", "")) / "data" / nome
    if not caminho.exists() and embutido.exists():
        caminho.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(embutido, caminho)
    return caminho


# ==========================================================
# QUESTION DATABASE
# ==========================================================
# Questions are normalized once on load (lowercase, no
# accents, no punctuation) and matched with RapidFuzz,
# which tolerates OCR errors.
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


class BancoPerguntas:

    similaridade_limite = 90
    # OCR fragments shorter than this are too ambiguous to match
    tamanho_minimo = 15

    def __init__(self, caminho):
        self.caminho = Path(caminho)
        self.perguntas = []
        self.respostas = []
        self.normalizadas = []
        self._indice = {}

        with open(self.caminho, mode="r", encoding="utf-8", newline="") as file:
            reader = csv.reader(file)
            next(reader, None)  # header

            for row in reader:
                if len(row) >= 2:
                    self._adicionar(row[0], row[1])

    def _adicionar(self, pergunta, resposta):
        pergunta, resposta = pergunta.strip(), resposta.strip()
        normalizada = normalizar(pergunta)

        if len(normalizada) < self.tamanho_minimo or not resposta or normalizada in self._indice:
            return False

        self._indice[normalizada] = len(self.perguntas)
        self.perguntas.append(pergunta)
        self.respostas.append(resposta)
        self.normalizadas.append(normalizada)
        return True

    def __len__(self):
        return len(self.perguntas)

    def buscar(self, texto):
        """Returns (question, answer, score) or None."""
        consulta = normalizar(texto)

        if len(consulta) < self.tamanho_minimo:
            return None

        exata = self._indice.get(consulta)
        if exata is not None:
            return self.perguntas[exata], self.respostas[exata], 100.0

        candidatos = process.extract(
            consulta,
            self.normalizadas,
            scorer=fuzz.ratio,
            score_cutoff=self.similaridade_limite,
            limit=5
        )

        for candidata, similaridade, i in candidatos:
            if palavras_batem(consulta, candidata) and palavras_batem(candidata, consulta):
                return self.perguntas[i], self.respostas[i], similaridade

        return None

    def salvar(self, pergunta, resposta):
        pergunta = " ".join(pergunta.split())

        if not self._adicionar(pergunta, resposta):
            return False

        with open(self.caminho, "a", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow([pergunta, resposta.strip()])

        return True


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
    instances are created once. There is one instance per option so
    the four options can be read in parallel (tesserocr releases the
    GIL while recognizing).
    """

    def __init__(self, lang, instancias=4):
        caminho = os.environ.get("TESSDATA_PREFIX")
        extra = {"path": caminho} if caminho else {}

        self._livres = queue.Queue()
        for _ in range(instancias):
            self._livres.put(tesserocr.PyTessBaseAPI(lang=lang, **extra))

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

    def responder(self, pergunta, opcoes):
        """Returns (answer, validated). validated=True when the reply maps to an option."""
        from google.genai import types

        texto_opcoes = "\n".join(f"{letra}) {opcao}" for letra, opcao in zip(LETRAS, opcoes))

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
            return " ".join(opcoes[LETRAS.index(letra)].split()), True

        return texto, False


# ==========================================================
# SEARCH PIPELINE
# ==========================================================
# Flow:
# 1 - Capture the question and option images (one grab)
# 2 - OCR the question
# 3 - Search the local database
# 4 - If not found, OCR the options and query Gemini
# 5 - Save the new question only if Gemini picked an option
# ==========================================================

class Pesquisa:

    def __init__(self, idioma, banco=None, ocr=None, gemini=None):
        self.idioma = idioma
        self.banco = banco or BancoPerguntas(caminho_csv(IDIOMAS[idioma]["csv"]))
        self.ocr = ocr or MotorOCR(IDIOMAS[idioma]["ocr"])
        self.gemini = gemini or Gemini(idioma)

    def executar(self, areas, imagens=None):
        textos = IDIOMAS[self.idioma]["textos"]
        inicio = time.perf_counter()

        imagens = imagens or capturar_tela(areas)
        texto_pergunta = self.ocr.ler(imagens["Pergunta"])

        if not texto_pergunta:
            return {"erro": textos["sem_texto"]}

        encontrada = self.banco.buscar(texto_pergunta)

        if encontrada:
            pergunta, resposta, _ = encontrada
            return {
                "pergunta": pergunta,
                "resposta": resposta,
                "fonte": textos["fonte_banco"],
                "tempo": time.perf_counter() - inicio
            }

        if not self.gemini.configurado:
            return {"pergunta": texto_pergunta, "erro": textos["sem_chave"]}

        opcoes = self.ocr.ler_varias([imagens[letra] for letra in LETRAS])

        try:
            resposta, validada = self.gemini.responder(texto_pergunta, opcoes)
        except Exception as erro:
            return {"pergunta": texto_pergunta, "erro": textos["erro_ia"].format(erro=erro)}

        if validada:
            self.banco.salvar(texto_pergunta, resposta)

        return {
            "pergunta": texto_pergunta,
            "resposta": resposta,
            "fonte": textos["fonte_ia"] if validada else textos["fonte_ia_nao_validada"],
            "tempo": time.perf_counter() - inicio
        }

    def fechar(self):
        self.ocr.fechar()


# ==========================================================
# MAIN APPLICATION CLASS
# ==========================================================
# The search runs in a worker thread so the window never
# freezes; results come back through a queue polled by Tk.
# ==========================================================

class OpenOCR:

    def __init__(self, root, idioma):

        self.root = root
        self.root.title("OpenRok")
        self.root.geometry("320x330")

        self.resultados = queue.Queue()
        self.pesquisa = None
        self.ocupado = False

        self.titulo_pergunta = tk.Label(root)
        self.titulo_pergunta.pack()

        self.pergunta_label = tk.Label(root, wraplength=280)
        self.pergunta_label.pack()

        self.titulo_resposta = tk.Label(root)
        self.titulo_resposta.pack()

        self.resposta_label = tk.Label(root, wraplength=280, font=("TkDefaultFont", 11, "bold"))
        self.resposta_label.pack()

        self.fonte_label = tk.Label(root, fg="gray40")
        self.fonte_label.pack()

        self.fixar_var = tk.BooleanVar()
        self.checkbutton = tk.Checkbutton(
            root,
            variable=self.fixar_var,
            command=self.fixar_janela
        )
        self.checkbutton.pack(pady=5)

        # --------------------------------------------------
        # Language and screen resolution selection
        # --------------------------------------------------
        self.idioma_var = tk.StringVar(value=IDIOMAS[idioma]["nome"])
        self.idioma_combo = ttk.Combobox(
            root,
            state="readonly",
            textvariable=self.idioma_var,
            values=[config["nome"] for config in IDIOMAS.values()]
        )
        self.idioma_combo.bind("<<ComboboxSelected>>", lambda _: self.trocar_idioma())
        self.idioma_combo.pack(pady=5)

        self.tamanho_tela = ttk.Combobox(root, state="readonly", values=list(tamanhos))
        self.tamanho_tela.current(0)
        self.tamanho_tela.pack(pady=5)

        self.pesquisar_botao = tk.Button(root, command=self.pesquisar)
        self.pesquisar_botao.pack(pady=10)

        self.idioma = idioma
        self.trocar_idioma(idioma)

    @property
    def textos(self):
        return IDIOMAS[self.idioma]["textos"]

    def fixar_janela(self):
        self.root.attributes('-topmost', 1 if self.fixar_var.get() else 0)

    def trocar_idioma(self, idioma=None):
        if idioma is None:
            idioma = next(k for k, v in IDIOMAS.items() if v["nome"] == self.idioma_var.get())

        if self.pesquisa and self.pesquisa.idioma == idioma:
            return

        self.idioma = idioma
        self.titulo_pergunta.config(text=self.textos["pergunta"])
        self.titulo_resposta.config(text=self.textos["resposta"])
        self.checkbutton.config(text=self.textos["fixar"])
        self.pesquisar_botao.config(text=self.textos["pesquisar"])

        # Loading Tesseract takes a moment: do it in the background too
        anterior, self.pesquisa = self.pesquisa, None
        self._rodar(lambda: ("pronto", self._carregar(idioma, anterior)))

    def _carregar(self, idioma, anterior):
        if anterior:
            anterior.fechar()
        return Pesquisa(idioma)

    def pesquisar(self):
        if self.ocupado or self.pesquisa is None:
            return

        areas = tamanhos[self.tamanho_tela.get()]
        pesquisa = self.pesquisa
        self._rodar(lambda: ("resultado", pesquisa.executar(areas)))

    def _rodar(self, tarefa):
        self.ocupado = True
        self.pesquisar_botao.config(state="disabled", text=self.textos["pesquisando"])

        def trabalho():
            try:
                self.resultados.put(tarefa())
            except Exception as erro:
                self.resultados.put(("resultado", {"erro": str(erro)}))

        threading.Thread(target=trabalho, daemon=True).start()
        self.root.after(30, self._verificar)

    def _verificar(self):
        try:
            tipo, valor = self.resultados.get_nowait()
        except queue.Empty:
            self.root.after(30, self._verificar)
            return

        self.ocupado = False
        self.pesquisar_botao.config(state="normal", text=self.textos["pesquisar"])

        if tipo == "pronto":
            self.pesquisa = valor
            return

        self.pergunta_label.config(text=valor.get("pergunta", ""))
        self.resposta_label.config(text=valor.get("resposta") or valor.get("erro", ""))

        fonte = valor.get("fonte", "")
        if "tempo" in valor:
            fonte = f"{fonte} · {valor['tempo']:.2f}s"
        self.fonte_label.config(text=fonte)


# ==========================================================
# PROGRAM INITIALIZATION
# ==========================================================

def ativar_dpi():
    # Without this, Windows display scaling (125%, 150%...) makes
    # ImageGrab capture the wrong area of the screen.
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="OpenRok - Lyceum of Wisdom helper")
    parser.add_argument("--lang", choices=list(IDIOMAS), default=os.environ.get("OPENROK_LANG", "en"))
    args = parser.parse_args()

    ativar_dpi()

    root = tk.Tk()
    OpenOCR(root, args.lang)
    root.mainloop()


if __name__ == "__main__":
    main()

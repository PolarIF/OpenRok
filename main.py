import argparse
import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from openrok.banco import BancoPerguntas
from openrok.caminhos import caminho_csv
from openrok.ia import Gemini
from openrok.idiomas import IDIOMAS, LETRAS
from openrok.ocr import MotorOCR, capturar_tela


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

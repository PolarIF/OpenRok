import tkinter as tk
from tkinter import messagebox, ttk
import cv2
import numpy as np
import csv
from PIL import ImageGrab, ImageEnhance, Image
import tesserocr  # Faster OCR than pytesseract
from rapidfuzz import fuzz
import concurrent.futures
from google import genai


# ==========================================================
# CAPTURE AREA CONFIGURATION
# ==========================================================
# Coordinates used to capture parts of the screen.
# Format: (x, y, width, height)
#
# Example:
# Question = area where the question shows up in the game
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
# GEMINI CLIENT CONFIGURATION
# ==========================================================
# Replace with your Google Gemini API key
# ==========================================================

client = genai.Client(api_key="my api key here")


# ==========================================================
# MAIN APPLICATION CLASS
# ==========================================================
class OpenOCR:

    def __init__(self, root):

        # --------------------------------------------------
        # Loads the local question/answer database
        # --------------------------------------------------
        self.perguntas_respostas = self.carregar_csv('perguntas_respostas_en.csv')

        # --------------------------------------------------
        # Main window configuration
        # --------------------------------------------------
        self.root = root
        self.root.title("OpenRok")
        self.root.geometry("300x250")

        # --------------------------------------------------
        # Question display area
        # --------------------------------------------------
        tk.Label(root, text="Question:").pack()

        self.pergunta_label = tk.Label(
            root,
            wraplength=250  # automatic line wrapping
        )
        self.pergunta_label.pack()

        # --------------------------------------------------
        # Answer display area
        # --------------------------------------------------
        tk.Label(root, text="Answer:").pack()

        self.resposta_label = tk.Label(
            root,
            wraplength=250
        )
        self.resposta_label.pack()

        # --------------------------------------------------
        # Checkbox to keep the window always on top
        # --------------------------------------------------
        self.fixar_var = tk.BooleanVar()

        self.checkbutton = tk.Checkbutton(
            root,
            text="Pin Window",
            variable=self.fixar_var,
            command=self.fixar_janela
        )
        self.checkbutton.pack(pady=10)

        # --------------------------------------------------
        # Screen resolution selection
        # --------------------------------------------------
        self.tamanho_tela = ttk.Combobox(root, state="readonly")
        self.tamanho_tela["values"] = ("1920x1080")
        self.tamanho_tela.current(0)
        self.tamanho_tela.pack(pady=10)

        # --------------------------------------------------
        # Capture areas based on the chosen resolution
        # --------------------------------------------------
        self.area_pergunta = tamanhos[self.tamanho_tela.get()]["Pergunta"]

        self.letra_A = tamanhos[self.tamanho_tela.get()]["A"]
        self.letra_B = tamanhos[self.tamanho_tela.get()]["B"]
        self.letra_C = tamanhos[self.tamanho_tela.get()]["C"]
        self.letra_D = tamanhos[self.tamanho_tela.get()]["D"]

        # --------------------------------------------------
        # Main button that starts reading the question
        # --------------------------------------------------
        self.pesquisar_botao = tk.Button(
            root,
            text="Search",
            command=lambda: self.responde(self.area_pergunta)
        )
        self.pesquisar_botao.pack(pady=10)


    # ======================================================
    # PIN / UNPIN WINDOW ON TOP
    # ======================================================
    def fixar_janela(self):
        self.root.attributes('-topmost', 1 if self.fixar_var.get() else 0)


    # ======================================================
    # MAIN BOT FUNCTION
    # ======================================================
    # Flow:
    # 1 - Capture the question image
    # 2 - Run OCR
    # 3 - Search the local database
    # 4 - If not found, query Gemini
    # 5 - Save the new question to the CSV
    # ======================================================
    def responde(self, area):

        imagem_processada_pergunta = self.processar_imagem(area)
        texto_extraido_pergunta = self.extrair_texto(imagem_processada_pergunta)

        self.pergunta_label.config(text=texto_extraido_pergunta or "No text detected")

        if texto_extraido_pergunta:

            pergunta, resposta = self.buscar_pergunta_resposta(texto_extraido_pergunta)

            if pergunta != "Not found" and resposta != "Not found":

                self.pergunta_label.config(text=pergunta)
                self.resposta_label.config(text=resposta)

            else:

                # --------------------------------------------------
                # If not found in the database, capture the options
                # --------------------------------------------------

                imagem_processada_letra_A = self.processar_imagem(self.letra_A)
                texto_extraido_letra_A = self.extrair_texto(imagem_processada_letra_A)

                imagem_processada_letra_B = self.processar_imagem(self.letra_B)
                texto_extraido_letra_B = self.extrair_texto(imagem_processada_letra_B)

                imagem_processada_letra_C = self.processar_imagem(self.letra_C)
                texto_extraido_letra_C = self.extrair_texto(imagem_processada_letra_C)

                imagem_processada_letra_D = self.processar_imagem(self.letra_D)
                texto_extraido_letra_D = self.extrair_texto(imagem_processada_letra_D)

                resposta_gemini = self.gemini(
                    texto_extraido_pergunta,
                    texto_extraido_letra_A,
                    texto_extraido_letra_B,
                    texto_extraido_letra_C,
                    texto_extraido_letra_D
                )

                print(f"Gemini answer: {resposta_gemini}")

                self.resposta_label.config(text=resposta_gemini)
                self.pergunta_label.config(text=texto_extraido_pergunta)

                self.salvar_no_csv(texto_extraido_pergunta, resposta_gemini)

        else:
            messagebox.showinfo("Error", "No text detected.")


    # ======================================================
    # IMAGE PROCESSING
    # ======================================================
    # Steps applied:
    # - Screen capture
    # - Grayscale conversion
    # - Resize
    # - Contrast boost
    # - Blur to remove noise
    # - Binarization
    # ======================================================
    def processar_imagem(self, area):

        x1, y1, w, h = area
        x2, y2 = x1 + w, y1 + h

        imagem = ImageGrab.grab(bbox=(x1, y1, x2, y2)).convert('L')

        imagem = imagem.resize(
            (imagem.width * 2, imagem.height * 2),
            Image.LANCZOS
        )

        imagem = ImageEnhance.Contrast(imagem).enhance(2.0)

        imagem_np = np.array(imagem)

        imagem_np = cv2.GaussianBlur(imagem_np, (3, 3), 0)

        _, imagem_processada = cv2.threshold(
            imagem_np,
            150,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        return Image.fromarray(imagem_processada)


    # ======================================================
    # OCR (TEXT EXTRACTION)
    # ======================================================
    def extrair_texto(self, imagem):

        with tesserocr.PyTessBaseAPI(lang='eng') as api:

            api.SetImage(imagem)

            texto = api.GetUTF8Text()

            print(f"Extracted text: {texto}")

            return texto.strip()


    # ======================================================
    # SEARCH THE QUESTION IN THE LOCAL DATABASE
    # ======================================================
    # Uses RapidFuzz for approximate matching
    # to cope with OCR errors.
    # ======================================================
    def buscar_pergunta_resposta(self, texto_extraido):

        import unicodedata

        similaridade_limite = 95

        def normalizar(texto):
            texto = texto.lower().strip().replace("\n", " ")
            texto = ''.join(
                c for c in unicodedata.normalize('NFD', texto)
                if unicodedata.category(c) != 'Mn'
            )
            return texto

        texto_normalizado = normalizar(texto_extraido)

        melhor_pergunta = "Not found"
        melhor_resposta = "Not found"
        melhor_similaridade = similaridade_limite

        candidatos = [
            (pergunta, resposta)
            for pergunta, resposta in self.perguntas_respostas
            if abs(len(pergunta) - len(texto_extraido)) <= 5
            or any(palavra in texto_normalizado for palavra in normalizar(pergunta).split())
        ]

        with concurrent.futures.ThreadPoolExecutor() as executor:

            futures = {
                executor.submit(
                    fuzz.partial_ratio,
                    texto_normalizado,
                    normalizar(pergunta)
                ): (pergunta, resposta)

                for pergunta, resposta in candidatos
            }

            for future in concurrent.futures.as_completed(futures):

                similaridade = future.result()
                pergunta, resposta_csv = futures[future]

                if similaridade > melhor_similaridade:
                    melhor_similaridade = similaridade
                    melhor_pergunta = pergunta
                    melhor_resposta = resposta_csv

            if melhor_similaridade >= similaridade_limite:
                return melhor_pergunta, melhor_resposta

        return melhor_pergunta, melhor_resposta


    # ======================================================
    # LOAD CSV DATABASE
    # ======================================================
    def carregar_csv(self, caminho_csv):

        perguntas_respostas = []

        with open(caminho_csv, mode='r', encoding='utf-8') as file:

            reader = csv.reader(file)

            for row in reader:
                perguntas_respostas.append((row[0], row[1]))

        return perguntas_respostas


    # ======================================================
    # GEMINI QUERY
    # ======================================================
    def gemini(self, pergunta, letra_A, letra_B, letra_C, letra_D):

        response = client.models.generate_content(

            model="gemini-3.1-flash-lite-preview",

            contents=f"Give me only the answer among the four options, "
                     f"question: {pergunta} "
                     f"{letra_A} "
                     f"{letra_B} "
                     f"{letra_C} "
                     f"{letra_D}"
        )

        return response.text


    # ======================================================
    # SAVE NEW QUESTIONS TO THE DATABASE
    # ======================================================
    def salvar_no_csv(self, pergunta, resposta):

        if (pergunta, resposta) not in self.perguntas_respostas:

            with open(
                "perguntas_respostas_en.csv",
                "a",
                newline="",
                encoding="utf-8"
            ) as file:

                writer = csv.writer(file)
                writer.writerow([pergunta, resposta])

            self.perguntas_respostas.append((pergunta, resposta))


# ==========================================================
# PROGRAM INITIALIZATION
# ==========================================================
root = tk.Tk()
app = OpenOCR(root)
root.mainloop()

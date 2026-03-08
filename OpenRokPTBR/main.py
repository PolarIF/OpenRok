import tkinter as tk
from tkinter import messagebox, ttk
import cv2
import numpy as np
import csv
from PIL import ImageGrab, ImageEnhance, Image
import tesserocr  # OCR mais rápido que pytesseract
from rapidfuzz import fuzz
import concurrent.futures
from google import genai


# ==========================================================
# CONFIGURAÇÃO DE ÁREAS DE CAPTURA
# ==========================================================
# Coordenadas usadas para capturar partes da tela
# Formato: (x, y, largura, altura)
#
# Exemplo:
# Pergunta = área onde aparece a pergunta no jogo
#
# Resolução base usada no projeto:
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
# CONFIGURAÇÃO DO CLIENTE GEMINI
# ==========================================================
# Substitua pela sua chave de API do Google Gemini
# ==========================================================

client = genai.Client(api_key="minha api key aqui")


# ==========================================================
# CLASSE PRINCIPAL DO APLICATIVO
# ==========================================================
class OpenOCR:

    def __init__(self, root):

        # --------------------------------------------------
        # Carrega o banco local de perguntas e respostas
        # --------------------------------------------------
        self.perguntas_respostas = self.carregar_csv('perguntas_respostas.csv')

        # --------------------------------------------------
        # Configuração da janela principal
        # --------------------------------------------------
        self.root = root
        self.root.title("OpenRok")
        self.root.geometry("300x250")

        # --------------------------------------------------
        # Área de exibição da pergunta
        # --------------------------------------------------
        tk.Label(root, text="Pergunta:").pack()

        self.pergunta_label = tk.Label(
            root,
            wraplength=250  # quebra automática de linha
        )
        self.pergunta_label.pack()

        # --------------------------------------------------
        # Área de exibição da resposta
        # --------------------------------------------------
        tk.Label(root, text="Resposta:").pack()

        self.resposta_label = tk.Label(
            root,
            wraplength=250
        )
        self.resposta_label.pack()

        # --------------------------------------------------
        # Checkbox para manter janela sempre no topo
        # --------------------------------------------------
        self.fixar_var = tk.BooleanVar()

        self.checkbutton = tk.Checkbutton(
            root,
            text="Fixar Janela",
            variable=self.fixar_var,
            command=self.fixar_janela
        )
        self.checkbutton.pack(pady=10)

        # --------------------------------------------------
        # Seleção de resolução da tela
        # --------------------------------------------------
        self.tamanho_tela = ttk.Combobox(root, state="readonly")
        self.tamanho_tela["values"] = ("1920x1080")
        self.tamanho_tela.current(0)
        self.tamanho_tela.pack(pady=10)

        # --------------------------------------------------
        # Áreas de captura baseadas na resolução escolhida
        # --------------------------------------------------
        self.area_pergunta = tamanhos[self.tamanho_tela.get()]["Pergunta"]

        self.letra_A = tamanhos[self.tamanho_tela.get()]["A"]
        self.letra_B = tamanhos[self.tamanho_tela.get()]["B"]
        self.letra_C = tamanhos[self.tamanho_tela.get()]["C"]
        self.letra_D = tamanhos[self.tamanho_tela.get()]["D"]

        # --------------------------------------------------
        # Botão principal para iniciar leitura da pergunta
        # --------------------------------------------------
        self.pesquisar_botao = tk.Button(
            root,
            text="Pesquisar",
            command=lambda: self.responde(self.area_pergunta)
        )
        self.pesquisar_botao.pack(pady=10)


    # ======================================================
    # FIXAR OU DESFIXAR JANELA NO TOPO
    # ======================================================
    def fixar_janela(self):
        self.root.attributes('-topmost', 1 if self.fixar_var.get() else 0)


    # ======================================================
    # FUNÇÃO PRINCIPAL DO BOT
    # ======================================================
    # Fluxo:
    # 1 - Captura imagem da pergunta
    # 2 - Executa OCR
    # 3 - Busca no banco local
    # 4 - Caso não encontre, consulta o Gemini
    # 5 - Salva nova pergunta no CSV
    # ======================================================
    def responde(self, area):

        imagem_processada_pergunta = self.processar_imagem(area)
        texto_extraido_pergunta = self.extrair_texto(imagem_processada_pergunta)

        self.pergunta_label.config(text=texto_extraido_pergunta or "Nenhum texto detectado")

        if texto_extraido_pergunta:

            pergunta, resposta = self.buscar_pergunta_resposta(texto_extraido_pergunta)

            if pergunta != "Não encontrado" and resposta != "Não encontrado":

                self.pergunta_label.config(text=pergunta)
                self.resposta_label.config(text=resposta)

            else:

                # --------------------------------------------------
                # Caso não encontre no banco, captura alternativas
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

            print(f"Resposta Gemini: {resposta_gemini}")

            self.resposta_label.config(text=resposta_gemini)
            self.pergunta_label.config(text=texto_extraido_pergunta)

            self.salvar_no_csv(texto_extraido_pergunta, resposta_gemini)

        else:
            messagebox.showinfo("Erro", "Nenhum texto detectado.")


    # ======================================================
    # PROCESSAMENTO DA IMAGEM
    # ======================================================
    # Passos aplicados:
    # - Captura da tela
    # - Conversão para escala de cinza
    # - Redimensionamento
    # - Aumento de contraste
    # - Blur para remover ruído
    # - Binarização
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
    # OCR (EXTRAÇÃO DE TEXTO)
    # ======================================================
    def extrair_texto(self, imagem):

        with tesserocr.PyTessBaseAPI(lang='por') as api:

            api.SetImage(imagem)

            texto = api.GetUTF8Text()

            print(f"Texto extraído: {texto}")

            return texto.strip()


    # ======================================================
    # BUSCA DE PERGUNTA NO BANCO LOCAL
    # ======================================================
    # Usa RapidFuzz para comparação aproximada
    # para lidar com erros do OCR.
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

        melhor_pergunta = "Não encontrado"
        melhor_resposta = "Não encontrado"
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
    # CARREGAR BANCO CSV
    # ======================================================
    def carregar_csv(self, caminho_csv):

        perguntas_respostas = []

        with open(caminho_csv, mode='r', encoding='utf-8') as file:

            reader = csv.reader(file)

            for row in reader:
                perguntas_respostas.append((row[0], row[1]))

        return perguntas_respostas


    # ======================================================
    # CONSULTA AO GEMINI
    # ======================================================
    def gemini(self, pergunta, letra_A, letra_B, letra_C, letra_D):

        response = client.models.generate_content(

            model="gemini-3.1-flash-lite-preview",

            contents=f"Me de somente a resposta dentro das quatro opções, "
                     f"pergunta: {pergunta} "
                     f"{letra_A} "
                     f"{letra_B} "
                     f"{letra_C} "
                     f"{letra_D}"
        )

        return response.text


    # ======================================================
    # SALVAR NOVAS PERGUNTAS NO BANCO
    # ======================================================
    def salvar_no_csv(self, pergunta, resposta):

        if (pergunta, resposta) not in self.perguntas_respostas:

            with open(
                "perguntas_respostas.csv",
                "a",
                newline="",
                encoding="utf-8"
            ) as file:

                writer = csv.writer(file)
                writer.writerow([pergunta, resposta])

            self.perguntas_respostas.append((pergunta, resposta))


# ==========================================================
# INICIALIZAÇÃO DO PROGRAMA
# ==========================================================
root = tk.Tk()
app = OpenOCR(root)
root.mainloop()
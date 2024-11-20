import tkinter as tk
from tkinter import messagebox
from line_profiler import profile
import cv2
import numpy as np
import csv
from PIL import ImageGrab, ImageEnhance, Image
from selecao_area import selecionar_area
import re
import unicodedata
from rapidfuzz import fuzz
import concurrent.futures
import tesserocr  # Substitui o pytesseract para OCR

# Classe principal do aplicativo
class OpenOCR:
    def __init__(self, root):
        # Carrega o arquivo CSV de perguntas e respostas e guarda em cache
        self.perguntas_respostas = self.carregar_csv('perguntas_respostas_en.csv')

        # Configuração inicial da janela principal
        self.root = root
        self.root.title("QuizRok")  # Título da janela
        self.root.geometry("300x250")  # Tamanho da janela
        self.area_selecionada = None  # Área de captura inicial

        # Rótulo para exibir a pergunta capturada
        tk.Label(root, text="question:").pack()
        self.pergunta_label = tk.Label(root, wraplength=250)  # Configura quebra de linha
        self.pergunta_label.pack()

        # Rótulo para exibir a resposta encontrada
        tk.Label(root, text="response:").pack()
        self.resposta_label = tk.Label(root, wraplength=250)  # Configura quebra de linha
        self.resposta_label.pack()

        # Botão para capturar a área selecionada
        self.btn_capturar = tk.Button(root, text="search", command=self.capturar_area)
        self.btn_capturar.pack(pady=5)

        # Botão para permitir a seleção de uma área na tela
        self.btn_selecionar_area = tk.Button(root, text="select area", command=self.selecionar_area)
        self.btn_selecionar_area.pack(pady=5)

        # Checkbox para fixar a janela no topo
        self.fixar_var = tk.BooleanVar()
        self.checkbutton = tk.Checkbutton(root, text="Pin Window", variable=self.fixar_var, command=self.fixar_janela)
        self.checkbutton.pack(pady=10)

    # Método para fixar ou desfixar a janela no topo
    def fixar_janela(self):
        self.root.attributes('-topmost', 1 if self.fixar_var.get() else 0)

    # Método para selecionar a área de captura na tela
    def selecionar_area(self):
        self.area_selecionada = selecionar_area()

    # Método principal para capturar e processar a área selecionada
    @profile
    def capturar_area(self):
        if not self.area_selecionada:
            messagebox.showwarning("Error", "Select an area first.")
            return

        # Processa a imagem capturada
        imagem_processada = self.processar_imagem(self.area_selecionada)
        texto_extraido = self.extrair_texto(imagem_processada)

        # Exibe o texto extraído na interface
        self.pergunta_label.config(text=texto_extraido or "No text detected")
        if texto_extraido:
            # Busca a pergunta e resposta correspondente
            pergunta, resposta = self.buscar_pergunta_resposta(texto_extraido)
            self.pergunta_label.config(text=pergunta)
            self.resposta_label.config(text=resposta)
        else:
            messagebox.showinfo("Error", "No text detected.")

    # Processa a imagem capturada (converte para escala de cinza, aumenta contraste, etc.)
    @profile
    def processar_imagem(self, area):
        x1, y1, x2, y2 = area  # Coordenadas da área selecionada
        imagem = ImageGrab.grab(bbox=(x1, y1, x2, y2)).convert('L')  # Captura e converte para escala de cinza
        imagem = imagem.resize((imagem.width * 2, imagem.height * 2), Image.LANCZOS)  # Redimensiona para melhorar OCR
        imagem = ImageEnhance.Contrast(imagem).enhance(2.0)  # Aumenta o contraste
        imagem_np = np.array(imagem)
        imagem_np = cv2.GaussianBlur(imagem_np, (3, 3), 0)  # Aplica desfoque para suavizar ruídos
        _, imagem_processada = cv2.threshold(imagem_np, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)  # Binarização
        return Image.fromarray(imagem_processada)

    # Extrai texto da imagem usando Tesseract OCR
    @profile
    def extrair_texto(self, imagem):
        with tesserocr.PyTessBaseAPI(lang='eng') as api:  # Define idioma como ingles
            api.SetImage(imagem)
            texto = api.GetUTF8Text()  # Obtém o texto extraído
            return texto.strip()

    # Normaliza o texto (remove acentos, converte para minúsculas, etc.)
    @profile
    def padronizar_texto(self, texto):
        texto = texto.lower()
        texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
        return re.sub(r'[^\w\s]', '', texto)  # Remove caracteres especiais

    # Busca a melhor correspondência de pergunta e resposta no CSV
    @profile
    def buscar_pergunta_resposta(self, texto_extraido):
        texto_padronizado = self.padronizar_texto(texto_extraido)
        similaridade_limite = 50  # Pontuação mínima para considerar uma correspondência válida
        limite_minimo = 20  # Limite inferior para perguntas aproximadas

        melhor_pergunta, melhor_resposta = "No matching questions found", "No answers founda"
        melhor_similaridade = similaridade_limite

        # Filtra candidatos que têm potencial de correspondência
        candidatos = [
            (pergunta, resposta)
            for pergunta, resposta in self.perguntas_respostas
            if abs(len(pergunta) - len(texto_padronizado)) <= 20
            or any(palavra in texto_padronizado for palavra in pergunta.split())
        ]

        # Paraleliza a avaliação de similaridade para melhorar o desempenho
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(fuzz.partial_ratio, texto_padronizado, pergunta_padronizada): (pergunta_padronizada, resposta)
                for pergunta_padronizada, resposta in candidatos
            }

            # Verifica os resultados das tarefas paralelas
            for future in concurrent.futures.as_completed(futures):
                similaridade = future.result()
                pergunta_padronizada, resposta_csv = futures[future]

                # Atualiza a melhor correspondência encontrada
                if similaridade > melhor_similaridade:
                    melhor_similaridade = similaridade
                    melhor_pergunta = pergunta_padronizada
                    melhor_resposta = resposta_csv

            # Retorna a melhor correspondência se atingir o limite mínimo
            if melhor_similaridade >= similaridade_limite:
                return melhor_pergunta, melhor_resposta

            similaridade_limite -= 5  # Reduz limite para buscar aproximações menores

        return melhor_pergunta, melhor_resposta

    # Carrega o CSV com perguntas e respostas e padroniza os textos
    @profile
    def carregar_csv(self, caminho_csv):
        perguntas_respostas = []
        with open(caminho_csv, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                pergunta_padronizada = self.padronizar_texto(row[0])
                perguntas_respostas.append((pergunta_padronizada, row[1]))
        return perguntas_respostas

# Inicializa a interface gráfica
root = tk.Tk()
app = OpenOCR(root)
root.mainloop()

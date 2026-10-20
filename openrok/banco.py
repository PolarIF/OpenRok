import csv
from pathlib import Path

from rapidfuzz import fuzz, process

from openrok.texto import normalizar, palavras_batem


# ==========================================================
# QUESTION DATABASE
# ==========================================================
# Questions are normalized once on load (lowercase, no
# accents, no punctuation) and matched with RapidFuzz,
# which tolerates OCR errors.
# ==========================================================

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

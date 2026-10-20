from openrok.banco import BancoPerguntas
from openrok.tela import LIMITE_MESMA, distancia


# ==========================================================
# EVERYTHING THE APP KNOWS FOR ONE LANGUAGE
# ==========================================================
# Base CSV + what the user learned (the user wins), plus the
# image fingerprints of questions confirmed by the game.
# ==========================================================

class Conhecimento:

    def __init__(self, idioma, csv, armazem):
        self.idioma = idioma
        self.armazem = armazem
        self.banco = BancoPerguntas(csv)

        for pergunta, resposta in armazem.perguntas(idioma):
            self.banco.definir(pergunta, resposta)

        self._hashes = armazem.hashes(idioma)

    def __len__(self):
        return len(self.banco)

    def buscar(self, texto):
        return self.banco.buscar(texto)

    def por_hash(self, hash_img):
        melhor = min(self._hashes, key=lambda item: distancia(item[0], hash_img), default=None)

        if melhor is None or distancia(melhor[0], hash_img) > LIMITE_MESMA:
            return None

        return melhor[1], melhor[2]

    def aprender(self, texto_pergunta, resposta, hash_img):
        encontrada = self.buscar(texto_pergunta)

        if encontrada:
            pergunta, anterior, _ = encontrada
        else:
            pergunta, anterior = " ".join(texto_pergunta.split()), None

        tipo = self.armazem.aprender(self.idioma, pergunta, resposta, anterior, hash_img)
        self.banco.definir(pergunta, resposta)

        if hash_img is not None:
            self._hashes = [item for item in self._hashes if item[0] != hash_img]
            self._hashes.append((hash_img, pergunta, resposta))

        return tipo

import csv

from openrok.banco import BancoPerguntas, mapear_resposta
from openrok.idiomas import LETRAS
from openrok.texto import normalizar
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

    def aprender(self, texto_pergunta, opcoes, letra, hash_img):
        """Learns the option the game showed in green. Returns nova/confirmada/corrigida.

        The OCR text of the green option may be noisy ("1905 4"): when the
        known answer already points to that option, it is a confirmation and
        the known text is kept.
        """
        lida = " ".join(opcoes[LETRAS.index(letra)].split())
        encontrada = self.buscar(texto_pergunta)

        if encontrada:
            pergunta, anterior, _ = encontrada
            resposta = anterior if mapear_resposta(anterior, opcoes) == letra else lida
        else:
            pergunta, anterior, resposta = " ".join(texto_pergunta.split()), None, lida

        tipo = self.armazem.aprender(self.idioma, pergunta, resposta, anterior, hash_img)
        self.banco.definir(pergunta, resposta)

        if hash_img is not None:
            self._hashes = [item for item in self._hashes if item[0] != hash_img]
            self._hashes.append((hash_img, pergunta, resposta))

        return tipo

    # ------------------------------------------------------
    # Database tab
    # ------------------------------------------------------
    def listar(self, busca="", filtro="todas"):
        do_usuario = {normalizar(item["pergunta"]): item for item in self.armazem.listar(self.idioma)}
        alvo = normalizar(busca)
        itens = []

        for pergunta, resposta in zip(self.banco.perguntas, self.banco.respostas):
            item = do_usuario.get(normalizar(pergunta)) or {
                "pergunta": pergunta, "resposta": resposta, "origem": "base", "confirmada": False,
                "corrigida_de": None, "atualizada_em": None,
            }

            if alvo and alvo not in normalizar(item["pergunta"]) and alvo not in normalizar(item["resposta"]):
                continue
            if filtro == "aprendidas" and item["origem"] != "jogo":
                continue
            if filtro == "corrigidas" and item["corrigida_de"] is None:
                continue
            if filtro == "nao_confirmadas" and item["confirmada"]:
                continue

            itens.append(item)

        return itens

    def desfazer_ultima_correcao(self):
        desfeita = self.armazem.desfazer_ultima_correcao(self.idioma)
        if desfeita:
            self.banco.definir(*desfeita)
        return desfeita

    def exportar_confirmadas(self, caminho):
        confirmadas = [(i["pergunta"], i["resposta"]) for i in self.armazem.listar(self.idioma) if i["confirmada"]]
        cabecalho = ["pergunta", "resposta"] if self.idioma == "pt" else ["question", "response"]

        with open(caminho, "w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(cabecalho)
            writer.writerows(confirmadas)

        return len(confirmadas)

    def importar_csv(self, caminho):
        """Imports question,answer rows; skips headers, blank and malformed lines."""
        validas = []

        with open(caminho, encoding="utf-8-sig", newline="") as file:
            for linha in csv.reader(file):
                if len(linha) < 2:
                    continue
                pergunta, resposta = " ".join(linha[0].split()), " ".join(linha[1].split())
                if len(normalizar(pergunta)) >= self.banco.tamanho_minimo and resposta:
                    validas.append((pergunta, resposta))

        importadas = self.armazem.importar(self.idioma, validas)
        for pergunta, resposta in importadas:
            self.banco.definir(pergunta, resposta)

        return len(importadas)

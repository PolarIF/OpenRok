import threading
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Protocol

from openrok.banco import mapear_resposta
from openrok.eventos import (Aprendido, ErroIA, JogoEncontrado, JogoPerdido, OutraTela, PerguntaDetectada, Respondida,
                             Resultado, SemResposta, Sugestao)
from openrok.geometria import areas_para
from openrok.idiomas import LETRAS
from openrok.tela import LIMITE_MESMA, EstadoOpcao, distancia, eh_tela_de_perguntas, estado_opcao, impressao


# ==========================================================
# THE WATCHER
# ==========================================================
# Looks at the game ~15 times per second and, without any
# click, detects a new question, suggests the answer and
# learns the official one when the game shows it in green.
#
#   AGUARDANDO_JOGO -> OUTRA_TELA -> PERGUNTA -> RESPONDIDA -> RESULTADO
#
# A new question is a question-area fingerprint that differs
# from the current one and holds still for 2 cycles (ignores
# the transition animation).
# ==========================================================


class Estado(Enum):
    AGUARDANDO_JOGO = "aguardando_jogo"
    OUTRA_TELA = "outra_tela"
    PERGUNTA = "pergunta"
    RESPONDIDA = "respondida"
    RESULTADO = "resultado"


class IA(Protocol):

    def escolher(self, pergunta: str, opcoes: list) -> str | None:
        """Letter of the right option, or None."""


class Vigia:

    def __init__(self, janela, captura, ocr, conhecimento, emitir, ia=None):
        self.janela = janela
        self.captura = captura
        self.ocr = ocr
        self.conhecimento = conhecimento
        self.emitir = emitir
        self.ia = ia

        self.estado = Estado.AGUARDANDO_JOGO
        self._esquecer_pergunta()
        self._numero = 0  # identifies the current question for late AI replies

        self._executor_ia = ThreadPoolExecutor(max_workers=1)
        self._parar = threading.Event()
        self._thread = None

    def _esquecer_pergunta(self):
        self._atual = None
        self._candidato = None
        self._texto = None
        self._opcoes = None
        self._resultado_visto = False
        self._eventos_pergunta = []  # replayed when the game comes back to this question
        self._reemitir = False

    def _emitir_da_pergunta(self, evento):
        self._eventos_pergunta.append(evento)
        self.emitir(evento)

    def _mudar(self, estado, evento=None):
        if self.estado != estado and evento is not None:
            self.emitir(evento)
        self.estado = estado

    # ------------------------------------------------------
    # One cycle
    # ------------------------------------------------------
    def ciclo(self):
        inicio = time.perf_counter()

        # Leaving the game (alt-tab, a popup) keeps the current question in
        # memory: coming back to it redraws the suggestion without OCR or AI,
        # and the green result can still be learned
        cliente = self.janela.localizar()
        if cliente is None or not self.janela.ativa():
            self._reemitir = True
            self._mudar(Estado.AGUARDANDO_JOGO, JogoPerdido())
            return

        if self.estado == Estado.AGUARDANDO_JOGO:
            self.emitir(JogoEncontrado())
            self.estado = None  # game found, screen not identified yet

        areas = areas_para(cliente)
        envoltorio = areas.envoltorio()
        imagem = self.captura.capturar(envoltorio)

        if not eh_tela_de_perguntas([s.recortar(imagem, envoltorio) for s in areas.sondas]):
            self._reemitir = True
            self._mudar(Estado.OUTRA_TELA, OutraTela())
            return

        estados = {
            letra: estado_opcao(areas.interior(letra).recortar(imagem, envoltorio))
            for letra in LETRAS
        }

        verdes = [letra for letra, e in estados.items() if e == EstadoOpcao.VERDE]
        if verdes:
            self._resultado(verdes[0], estados)
            return

        if EstadoOpcao.COLORIDA in estados.values():
            self._mudar(Estado.RESPONDIDA, Respondida())
            return

        h = impressao(areas.pergunta.recortar(imagem, envoltorio))

        if self._atual is not None and distancia(h, self._atual) <= LIMITE_MESMA:
            if self._reemitir:
                self._reemitir = False
                self.estado = Estado.PERGUNTA
                for evento in self._eventos_pergunta:
                    self.emitir(evento)
            return

        if self._candidato is not None and distancia(h, self._candidato) <= LIMITE_MESMA:
            self._resolver(h, areas, imagem, envoltorio, inicio)
        else:
            self._candidato = h

    # ------------------------------------------------------
    # The game showed the official answer
    # ------------------------------------------------------
    def _resultado(self, correta, estados):
        self.estado = Estado.RESULTADO

        if self._resultado_visto or self._atual is None:
            return
        self._resultado_visto = True

        vermelhas = [letra for letra, e in estados.items() if e == EstadoOpcao.VERMELHA]
        self.emitir(Resultado(correta, vermelhas[0] if vermelhas else correta))

        if not self._opcoes or not self._opcoes[LETRAS.index(correta)]:
            return

        try:
            tipo = self.conhecimento.aprender(self._texto, self._opcoes, correta, self._atual)
        except Exception:
            # Learning is a bonus: a locked or full database must never stop the watcher
            return

        self.emitir(Aprendido(tipo))

    # ------------------------------------------------------
    # A new question held still: find its answer
    # ------------------------------------------------------
    def _resolver(self, h, areas, imagem, envoltorio, inicio):
        self._esquecer_pergunta()
        self._atual = h
        self._numero += 1
        self.estado = Estado.PERGUNTA

        imagens_opcoes = [areas.texto_opcao(letra).recortar(imagem, envoltorio) for letra in LETRAS]

        do_cache = self.conhecimento.por_hash(h)
        if do_cache:
            pergunta, resposta = do_cache
            opcoes = self.ocr.ler_opcoes(imagens_opcoes)
            texto, origem = pergunta, "cache"

            # A cached answer that is not among the options means the
            # fingerprint matched the wrong question: read it properly
            if mapear_resposta(resposta, opcoes) is None:
                do_cache = None

        if not do_cache:
            texto, opcoes = self.ocr.ler_tudo(areas.pergunta.recortar(imagem, envoltorio), imagens_opcoes)
            encontrada = self.conhecimento.buscar(texto)
            pergunta = encontrada[0] if encontrada else " ".join(texto.split())
            resposta = encontrada[1] if encontrada else None
            origem = "banco"

        self._texto, self._opcoes = texto, opcoes
        self._emitir_da_pergunta(PerguntaDetectada(pergunta, opcoes))

        letra = mapear_resposta(resposta, opcoes) if resposta else None
        if letra:
            self._emitir_da_pergunta(Sugestao(letra, origem, (time.perf_counter() - inicio) * 1000))
            return

        if self.ia is not None:
            self._perguntar_ia(pergunta, opcoes, inicio)
        elif resposta:
            self._emitir_da_pergunta(SemResposta(f"resposta do banco não está entre as opções: {resposta}"))
        else:
            self._emitir_da_pergunta(SemResposta("fora do banco"))

    def _perguntar_ia(self, pergunta, opcoes, inicio):
        numero = self._numero

        def trabalho():
            try:
                letra = self.ia.escolher(pergunta, opcoes)
            except Exception as erro:
                self.emitir(ErroIA(str(erro)))
                return

            # The question may have changed while the AI was thinking
            if letra in LETRAS and numero == self._numero:
                self._emitir_da_pergunta(Sugestao(letra, "ia", (time.perf_counter() - inicio) * 1000))

        self._executor_ia.submit(trabalho)

    # ------------------------------------------------------
    # Background thread
    # ------------------------------------------------------
    def iniciar(self, hz=15.0):
        self._parar.clear()

        def laco():
            intervalo = 1 / hz
            while not self._parar.is_set():
                inicio = time.perf_counter()
                try:
                    self.ciclo()
                except Exception:
                    pass  # a bad frame must not kill the watcher
                self._parar.wait(max(0.0, intervalo - (time.perf_counter() - inicio)))

        self._thread = threading.Thread(target=laco, daemon=True)
        self._thread.start()

    def parar(self):
        self._parar.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._executor_ia.shutdown(wait=True)

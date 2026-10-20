"""Replays the real game video through the watcher.

    python -m bench.replay

Prints the events and how long each suggestion took, measured
from the cycle that confirmed the question to the suggestion.
"""
import statistics
from functools import lru_cache

from openrok.armazem import Armazem
from openrok.caminhos import pasta_base
from openrok.captura import CapturaDeQuadro
from openrok.conhecimento import Conhecimento
from openrok.eventos import Sugestao
from openrok.geometria import Ret
from openrok.janela_jogo import JanelaFixa
from openrok.ocr import MotorOCR
from openrok.vigia import Vigia
from tests.fixtures import quadros_video


@lru_cache(maxsize=1)
def _ocr():
    return MotorOCR("por")


def rodar(armazem, fps=15):
    eventos = []
    captura = CapturaDeQuadro()
    conhecimento = Conhecimento("pt", pasta_base() / "data" / "perguntas_respostas_pt.csv", armazem)
    vigia = Vigia(JanelaFixa(Ret(0, 0, 1920, 1080)), captura, _ocr(), conhecimento, eventos.append)

    for _, quadro in quadros_video(fps):
        captura.quadro = quadro
        vigia.ciclo()

    vigia.parar()
    return eventos


def resumo(eventos, titulo):
    print(f"\n== {titulo}")
    for evento in eventos:
        print("  ", evento)

    por_origem = {}
    for s in eventos:
        if isinstance(s, Sugestao):
            por_origem.setdefault(s.origem, []).append(s.tempo_ms)

    for origem, tempos in por_origem.items():
        print(f"   {origem}: mediana {statistics.median(tempos):.0f} ms, máximo {max(tempos):.0f} ms")


if __name__ == "__main__":
    armazem = Armazem(":memory:")
    resumo(rodar(armazem), "primeira vez (banco)")
    resumo(rodar(armazem), "segunda vez (cache de imagem)")

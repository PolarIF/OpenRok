from openrok.armazem import Armazem
from openrok.eventos import Aprendido, PerguntaDetectada, Resultado, Sugestao

from bench.replay import rodar


def do_tipo(eventos, tipo):
    return [e for e in eventos if isinstance(e, tipo)]


def test_replay_primeira_vez():
    eventos = rodar(Armazem(":memory:"))

    perguntas = do_tipo(eventos, PerguntaDetectada)
    assert len(perguntas) == 3
    for pergunta, trecho in zip(perguntas, ["Saladino", "pandas", "shakespeariana"]):
        assert trecho in pergunta.texto

    sugestoes = do_tipo(eventos, Sugestao)
    assert [(s.letra, s.origem) for s in sugestoes] == [("D", "banco"), ("D", "banco"), ("B", "banco")]
    assert all(s.tempo_ms <= 250 for s in sugestoes), [s.tempo_ms for s in sugestoes]

    assert do_tipo(eventos, Resultado) == [Resultado("D", "C"), Resultado("D", "D")]
    assert do_tipo(eventos, Aprendido) == [Aprendido("confirmada"), Aprendido("confirmada")]


def test_replay_segunda_vez_usa_cache():
    armazem = Armazem(":memory:")
    rodar(armazem)
    sugestoes = do_tipo(rodar(armazem), Sugestao)

    assert [(s.letra, s.origem) for s in sugestoes[:2]] == [("D", "cache"), ("D", "cache")]
    assert all(s.tempo_ms <= 150 for s in sugestoes[:2]), [s.tempo_ms for s in sugestoes[:2]]

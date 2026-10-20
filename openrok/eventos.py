from dataclasses import dataclass


# ==========================================================
# EVENTS PUBLISHED BY THE WATCHER
# ==========================================================
# The interface (and the tests) only see these: the watcher
# knows nothing about Qt.
# ==========================================================

@dataclass(frozen=True)
class JogoEncontrado:
    pass


@dataclass(frozen=True)
class JogoPerdido:
    pass


@dataclass(frozen=True)
class OutraTela:
    pass


@dataclass(frozen=True)
class Respondida:
    pass


@dataclass(frozen=True)
class PerguntaDetectada:
    texto: str
    opcoes: list


@dataclass(frozen=True)
class Sugestao:
    letra: str
    origem: str  # "cache" | "banco" | "ia"
    tempo_ms: float


@dataclass(frozen=True)
class SemResposta:
    motivo: str


@dataclass(frozen=True)
class Resultado:
    correta: str
    marcada: str


@dataclass(frozen=True)
class Aprendido:
    tipo: str  # "nova" | "confirmada" | "corrigida"


@dataclass(frozen=True)
class ErroIA:
    mensagem: str

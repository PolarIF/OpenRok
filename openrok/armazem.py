import sqlite3
import threading
from datetime import datetime, timezone

from openrok.texto import normalizar


# ==========================================================
# USER STORE (SQLITE)
# ==========================================================
# What this machine learned from the game: confirmed and
# corrected answers, the corrections log (for undo) and the
# question image fingerprints (to skip OCR next time).
# Every write is a transaction, so closing the app in the
# middle of a quiz never corrupts the file.
# ==========================================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS perguntas (
    id INTEGER PRIMARY KEY,
    idioma TEXT NOT NULL,
    pergunta TEXT NOT NULL,
    normalizada TEXT NOT NULL,
    resposta TEXT NOT NULL,
    origem TEXT NOT NULL CHECK (origem IN ('base', 'ia', 'jogo')),
    confirmada INTEGER NOT NULL DEFAULT 0,
    criada_em TEXT NOT NULL,
    atualizada_em TEXT NOT NULL,
    UNIQUE (idioma, normalizada)
);
CREATE TABLE IF NOT EXISTS correcoes (
    id INTEGER PRIMARY KEY,
    pergunta_id INTEGER NOT NULL REFERENCES perguntas(id),
    resposta_antiga TEXT NOT NULL,
    resposta_nova TEXT NOT NULL,
    em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cache_imagem (
    hash INTEGER NOT NULL,
    idioma TEXT NOT NULL,
    pergunta_id INTEGER NOT NULL REFERENCES perguntas(id),
    PRIMARY KEY (hash, idioma)
);
"""


def _agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# SQLite integers are signed 64-bit; image hashes are unsigned
def _com_sinal(h):
    return h - 2 ** 64 if h >= 2 ** 63 else h


def _sem_sinal(h):
    return h + 2 ** 64 if h < 0 else h


class Armazem:

    def __init__(self, caminho):
        self._conexao = sqlite3.connect(str(caminho), check_same_thread=False)
        self._trava = threading.Lock()
        with self._conexao:
            self._conexao.executescript(SCHEMA)

    def perguntas(self, idioma):
        with self._trava:
            linhas = self._conexao.execute(
                "SELECT pergunta, resposta FROM perguntas WHERE idioma = ? ORDER BY id", (idioma,)
            ).fetchall()
        return [tuple(linha) for linha in linhas]

    def aprender(self, idioma, pergunta, resposta, resposta_anterior, hash_img):
        """Stores an answer confirmed by the game. Returns nova/confirmada/corrigida."""
        if resposta_anterior is None:
            tipo = "nova"
        elif normalizar(resposta_anterior) == normalizar(resposta):
            tipo = "confirmada"
        else:
            tipo = "corrigida"

        agora = _agora()

        with self._trava, self._conexao:
            self._conexao.execute(
                """INSERT INTO perguntas (idioma, pergunta, normalizada, resposta, origem, confirmada, criada_em, atualizada_em)
                   VALUES (?, ?, ?, ?, 'jogo', 1, ?, ?)
                   ON CONFLICT (idioma, normalizada) DO UPDATE SET
                       resposta = excluded.resposta, origem = 'jogo', confirmada = 1,
                       atualizada_em = excluded.atualizada_em""",
                (idioma, pergunta, normalizar(pergunta), resposta, agora, agora)
            )
            pergunta_id = self._conexao.execute(
                "SELECT id FROM perguntas WHERE idioma = ? AND normalizada = ?", (idioma, normalizar(pergunta))
            ).fetchone()[0]

            if tipo == "corrigida":
                self._conexao.execute(
                    "INSERT INTO correcoes (pergunta_id, resposta_antiga, resposta_nova, em) VALUES (?, ?, ?, ?)",
                    (pergunta_id, resposta_anterior, resposta, agora)
                )

            if hash_img is not None:
                self._conexao.execute(
                    "INSERT OR REPLACE INTO cache_imagem (hash, idioma, pergunta_id) VALUES (?, ?, ?)",
                    (_com_sinal(hash_img), idioma, pergunta_id)
                )

        return tipo

    def desfazer_ultima_correcao(self, idioma):
        with self._trava, self._conexao:
            linha = self._conexao.execute(
                """SELECT c.id, p.id, p.pergunta, c.resposta_antiga FROM correcoes c
                   JOIN perguntas p ON p.id = c.pergunta_id
                   WHERE p.idioma = ? ORDER BY c.id DESC LIMIT 1""",
                (idioma,)
            ).fetchone()

            if linha is None:
                return None

            correcao_id, pergunta_id, pergunta, antiga = linha
            self._conexao.execute(
                "UPDATE perguntas SET resposta = ?, atualizada_em = ? WHERE id = ?", (antiga, _agora(), pergunta_id)
            )
            self._conexao.execute("DELETE FROM correcoes WHERE id = ?", (correcao_id,))

        return pergunta, antiga

    def hashes(self, idioma):
        with self._trava:
            linhas = self._conexao.execute(
                """SELECT c.hash, p.pergunta, p.resposta FROM cache_imagem c
                   JOIN perguntas p ON p.id = c.pergunta_id WHERE c.idioma = ?""",
                (idioma,)
            ).fetchall()
        return [(_sem_sinal(h), pergunta, resposta) for h, pergunta, resposta in linhas]

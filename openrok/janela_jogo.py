from typing import Protocol

from openrok.geometria import Ret


# ==========================================================
# THE GAME WINDOW
# ==========================================================
# Platform implementations (Windows, X11) come with the
# interface milestones; JanelaFixa covers a fixed area.
# ==========================================================

class JanelaJogo(Protocol):

    def localizar(self) -> Ret | None:
        """Client rectangle in screen coordinates, or None."""

    def ativa(self) -> bool:
        """True when the game is the foreground window."""


class JanelaFixa:

    def __init__(self, ret):
        self.ret = ret

    def localizar(self):
        return self.ret

    def ativa(self):
        return True

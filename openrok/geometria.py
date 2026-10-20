from dataclasses import dataclass


# ==========================================================
# SCREEN AREAS
# ==========================================================
# Measured on real 1920x1080 screenshots of the Lyceum of
# Wisdom question screen. Other window sizes are scaled
# from this reference, keeping it centered.
# ==========================================================

REFERENCIA = (1920, 1080)


@dataclass(frozen=True)
class Ret:
    x: int
    y: int
    w: int
    h: int

    def recortar(self, imagem, origem):
        """Crops this area from an image whose top-left corner is at origem."""
        x, y = self.x - origem.x, self.y - origem.y
        return imagem.crop((x, y, x + self.w, y + self.h))


PERGUNTA_REF = Ret(640, 335, 850, 120)

CAIXAS_REF = {
    "A": Ret(592, 471, 438, 80),
    "B": Ret(1053, 471, 438, 80),
    "C": Ret(592, 571, 438, 80),
    "D": Ret(1053, 571, 438, 80),
}

# Plain parchment between the option boxes: tells the
# question screen apart from anything else
SONDAS_REF = (Ret(1034, 475, 16, 70), Ret(1034, 575, 16, 70), Ret(640, 555, 800, 12))

SELO_REF = 36  # width of the letter badge; the option text starts after it
INSET_COR_REF = 8  # inner margin where the box color is measured


@dataclass(frozen=True)
class Areas:
    pergunta: Ret
    caixas: dict
    sondas: tuple
    selo: int
    inset: int

    def texto_opcao(self, letra):
        c = self.caixas[letra]
        return Ret(c.x + self.selo, c.y + 2, c.w - self.selo - 4, c.h - 4)

    def interior(self, letra):
        c = self.caixas[letra]
        return Ret(c.x + self.inset, c.y + self.inset, c.w - 2 * self.inset, c.h - 2 * self.inset)

    def envoltorio(self):
        todas = [self.pergunta, *self.caixas.values(), *self.sondas]
        x1 = min(r.x for r in todas)
        y1 = min(r.y for r in todas)
        x2 = max(r.x + r.w for r in todas)
        y2 = max(r.y + r.h for r in todas)
        return Ret(x1, y1, x2 - x1, y2 - y1)


ENVOLTORIO_REF = Ret(592, 335, 899, 316)


def areas_para(cliente, calibracao=None):
    """Areas in screen coordinates for a game client rectangle.

    calibracao = [fx, fy, fw, fh]: where the user marked the question and
    options area, as fractions of the client. The reference layout is then
    stretched onto it (x and y scaled independently).
    """
    if calibracao:
        fx, fy, fw, fh = calibracao
        sx = fw * cliente.w / ENVOLTORIO_REF.w
        sy = fh * cliente.h / ENVOLTORIO_REF.h
        dx = cliente.x + fx * cliente.w - ENVOLTORIO_REF.x * sx
        dy = cliente.y + fy * cliente.h - ENVOLTORIO_REF.y * sy
    else:
        sx = sy = min(cliente.w / REFERENCIA[0], cliente.h / REFERENCIA[1])
        dx = cliente.x + (cliente.w - REFERENCIA[0] * sx) / 2
        dy = cliente.y + (cliente.h - REFERENCIA[1] * sy) / 2

    def escalar(r):
        return Ret(round(r.x * sx + dx), round(r.y * sy + dy), round(r.w * sx), round(r.h * sy))

    s = min(sx, sy)
    return Areas(
        pergunta=escalar(PERGUNTA_REF),
        caixas={letra: escalar(r) for letra, r in CAIXAS_REF.items()},
        sondas=tuple(escalar(r) for r in SONDAS_REF),
        selo=max(1, round(SELO_REF * s)),
        inset=max(1, round(INSET_COR_REF * s)),
    )

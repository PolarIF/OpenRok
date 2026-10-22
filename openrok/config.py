import json
import locale
import os
from dataclasses import asdict, dataclass, field, fields


# ==========================================================
# USER SETTINGS
# ==========================================================
# Saved as config.json in the user data folder. A missing,
# corrupted or old file never stops the app: anything that
# can't be read falls back to the default.
# ==========================================================

def _idioma_do_sistema():
    try:
        codigo = locale.getlocale()[0] or ""
    except ValueError:
        codigo = ""
    return "pt" if codigo.lower().startswith("pt") else "en"


TAMANHO_LISTAS = {"calibracao": 4, "painel_posicao": 2}


@dataclass
class Config:
    idioma: str = field(default_factory=_idioma_do_sistema)
    marcar_no_jogo: bool = True
    usar_ia: bool = True
    opacidade: float = 1.0
    fixar_no_topo: bool = False
    iniciar_com_sistema: bool = False
    calibracao: list | None = None  # [fx, fy, fw, fh] of the question+options area, fractions of the game window
    painel_no_jogo: bool = True
    painel_posicao: list | None = None  # [fx, fy]: center-top of the pill, fractions of the game window
    ia_provedor: str = "gemini"  # id of a preset in openrok.ia.PRESETS
    ia_modelo: str = ""  # "" = the preset's default model
    ia_base_url: str = ""  # only for the "personalizado" preset; the key lives in the vault

    @classmethod
    def carregar(cls, caminho):
        config = cls()

        try:
            dados = json.loads(open(caminho, encoding="utf-8").read())
        except (OSError, ValueError):
            return config

        if not isinstance(dados, dict):
            return config

        for campo in fields(cls):
            if campo.name not in dados:
                continue
            valor, padrao = dados[campo.name], getattr(config, campo.name)
            if campo.name in TAMANHO_LISTAS:
                if valor is None or (isinstance(valor, list) and len(valor) == TAMANHO_LISTAS[campo.name]
                                     and all(isinstance(v, (int, float)) for v in valor)):
                    setattr(config, campo.name, valor)
            elif isinstance(padrao, bool):
                if isinstance(valor, bool):
                    setattr(config, campo.name, valor)
            elif isinstance(padrao, float):
                if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                    setattr(config, campo.name, float(valor))
            elif isinstance(valor, type(padrao)):
                setattr(config, campo.name, valor)

        return config

    def salvar(self, caminho):
        temporario = f"{caminho}.tmp"
        with open(temporario, "w", encoding="utf-8") as file:
            json.dump(asdict(self), file, ensure_ascii=False, indent=2)
        os.replace(temporario, caminho)

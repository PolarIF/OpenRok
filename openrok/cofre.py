import keyring


# ==========================================================
# API KEY VAULT
# ==========================================================
# Keys go to the system vault (Windows Credential Manager,
# Secret Service / KWallet on Linux), never to config.json.
# A machine without a working vault still runs: the key then
# lives in memory until the app closes.
# ==========================================================

SERVICO = "OpenRok"


class CofreMemoria:

    disponivel = True

    def __init__(self):
        self._chaves = {}

    def ler(self, provedor):
        return self._chaves.get(provedor)

    def gravar(self, provedor, chave):
        if chave:
            self._chaves[provedor] = chave
        else:
            self._chaves.pop(provedor, None)


class Cofre:

    def __init__(self):
        self.disponivel = True
        self._memoria = CofreMemoria()
        self._lidos = set()  # each provider is read from the vault once: it may block to unlock

    def ler(self, provedor):
        if self.disponivel and provedor not in self._lidos:
            try:
                self._memoria.gravar(provedor, keyring.get_password(SERVICO, provedor))
                self._lidos.add(provedor)
            except Exception:
                self.disponivel = False
        return self._memoria.ler(provedor)

    def gravar(self, provedor, chave):
        self._memoria.gravar(provedor, chave)
        self._lidos.add(provedor)
        if not self.disponivel:
            return

        try:
            if chave:
                keyring.set_password(SERVICO, provedor, chave)
            elif keyring.get_password(SERVICO, provedor) is not None:
                keyring.delete_password(SERVICO, provedor)
        except Exception:
            self.disponivel = False

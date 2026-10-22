import keyring
import keyring.backend
import keyring.errors
import pytest

from openrok.cofre import Cofre, CofreMemoria


class CofreFalso(keyring.backend.KeyringBackend):
    priority = 1

    def __init__(self):
        super().__init__()
        self.dados = {}

    def get_password(self, servico, usuario):
        return self.dados.get((servico, usuario))

    def set_password(self, servico, usuario, senha):
        self.dados[(servico, usuario)] = senha

    def delete_password(self, servico, usuario):
        if (servico, usuario) not in self.dados:
            raise keyring.errors.PasswordDeleteError(usuario)
        del self.dados[(servico, usuario)]


class CofreQuebrado(keyring.backend.KeyringBackend):
    priority = 1

    def get_password(self, servico, usuario):
        raise keyring.errors.KeyringError("sem cofre")

    def set_password(self, servico, usuario, senha):
        raise keyring.errors.KeyringError("sem cofre")

    def delete_password(self, servico, usuario):
        raise keyring.errors.KeyringError("sem cofre")


@pytest.fixture
def backend():
    original = keyring.get_keyring()

    def usar(novo):
        keyring.set_keyring(novo)
        return novo

    yield usar
    keyring.set_keyring(original)


def test_ida_e_volta_no_keyring(backend):
    falso = backend(CofreFalso())
    cofre = Cofre()

    cofre.gravar("groq", "k")

    assert cofre.ler("groq") == "k"
    assert falso.dados[("OpenRok", "groq")] == "k"
    assert cofre.disponivel is True


def test_gravar_vazio_apaga(backend):
    backend(CofreFalso())
    cofre = Cofre()
    cofre.gravar("groq", "k")

    cofre.gravar("groq", "")
    cofre.gravar("openai", "")  # nothing saved: still no error

    assert cofre.ler("groq") is None


def test_keyring_quebrado_usa_memoria(backend):
    backend(CofreQuebrado())
    cofre = Cofre()

    cofre.gravar("groq", "k")

    assert cofre.ler("groq") == "k"
    assert cofre.disponivel is False


def test_cofre_memoria():
    cofre = CofreMemoria()

    cofre.gravar("groq", "k")
    assert cofre.ler("groq") == "k" and cofre.disponivel is True

    cofre.gravar("groq", "")
    assert cofre.ler("groq") is None


def test_le_o_keyring_uma_vez_por_provedor(backend):
    falso = backend(CofreFalso())
    falso.dados[("OpenRok", "groq")] = "k"
    leituras = []
    original = falso.get_password
    falso.get_password = lambda servico, usuario: leituras.append(usuario) or original(servico, usuario)
    cofre = Cofre()

    assert cofre.ler("groq") == "k" and cofre.ler("groq") == "k"
    cofre.gravar("groq", "nova")

    assert cofre.ler("groq") == "nova"
    assert leituras == ["groq"]

import pytest

from openrok.banco import mapear_resposta


@pytest.mark.parametrize("resposta, opcoes, esperado", [
    ("1192", ["1286", "1360", "1083", "1192"], "D"),
    ("2", ["2", "1", "4", "3"], "A"),
    ("Noite de Reis", ["Rei Lear", "Naite de Reis", "Hamlet", "Macbeth"], "B"),
    ("Para segurar o bambu enquanto comem",
     ["Para separar comida para comer", "Para disputas territoriais", "Não desempenha nenhuma\nfunção",
      "Para segurar o bambu enquanto\ncomem"], "D"),
    ("1905", ["1915", "", "1921", "1905"], "D"),
    ("1905", ["1915 v", "", "1921", "1905 4"], "D"),  # stray OCR digit after the number
    ("Lungs", ["Heart", "Liver", "Stomach", "Kidney"], None),
    ("Cometa", ["Cometa Halley", "Cometa Faye", "", ""], None),
    ("Achilles", ["Achilles", "Hector", "Achilles", "Paris"], None),  # tie
])
def test_mapear_resposta(resposta, opcoes, esperado):
    assert mapear_resposta(resposta, opcoes) == esperado

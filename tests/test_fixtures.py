from tests.fixtures import carregar_print, quadros_video


def test_fixtures_carregam():
    imagem = carregar_print("q1_go")

    assert imagem.size == (1920, 1080)
    assert imagem.getpixel((800, 510)) != (0, 0, 0)
    assert 175 <= sum(1 for _ in quadros_video()) <= 185

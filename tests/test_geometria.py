from openrok.geometria import CAIXAS_REF, PERGUNTA_REF, SONDAS_REF, Ret, areas_para


def test_referencia_1920x1080():
    areas = areas_para(Ret(0, 0, 1920, 1080))

    assert areas.pergunta == PERGUNTA_REF
    assert areas.caixas == CAIXAS_REF
    assert areas.sondas == SONDAS_REF
    assert (areas.selo, areas.inset) == (36, 8)


def test_escala_720p_com_deslocamento():
    areas = areas_para(Ret(100, 50, 1280, 720))
    assert areas.caixas["A"] == Ret(100 + 395, 50 + 314, 292, 53)


def test_ultrawide_centraliza():
    areas = areas_para(Ret(0, 0, 2560, 1080))
    assert areas.caixas["A"].x == 912


def test_envoltorio():
    assert areas_para(Ret(0, 0, 1920, 1080)).envoltorio() == Ret(592, 335, 899, 316)


def test_texto_opcao_e_interior():
    areas = areas_para(Ret(0, 0, 1920, 1080))

    assert areas.texto_opcao("B") == Ret(1089, 473, 398, 76)
    assert areas.interior("A") == Ret(600, 479, 422, 64)


def test_recortar_relativo_a_origem():
    from PIL import Image

    imagem = Image.new("RGB", (100, 100))
    imagem.putpixel((15, 25), (255, 0, 0))

    recorte = Ret(110, 220, 10, 10).recortar(imagem, Ret(100, 200, 100, 100))

    assert recorte.size == (10, 10)
    assert recorte.getpixel((5, 5)) == (255, 0, 0)

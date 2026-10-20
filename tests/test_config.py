from openrok.config import Config


def test_padroes_sem_arquivo(tmp_path):
    config = Config.carregar(tmp_path / "config.json")

    assert config.idioma in ("pt", "en")
    assert (config.marcar_no_jogo, config.usar_ia, config.opacidade) == (True, True, 1.0)
    assert config.calibracao is None


def test_ida_e_volta(tmp_path):
    caminho = tmp_path / "config.json"
    config = Config(idioma="en", opacidade=0.5, calibracao=[0.1, 0.2, 0.3, 0.4])
    config.salvar(caminho)

    assert Config.carregar(caminho) == config


def test_json_corrompido_usa_padroes(tmp_path):
    caminho = tmp_path / "config.json"
    caminho.write_text("{nao é json", encoding="utf-8")

    assert Config.carregar(caminho) == Config()


def test_chaves_desconhecidas_e_faltando(tmp_path):
    caminho = tmp_path / "config.json"
    caminho.write_text('{"idioma": "en", "velha": 1}', encoding="utf-8")

    config = Config.carregar(caminho)
    assert config.idioma == "en"
    assert config.usar_ia is True


def test_valores_de_tipo_errado_usam_padrao(tmp_path):
    caminho = tmp_path / "config.json"
    caminho.write_text('{"opacidade": "muita", "marcar_no_jogo": false}', encoding="utf-8")

    config = Config.carregar(caminho)
    assert config.opacidade == 1.0
    assert config.marcar_no_jogo is False


def test_painel_padrao_e_posicao(tmp_path):
    caminho = tmp_path / "config.json"
    assert Config().painel_no_jogo is True and Config().painel_posicao is None

    caminho.write_text('{"painel_posicao": [0.3, 0.1]}', encoding="utf-8")
    assert Config.carregar(caminho).painel_posicao == [0.3, 0.1]

    caminho.write_text('{"painel_posicao": "topo"}', encoding="utf-8")
    assert Config.carregar(caminho).painel_posicao is None

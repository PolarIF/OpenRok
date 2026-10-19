# Marco 1: Motor sem interface — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para implementar este plano tarefa por tarefa. Os passos usam checkbox (`- [ ]`).

**Objetivo:** criar o pacote `openrok/` com o motor do OpenRok 2.0 (geometria, cores, OCR das opções, banco com SQLite e cache de imagem, vigia), validado por um replay do vídeo real do jogo.

**Arquitetura:**
- As peças testadas do `main.py` são movidas para módulos do pacote, sem reescrever.
- O `vigia` é uma máquina de estados sem Qt. Recebe janela, captura, OCR, conhecimento e IA por injeção e publica eventos por um callback.
- O replay alimenta o `vigia` com quadros do vídeo, usando janela e captura simuladas.
- O `main.py` (Tkinter) continua funcionando, importando do pacote, até o marco 2 substituí-lo.

**Stack:** Python 3.12, tesserocr, OpenCV, Pillow, NumPy, RapidFuzz, mss, sqlite3 (stdlib), pytest.

**Spec:** `docs/superpowers/specs/2026-10-19-openrok-2-design.md` (§4, §5, §7, §8, §14, §15 marco 1)

## Restrições globais

- Identificadores e comentários seguem o estilo atual: nomes em português e comentários em inglês, com cabeçalhos `# ===`.
- Referência de geometria: **1920×1080**. Escala `s = min(w/1920, h/1080)`, com a área de referência centralizada no cliente.
- Vigia a **15 Hz**. Pergunta nova = dHash de 64 bits com distância de Hamming **> 6**, e o mesmo hash (distância ≤ 6) em **2 ciclos seguidos**.
- Cache de imagem: casa com distância **≤ 4**.
- Estado da opção, medido no interior da caixa:
  - verde > **0,35** → VERDE;
  - vermelho > **0,35** → VERMELHA;
  - bege ≥ **0,6** → NEUTRA;
  - senão → COLORIDA (o azul do fim de semana).
- Assinatura da tela de perguntas: fração de bege ≥ **0,6** em todas as sondas.
- Mapeamento resposta → letra:
  - respostas numéricas: igualdade exata dos dígitos;
  - texto: `fuzz.ratio ≥ 85`, com um único melhor resultado.
- Nada é gravado sem o verde do jogo. Sugestão da IA nunca é gravada.
- Metas, medidas no replay da máquina de desenvolvimento:
  - **cache ≤ 150 ms**;
  - **banco ≤ 250 ms**, do ciclo que confirma a estabilidade até o evento `Sugestao`.
- O SQLite do usuário fica em `%APPDATA%\OpenRok\openrok.db` (Windows) ou em `$XDG_DATA_HOME/OpenRok/openrok.db`, com padrão `~/.local/share/OpenRok/openrok.db`.

## Foco da revisão

1. **Jogo fica inativo no meio da pergunta e volta para a mesma pergunta:** o vigia emite `JogoPerdido` e, ao voltar, emite `JogoEncontrado` e de novo `PerguntaDetectada`/`Sugestao`, para o overlay redesenhar. Não aprende nada em duplicidade. Teste na Tarefa 7.
2. **Resposta da IA chega depois que a pergunta mudou:** é descartada, sem `Sugestao`. Teste na Tarefa 7.
3. **SQLite falha ao gravar** (disco cheio, arquivo bloqueado): o vigia emite `Resultado`, não emite `Aprendido` e continua rodando. Teste na Tarefa 7.
4. **Texto da opção verde vazio no OCR** (baú de recompensa por cima, por exemplo): não aprende e não quebra. Teste na Tarefa 7.
5. **Ruído de compressão faz o hash da mesma pergunta oscilar:** nenhuma `PerguntaDetectada` duplicada. O replay exige exatamente 3. Teste na Tarefa 8.

---

### Tarefa 1: Pacote `openrok/` com as peças atuais e tessdata embutido

**Arquivos:**
- Criar:
  - `openrok/__init__.py` (vazio)
  - `openrok/texto.py`: `normalizar`, `palavras_batem`
  - `openrok/idiomas.py`: `IDIOMAS`, `LETRAS`
  - `openrok/caminhos.py`
  - `openrok/banco.py`: `BancoPerguntas`
  - `openrok/ocr.py`: `preprocessar`, `MotorOCR`, `capturar_tela`
  - `openrok/ia.py`: `extrair_letra`, `Gemini`, `MODELO_GEMINI`
  - `openrok/tessdata/eng.traineddata`, `openrok/tessdata/por.traineddata`
  - `tests/conftest.py`
- Modificar:
  - `main.py`: fica só com `tamanhos`, `Pesquisa`, a classe Tk `OpenOCR`, `ativar_dpi` e `main`, importando o resto do pacote.
  - `tests/test_main.py`: imports.
  - `main.spec`: inclui `('openrok/tessdata', 'openrok/tessdata')` em `datas`.

**Interfaces:**
- Produz:
  - `openrok.texto.normalizar(texto: str) -> str` e `palavras_batem(origem: str, destino: str, minimo: int = 60) -> bool`;
  - `openrok.banco.BancoPerguntas` (API atual);
  - `openrok.ocr.MotorOCR(lang: str, instancias: int = 5)`;
  - `openrok.caminhos.pasta_base() -> Path`, `caminho_csv(nome: str) -> Path`, `pasta_dados() -> Path` (cria a pasta), `pasta_tessdata() -> str` (termina em `/`).

- [ ] **Passo 1:** baixar os modelos `tessdata_fast` para `openrok/tessdata/`:
  ```bash
  for l in eng por; do curl -sSL -o openrok/tessdata/$l.traineddata https://github.com/tesseract-ocr/tessdata_fast/raw/main/$l.traineddata; done
  ```
- [ ] **Passo 2:** mover o código do `main.py` para os módulos acima, sem mudar o comportamento.
  - `MotorOCR` passa a usar `path=os.environ.get("TESSDATA_PREFIX") or pasta_tessdata()`.
  - O padrão de `instancias` passa a ser **5** (pergunta + 4 opções em paralelo).
  - `pasta_tessdata()` resolve `sys._MEIPASS/openrok/tessdata/` quando o app está empacotado, e `openrok/tessdata/` ao lado do pacote fora dele.
  - `pasta_dados()` resolve `%APPDATA%/OpenRok` no Windows e `$XDG_DATA_HOME/OpenRok` (padrão `~/.local/share/OpenRok`) nos outros sistemas.
- [ ] **Passo 3:** criar `tests/conftest.py`, que insere a raiz do repositório no `sys.path`. Remover o `sys.path.insert` de `tests/test_main.py` e trocar os imports para `openrok.*` (`Pesquisa` continua vindo de `main`).
- [ ] **Passo 4:** rodar `python -m pytest -q`. Esperado: **28 passed**, sem `TESSDATA_PREFIX` definido.
- [ ] **Passo 5:** rodar `python -c "import main; from openrok.ocr import MotorOCR; MotorOCR('por').fechar()"`. Esperado: sem erro.
- [ ] **Passo 6:** commit `Extrai o motor para o pacote openrok e embute o tessdata`.

### Tarefa 2: Fixtures reais

**Arquivos:**
- Criar:
  - `tests/fixtures/q1_go.png`, `q4_einstein.png`, `q5_nobel.png`, `q6_cometa.png`
  - `tests/fixtures/simulado_0-12s.mp4`
  - `tests/fixtures/__init__.py`
  - `tests/test_fixtures.py`

**Interfaces:**
- Produz, em `tests/fixtures/__init__.py`:
  - `RECORTE = (560, 330)`, o canto superior esquerdo do recorte;
  - `carregar_print(nome: str) -> PIL.Image.Image`, que devolve uma imagem **1920×1080 RGB** com o recorte colado em `RECORTE` sobre fundo preto;
  - `quadros_video(fps: int = 15) -> Iterator[tuple[float, PIL.Image.Image]]`, com o tempo em segundos e um quadro RGB 1920×1080 amostrado a `fps`.

- [ ] **Passo 1:** recortar os prints de `fotos e videos/` na região x 560–1520, y 330–670, sem perda:

  | Print | Arquivo |
  |---|---|
  | `183931` | `q1_go` |
  | `184057` | `q4_einstein` |
  | `184209` | `q5_nobel` |
  | `184228` | `q6_cometa` |

- [ ] **Passo 2:** cortar o vídeo em 0–12 s, reencodando para o corte ser exato:
  ```bash
  ffmpeg -i "fotos e videos/Gravação_de_tela_20261019_184249.mp4" -t 12 -an -c:v libx264 -crf 20 tests/fixtures/simulado_0-12s.mp4
  ```
- [ ] **Passo 3:** escrever o teste `test_fixtures_carregam`. Ele afirma que `carregar_print("q1_go").size == (1920, 1080)`, que o pixel (800, 510) não é preto e que `quadros_video()` gera entre 175 e 185 quadros.
- [ ] **Passo 4:** rodar `python -m pytest tests/test_fixtures.py -q`. Esperado: PASS.
- [ ] **Passo 5:** commit `Adiciona prints e vídeo do jogo como fixtures de teste`.

### Tarefa 3: Geometria

**Arquivos:**
- Criar: `openrok/geometria.py`, `tests/test_geometria.py`

**Interfaces:**
- Produz:
  ```python
  @dataclass(frozen=True)
  class Ret:
      x: int; y: int; w: int; h: int
      def recortar(self, imagem: Image.Image, origem: "Ret") -> Image.Image  # imagem cujo canto é (origem.x, origem.y)

  PERGUNTA_REF = Ret(640, 335, 850, 120)
  CAIXAS_REF = {"A": Ret(592, 471, 438, 80), "B": Ret(1053, 471, 438, 80),
                "C": Ret(592, 571, 438, 80), "D": Ret(1053, 571, 438, 80)}
  SONDAS_REF = (Ret(1034, 475, 16, 70), Ret(1034, 575, 16, 70), Ret(640, 555, 800, 12))
  SELO_REF = 36      # largura do selo da letra; o texto da opção começa depois dele
  INSET_COR_REF = 8  # margem interna onde a cor é medida

  @dataclass(frozen=True)
  class Areas:
      pergunta: Ret; caixas: dict[str, Ret]; sondas: tuple[Ret, ...]; selo: int; inset: int
      def texto_opcao(self, letra: str) -> Ret   # Ret(x+selo, y+2, w-selo-4, h-4)
      def interior(self, letra: str) -> Ret      # caixa reduzida em `inset` de cada lado
      def envoltorio(self) -> Ret                # menor Ret que contém pergunta, caixas e sondas

  def areas_para(cliente: Ret) -> Areas   # coordenadas absolutas de tela
  ```

- [ ] **Passo 1:** escrever os testes.
  - `areas_para(Ret(0, 0, 1920, 1080))` devolve exatamente as constantes de referência.
  - `areas_para(Ret(100, 50, 1280, 720)).caixas["A"] == Ret(100 + 395, 50 + 314, 292, 53)`, com arredondamento por `round`.
  - Para o cliente `Ret(0, 0, 2560, 1080)` (21:9), `s = 1,0` e um deslocamento horizontal de 320: `caixas["A"].x == 912`.
  - `envoltorio()` em 1920×1080 é `Ret(592, 335, 899, 316)`.
  - `texto_opcao("B")` em 1920×1080 é `Ret(1089, 473, 398, 76)`.
- [ ] **Passo 2:** rodar `python -m pytest tests/test_geometria.py -q`. Esperado: FAIL, porque o módulo ainda não existe.
- [ ] **Passo 3:** implementar. Cada `Ret` escala com `round(x*s + dx)`, onde `dx = cliente.x + (cliente.w - 1920*s)/2` e `dy` é calculado da mesma forma. `selo` e `inset` escalam com `max(1, round(v*s))`.
- [ ] **Passo 4:** rodar os testes de novo. Esperado: PASS.
- [ ] **Passo 5:** commit `Adiciona geometria proporcional à janela do jogo`.

### Tarefa 4: Leitura da tela (cores, assinatura e hash)

**Arquivos:**
- Criar: `openrok/tela.py`, `tests/test_tela.py`

**Interfaces:**
- Consome: `Areas`, `Ret` (Tarefa 3) e `carregar_print` (Tarefa 2).
- Produz:
  ```python
  class EstadoOpcao(Enum): NEUTRA, VERDE, VERMELHA, COLORIDA
  def fracoes(imagem: Image.Image) -> tuple[float, float, float]   # (bege, verde, vermelho)
  def estado_opcao(imagem: Image.Image) -> EstadoOpcao
  def eh_tela_de_perguntas(sondas: list[Image.Image]) -> bool
  def dhash(imagem: Image.Image) -> int   # 64 bits
  def distancia(a: int, b: int) -> int    # Hamming
  ```
  Faixas HSV do OpenCV, medidas nos prints:

  | Cor | H | S | V |
  |---|---|---|---|
  | bege | 10–22 | 105–165 | 165–230 |
  | verde | 50–75 | ≥ 140 | ≥ 100 |
  | vermelho | ≤ 6 ou ≥ 174 | ≥ 170 | ≥ 100 |

  `dhash`: escala de cinza, redimensiona para 9×8, um bit por comparação entre vizinhos horizontais.

- [ ] **Passo 1:** escrever os testes, parametrizados pelas fixtures, recortando `areas.interior(letra)` de `carregar_print(...)` com `areas = areas_para(Ret(0, 0, 1920, 1080))`.

  | Print | A | B | C | D |
  |---|---|---|---|---|
  | `q1_go` | NEUTRA | NEUTRA | NEUTRA | NEUTRA |
  | `q4_einstein` | VERMELHA | NEUTRA | NEUTRA | VERDE |
  | `q5_nobel` | VERDE (baú por cima) | NEUTRA | NEUTRA | NEUTRA |
  | `q6_cometa` | VERDE | NEUTRA | NEUTRA | NEUTRA |

  E também:
  - `test_estado_colorido`: uma imagem sólida azul `(40, 110, 230)` dá COLORIDA.
  - `test_assinatura`: `eh_tela_de_perguntas` é `True` nos 4 prints e `False` numa imagem cinza-escuro `(30, 30, 35)` de 1920×1080.
  - `test_dhash_estavel`: a distância entre o `dhash` da pergunta de `q1_go` e a mesma imagem salva em JPEG com qualidade 70 e recarregada é ≤ 4. A distância entre as perguntas de `q1_go` e `q4_einstein` é > 6.
- [ ] **Passo 2:** rodar `python -m pytest tests/test_tela.py -q`. Esperado: FAIL.
- [ ] **Passo 3:** implementar com `cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2HSV)` e máscaras booleanas. A ordem de decisão em `estado_opcao` é verde, vermelho, bege e, por último, colorida.
- [ ] **Passo 4:** rodar os testes. Esperado: PASS.
- [ ] **Passo 5:** commit `Adiciona leitura de estado das opções por cor e hash da pergunta`.

### Tarefa 5: OCR das opções e mapeamento resposta → letra

**Arquivos:**
- Modificar: `openrok/ocr.py`, `openrok/banco.py`
- Criar: `tests/test_ocr_opcoes.py`, `tests/test_mapear.py`

**Interfaces:**
- Produz:
  - `MotorOCR.ler_opcao(imagem: Image.Image) -> str`: primeiro `PSM.SINGLE_BLOCK` (6); se vier vazio, `PSM.SINGLE_LINE` (7). Devolve o texto com os espaços normalizados. Restaura o PSM `AUTO` da instância antes de devolvê-la ao pool.
  - `MotorOCR.ler_opcoes(imagens: list[Image.Image]) -> list[str]`: paralelo. Substitui `ler_varias`; atualizar o `main.py`.
  - `MotorOCR.ler_tudo(pergunta: Image.Image, opcoes: list[Image.Image]) -> tuple[str, list[str]]`: as 5 leituras em paralelo.
  - `openrok.banco.mapear_resposta(resposta: str, opcoes: list[str]) -> str | None` (letra).
  - Uma opção com texto vazio é tratada como eliminada (Lampejo de Insight) ou ilegível, e fica fora do mapeamento e da IA.

- [ ] **Passo 1:** escrever `test_ocr_opcoes`, parametrizado. Para cada print, lê `areas.texto_opcao(l)` com `MotorOCR("por")` e compara `normalizar(lido)` com o esperado. Pode haver sujeira depois do texto, então o critério é que o esperado normalizado seja prefixo do lido normalizado.

  | Print | Opções esperadas |
  |---|---|
  | `q1_go` | `["2", "1", "4", "3"]` |
  | `q4_einstein` | `["1915", "1879", "1921", "1905"]` |
  | `q5_nobel` | `["marie curie", "bertha von suttner", "aung san suu kyi", "pearl s buck"]` |
  | `q6_cometa` | `["cometa halley", "cometa faye", "cometa brorsen", "cometa biela"]` |

  Mais um teste com o quadro de 1,0 s do vídeo, que deve dar `["1286", "1360", "1083", "1192"]`.
- [ ] **Passo 2:** escrever `test_mapear`.
  - `("1192", ["1286", "1360", "1083", "1192"])` → `"D"`
  - `("2", ["2", "1", "4", "3"])` → `"A"`
  - `("Noite de Reis", ["Rei Lear", "Naite de Reis", "Hamlet", "Macbeth"])` → `"B"`
  - `("Para segurar o bambu enquanto comem", [..., "Para segurar o bambu enquanto\ncomem"])` → `"D"`
  - `("1905", ["1915", "", "1921", "1905"])` → `"D"`
  - `("Lungs", ["Heart", "Liver", "Stomach", "Kidney"])` → `None`
  - `("Cometa", ["Cometa Halley", "Cometa Faye", "", ""])` → `None` (abaixo de 85)
  - empate entre duas opções idênticas → `None`
- [ ] **Passo 3:** rodar os dois testes. Esperado: FAIL.
- [ ] **Passo 4:** implementar. Se a resposta normalizada for só dígitos, compara com os dígitos de cada opção. Se não for, usa `process.extract(..., scorer=fuzz.ratio, score_cutoff=85, limit=2)` e exige um único melhor resultado.
- [ ] **Passo 5:** rodar todos os testes (`python -m pytest -q`). Esperado: PASS.
- [ ] **Passo 6:** commit `Lê opções curtas sem o selo da letra e mapeia resposta para a letra`.

### Tarefa 6: Armazém do usuário (SQLite) e `Conhecimento`

**Arquivos:**
- Criar: `openrok/armazem.py`, `openrok/conhecimento.py`, `tests/test_armazem.py`
- Modificar: `openrok/banco.py`, que ganha `BancoPerguntas.definir(pergunta: str, resposta: str) -> None` (sobrescreve ou adiciona, sem gravar CSV).

**Interfaces:**
- Produz:
  ```python
  class Armazem:
      def __init__(self, caminho: Path)   # cria o schema do spec §8; ":memory:" aceito nos testes
      def perguntas(self, idioma: str) -> list[tuple[str, str]]
      def aprender(self, idioma: str, pergunta: str, resposta: str,
                   resposta_anterior: str | None, hash_img: int | None) -> str   # "nova" | "confirmada" | "corrigida"
      def desfazer_ultima_correcao(self, idioma: str) -> tuple[str, str] | None  # (pergunta, resposta restaurada)
      def hashes(self, idioma: str) -> list[tuple[int, str, str]]                 # (hash, pergunta, resposta)

  class Conhecimento:
      def __init__(self, idioma: str, csv: Path, armazem: Armazem)
      def buscar(self, texto: str) -> tuple[str, str, float] | None
      def por_hash(self, hash_img: int) -> tuple[str, str] | None   # distância ≤ 4
      def aprender(self, texto_pergunta: str, resposta: str, hash_img: int | None) -> str
      def __len__(self) -> int
  ```
- O hash é guardado como inteiro com sinal: `h - 2**64 if h >= 2**63 else h`, convertido de volta na leitura.
- `Conhecimento.aprender`:
  - usa a pergunta canônica de `buscar(texto_pergunta)` quando houver; senão, o texto com os espaços normalizados;
  - passa a resposta anterior para o `Armazem`;
  - chama `BancoPerguntas.definir`;
  - acrescenta o hash à lista em memória.
- Na inicialização, `Conhecimento` aplica `armazem.perguntas(idioma)` por cima do CSV com `definir`, ou seja, **o usuário vence**.

- [ ] **Passo 1:** escrever os testes.
  - `test_nova_confirmada_corrigida`, sobre `Armazem(":memory:")`:
    1. a primeira chamada sem resposta anterior dá `"nova"`;
    2. a mesma resposta dá `"confirmada"`;
    3. uma resposta diferente dá `"corrigida"` e grava uma linha em `correcoes`.
  - `test_desfazer`: depois da correção, `desfazer_ultima_correcao` restaura a resposta antiga, e `perguntas()` reflete a restauração.
  - `test_hash_64_bits`: `2**64 - 1` grava e volta igual.
  - `test_conhecimento_usuario_vence` (CSV temporário + armazém):
    1. o CSV diz "impact wrench";
    2. `aprender(...)` com "Lungs" devolve `"corrigida"`;
    3. um novo `Conhecimento` sobre o mesmo armazém responde "Lungs" em `buscar`.
  - `test_por_hash`: com um hash aprendido `h`, `por_hash(h ^ 0b1011)` (distância 3) acha a pergunta e `por_hash(h ^ 0b11111)` (distância 5) não acha.
  - `test_persistencia_em_arquivo`: em `tmp_path / "openrok.db"`, os dados sobrevivem ao reabrir.
- [ ] **Passo 2:** rodar `python -m pytest tests/test_armazem.py -q`. Esperado: FAIL.
- [ ] **Passo 3:** implementar. Cada `aprender` roda numa transação (`with conexao:`), e `normalizada` vem de `openrok.texto.normalizar`.
- [ ] **Passo 4:** rodar os testes. Esperado: PASS.
- [ ] **Passo 5:** commit `Adiciona armazém SQLite do usuário com correções e cache de imagem`.

### Tarefa 7: Vigia (máquina de estados)

**Arquivos:**
- Criar: `openrok/vigia.py`, `openrok/eventos.py`, `openrok/janela_jogo.py`, `openrok/captura.py`, `tests/test_vigia.py`
- Modificar: `openrok/ia.py`, onde `Gemini` ganha `escolher(pergunta: str, opcoes: list[str]) -> str | None`, que devolve a letra ou `None`.

**Interfaces:**
- Consome: `Areas`/`areas_para` (T3), `estado_opcao`/`eh_tela_de_perguntas`/`dhash`/`distancia` (T4), `MotorOCR.ler_tudo`/`ler_opcoes` (T5), `mapear_resposta` (T5) e `Conhecimento` (T6).
- Produz:
  ```python
  # eventos.py — dataclasses frozen
  JogoEncontrado(); JogoPerdido(); OutraTela(); Respondida()
  PerguntaDetectada(texto: str, opcoes: list[str])
  Sugestao(letra: str, origem: str, tempo_ms: float)   # origem: "cache" | "banco" | "ia"
  SemResposta(motivo: str); Resultado(correta: str, marcada: str)
  Aprendido(tipo: str); ErroIA(mensagem: str)

  # janela_jogo.py
  class JanelaJogo(Protocol):
      def localizar(self) -> Ret | None   # retângulo do cliente em coordenadas de tela
      def ativa(self) -> bool
  class JanelaFixa:  # JanelaJogo sobre um Ret fixo, sempre ativa (usada pelo main.py Tk e pelos testes)

  # captura.py
  class Captura(Protocol):
      def capturar(self, ret: Ret) -> Image.Image
  class CapturaMss:  # mss.MSS().grab → PIL RGB

  # vigia.py
  class Estado(Enum): AGUARDANDO_JOGO, OUTRA_TELA, PERGUNTA, RESPONDIDA, RESULTADO
  class IA(Protocol):
      def escolher(self, pergunta: str, opcoes: list[str]) -> str | None
  class Vigia:
      def __init__(self, janela: JanelaJogo, captura: Captura, ocr: MotorOCR,
                   conhecimento: Conhecimento, emitir: Callable[[object], None], ia: IA | None = None)
      estado: Estado
      def ciclo(self) -> None              # uma iteração; síncrona, exceto a chamada à IA
      def iniciar(self, hz: float = 15.0) -> None   # thread daemon chamando ciclo()
      def parar(self) -> None
  ```

**Regras do `ciclo()`:**

1. **Janela.** `localizar()` devolveu `None` ou `ativa()` é falso → estado `AGUARDANDO_JOGO`, emite `JogoPerdido` uma vez (na transição) e **esquece a pergunta atual**. Na volta, emite `JogoEncontrado`.
2. **Captura.** Uma única captura de `areas.envoltorio()`. Os recortes usam `Ret.recortar(img, envoltorio)`.
3. **Assinatura.** Se falhar → `OUTRA_TELA`, com `OutraTela` emitido na transição. A pergunta atual também é esquecida.
4. **Estados das 4 opções:**
   - **Alguma VERDE:**
     - se ainda não processou o resultado desta pergunta, emite `Resultado(correta, marcada)`. `marcada` é a letra VERMELHA, se houver; senão, igual a `correta`.
     - Se `opcoes[correta]` não estiver vazio, chama `conhecimento.aprender(texto, opcoes[correta], hash)` e emite `Aprendido(tipo)`.
     - Qualquer exceção ao gravar é ignorada; `Resultado` já foi emitido.
     - Estado `RESULTADO`.
   - **Alguma COLORIDA, sem verde:** `RESPONDIDA`, com `Respondida` emitido na transição.
   - **Todas NEUTRA ou VERMELHA:** calcula `dhash` da pergunta.
     - Se for diferente da pergunta atual (distância > 6, ou não há pergunta atual), vira **candidato**.
     - O candidato é **confirmado** quando o ciclo seguinte tem distância ≤ 6 em relação a ele; aí resolve a pergunta.
5. **Resolver**, com `t0` marcado no ciclo da confirmação:
   1. **`por_hash(h)`:** se achar, lê só as opções (`ler_opcoes`), emite `PerguntaDetectada(pergunta_do_cache, opcoes)` e, se `mapear_resposta` der uma letra, `Sugestao(letra, "cache", ms)`.
   2. **Senão,** `ler_tudo` → `buscar` → `mapear_resposta` → `PerguntaDetectada` + `Sugestao(letra, "banco", ms)`.
   3. **Sem letra:**
      - com IA, envia `ia.escolher` para um `ThreadPoolExecutor(1)`. No retorno, só emite `Sugestao(letra, "ia", ms)` se a pergunta atual for **a mesma** (compara um contador de pergunta). Uma exceção vira `ErroIA(str(e))`.
      - sem IA, emite `SemResposta`, com o motivo `"fora do banco"` ou `"resposta do banco não está entre as opções: <resposta>"`.
   4. Estado `PERGUNTA`.

- [ ] **Passo 1:** escrever os testes com fakes.
  - **Fakes:** `JanelaFake`, com `ativa` mutável; `CapturaFake`, que recorta de um quadro atual mutável; e o `Conhecimento` real sobre o CSV PT com `Armazem(":memory:")`. O `MotorOCR("por")` real é compartilhado por fixture de módulo.
  - `test_pergunta_do_banco`: com o quadro `q1_go` em 2 ciclos, os eventos são `[JogoEncontrado, PerguntaDetectada(texto contém "Go"), Sugestao("A", "banco", _)]`.
  - `test_resultado_aprende`: `q4_einstein` mostra o resultado direto. O quadro neutro é o mesmo print com **só os pixels das máscaras verde e vermelha** dentro das caixas A e D trocados por bege `(214, 170, 120)`, preservando o texto branco. Com o quadro neutro em 2 ciclos e depois o `q4_einstein` original, sai `Resultado("D", "A")` e `Aprendido("confirmada")`, porque o CSV PT já tem 1905.
  - `test_colorida_vira_respondida`: com o quadro neutro e depois a caixa B pintada de azul `(40, 110, 230)`, sai `Respondida` e nenhum `Aprendido`.
  - `test_outra_tela`: um quadro cinza dá `OutraTela`, e nenhuma `PerguntaDetectada`.
  - `test_jogo_inativo_e_volta` (foco 1): `q1_go` resolvido; `ativa = False` → `JogoPerdido`; `ativa = True` e mais 2 ciclos → `JogoEncontrado`, `PerguntaDetectada`, `Sugestao("A", ...)` de novo.
  - `test_ia_atrasada_descartada` (foco 2): uma `IA` fake que espera um `threading.Event`, sobre uma pergunta fora do banco (quadro `q1_go` com o texto da pergunta coberto por um retângulo bege onde se escreve "Pergunta inexistente de teste qualquer" em preto). A pergunta muda para `q6_cometa` antes de liberar o evento, e nenhuma `Sugestao("ia")` é emitida.
  - `test_falha_ao_gravar` (foco 3): um `Conhecimento` cujo `aprender` lança `sqlite3.OperationalError`. `Resultado` é emitido, `Aprendido` não, e o próximo `ciclo()` roda normalmente.
  - `test_opcao_verde_vazia` (foco 4): `OCR` fake que devolve `""` para a opção D em `q4_einstein`. `Resultado` é emitido e nenhum `Aprendido`.
- [ ] **Passo 2:** rodar `python -m pytest tests/test_vigia.py -q`. Esperado: FAIL.
- [ ] **Passo 3:** implementar `eventos.py`, `janela_jogo.py` (Protocol e `JanelaFixa`), `captura.py` e `vigia.py` seguindo as regras acima, e `Gemini.escolher` usando o `extrair_letra` atual.
- [ ] **Passo 4:** rodar todos os testes. Esperado: PASS.
- [ ] **Passo 5:** commit `Adiciona o vigia: detecção automática de pergunta, sugestão e aprendizado`.

### Tarefa 8: Replay do vídeo, metas de tempo e benchmark

**Arquivos:**
- Criar: `tests/test_replay.py`, `bench/__init__.py`, `bench/replay.py`, `bench/comparar_v1.py`
- Modificar: `requirements.txt` (adiciona `mss`), `README.md` e `README.pt-BR.md` (seção "Tests" com os comandos de replay e benchmark)

**Interfaces:**
- Consome: `Vigia` e os eventos (T7), `quadros_video` (T2).
- Produz: `bench.replay.rodar(armazem: Armazem, fps: int = 15) -> list[object]`, que devolve os eventos emitidos ao passar todos os quadros por um `Vigia` com `JanelaFixa(Ret(0, 0, 1920, 1080))`, uma `CapturaFake` sobre o quadro atual e o idioma PT. Também imprime um resumo de tempos quando roda com `python -m bench.replay`.

- [ ] **Passo 1:** escrever `test_replay_primeira_vez`, com `Armazem(":memory:")`.
  - Há **exatamente 3** `PerguntaDetectada` (foco 5), com textos contendo `"Saladino"`, `"pandas"` e `"shakespeariana"`.
  - As `Sugestao` são `("D", "banco")`, `("D", "banco")` e `("B", "banco")`, todas com `tempo_ms ≤ 250`.
  - Os `Resultado` são `("D", "C")` e `("D", "D")`, nessa ordem.
  - Há dois `Aprendido("confirmada")`.
- [ ] **Passo 2:** escrever `test_replay_segunda_vez_usa_cache`. Rodar duas vezes com o mesmo armazém; na segunda, as duas primeiras `Sugestao` têm origem `"cache"` e `tempo_ms ≤ 150`.
- [ ] **Passo 3:** rodar `python -m pytest tests/test_replay.py -q`. Esperado: FAIL até `bench/replay.py` existir.
- [ ] **Passo 4:** implementar `bench/replay.py`. Migrar o benchmark do scratchpad para `bench/comparar_v1.py`: ele lê a versão antiga com `git show 4e11a457:OpenRokEN/main.py` em vez de `antes/` e importa a nova de `openrok`/`main`.
- [ ] **Passo 5:** rodar `python -m pytest -q` (todos) e `python -m bench.replay`. Esperado: tudo PASS, e o resumo impresso com mediana e máximo de `tempo_ms` por origem.
- [ ] **Passo 6:** commit `Adiciona replay do vídeo real com metas de tempo e benchmark`.

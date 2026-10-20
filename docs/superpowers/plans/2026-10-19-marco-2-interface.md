# Marco 2: Interface Qt e overlay — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para implementar este plano tarefa por tarefa. Os passos usam checkbox (`- [ ]`).

**Objetivo:** substituir o app Tkinter por uma interface PySide6 com abas (Início, Banco, Ajustes), ícone na bandeja e o overlay de contorno sobre o jogo. Tudo ligado ao vigia do marco 1, validado de ponta a ponta no Linux. O código do Windows fica escrito, mas não validado.

**Arquitetura:**
- O vigia roda na própria thread e emite eventos para uma `Ponte` (`QObject` com sinal). O Qt entrega cada evento na thread da interface.
- A janela principal e o overlay só consomem eventos e chamam `Conhecimento` e `Config`.
- A plataforma (achar a janela e capturar) é escolhida em `openrok/plataforma.py`:
  - **Linux:** X11 via XWayland, com `XGetImage` direto na janela do jogo;
  - **Windows:** Win32 via ctypes, com `mss`.

**Stack:** Python 3.12, PySide6, python-xlib (Linux), ctypes (Windows), pytest-qt.

**Spec:** `docs/superpowers/specs/2026-10-19-openrok-2-design.md` (§6, §8, §10, §11, §12 com o resultado do teste de viabilidade, §15 marco 2)

## Restrições globais

- Mesmo estilo do pacote: identificadores em português, comentários em inglês com cabeçalhos `# ===`.
- **Overlay:**
  - contorno de **4 px** (escalado), por fora da caixa, com margem de **~6 px** escalada;
  - **verde `#21E05A`** para banco ou cache, **amarelo `#FFC928`** para IA;
  - selo `✓ banco · 0,06 s` / `IA · sugestão · 1,2 s`.
- O overlay converte pixels físicos (X11/Win32) em lógicos dividindo pelo `devicePixelRatio`. No Linux, o app força `QT_QPA_PLATFORM=xcb`.
- O overlay some em `PerguntaDetectada` (até chegar a sugestão), `Respondida`, `Resultado`, `OutraTela` e `JogoPerdido`.
- **Captura:**
  - Linux: `XGetImage` na janela do jogo (achada por `_NET_CLIENT_LIST` com `WM_NAME == "Rise of Kingdoms"`). Janela ativa = `_NET_ACTIVE_WINDOW` igual ao id do jogo.
  - Windows: `EnumWindows` pelo título, `GetClientRect` + `ClientToScreen`, `GetForegroundWindow`, `mss`, e `SetWindowDisplayAffinity(hwnd, 0x11)` no overlay.
- Todo texto da interface fica em `IDIOMAS[idioma]["textos"]`, com as **mesmas chaves em `en` e `pt`**.
- Tema escuro: fundo `#15181D`, painel `#1E232A`, texto `#E8ECF1`, secundário `#8A94A3`, borda `#2C333D`, destaque `#21E05A`.
- `config.json` e `openrok.db` ficam em `pasta_dados()`.
- A IA continua sendo o `Gemini` atual via `GEMINI_API_KEY` (a aba IA é o marco 3).
- Testes de interface rodam com `QT_QPA_PLATFORM=offscreen`. Os testes de X11 rodam só quando há `DISPLAY` e o sistema é Linux; caso contrário, `skip`.

## Foco da revisão

1. **Jogo fechado com o app aberto, ou reaberto com outro id de janela:** o vigia emite `JogoPerdido` e reencontra a janela nova, sem guardar o id antigo. Teste na Tarefa 2.
2. **Troca de idioma com o vigia rodando:** o vigia antigo para (incluindo o executor da IA) antes de o novo começar, e nenhum evento do antigo chega depois da troca. Teste na Tarefa 7.
3. **`config.json` corrompido ou de uma versão antiga, com chaves faltando:** o app abre com os padrões e não quebra. Teste na Tarefa 1.
4. **Overlay em tela com escala diferente de 100%:** a geometria lógica é `round(físico / dpr)`. Teste na Tarefa 4, com dpr 1,25 e 1,5.
5. **Importar um CSV com cabeçalho diferente ou linhas vazias:** importa só as linhas válidas e informa quantas entraram. Teste na Tarefa 3.

---

### Tarefa 1: Config e áreas calibradas

**Arquivos:**
- Criar: `openrok/config.py`, `tests/test_config.py`
- Modificar: `openrok/geometria.py` (`areas_para` aceita calibração), `tests/test_geometria.py`, `tests/conftest.py` (`os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")`)

**Interfaces:**
- Produz:
  ```python
  @dataclass
  class Config:
      idioma: str = <"pt" se locale do sistema começa com "pt", senão "en">
      marcar_no_jogo: bool = True
      usar_ia: bool = True
      opacidade: float = 1.0          # 0.3–1.0
      fixar_no_topo: bool = False
      iniciar_com_sistema: bool = False
      calibracao: list[float] | None = None   # [fx, fy, fw, fh] do envoltório, frações do cliente
      @classmethod
      def carregar(cls, caminho: Path) -> "Config"   # arquivo ausente/corrompido/chaves desconhecidas → padrões
      def salvar(self, caminho: Path) -> None        # escrita atômica (arquivo .tmp + os.replace)

  def areas_para(cliente: Ret, calibracao: list[float] | None = None) -> Areas
  ```
- Com `calibracao`, o envoltório de referência `Ret(592, 335, 899, 316)` é mapeado para `Ret(cliente.x + fx*w, cliente.y + fy*h, fw*w, fh*h)`, com escalas `sx` e `sy` independentes. `selo` e `inset` escalam por `min(sx, sy)`.

- [ ] **Passo 1:** escrever os testes.
  - `test_padroes_sem_arquivo`.
  - `test_ida_e_volta`: salvar e carregar dão o mesmo resultado.
  - `test_json_corrompido_usa_padroes` (foco 3): o arquivo contém `"{nao é json"`.
  - `test_chaves_desconhecidas_e_faltando`: `{"idioma": "en", "velha": 1}` dá `idioma == "en"`, e os outros campos ficam no padrão.
  - `test_calibracao_identidade`: `areas_para(Ret(0, 0, 1920, 1080), [592/1920, 335/1080, 899/1920, 316/1080]) == areas_para(Ret(0, 0, 1920, 1080))`.
  - `test_calibracao_esticada`: com o envoltório calibrado em `Ret(0, 0, 1798, 316)` num cliente de 1920×1080, `caixas["B"].x == 2 * (1053 - 592)`.
- [ ] **Passo 2:** rodar `python -m pytest tests/test_config.py tests/test_geometria.py -q`. Esperado: FAIL.
- [ ] **Passo 3:** implementar.
- [ ] **Passo 4:** rodar de novo. Esperado: PASS.
- [ ] **Passo 5:** commit `Adiciona configuração do usuário e áreas calibradas`.

### Tarefa 2: Plataforma — janela do jogo e captura (Linux e Windows)

**Arquivos:**
- Criar: `openrok/plataforma.py`, `tests/test_plataforma.py`
- Modificar: `openrok/janela_jogo.py` (adiciona `JanelaX11`, `JanelaWindows`), `openrok/captura.py` (adiciona `CapturaX11`)

**Interfaces:**
- Produz:
  ```python
  TITULO_JOGO = "Rise of Kingdoms"
  class JanelaX11:      # JanelaJogo; procura de novo a cada localizar() se a janela sumiu
      def __init__(self, titulo: str = TITULO_JOGO)
      xid: int | None   # id da janela achada (usado pela CapturaX11)
  class JanelaWindows:  # JanelaJogo via ctypes (user32); hwnd: int | None
  class CapturaX11:     # Captura: XGetImage na janela da JanelaX11, convertendo ret absoluto → relativo à janela
      def __init__(self, janela: JanelaX11)
  def plataforma() -> tuple[JanelaJogo, Captura]   # linux → (JanelaX11, CapturaX11); win32 → (JanelaWindows, CapturaMss)
  ```
- **`JanelaX11.localizar`:**
  - Reaproveita o `xid` se a janela ainda existir com o mesmo `WM_NAME`; senão, varre `_NET_CLIENT_LIST`.
  - O retângulo vem de `translate_coords(raiz, 0, 0)` (com sinal invertido) mais `get_geometry()`.
- **`JanelaX11.ativa`:** `_NET_ACTIVE_WINDOW == xid`.
- **Erros do X11** (`BadWindow`) viram `None` ou `False`, nunca exceção.

- [ ] **Passo 1:** escrever os testes. Todos os de X11 têm `skipif(not sys.platform.startswith("linux") or not os.environ.get("DISPLAY"))`.
  - `test_acha_janela_x11`: cria uma janela X11 de 400×300 com python-xlib, `WM_NAME = "Rise of Kingdoms"`, `background_pixel` vermelho, mapeada. Espera até 2 s aparecer em `_NET_CLIENT_LIST`. `JanelaX11().localizar()` tem `w == 400` e `h == 300`.
  - `test_captura_x11_le_conteudo`: com a mesma janela, `CapturaX11(janela).capturar(Ret(x+10, y+10, 50, 40))` tem tamanho `(50, 40)` e pixel `(25, 20)` vermelho.
  - `test_janela_fechada_e_reaberta` (foco 1): destruir a janela faz `localizar()` devolver `None`; criar outra com o mesmo título faz `localizar()` achá-la (com outro `xid`).
  - `test_titulo_diferente_nao_casa`: com o título `"Rise of Kingdoms - Wiki"`, devolve `None`.
  - `test_plataforma_no_linux`: devolve os tipos `JanelaX11` e `CapturaX11`.
- [ ] **Passo 2:** rodar `python -m pytest tests/test_plataforma.py -q`. Esperado: FAIL.
- [ ] **Passo 3:** implementar.
  - O `JanelaWindows` usa `ctypes.windll.user32`: `EnumWindows` com `GetWindowTextW == TITULO_JOGO`, `GetClientRect`, `ClientToScreen`, `GetForegroundWindow` e `IsIconic` (minimizada conta como inativa).
  - Fica sem teste automático aqui; registrar no ledger como não validado.
- [ ] **Passo 4:** rodar de novo. Esperado: PASS no Linux.
- [ ] **Passo 5:** commit `Acha e captura a janela do jogo no Linux (X11) e no Windows`.

### Tarefa 3: Banco para a interface — listar, desfazer, exportar e importar

**Arquivos:**
- Modificar: `openrok/armazem.py`, `openrok/conhecimento.py`, `tests/test_armazem.py`

**Interfaces:**
- Produz:
  ```python
  Armazem.listar(idioma) -> list[dict]   # chaves: pergunta, resposta, origem, confirmada, corrigida_de (str|None), atualizada_em
  Armazem.importar(idioma, linhas: list[tuple[str, str]]) -> int   # origem 'base', confirmada 0; não sobrescreve linhas 'jogo'
  Conhecimento.listar(busca: str = "", filtro: str = "todas") -> list[dict]
      # filtro: "todas" | "aprendidas" (origem jogo) | "corrigidas" (corrigida_de não None) | "nao_confirmadas"
      # inclui as perguntas do CSV base que o usuário não tem, como origem "base", confirmada False
      # busca: substring em normalizar(pergunta) ou normalizar(resposta)
  Conhecimento.desfazer_ultima_correcao() -> tuple[str, str] | None   # também atualiza o banco em memória
  Conhecimento.exportar_confirmadas(caminho: Path) -> int             # CSV pergunta,resposta (cabeçalho do idioma)
  Conhecimento.importar_csv(caminho: Path) -> int                     # ignora cabeçalho e linhas inválidas
  ```

- [ ] **Passo 1:** escrever os testes.
  - `test_listar_filtros`: com um CSV de 3 perguntas, uma aprendida, uma corrigida e uma não tocada:
    - "aprendidas" traz 2;
    - "corrigidas" traz 1, com `corrigida_de` igual à resposta antiga;
    - "nao_confirmadas" traz 1;
    - "todas" traz 3.
  - `test_busca_sem_acento`: `listar("espartaco")` acha "Espártaco".
  - `test_desfazer_atualiza_memoria`: depois de corrigir e desfazer, `buscar` devolve a resposta antiga.
  - `test_exportar_confirmadas`: gera um arquivo com o cabeçalho mais as linhas confirmadas.
  - `test_importar_csv_tolerante` (foco 5): um arquivo com cabeçalho `"Q;A"`, uma linha vazia, uma linha com 1 coluna e 2 válidas devolve 2, e as válidas passam a ser achadas por `buscar`.
- [ ] **Passo 2:** rodar `python -m pytest tests/test_armazem.py -q`. Esperado: FAIL.
- [ ] **Passo 3:** implementar. `corrigida_de` é a `resposta_antiga` da correção mais recente da pergunta.
- [ ] **Passo 4:** rodar de novo. Esperado: PASS.
- [ ] **Passo 5:** commit `Banco: listar, filtrar, desfazer, exportar e importar`.

### Tarefa 4: Ponte de eventos e overlay

**Arquivos:**
- Criar: `openrok/ui/__init__.py`, `openrok/ui/tema.py`, `openrok/ui/ponte.py`, `openrok/ui/overlay.py`, `tests/test_overlay.py`
- Modificar: `openrok/vigia.py` (atributo `geometria: tuple[Ret, Areas] | None`, atualizado a cada ciclo com o jogo visível)

**Interfaces:**
- Produz:
  ```python
  class Ponte(QObject):
      evento = Signal(object)
      def emitir(self, evento) -> None    # chamável de qualquer thread
  def para_logico(ret: Ret, dpr: float) -> QRect   # round(x/dpr), round(y/dpr), round(w/dpr), round(h/dpr)
  class Overlay(QWidget):
      def __init__(self, textos: dict)
      def aplicar(self, evento, geometria: tuple[Ret, Areas] | None) -> None
      marcada: tuple[str, str] | None   # (letra, origem) atualmente desenhada
      def definir_opacidade(self, valor: float) -> None
  ```
- **Flags do overlay:** `FramelessWindowHint | WindowStaysOnTopHint | Tool | WindowTransparentForInput | X11BypassWindowManagerHint`, mais `WA_TranslucentBackground` e `WA_ShowWithoutActivating`.
- **Geometria:** `para_logico(cliente, dpr)`, desenhando com `QPainter.scale(1/dpr, 1/dpr)` em coordenadas físicas relativas ao cliente.
- **No Windows:** depois de `show()`, `ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 0x11)`, ignorando falha.

- [ ] **Passo 1:** escrever os testes com `qtbot`.
  - `test_para_logico` (foco 4): `para_logico(Ret(0, 0, 1920, 1080), 1.25) == QRect(0, 0, 1536, 864)`, e com dpr 1,5 `Ret(300, 150, 900, 450)` dá `QRect(200, 100, 600, 300)`.
  - `test_sugestao_banco_desenha_verde`: `aplicar(Sugestao("A", "banco", 60), geometria_1080p)` deixa o overlay visível com `marcada == ("A", "banco")`. Em `overlay.grab().toImage()` (com dpr 1 no offscreen), o pixel 3 px à esquerda da caixa A, na altura do meio, tem verde dominante (`G > 180`, `R < 120`).
  - `test_sugestao_ia_desenha_amarelo`: o mesmo ponto fica com `R > 200`, `G > 160` e `B < 100`.
  - `test_eventos_que_escondem`: para cada evento de `[Respondida(), Resultado("A", "A"), OutraTela(), JogoPerdido(), PerguntaDetectada("x", [])]`, depois de uma sugestão o overlay fica `isVisible() == False` e `marcada is None`.
  - `test_ponte_entre_threads`: `emitir` chamado de uma `threading.Thread` chega ao slot ligado na thread principal (`qtbot.waitSignal`).
- [ ] **Passo 2:** rodar `python -m pytest tests/test_overlay.py -q`. Esperado: FAIL.
- [ ] **Passo 3:** implementar. O selo fica no canto superior direito da área da pergunta, com fundo `rgba(15, 20, 15, 0.82)` e texto na cor da marcação.
- [ ] **Passo 4:** rodar de novo. Esperado: PASS.
- [ ] **Passo 5:** commit `Adiciona ponte de eventos e overlay de contorno`.

### Tarefa 5: Janela principal com abas, tema e bandeja

**Arquivos:**
- Criar: `openrok/ui/janela.py`, `openrok/ui/aba_inicio.py`, `openrok/ui/aba_banco.py`, `openrok/ui/aba_ajustes.py`, `tests/test_janela.py`
- Modificar: `openrok/idiomas.py` (troca os textos do app Tk pelos textos da nova interface, em `en` e `pt`)

**Interfaces:**
- Consome: `Config` (T1), `Conhecimento.listar` / `desfazer_ultima_correcao` / `exportar_confirmadas` / `importar_csv` (T3), eventos.
- Produz:
  ```python
  class JanelaPrincipal(QMainWindow):
      def __init__(self, config: Config, conhecimento: Conhecimento, salvar_config: Callable[[], None])
      def aplicar(self, evento) -> None            # atualiza a aba Início
      def trocar_conhecimento(self, c: Conhecimento) -> None
      idioma_mudou = Signal(str)
      opacidade_mudou = Signal(float)
      calibrar_pedido = Signal()
  class AbaInicio(QWidget):  # status, pergunta, resposta (letra + texto), origem·tempo, estatísticas, interruptores
      status: QLabel; pergunta: QLabel; resposta: QLabel; origem: QLabel
      marcar_no_jogo: QCheckBox; usar_ia: QCheckBox
  class AbaBanco(QWidget):   # busca, filtros (chips), lista, exportar/importar/desfazer
  class AbaAjustes(QWidget): # idioma, opacidade (slider 30–100), fixar no topo, iniciar com o sistema, botão calibrar
  ```
- **Aba Início:**
  - **status:** `JogoEncontrado` → "Vigiando · Rise of Kingdoms encontrado"; `JogoPerdido` → "Aguardando o jogo".
  - **resposta:** `Sugestao` → letra mais o texto da opção (vindo da `PerguntaDetectada` anterior).
  - **origem:** "✓ banco · 0,06 s" ou "IA · sugestão · 1,20 s".
  - `SemResposta` e `ErroIA` → a mensagem aparece no campo da resposta.
  - **estatísticas:**
    - "no banco" = `len(conhecimento)`;
    - "aprendidas hoje" = número de `Aprendido` na sessão;
    - "acertos na sessão" = `Resultado` com `correta == marcada`, sobre o total.
- **Itens da lista do banco:**
  - "✓ confirmada pelo jogo";
  - "⟲ corrigida pelo jogo (era "X")";
  - "banco original · ainda não confirmada".

- [ ] **Passo 1:** escrever os testes com `qtbot` e `Conhecimento` real sobre um CSV temporário.
  - `test_textos_mesmas_chaves`: `IDIOMAS["en"]["textos"].keys() == IDIOMAS["pt"]["textos"].keys()`.
  - `test_inicio_mostra_sugestao`: aplicando `JogoEncontrado`, `PerguntaDetectada("Quem pintou a Mona Lisa?", ["Da Vinci", "Rafael", "", ""])` e `Sugestao("A", "banco", 60)`, o rótulo de resposta contém "A" e "Da Vinci", e a origem contém "0,06".
  - `test_inicio_estatisticas`: depois de `Resultado("D", "C")` e `Resultado("B", "B")`, o rótulo mostra "1/2".
  - `test_banco_filtro_e_busca`: clicar no chip "Corrigidas" mostra 1 item.
  - `test_ajustes_salva_config`: mexer na opacidade para 50 deixa `config.opacidade == 0.5`, chama `salvar_config` e emite `opacidade_mudou(0.5)`.
  - `test_trocar_idioma_emite`: escolher "English" emite `idioma_mudou("en")`.
- [ ] **Passo 2:** rodar `python -m pytest tests/test_janela.py -q`. Esperado: FAIL.
- [ ] **Passo 3:** implementar.
  - O tema vem de `openrok/ui/tema.py` (QSS com as cores das Restrições globais).
  - Ícone na bandeja com o menu: Mostrar, Vigiando ✓, Marcar no jogo ✓, Usar IA ✓, Sair.
  - Fechar a janela minimiza para a bandeja; "Sair" encerra o app.
- [ ] **Passo 4:** rodar de novo. Esperado: PASS.
- [ ] **Passo 5:** commit `Adiciona janela principal com abas Início, Banco e Ajustes`.

### Tarefa 6: Calibração e iniciar com o sistema

**Arquivos:**
- Criar: `openrok/ui/calibracao.py`, `openrok/autostart.py`, `tests/test_calibracao.py`

**Interfaces:**
- Produz:
  ```python
  class DialogoCalibracao(QDialog):
      def __init__(self, captura_cliente: Image.Image, atual: list[float] | None)
      def resultado(self) -> list[float] | None   # [fx, fy, fw, fh] do retângulo desenhado
  def retangulo_para_fracoes(ret_imagem: QRect, tamanho_imagem: QSize) -> list[float]
  def ativar_inicio(ativo: bool) -> None
      # Linux: $XDG_CONFIG_HOME/autostart/openrok.desktop (padrão ~/.config)
      # Windows: HKCU\Software\Microsoft\Windows\CurrentVersion\Run, valor "OpenRok"
  def comando_inicio() -> list[str]   # [sys.executable] se empacotado, senão [sys.executable, "-m", "openrok"]
  ```
- **O diálogo:** mostra a captura do cliente do jogo e deixa arrastar um retângulo em volta da pergunta e das 4 opções. Desenha por cima, em pré-visualização, as áreas resultantes de `areas_para(..., calibracao)`. Tem os botões OK, Restaurar padrão e Cancelar.

- [ ] **Passo 1:** escrever os testes.
  - `test_fracoes`: `retangulo_para_fracoes(QRect(592, 335, 899, 316), QSize(1920, 1080))` ≈ `[0.3083, 0.3102, 0.4682, 0.2926]` (4 casas).
  - `test_dialogo_arrastar`: `qtbot.mousePress`/`mouseMove`/`mouseRelease` sobre o widget de imagem de 960×540 (escala 0,5), de (296, 167) até (746, 325), resulta em `[0.3083, 0.3093, 0.4687, 0.2926]` ± 0,002.
  - `test_autostart_linux` (Linux, `XDG_CONFIG_HOME` em `tmp_path`): ligar cria o `.desktop` com `Exec=` contendo `-m openrok`, e desligar remove.
- [ ] **Passo 2:** rodar `python -m pytest tests/test_calibracao.py -q`. Esperado: FAIL.
- [ ] **Passo 3:** implementar. O ramo Windows de `ativar_inicio` usa `winreg` e não tem teste aqui; registrar no ledger.
- [ ] **Passo 4:** rodar de novo. Esperado: PASS.
- [ ] **Passo 5:** commit `Adiciona calibração das áreas e iniciar com o sistema`.

### Tarefa 7: Montagem do app, troca de idioma e lançador

**Arquivos:**
- Criar: `openrok/app.py`, `openrok/__main__.py`, `tests/test_app.py`
- Modificar:
  - `main.py`: vira só `from openrok.app import main` + `main()`. O app Tk e `Pesquisa` saem.
  - `tests/test_main.py`: remove os testes de `Pesquisa`, que já são cobertos pelo vigia, e mantém o resto.
  - `requirements.txt`: `PySide6`, `python-xlib ; sys_platform == "linux"`, `keyring`, `pytest-qt`.
  - `main.spec`: `hiddenimports` para `Xlib` e `PySide6`.
  - `README.md` / `README.pt-BR.md`: uso e capturas da nova interface.

**Interfaces:**
- Consome tudo das tarefas anteriores e do marco 1.
- Produz:
  ```python
  class Aplicacao:
      def __init__(self, config: Config, janela_jogo: JanelaJogo, captura: Captura, armazem: Armazem,
                   caminho_config: Path, ia_fabrica: Callable[[str], IA | None])
      def iniciar(self) -> None                 # cria Conhecimento + MotorOCR do idioma e inicia o Vigia
      def trocar_idioma(self, idioma: str) -> None
      janela: JanelaPrincipal; overlay: Overlay; vigia: Vigia
  def main() -> None   # força QT_QPA_PLATFORM=xcb no Linux; config de pasta_dados(); plataforma(); Armazem(pasta_dados()/"openrok.db")
  ```
- **Regras:**
  - Cada evento vai para `janela.aplicar` e também para `overlay.aplicar(evento, vigia.geometria)`, este só se `config.marcar_no_jogo`.
  - Com `usar_ia` desligado, o vigia recebe `ia=None`.
  - `ia_fabrica(idioma)` devolve `Gemini(idioma)` se `GEMINI_API_KEY` estiver definida; senão, `None`.
  - **`trocar_idioma`:** chama `vigia.parar()`, fecha o OCR antigo, cria um `Conhecimento` e um OCR novos, cria um novo `Vigia` com uma `Ponte` nova e chama `janela.trocar_conhecimento`. Os eventos da ponte antiga são desconectados antes de parar, para que nada do vigia antigo chegue depois (foco 2).

- [ ] **Passo 1:** escrever os testes com `qtbot`.
  - `test_app_de_ponta_a_ponta`: `Aplicacao` com `JanelaFixa(Ret(0, 0, 1920, 1080))`, `CapturaDeQuadro(carregar_print("q1_go"))`, `Armazem(":memory:")`, config com `idioma="pt"` e `ia_fabrica=lambda i: None`. Depois de `iniciar()`, `qtbot.waitUntil` (5 s) até `app.overlay.marcada == ("A", "banco")`, e a aba Início mostra "A".
  - `test_trocar_idioma_sem_eventos_velhos` (foco 2): depois de iniciar em pt, `trocar_idioma("en")` faz `app.vigia` ser outro objeto, e o vigia antigo tem `_thread.is_alive() == False`. Um `Sugestao` emitido na ponte antiga depois da troca não muda a aba Início.
  - `test_marcar_no_jogo_desligado`: com `config.marcar_no_jogo = False`, a sugestão aparece na aba Início, mas `overlay.marcada is None`.
- [ ] **Passo 2:** rodar `python -m pytest tests/test_app.py -q`. Esperado: FAIL.
- [ ] **Passo 3:** implementar e atualizar o lançador, os requirements, o spec do PyInstaller e os READMEs.
- [ ] **Passo 4:** rodar `python -m pytest -q` (todos). Esperado: PASS.
- [ ] **Passo 5:** commit `Monta o app Qt e substitui a interface Tkinter`.

### Tarefa 8: Validação de ponta a ponta no Linux, com o jogo

**Arquivos:** nenhum novo. As correções que surgirem seguem TDD e ganham commit próprio.

- [ ] **Passo 1:** com o jogo aberto num Exame Simulado, rodar `python -m openrok` e conferir com o mantenedor:
  1. a aba Início mostra "Vigiando";
  2. o contorno aparece na opção certa sem clicar em nada;
  3. o clique atravessa o overlay;
  4. o resultado aparece e a estatística atualiza;
  5. alt-tab esconde o overlay, e voltar ao jogo o redesenha;
  6. a aba Banco mostra as perguntas aprendidas.
- [ ] **Passo 2:** registrar no ledger o resultado de cada item. Cada falha vira uma correção com teste antes do commit.
- [ ] **Passo 3:** commit (só se houver correções).

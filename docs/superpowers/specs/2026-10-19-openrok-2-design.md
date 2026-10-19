# OpenRok 2.0 — Design

**Data:** 2026-10-19
**Status:** aprovado em conversa; aguardando revisão do documento
**Branch:** `openrok-2`

## 1. Objetivo

Fazer o OpenRok marcar a resposta certa **diretamente sobre o jogo**, sozinho, rápido o bastante para as perguntas de 10 s do exame de fim de semana, e ficar mais confiável a cada uso, aprendendo com o próprio jogo.

**Para quem:** público geral de jogadores de Rise of Kingdoms. Precisa funcionar baixando e abrindo, sem instalar Python nem Tesseract, em resoluções variadas. A plataforma principal é o **Windows**. O **Linux** precisa funcionar na máquina do mantenedor: KDE Plasma em Wayland, com o jogo rodando no Wine via [Rise-of-Kingdoms-Linux-Installer](https://github.com/limeskat/Rise-of-Kingdoms-Linux-Installer), instalado em `~/Games/RiseofKingdoms`.

**Critérios de sucesso:**
- A pergunta aparece no jogo e, sem clique nenhum, o contorno verde surge na opção certa:
  - em até **150 ms** se a pergunta já foi vista nesta máquina (cache de imagem);
  - em até **250 ms** se ela está só no banco.

  Os tempos são medidos do primeiro quadro estável até o overlay desenhado, no teste de replay da máquina de desenvolvimento.
- Nenhuma resposta entra no banco sem confirmação do jogo (o verde do resultado).
- Uma resposta errada já existente no banco é corrigida na primeira vez que o jogo mostra a certa.
- A IA é opcional, funciona com provedores gratuitos e nunca trava a interface.

## 2. Fora de escopo

- **Clicar na resposta automaticamente.** O app só mostra; quem clica é o jogador.
- Banco online compartilhado entre usuários. Por enquanto, "Exportar confirmadas" mais contribuição pelo GitHub.
- Instalador (`.msi`/Inno Setup) e AppImage. A v2 sai como ZIP/tar.
- Detecção automática do idioma do jogo. Continua o seletor, com padrão pelo idioma do sistema.
- Versões mobile ou para emulador Android.

## 3. O evento: fatos que guiam o desenho

Pesquisados em 2026-10-19 e confirmados pelo mantenedor com prints e vídeo (`fotos e videos/`).

| | Simulado (seg–sex, diário) | Preliminar e Final (fim de semana, quinzenal) |
|---|---|---|
| Cronômetro | não | sim, decrescente (~15 → 12 → 10 s; as fontes divergem) |
| Ao clicar | o resultado aparece na hora | a opção fica **azul** até o tempo acabar, e então aparece o resultado |
| Resultado | a certa fica **verde**; se errou, a marcada fica **vermelha** | igual |
| Duração do resultado | ~0,75–1 s antes da próxima pergunta (medido no vídeo) | igual |
| Ajudas | "Solicitação" a aliados | **Lampejo de Insight**: elimina uma alternativa errada |

Medições nos prints reais (1920×1080, PT):
- **OCR da pergunta e busca no banco:** acertou 4 de 4, em 70–130 ms.
- **Fração de pixels verdes ou vermelhos dentro da caixa da opção:** 0,00 numa opção normal, 0,62–0,87 na opção verde (0,62 com o baú de recompensa por cima) e 0,87 na vermelha.
- **OCR das opções com o recorte atual:** falha em textos curtos. `2`, `1`, `4`, `3` e `1879` vieram vazios. Isso precisa ser corrigido, porque a marcação depende de saber *qual* opção contém a resposta.
- **Tempo por etapa** (pergunta já no banco):

  | Etapa | Tempo |
  |---|---|
  | Captura (`mss`) | 0,3 ms |
  | Pré-processamento | 5,9 ms |
  | Tesseract | 50,7 ms |
  | Busca | 0,04 ms |

  Trocar de linguagem ou de banco de dados não traria ganho relevante.

## 4. Arquitetura

O `main.py` atual vira o pacote `openrok/`. As peças já testadas (`normalizar`, `palavras_batem`, `BancoPerguntas`, `MotorOCR`, `extrair_letra`) são movidas, não reescritas.

```
openrok/
├── __main__.py        # python -m openrok
├── idiomas.py         # textos da interface e prompts (en, pt)
├── config.py          # Config (JSON) + chave no cofre (keyring)
├── geometria.py       # áreas de referência 1920x1080, escala, calibração
├── janela_jogo.py     # acha a janela do jogo, retângulo do cliente, se está ativa (Windows e X11)
├── captura.py         # captura do retângulo com mss
├── tela.py            # assinatura da tela de perguntas, estado das opções por cor, hash da imagem
├── ocr.py             # MotorOCR + recorte das opções sem o selo da letra
├── banco.py           # BancoPerguntas (CSV base) + ArmazemUsuario (SQLite) + cache de imagem
├── ia.py              # cliente compatível com OpenAI, presets de provedores, extrair_letra
├── vigia.py           # thread com a máquina de estados; emite eventos
└── ui/
    ├── app.py         # QApplication, janela com abas, bandeja
    ├── aba_inicio.py
    ├── aba_ia.py
    ├── aba_banco.py
    ├── aba_ajustes.py # inclui a calibração das áreas
    └── overlay.py
main.py                # lançador fino (entrada do PyInstaller)
bench/benchmark.py     # benchmark de antes e depois (migrado do scratchpad)
tests/                 # unitários + fixtures reais + replay do vídeo
```

**Dependências novas:** `PySide6`, `mss`, `httpx`, `keyring`, `pywin32` (Windows) e `python-xlib` (Linux). **Saem:** `google-genai`, `tkinter` e `ImageGrab`.

**Fronteiras:**
- `vigia` não conhece Qt. Ele recebe as dependências (janela, captura, tela, OCR, banco, IA) e publica eventos numa fila.
- `ui` não conhece OCR nem banco diretamente. Consome eventos e chama métodos de alto nível (`banco.listar`, `banco.desfazer_ultima_correcao`, `ia.testar`).
- Assim o `vigia` roda no teste de replay sem tela e sem jogo.

## 5. Fluxo do vigia

O vigia roda numa thread a ~15 Hz. Cada ciclo custa ~2 ms quando nada mudou: captura de 0,3 ms mais um hash de ~1 ms.

```
AGUARDANDO_JOGO ──janela do jogo ativa──▶ OUTRA_TELA ──assinatura ok──▶ PERGUNTA
      ▲                                       ▲                          │
      └──────janela perdida/inativa───────────┴────── assinatura falhou ─┤
                                                                         ▼
                  PERGUNTA ──alguma opção azul──▶ RESPONDIDA ──verde──▶ RESULTADO
                     │                                                     │
                     └─────────────────── verde direto (simulado) ─────────┘
                  RESULTADO ──opções neutras e hash novo──▶ PERGUNTA
```

**Em cada ciclo:**
1. **Janela do jogo.** Se não for a janela ativa (ou estiver minimizada), vai para `AGUARDANDO_JOGO` e esconde o overlay.
2. **Captura.** Uma única captura do retângulo que envolve a pergunta e as 4 opções, com coordenadas da `geometria`.
3. **Assinatura.** As 4 caixas precisam ter a cor de fundo bege do pergaminho ou um dos estados (azul, verde, vermelho). Se não tiverem, vai para `OUTRA_TELA` e esconde o overlay.
4. **Estado das opções**, pela fração de pixels de cada faixa HSV, medida só no **interior** da caixa:
   - *verde:* fração > 0,35 numa caixa. A faixa vale para o verde do jogo; o verde do overlay fica fora da caixa (ver §6).
   - *vermelho:* fração > 0,35.
   - *azul:* fração > 0,35 numa faixa de matiz separada. A faixa e o limiar são confirmados com um print do estado azul, que é pré-requisito dos testes do marco 1.
   - *eliminada* (Lampejo): caixa sem texto e com contraste baixo; essa opção fica de fora.
5. **Pergunta nova.** Todas as opções neutras e o dHash de 64 bits da área da pergunta mudou (distância de Hamming > 6). Exige **o mesmo hash em 2 ciclos seguidos** (~66 ms) para ignorar a animação de troca.
6. **Resolver a pergunta**, nesta ordem, parando no primeiro que responder:
   1. **Cache de imagem:** hash a distância ≤ 4 de um hash confirmado.
   2. **Banco:** OCR da pergunta e das 4 opções em paralelo, busca no banco e mapeamento da resposta para uma letra (§7).
   3. **IA:** chamada assíncrona. O loop do vigia continua rodando durante a espera, e a sugestão é descartada se a pergunta mudar antes de a resposta chegar.
7. **Resultado.** Na primeira leitura de verde para a pergunta atual, chama `aprender()` (§8) uma única vez e esconde o overlay.

**Eventos emitidos para a UI:** `JogoEncontrado`, `JogoPerdido`, `PerguntaDetectada(texto, opcoes)`, `Sugestao(letra, origem, tempo_ms)`, `SemResposta(motivo)`, `Resultado(correta, marcada)`, `Aprendido(tipo: nova|confirmada|corrigida)`, `ErroIA(mensagem)`.

## 6. Overlay

- Janela Qt sem moldura, transparente, sempre no topo e **atravessável pelo clique** (`Qt.WindowTransparentForInput`, `Qt.Tool`, `WA_TranslucentBackground`). Ocupa o retângulo do cliente do jogo e acompanha a janela.
- **Estilo aprovado: contorno brilhante.** Borda de 4 px (escalada) com brilho, desenhada **por fora** da caixa da opção, com uma margem de ~6 px escalada. **Verde** `#21E05A` quando a resposta vem do banco ou do cache; **amarelo** `#FFC928` quando é sugestão da IA.
- Um selo pequeno no canto da área da pergunta mostra a origem e o tempo (`✓ banco · 0,06 s`, `IA · sugestão · 1,2 s`).
- **O overlay não pode contaminar a captura:**
  - No Windows: `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)`, disponível no Windows 10 2004 em diante.
  - Em qualquer sistema: o contorno fica fora da caixa e a cor é lida só no interior dela.
- No Linux o app força `QT_QPA_PLATFORM=xcb`, para que o overlay viva no XWayland, no mesmo sistema de coordenadas do jogo no Wine.
- O overlay some ao entrar em `RESPONDIDA`, `RESULTADO`, `OUTRA_TELA` ou `AGUARDANDO_JOGO`, para nunca atrapalhar o azul, o verde ou o vermelho do jogo.

## 7. OCR das opções e mapeamento resposta → letra

**Recorte:**
- A área de cada opção passa a começar **depois do selo da letra**: ~20 px a mais na referência 1920×1080, medidos nos prints.
- Modo de página `PSM 6`. Se o resultado vier vazio, tenta de novo com `PSM 7` (uma linha), o que cobre números isolados.
- **Critério de aceite:** nas fixtures, ler `2, 1, 4, 3` (Q1), `1915, 1879, 1921, 1905` (Q4), os nomes de Q5 e os cometas de Q6.

**Mapeamento:**
- A resposta do banco é normalizada e comparada com cada opção normalizada.
- **Respostas numéricas:** igualdade exata dos dígitos.
- **Respostas em texto:** `fuzz.ratio ≥ 85`, e precisa haver um único melhor resultado.
- Se nenhuma opção bater (banco errado ou OCR falho), a pergunta é tratada como desconhecida: vai para a IA, se estiver ativa, e a aba Início mostra "resposta do banco não está entre as opções: <texto>".

## 8. Dados

**Banco base:** `data/perguntas_respostas_{en,pt}.csv`, empacotados e somente leitura, carregados por `BancoPerguntas`, que já ignora cabeçalho, linhas vazias, `#VALUE!` e duplicadas.

**Armazém do usuário:** SQLite em `%APPDATA%\OpenRok\openrok.db` (Windows) ou `~/.local/share/OpenRok/openrok.db` (Linux).

```sql
perguntas(id INTEGER PRIMARY KEY, idioma TEXT, pergunta TEXT, normalizada TEXT,
          resposta TEXT, origem TEXT CHECK(origem IN ('base','ia','jogo')),
          confirmada INTEGER, criada_em TEXT, atualizada_em TEXT,
          UNIQUE(idioma, normalizada))
correcoes(id INTEGER PRIMARY KEY, pergunta_id INTEGER, resposta_antiga TEXT,
          resposta_nova TEXT, em TEXT)
cache_imagem(hash INTEGER, idioma TEXT, pergunta_id INTEGER, PRIMARY KEY(hash, idioma))
```

- **Ao carregar:** base CSV mais as linhas do usuário. Para a mesma pergunta normalizada, **a do usuário vence**.
- **`aprender(pergunta, opcoes, letra_verde, hash)`:** grava ou atualiza `resposta = opcoes[letra_verde]`, com `origem='jogo'` e `confirmada=1`. Se havia uma resposta diferente, registra em `correcoes`. Também grava o hash no `cache_imagem`. Tudo numa transação.
- **Texto canônico:** se a pergunta casou com o banco, usa o texto do banco. Se não, usa o texto do OCR com os espaços normalizados.
- **Desfazer última correção:** restaura `resposta_antiga` a partir de `correcoes`.
- **Exportar confirmadas:** CSV com `pergunta,resposta` no formato do banco base.

**Config:** `config.json` na mesma pasta, com idioma, provedor, modelo, URL personalizada, opacidade do overlay, áreas calibradas e flags (marcar no jogo, usar IA, iniciar com o sistema). A **chave da IA** vai no cofre do sistema via `keyring` (Credential Manager ou KWallet/Secret Service). Se não houver cofre, vai para o `config.json` e a aba IA avisa que a chave está salva em texto.

## 9. IA de qualquer provedor

**Cliente:**
- Um único cliente `httpx` para o formato `POST {base}/chat/completions`.
- **Requisição:** `temperature: 0`, timeout de **6 s** e nenhuma nova tentativa, porque o tempo é crítico.
- **Prompt:** só as opções não eliminadas, com letras, pedindo apenas a letra. A resposta é lida por `extrair_letra` (já testado).

**Presets, na ordem da interface (gratuitos primeiro):**

| Provedor | Base URL | Chave |
|---|---|---|
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | sim (plano grátis) |
| Groq | `https://api.groq.com/openai/v1` | sim (plano grátis) |
| OpenRouter | `https://openrouter.ai/api/v1` | sim (modelos `:free`) |
| Ollama | `http://localhost:11434/v1` | não |
| LM Studio | `http://localhost:1234/v1` | não |
| OpenAI | `https://api.openai.com/v1` | sim |
| Anthropic | `https://api.anthropic.com/v1` | sim |
| DeepSeek | `https://api.deepseek.com/v1` | sim |
| Personalizado | definida pelo usuário | opcional |

- O modelo padrão de cada preset é conferido na documentação do provedor durante o marco 3. O usuário pode trocar o modelo livremente.
- **Erros:**
  - `401` vira "chave inválida".
  - `429` vira "limite do plano gratuito atingido".
  - Timeout vira "IA demorou demais".
  - Todos viram `ErroIA`, sem exceção chegando à UI.
- **Testar:** envia uma pergunta conhecida do banco e mostra se a IA acertou e quanto tempo levou.
- A sugestão da IA só é desenhada se `extrair_letra` devolver uma letra válida. **Nunca é gravada:** só o verde do jogo grava.

## 10. Interface (PySide6, tema escuro)

Mockups aprovados em `.superpowers/brainstorm/` (fora do git).

- **Janela com abas**, fixável no topo e com ícone na bandeja:
  - **Início:** status do vigia ("Vigiando · Rise of Kingdoms encontrado"), a última pergunta com a resposta (letra, texto, origem e tempo) e as estatísticas: perguntas no banco, aprendidas hoje, acertos na sessão.
  - **IA:** lista de provedores com selo **GRÁTIS** nos gratuitos, chave (mascarada, com link "como conseguir uma chave grátis"), modelo e botão **Testar** com o resultado.
  - **Banco:**
    - busca;
    - filtros: Todas, Aprendidas, Corrigidas, Não confirmadas;
    - cada item mostra a situação: confirmada, corrigida (com a resposta antiga) ou banco original;
    - exportar e importar CSV;
    - desfazer a última correção.
  - **Ajustes:** idioma, calibração das áreas (arrastar retângulos sobre uma captura do jogo), opacidade do overlay e iniciar com o sistema.
- Interruptores rápidos na aba Início: **Marcar no jogo** e **Usar IA se não souber**.

## 11. Janela do jogo e escala

- **Windows:** `EnumWindows` procurando o título "Rise of Kingdoms", depois `GetClientRect` mais `ClientToScreen`, e `GetForegroundWindow` para saber se está ativa.
- **Linux (X11/XWayland):** `_NET_CLIENT_LIST` e `WM_NAME`/`WM_CLASS` via `python-xlib`, mais `_NET_ACTIVE_WINDOW`.
- **Escala:** as áreas de referência ficam definidas em 1920×1080. Com `s = min(w/1920, h/1080)` e a área de referência centralizada no cliente, cobre janelas 16:9 de qualquer tamanho.
- **Proporção diferente de 16:9:** usa as áreas calibradas pelo usuário, se existirem. Se não existirem, a aba Início avisa "calibre as áreas em Ajustes".

## 12. Linux

O marco 4 começa com um **teste de viabilidade**, com o jogo aberto pelo instalador. Três perguntas, cada uma com sim ou não registrado:
1. A janela do Wine aparece em `_NET_CLIENT_LIST` com um título identificável?
2. A captura do retângulo traz o conteúdo do jogo? Testar `mss` na raiz e, se vier preto, `XGetImage` direto na janela do jogo.
3. O overlay Qt com `xcb` fica acima do jogo e deixa o clique passar no KWin?

Se as três passarem, o código do Windows serve para o Linux com as implementações X11 de `janela_jogo`. **Plano B**, se a 2 ou a 3 falhar: captura pelo portal `org.freedesktop.portal.ScreenCast` (PipeWire) e overlay por `layer-shell` (LayerShellQt). Nesse caso o marco 4 é re-especificado antes de implementar.

## 13. Empacotamento

- **Windows:**
  - PyInstaller em modo **pasta** (`onedir`), que abre mais rápido que o `onefile`, distribuído em ZIP.
  - Embute os CSVs base e os modelos `eng`/`por` do `tessdata_fast` (~6 MB).
  - O primeiro passo do marco 5 é verificar se o wheel `tesserocr` para Windows já traz as DLLs do Tesseract. Se não trouxer, as DLLs são incluídas como `binaries` no spec.
- **Linux:** PyInstaller `onedir` em `.tar.gz` mais um arquivo `.desktop`. O wheel do `tesserocr` no PyPI já traz a libtesseract.
- Python 3.12 nos dois.

## 14. Testes

- **Unitários:** os 28 atuais, migrados para o pacote, mais:
  - `tela`: cores e assinatura;
  - `geometria`: escala e calibração;
  - `banco`: SQLite, aprender, corrigir, desfazer, cache;
  - `ia`: presets, mapeamento de erros HTTP com `httpx.MockTransport`.
- **Fixtures reais** em `tests/fixtures/`:
  - os 4 prints, recortados para a região do pergaminho (x 560–1520, y 330–670) para ficarem menores, sem perda;
  - o vídeo de 16 s;
  - um print do estado **azul**, a ser fornecido pelo mantenedor.

  Os testes de cor e OCR rodam sobre elas.
- **Replay:** os quadros do vídeo passam pelo `vigia`, com janela e captura simuladas, e o teste confere a sequência de eventos:
  1. `PerguntaDetectada`, `Sugestao` (letra certa) e `Resultado` na primeira pergunta;
  2. depois a segunda pergunta;
  3. e nenhum evento durante a troca de janela (12–14,5 s).

  O mesmo replay mede os tempos do §1.
- **Benchmark:** `bench/benchmark.py` compara as versões e entra no repositório.

## 15. Marcos

Cada marco tem seu próprio plano de implementação.

| # | Marco | Pronto quando |
|---|---|---|
| 1 | **Motor sem interface:** pacote `openrok/`, `tela`, `geometria`, OCR das opções, `banco` com SQLite e cache, `vigia` | Replay do vídeo passa; OCR das opções passa nas fixtures; metas de tempo do §1 atingidas no replay |
| 2 | **Interface Qt e overlay (Windows)** | Abas Início, Banco e Ajustes funcionando; overlay excluído da captura; rodando de ponta a ponta no Windows |
| 3 | **IA de qualquer provedor** | Presets, aba IA com Testar, chave no cofre, erros mapeados, testes com `MockTransport` |
| 4 | **Linux** | Teste de viabilidade registrado; app funcionando no KDE Wayland com o jogo no Wine |
| 5 | **Empacotamento** | ZIP do Windows e tar do Linux abrindo numa máquina limpa, sem Python nem Tesseract instalados; READMEs atualizados |

## 16. Riscos

| Risco | Mitigação |
|---|---|
| Faixa do azul não confirmada | Print do estado azul como pré-requisito dos testes do marco 1 |
| Layout diferente em outras resoluções ou proporções | Escala por `min(w/1920, h/1080)` mais calibração manual |
| Captura ou overlay no XWayland do KWin | Teste de viabilidade no início do marco 4, com plano B definido |
| `WDA_EXCLUDEFROMCAPTURE` indisponível (Windows antigo) | O contorno por fora da caixa já evita o falso verde |
| Plano grátis de IA com limite baixo | Erro claro; o banco e o aprendizado pelo jogo reduzem as chamadas com o tempo |
| Respostas erradas no banco base | Corrigidas pelo verde do jogo; aba Banco mostra e permite desfazer |

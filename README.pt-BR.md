> **Idioma:** [English](README.md) · **Português**

# OpenRok

**Assistente para o evento *Liceu da Sabedoria* (Peerless Scholar / Lyceum of Wisdom) do jogo Rise of Kingdoms.**

O OpenRok vigia o jogo, lê cada pergunta assim que ela aparece e contorna a opção certa direto na tela do jogo, em uma fração de segundo, para dar tempo de responder antes do cronômetro acabar. Ele aprende com o próprio jogo: cada resposta que o jogo confirma em verde o deixa mais confiável.

---

## Sobre o evento

O **Liceu da Sabedoria** (em inglês, *Lyceum of Wisdom* / evento *Peerless Scholar*) é um evento de perguntas e respostas de múltipla escolha do Rise of Kingdoms. As perguntas cobrem tanto o lore do jogo quanto história e cultura geral, e o jogador é recompensado por acertar.

O desafio é o **tempo**: o evento é dividido em fases (Preliminar, Intermediária e Final), e nas fases mais avançadas cada pergunta tem um cronômetro curto — de 10 a 15 segundos. É praticamente impossível pesquisar a resposta manualmente a tempo, e é exatamente esse gargalo que o OpenRok resolve: ele identifica a pergunta e devolve a resposta quase instantaneamente.

Referências sobre o evento:
- [Liceu da Sabedoria — Perguntas e Respostas (Elite Brasil)](https://elite-bras.webnode.page/l/liceu-da-sabedoria-perguntas-e-respostas/)
- [Lyceum of Wisdom — Rise of Kingdoms Wiki](https://riseofkingdoms.fandom.com/wiki/Buildings/Lyceum_of_Wisdom)
- [All Peerless Scholar Questions & Answers (rok.guide)](https://www.rok.guide/buildings/lyceum-of-wisdom/)

---

## Como funciona

O OpenRok vigia o jogo sozinho: não há nada para clicar.

1. **Acha a janela do jogo** ("Rise of Kingdoms") e olha para ela cerca de 15 vezes por segundo, só enquanto o jogo é a janela ativa.
2. **Detecta uma pergunta nova.** Uma "impressão digital" do texto da pergunta distingue uma pergunta nova da mesma, mesmo com compressão ou mudança de luz.
3. **Lê a pergunta** com o [Tesseract](https://github.com/tesseract-ocr/tesseract) (via `tesserocr`), com a pergunta e as quatro opções em paralelo. Os modelos do Tesseract são carregados uma vez e vêm junto com o app.
4. **Acha a resposta:**
   - primeiro num cache de imagens de perguntas já vistas neste computador, que pula o OCR;
   - depois no banco de perguntas, com busca aproximada ([RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)) que tolera erros do OCR sem confundir perguntas que diferem em uma palavra;
   - só se os dois falharem, pergunta a letra a uma **IA** do provedor que você escolher (opcional).
5. **Marca no jogo:** um contorno brilhante em volta da opção certa. Ele é **verde** quando a resposta vem do banco e **amarelo** quando é sugestão da IA. O clique atravessa o contorno e chega ao jogo.
6. **Aprende com o jogo.** Quando o jogo mostra a resposta oficial em verde, o OpenRok grava *essa* resposta num banco SQLite local. Nada que a IA diz é salvo sem a confirmação do jogo, e respostas erradas do banco são corrigidas sozinhas (com opção de desfazer).

O OpenRok só olha a tela. Ele não lê nem altera a memória ou os arquivos do jogo, e nunca clica ou digita por você.

**Velocidade** (replay de um vídeo real do jogo): cerca de 60–70 ms entre a pergunta aparecer e o contorno com o computador ocioso, e cerca de 20–30 ms para perguntas já vistas. Com o próprio jogo rodando no mesmo computador, o OCR disputa a CPU e pode levar até cerca de 0,3 s.

---

## Idiomas

| Idioma | OCR | Banco |
|---|---|---|
| English | `eng` | `data/perguntas_respostas_en.csv` |
| Português | `por` | `data/perguntas_respostas_pt.csv` |

Troque em **Ajustes**. O padrão segue o idioma do sistema.

---

## Requisitos

- **Windows 10/11 (64 bits)** ou **Linux x86-64** com glibc 2.35 ou mais nova (Ubuntu 22.04+, Fedora 36+ e equivalentes).
  - No Windows o app já é gerado e testado automaticamente, mas **ainda está em teste com o jogo**.
  - No Linux o jogo roda pelo Wine (por exemplo, com o [Rise-of-Kingdoms-Linux-Installer](https://github.com/limeskat/Rise-of-Kingdoms-Linux-Installer)). O OpenRok funciona em X11 e em desktops Wayland via XWayland; foi testado no KDE Plasma. Veja [Linux](#linux) para um ajuste do Wine.
- Uma **IA** é opcional, para perguntas que não estão no banco: Gemini, Groq e OpenRouter têm plano grátis, e Ollama/LM Studio rodam no seu computador.

Não é preciso instalar Python nem Tesseract: os dois vêm dentro do app, com os modelos `eng`/`por`.

---

## Instalação

Baixe a versão mais recente na [página de releases](https://github.com/PolarIF/OpenRok/releases):

- **Windows:** baixe o `OpenRok-windows.zip`, extraia e abra `OpenRok\OpenRok.exe`. Na primeira vez o Windows avisa que o app não tem assinatura digital: clique em **Mais informações** → **Executar assim mesmo**.
- **Linux:** baixe o `OpenRok-linux.tar.gz` e rode:

  ```bash
  tar -xzf OpenRok-linux.tar.gz
  ./OpenRok/OpenRok
  ```

O que o OpenRok aprende, as configurações e o log ficam em `%APPDATA%\OpenRok` (Windows) ou `~/.local/share/OpenRok` (Linux). Para atualizar, basta trocar a pasta do app por uma versão nova: os dados continuam.

---

## Uso

1. Abra o OpenRok. Ele começa **pausado**: não lê a tela nem chama a IA até você mandar.
2. Abra o jogo num exame do Liceu da Sabedoria. Sobre o jogo aparece uma bolha com "Pausado"; clique no **▶** dela (ou ligue **Vigiar o jogo** na aba Início). O **⏸** pausa de novo.
3. A cada pergunta, a opção certa ganha o contorno, e a bolha mostra a resposta e o tempo. A bolha pode ser arrastada para onde atrapalhar menos.
4. A aba **Banco** lista todas as perguntas com a situação de cada uma (confirmada pelo jogo, corrigida ou original). Por ali dá para buscar, exportar as confirmadas, importar um CSV e desfazer a última correção.
5. A aba **Ajustes** tem idioma, opacidade do contorno, pílula de resposta sobre o jogo (a bolha), manter no topo, iniciar com o sistema e **Calibrar áreas**. Só é preciso calibrar se o contorno não bater com as caixas no tamanho da sua janela: arraste um retângulo em volta da pergunta e das quatro opções.

Fechar a janela mantém o OpenRok na bandeja do sistema; use **Sair** por lá para encerrar.

### IA (opcional)

Na aba **IA**, escolha o provedor, cole a chave e clique em **Testar**: o OpenRok faz uma pergunta conhecida do banco e mostra se a IA acertou e quanto tempo levou. A chave fica no cofre de senhas do sistema (Gerenciador de Credenciais no Windows, KWallet/Secret Service no Linux), nunca num arquivo.

| Provedor | Grátis | Observação |
|---|---|---|
| Google Gemini | sim | chave em [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Groq | sim | chave em [console.groq.com/keys](https://console.groq.com/keys); padrão `openai/gpt-oss-120b` |
| OpenRouter | sim | modelos `:free`; chave em [openrouter.ai/keys](https://openrouter.ai/keys) |
| Ollama / LM Studio | sim | rodam no seu computador, sem chave |
| OpenAI, Anthropic, DeepSeek | não | pagos por uso |
| Personalizado | — | qualquer servidor compatível com a API da OpenAI |

O campo **Modelo** aceita qualquer modelo do provedor; vazio, usa o padrão. A IA só sugere (contorno amarelo) e nunca grava nada no banco. Quem já usava `GEMINI_API_KEY` continua funcionando com o Gemini. O log registra tudo o que vai para a IA e volta dela, sem a chave.

---

## Linux

### Liberar o mouse no Wine

Em tela cheia, o Wine prende o mouse dentro da janela do jogo, e aí nenhum clique chega na bolha do OpenRok (ela não liga nem arrasta). Para liberar, desligue o `GrabPointer` no prefixo do jogo e reabra o jogo:

```bash
WINEPREFIX=~/Games/RiseofKingdoms ~/Games/RiseofKingdoms/wine_bin/bin/wine \
  reg add 'HKCU\Software\Wine\X11 Driver' /v GrabPointer /t REG_SZ /d N /f
```

Troque os caminhos se o jogo estiver em outro lugar (`wine` comum serve se o jogo usar o Wine do sistema). Com uma tela só e o jogo em tela cheia, nada muda no jogo; com dois monitores, o cursor passa a poder sair da janela do jogo.

### Captura da tela

Por padrão o OpenRok lê os pixels da própria janela do jogo (X11/XWayland): só o jogo entra na leitura, sem pedir permissão. Com o Wine, essa imagem às vezes fica parada por alguns segundos e o OpenRok deixa de ver o verde de uma pergunta (a sugestão continua aparecendo; só o aprendizado daquela pergunta se perde).

Com `OPENROK_CAPTURA=portal`, ele captura a tela pelo portal do Wayland (o mesmo do compartilhamento de tela). O desktop pede para escolher a tela a cada abertura, e o próprio contorno entra na captura, o que pode fazer a marcação piscar. Fica como opção para diagnóstico.

### Diagnóstico

```bash
OPENROK_DEBUG=1 ./OpenRok/OpenRok           # log detalhado e quadros salvos em ~/.local/share/OpenRok/quadros
OPENROK_SEM_BANCO=1 ./OpenRok/OpenRok       # finge banco vazio, sem tocar no banco de verdade
```

---

## Rodando a partir do código

Requer **Python 3.12**.

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m openrok
```

No Windows, o `wheels/tesserocr-*.whl` incluído instala o `tesserocr` sem compilar.

### Gerando o executável

```bash
pyinstaller main.spec          # gera dist/OpenRok/
```

O PyInstaller só gera para o sistema em que roda. O workflow [`pacotes.yml`](.github/workflows/pacotes.yml) roda os testes e gera os pacotes no Windows e no Linux a cada push no `main`; uma tag `v*` publica os dois numa pré-release.

### Testes

```bash
pytest                       # testes unitários, de interface e de X11 + replay de um vídeo real do jogo
python -m bench.replay       # o que o vigia faz com o vídeo e quanto tempo cada resposta levou
python -m bench.comparar_v1  # benchmark de antes e depois contra a primeira versão
```

---

## Estrutura do projeto

```
OpenRok/
├── openrok/            # O app
│   ├── vigia.py        # Vigia: detecta perguntas, sugere e aprende com o verde do jogo
│   ├── tela.py         # Lê as cores das opções e a impressão digital da pergunta
│   ├── ocr.py          # Tesseract (modelos em tessdata/)
│   ├── conhecimento.py # Banco + o que este computador aprendeu (SQLite, armazem.py)
│   ├── plataforma.py   # Janela do jogo e captura (X11 no Linux, Win32 no Windows)
│   ├── ia.py           # Provedores de IA (compatíveis com a OpenAI); a chave fica no cofre (cofre.py)
│   └── ui/             # Interface Qt: abas, overlay, calibração
├── data/               # Bancos de perguntas e respostas (EN, PT)
├── tests/              # Testes, com prints e vídeo reais em tests/fixtures/
├── bench/              # Replay e benchmarks
└── docs/superpowers/   # Spec do design e planos de implementação
```

---

## Tecnologias

- **Python** + **PySide6 (Qt)** para a interface e o overlay
- **Tesseract / tesserocr**, **OpenCV** e **Pillow** para ler a tela
- **RapidFuzz** para a busca aproximada
- **SQLite** para o que o OpenRok aprende
- **python-xlib** (Linux) e **mss** (Windows) para capturar a janela
- **httpx** para a IA opcional (qualquer provedor compatível com a API da OpenAI) e **keyring** para guardar a chave
- **pytest** + **pytest-qt** para os testes, e **PyInstaller** para empacotar

---

## Aviso

Este projeto foi feito para fins de estudo e como ferramenta auxiliar pessoal. Use por sua conta e risco e de acordo com os termos de serviço do Rise of Kingdoms.

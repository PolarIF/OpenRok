> **Idioma:** [English](README.md) · **Português**

# OpenRok

**Assistente para o evento *Liceu da Sabedoria* (Peerless Scholar / Lyceum of Wisdom) do jogo Rise of Kingdoms.**

O OpenRok lê a pergunta que aparece na tela do jogo usando OCR, procura a resposta em um banco local de perguntas e respostas e — quando a pergunta é inédita — consulta o Google Gemini, exibindo o resultado em uma pequena janela flutuante. Tudo em poucos segundos, para dar tempo de responder antes do cronômetro acabar.

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

1. **Captura de tela** — o programa captura, de uma só vez, a área fixa onde a pergunta e as alternativas A/B/C/D aparecem no jogo.
2. **Pré-processamento da imagem** — a imagem é convertida para escala de cinza, ampliada (2×), tem o contraste aumentado, passa por um leve desfoque para reduzir ruído e é binarizada (`OpenCV`), tudo para maximizar a precisão do OCR.
3. **OCR** — o texto é extraído com o [Tesseract](https://github.com/tesseract-ocr/tesseract) (via `tesserocr`). As instâncias do Tesseract são carregadas uma única vez ao abrir o programa e reaproveitadas, e as quatro alternativas são lidas em paralelo.
4. **Busca no banco local** — o texto reconhecido é normalizado (minúsculas, sem acentos, sem pontuação) e comparado com o banco de perguntas usando *fuzzy matching* ([RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)), o que tolera erros de leitura do OCR. Uma checagem palavra a palavra evita confundir perguntas do mesmo modelo que diferem em uma palavra (ex.: *"Qual das seguintes NÃO é uma habilidade de Mulan?"* × *"...de Osman I?"*).
5. **Fallback com IA** — se a pergunta não estiver no banco local, as quatro alternativas são enviadas, junto da pergunta, para o **Google Gemini**, que responde com a letra da alternativa correta.
6. **Banco que se auto-alimenta** — quando a resposta do Gemini aponta claramente para uma das alternativas, a pergunta e essa alternativa são gravadas no CSV, então o banco local cresce com o uso. Respostas ambíguas são exibidas mas **não** são salvas, para que uma resposta duvidosa nunca contamine o banco.
7. **Exibição** — a pergunta, a resposta, a origem (banco ou Gemini) e o tempo gasto aparecem em uma pequena janela que pode ser fixada sempre no topo. A busca roda em segundo plano, então a janela nunca congela.

---

## Idiomas

Um único programa atende os dois idiomas; cada um tem seu banco de perguntas, idioma de OCR, textos da interface e prompt do Gemini:

| Idioma | OCR | Banco |
|---|---|---|
| English (padrão) | `eng` | `data/perguntas_respostas_en.csv` |
| Português | `por` | `data/perguntas_respostas_pt.csv` |

Troque pelo seletor de idioma na janela, ou inicie com `--lang pt`.

---

## Requisitos

- **Windows** — o projeto é voltado para Windows (o wheel do `tesserocr` incluído é `cp312 / win_amd64`, e a captura de tela usa `PIL.ImageGrab`).
- **Python 3.12** (compatível com o wheel do `tesserocr` incluído).
- **[Tesseract-OCR](https://github.com/tesseract-ocr/tesseract)** instalado, com os dados de idioma `eng` e/ou `por`. Se o Tesseract não encontrar os dados, defina `TESSDATA_PREFIX` apontando para a pasta `tessdata`.
- Uma **chave de API do Google Gemini** para perguntas que não estão no banco (opcional — sem ela, o OpenRok continua respondendo tudo o que está no banco).
- Jogo rodando em **1920×1080** (as coordenadas de captura estão mapeadas para essa resolução).

---

## Instalação

```bash
# (recomendado) crie um ambiente virtual
python -m venv .venv
.venv\Scripts\activate

# instale as dependências
pip install -r requirements.txt
```

> O wheel `wheels/tesserocr-2.7.1-cp312-cp312-win_amd64.whl` é usado para instalar o `tesserocr` no Windows sem compilar.

---

## Configuração

- **Chave do Gemini** — lida da variável de ambiente `GEMINI_API_KEY` (nunca coloque no código):
  ```bash
  setx GEMINI_API_KEY "sua-chave"
  ```
  Abra um novo terminal depois disso. O modelo pode ser trocado com `OPENROK_MODEL` (padrão: `gemini-3.1-flash-lite-preview`).
- **Áreas de captura** — dicionário `tamanhos` em `main.py` (resolução `1920x1080`). Se o seu jogo estiver em outra resolução ou posição, adicione uma entrada com as coordenadas `(x, y, largura, altura)` de `Pergunta`, `A`, `B`, `C` e `D`; ela aparece no seletor de resolução.
- **Escala de tela** — o OpenRok se declara DPI-aware, então a escala do Windows (125%, 150%…) não desloca as áreas de captura.

---

## Uso

```bash
python main.py            # Inglês
python main.py --lang pt  # Português
```

1. Deixe o jogo aberto em **1920×1080**, na tela de perguntas do Liceu da Sabedoria.
2. Clique em **Pesquisar**.
3. A pergunta e a resposta aparecem na janela, com a origem. Se a pergunta for inédita, o Gemini responde e ela é salva no banco para as próximas vezes.
4. Use **Fixar Janela** para manter o OpenRok sempre visível sobre o jogo.

### Gerando o `.exe`

```bash
pyinstaller main.spec
```

O executável (`dist/OpenRok.exe`) leva uma cópia dos bancos e os extrai para uma pasta `data/` ao lado dele na primeira execução; é nessa pasta que as perguntas novas são salvas.

### Testes

```bash
pytest
```

---

## Estrutura do projeto

```
OpenRok/
├── main.py                        # O aplicativo (Tkinter + OCR + banco + Gemini)
├── data/
│   ├── perguntas_respostas_en.csv # Banco de perguntas e respostas (EN)
│   └── perguntas_respostas_pt.csv # Banco de perguntas e respostas (PT)
├── tests/test_main.py             # Testes (busca, leitura da resposta do Gemini, fluxo)
├── requirements.txt               # Dependências
├── main.spec                      # Spec do PyInstaller para gerar o .exe
└── wheels/tesserocr-*.whl         # Wheel do tesserocr para Windows
```

---

## Tecnologias

- **Python** + **Tkinter** (interface)
- **pytest** (testes)
- **OpenCV** e **Pillow** (captura e pré-processamento de imagem)
- **Tesseract / tesserocr** (OCR)
- **RapidFuzz** (busca aproximada tolerante a erros de OCR)
- **Google Gemini** (fallback de IA para perguntas inéditas)
- **PyInstaller** (empacotamento em `.exe`)

---

## Aviso

Este projeto foi feito para fins de estudo e como ferramenta auxiliar pessoal. Use por sua conta e risco e de acordo com os termos de serviço do Rise of Kingdoms.

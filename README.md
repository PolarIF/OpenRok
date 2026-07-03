# OpenRok

**Assistente para o evento *Liceu da Sabedoria* (Peerless Scholar / Lyceum of Wisdom) do jogo Rise of Kingdoms.**

O OpenRok lê a pergunta que aparece na tela do jogo usando OCR, procura a resposta em um banco local de perguntas e respostas e a exibe em uma pequena janela flutuante — tudo em segundos, para dar tempo de responder antes do cronômetro acabar.

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

1. **Captura de tela** — o programa tira um print da área onde a pergunta aparece no jogo.
2. **Pré-processamento da imagem** — a imagem é convertida para escala de cinza, ampliada (2×), tem o contraste aumentado, passa por um leve desfoque para reduzir ruído e é binarizada (`OpenCV`), tudo para maximizar a precisão do OCR.
3. **OCR** — o texto é extraído com o [Tesseract](https://github.com/tesseract-ocr/tesseract) (via `tesserocr`).
4. **Busca no banco local** — o texto reconhecido é normalizado (minúsculas, sem acentos/pontuação) e comparado com o banco de perguntas usando *fuzzy matching* ([RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)), o que tolera erros de leitura do OCR. A comparação roda em paralelo (`ThreadPoolExecutor`) para ser rápida.
5. **Exibição** — a pergunta identificada e a resposta correspondente são mostradas em uma pequena janela que pode ser fixada sempre no topo (*Pin Window*).

---

## As duas versões

O projeto tem duas versões, em pastas separadas:

### `OpenRokPTBR` — versão em Português (mais completa)

- Banco de perguntas em **português** (`perguntas_respostas.csv`).
- **Áreas de captura fixas** para resolução **1920×1080** — não é preciso selecionar a região da tela manualmente. As coordenadas da pergunta e das alternativas (A, B, C, D) já estão mapeadas.
- **Fallback com IA (Google Gemini):** quando a pergunta **não** é encontrada no banco local, o programa também captura as quatro alternativas por OCR e as envia, junto da pergunta, para o Gemini, que escolhe a resposta correta.
- **Banco que se auto-alimenta:** toda resposta nova obtida pela IA é gravada de volta no CSV, então o banco local cresce e fica mais completo com o uso.

### `OpenRokEN` — versão em Inglês (legada / desatualizada)

> ⚠️ Esta é a versão **original e mais antiga** do projeto. A versão PTBR é a mais recente e completa; a intenção é portar as melhorias da PTBR (áreas fixas, fallback com Gemini e banco auto-alimentado) para cá.

- Banco de perguntas em **inglês** (`perguntas_respostas_en.csv`).
- **Seleção manual da área** da pergunta na tela (via `cv2.selectROI`) — funciona em qualquer resolução/posição de janela.
- Apenas busca no banco local (sem fallback de IA).
- Inclui *spec* do PyInstaller (`main.spec`) para gerar um executável `.exe`.

> As duas versões compartilham o mesmo núcleo: pré-processamento de imagem + OCR + busca *fuzzy* no CSV. A diferença principal é o idioma, o modo de captura e o fallback de IA.

---

## Requisitos

- **Windows** — o projeto foi feito para Windows (a wheel do `tesserocr` incluída é `cp312 / win_amd64`, além do uso de `PIL.ImageGrab`, `pywin32`, etc.).
- **Python 3.12** (compatível com a wheel do `tesserocr` fornecida).
- **[Tesseract-OCR](https://github.com/tesseract-ocr/tesseract)** instalado, com os dados de idioma:
  - `eng` para a versão EN;
  - `por` para a versão PTBR.
- Para a versão PTBR: uma **chave de API do Google Gemini**.

---

## Instalação

Escolha a pasta da versão desejada. Exemplo com a versão em português:

```bash
cd OpenRokPTBR

# (recomendado) crie um ambiente virtual
python -m venv .venv
.venv\Scripts\activate

# instale as dependências
pip install -r requeriments.txt
```

Para a versão em inglês, use `OpenRokEN/requirements.txt`.

> A wheel `tesserocr-2.7.1-cp312-cp312-win_amd64.whl` já está incluída em cada pasta e é usada para instalar o `tesserocr` sem precisar compilar.

---

## Configuração

### Versão PTBR

- Abra `OpenRokPTBR/main.py` e insira sua chave do Gemini:
  ```python
  client = genai.Client(api_key="SUA_API_KEY_AQUI")
  ```
- As áreas de captura estão no dicionário `tamanhos` (resolução `1920x1080`). Se seu jogo estiver em outra resolução ou posição, ajuste as coordenadas `(x, y, largura, altura)` de `Pergunta`, `A`, `B`, `C` e `D`.

### Versão EN

- O arquivo `OpenRokEN/config.json` guarda o caminho do executável do Tesseract e uma área de captura padrão:
  ```json
  {
      "tesseract_path": "C:/Program Files/Tesseract-OCR/tesseract.exe"
  }
  ```
  Ajuste `tesseract_path` conforme sua instalação.

---

## Como usar

### Versão PTBR

```bash
cd OpenRokPTBR
python main.py
```

1. Deixe o jogo aberto em **1920×1080**, na tela da pergunta do Liceu da Sabedoria.
2. Clique em **Pesquisar**.
3. A pergunta e a resposta aparecem na janela. Se a pergunta for inédita, o Gemini responde e a pergunta é salva no banco para as próximas vezes.
4. Use **Fixar Janela** para manter o OpenRok sempre visível por cima do jogo.

### Versão EN

```bash
cd OpenRokEN
python main.py
```

1. Clique em **select area** e desenhe um retângulo sobre a região onde a pergunta aparece.
2. Clique em **search** para capturar e buscar a resposta.
3. Use **Pin Window** para manter a janela sempre no topo.

---

## Estrutura do projeto

```
OpenRok/
├── OpenRokPTBR/                # Versão em português (com fallback Gemini)
│   ├── main.py                 # App principal (Tkinter + OCR + CSV + Gemini)
│   ├── perguntas_respostas.csv # Banco local de perguntas e respostas (PT)
│   ├── requeriments.txt        # Dependências
│   └── tesserocr-*.whl         # Wheel do tesserocr para Windows
│
└── OpenRokEN/                  # Versão em inglês (seleção manual de área)
    ├── main.py                 # App principal (Tkinter + OCR + CSV)
    ├── selecao_area.py         # Seleção da área da tela (cv2.selectROI)
    ├── config.json             # Caminho do Tesseract e área padrão
    ├── perguntas_respostas_en.csv
    ├── requirements.txt
    ├── main.spec               # Build de .exe com PyInstaller
    └── tesserocr-*.whl
```

---

## Tecnologias

- **Python** + **Tkinter** (interface)
- **OpenCV** e **Pillow** (captura e pré-processamento de imagem)
- **Tesseract / tesserocr** (OCR)
- **RapidFuzz** (busca aproximada tolerante a erros de OCR)
- **Google Gemini** (fallback de IA — apenas na versão PTBR)
- **PyInstaller** (empacotamento em `.exe` — versão EN)

---

## Aviso

Este projeto foi feito para fins de estudo e como ferramenta auxiliar pessoal. Use por sua conta e risco e de acordo com os termos de serviço do Rise of Kingdoms.

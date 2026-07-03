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

1. **Captura de tela** — o programa captura a área fixa onde a pergunta (e as alternativas A/B/C/D) aparecem no jogo.
2. **Pré-processamento da imagem** — a imagem é convertida para escala de cinza, ampliada (2×), tem o contraste aumentado, passa por um leve desfoque para reduzir ruído e é binarizada (`OpenCV`), tudo para maximizar a precisão do OCR.
3. **OCR** — o texto é extraído com o [Tesseract](https://github.com/tesseract-ocr/tesseract) (via `tesserocr`).
4. **Busca no banco local** — o texto reconhecido é normalizado (minúsculas, sem acentos/pontuação) e comparado com o banco de perguntas usando *fuzzy matching* ([RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)), o que tolera erros de leitura do OCR. A comparação roda em paralelo (`ThreadPoolExecutor`) para ser rápida.
5. **Fallback com IA** — se a pergunta não estiver no banco local, as quatro alternativas também são lidas por OCR e enviadas, junto da pergunta, para o **Google Gemini**, que escolhe a resposta correta.
6. **Banco que se auto-alimenta** — toda resposta nova obtida pela IA é gravada de volta no CSV, então o banco local cresce e fica mais completo com o uso.
7. **Exibição** — a pergunta identificada e a resposta correspondente são mostradas em uma pequena janela que pode ser fixada sempre no topo.

---

## As duas versões

O projeto tem duas versões, em pastas separadas. Elas compartilham o mesmo núcleo (captura por áreas fixas → OCR → busca *fuzzy* no CSV → fallback com Gemini → banco auto-alimentado) e diferem essencialmente no **idioma**:

### `OpenRokEN` — versão em Inglês

- Banco de perguntas em **inglês** (`perguntas_respostas_en.csv`).
- OCR em inglês (`eng`) e prompt do Gemini / interface em inglês.
- Inclui *spec* do PyInstaller (`main.spec`) para gerar um executável `.exe`.

### `OpenRokPTBR` — versão em Português

- Banco de perguntas em **português** (`perguntas_respostas.csv`).
- OCR em português (`por`) e prompt do Gemini / interface em português.

---

## Requisitos

- **Windows** — o projeto foi feito para Windows (a wheel do `tesserocr` incluída é `cp312 / win_amd64`, além do uso de `PIL.ImageGrab`, `pywin32`, etc.).
- **Python 3.12** (compatível com a wheel do `tesserocr` fornecida).
- **[Tesseract-OCR](https://github.com/tesseract-ocr/tesseract)** instalado, com os dados de idioma:
  - `eng` para a versão EN;
  - `por` para a versão PTBR.
- Uma **chave de API do Google Gemini** (as duas versões usam o fallback de IA).
- O jogo rodando em **1920×1080** (as coordenadas de captura estão mapeadas para essa resolução).

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

Em `OpenRokPTBR/main.py` (ou `OpenRokEN/main.py`):

- Insira sua chave do Gemini:
  ```python
  client = genai.Client(api_key="SUA_API_KEY_AQUI")
  ```
- As áreas de captura estão no dicionário `tamanhos` (resolução `1920x1080`). Se seu jogo estiver em outra resolução ou posição, ajuste as coordenadas `(x, y, largura, altura)` de `Pergunta`, `A`, `B`, `C` e `D`.

---

## Como usar

```bash
cd OpenRokPTBR    # ou: cd OpenRokEN
python main.py
```

1. Deixe o jogo aberto em **1920×1080**, na tela da pergunta do Liceu da Sabedoria.
2. Clique em **Pesquisar** (**Search** na versão EN).
3. A pergunta e a resposta aparecem na janela. Se a pergunta for inédita, o Gemini responde e a pergunta é salva no banco para as próximas vezes.
4. Use **Fixar Janela** para manter o OpenRok sempre visível por cima do jogo.

---

## Estrutura do projeto

```
OpenRok/
├── OpenRokPTBR/                   # Versão em português
│   ├── main.py                    # App principal (Tkinter + OCR + CSV + Gemini)
│   ├── perguntas_respostas.csv    # Banco local de perguntas e respostas (PT)
│   ├── requeriments.txt           # Dependências
│   └── tesserocr-*.whl            # Wheel do tesserocr para Windows
│
└── OpenRokEN/                     # Versão em inglês
    ├── main.py                    # App principal (Tkinter + OCR + CSV + Gemini)
    ├── perguntas_respostas_en.csv # Banco local de perguntas e respostas (EN)
    ├── requirements.txt           # Dependências
    ├── main.spec                  # Build de .exe com PyInstaller
    └── tesserocr-*.whl            # Wheel do tesserocr para Windows
```

---

## Tecnologias

- **Python** + **Tkinter** (interface)
- **OpenCV** e **Pillow** (captura e pré-processamento de imagem)
- **Tesseract / tesserocr** (OCR)
- **RapidFuzz** (busca aproximada tolerante a erros de OCR)
- **Google Gemini** (fallback de IA para perguntas inéditas)
- **PyInstaller** (empacotamento em `.exe` — versão EN)

---

## Aviso

Este projeto foi feito para fins de estudo e como ferramenta auxiliar pessoal. Use por sua conta e risco e de acordo com os termos de serviço do Rise of Kingdoms.

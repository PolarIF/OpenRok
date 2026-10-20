> **Language:** **English** · [Português](README.pt-BR.md)

# OpenRok

**A helper for the *Lyceum of Wisdom* (Peerless Scholar) event in Rise of Kingdoms.**

OpenRok reads the question shown on the game screen using OCR, looks the answer up in a local question/answer database and — when the question is new — asks Google Gemini, displaying the result in a small floating window. All in a couple of seconds, so you can answer before the timer runs out.

---

## About the event

The **Lyceum of Wisdom** (the *Peerless Scholar* event) is a multiple-choice trivia event in Rise of Kingdoms. The questions cover both game lore and general history/culture, and you are rewarded for answering correctly.

The challenge is **time**: the event is split into phases (Preliminary, Midterm and Final), and in the later phases each question has a short timer — 10 to 15 seconds. It is nearly impossible to look the answer up by hand in time, and that is exactly the bottleneck OpenRok solves: it identifies the question and returns the answer almost instantly.

Event references:
- [Lyceum of Wisdom — Rise of Kingdoms Wiki](https://riseofkingdoms.fandom.com/wiki/Buildings/Lyceum_of_Wisdom)
- [All Peerless Scholar Questions & Answers (rok.guide)](https://www.rok.guide/buildings/lyceum-of-wisdom/)
- [Peerless Scholar Answers (Rise of Kingdoms Guides)](https://riseofkingdomsguides.com/lyceum-of-wisdom-rok-answers/)

---

## How it works

1. **Screen capture** — the program grabs, in a single capture, the fixed area where the question and the A/B/C/D options appear in the game.
2. **Image pre-processing** — the image is converted to grayscale, upscaled (2×), contrast-boosted, lightly blurred to reduce noise and binarized (`OpenCV`), all to maximize OCR accuracy.
3. **OCR** — the text is extracted with [Tesseract](https://github.com/tesseract-ocr/tesseract) (via `tesserocr`). The Tesseract instances are loaded once at startup and reused, and the four options are read in parallel.
4. **Local database lookup** — the recognized text is normalized (lowercase, no accents, no punctuation) and compared against the question database using *fuzzy matching* ([RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)), which tolerates OCR errors. A word-by-word check prevents mixing up questions that share a template and differ in one word (e.g. *"Which of the following is NOT one of Mulan's abilities?"* vs *"...Osman I's abilities?"*).
5. **AI fallback** — if the question is not in the local database, the four options are sent, together with the question, to **Google Gemini**, which replies with the letter of the correct option.
6. **Self-feeding database** — when Gemini's reply clearly points to one of the options, the question and that option are written back to the CSV, so the local database grows with use. Ambiguous replies are shown but **not** saved, so a doubtful answer never pollutes the database.
7. **Display** — the question, the answer, where it came from (database or Gemini) and how long it took are shown in a small window that can be pinned always on top. The search runs in the background, so the window never freezes.

---

## Languages

A single program supports both languages; each one has its own question database, OCR language, interface text and Gemini prompt:

| Language | OCR | Database |
|---|---|---|
| English (default) | `eng` | `data/perguntas_respostas_en.csv` |
| Português | `por` | `data/perguntas_respostas_pt.csv` |

Switch between them in the window's language selector, or start with `--lang pt`.

---

## Requirements

- **Windows** — the project targets Windows (the bundled `tesserocr` wheel is `cp312 / win_amd64`, and screen capture uses `PIL.ImageGrab`).
- **Python 3.12** (compatible with the bundled `tesserocr` wheel).
- **[Tesseract-OCR](https://github.com/tesseract-ocr/tesseract)** installed, with the language data `eng` and/or `por`. If Tesseract can't find its data, set `TESSDATA_PREFIX` to the `tessdata` folder.
- A **Google Gemini API key** for questions that are not in the database (optional — without it, OpenRok still answers everything that's in the database).
- A game running at **1920×1080** (the capture coordinates are mapped for that resolution).

---

## Installation

```bash
# (recommended) create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# install the dependencies
pip install -r requirements.txt
```

> The `wheels/tesserocr-2.7.1-cp312-cp312-win_amd64.whl` wheel is used to install `tesserocr` on Windows without compiling.

---

## Configuration

- **Gemini API key** — read from the `GEMINI_API_KEY` environment variable (never put it in the code):
  ```bash
  setx GEMINI_API_KEY "your-key"
  ```
  Open a new terminal afterwards. The model can be changed with `OPENROK_MODEL` (default: `gemini-3.1-flash-lite-preview`).
- **Capture areas** — the `tamanhos` dictionary in `main.py` (resolution `1920x1080`). If your game runs at a different resolution or position, add an entry with the `(x, y, width, height)` coordinates for `Pergunta` (question), `A`, `B`, `C` and `D`; it will show up in the resolution selector.
- **Display scaling** — OpenRok declares itself DPI-aware, so Windows scaling (125%, 150%…) doesn't shift the capture areas.

---

## Usage

```bash
python main.py            # English
python main.py --lang pt  # Portuguese
```

1. Keep the game open at **1920×1080**, on the Lyceum of Wisdom question screen.
2. Click **Search**.
3. The question and answer appear in the window, with their source. If the question is new, Gemini answers it and the question is saved to the database for next time.
4. Use **Pin Window** to keep OpenRok always visible on top of the game.

### Building the `.exe`

```bash
pyinstaller main.spec
```

The executable (`dist/OpenRok.exe`) carries a copy of the databases and extracts them to a `data/` folder next to itself on first run; that folder is where new questions are saved.

### Tests

```bash
pytest                       # unit tests + replay of a real game video
python -m bench.replay       # what the watcher does with the video, and how long each answer took
python -m bench.comparar_v1  # before/after benchmark against the first version
```

---

## Project structure

```
OpenRok/
├── main.py                        # The app (Tkinter + OCR + database + Gemini)
├── data/
│   ├── perguntas_respostas_en.csv # Question/answer database (EN)
│   └── perguntas_respostas_pt.csv # Question/answer database (PT)
├── tests/test_main.py             # Tests (matching, Gemini reply parsing, pipeline)
├── requirements.txt               # Dependencies
├── main.spec                      # PyInstaller .exe build spec
└── wheels/tesserocr-*.whl         # tesserocr wheel for Windows
```

---

## Tech stack

- **Python** + **Tkinter** (interface)
- **pytest** (tests)
- **OpenCV** and **Pillow** (screen capture and image pre-processing)
- **Tesseract / tesserocr** (OCR)
- **RapidFuzz** (approximate matching, tolerant to OCR errors)
- **Google Gemini** (AI fallback for unknown questions)
- **PyInstaller** (packaging into an `.exe`)

---

## Disclaimer

This project was built for study purposes and as a personal helper tool. Use it at your own risk and in accordance with the Rise of Kingdoms terms of service.

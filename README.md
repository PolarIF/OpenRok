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

1. **Screen capture** — the program grabs the fixed area where the question (and the A/B/C/D options) appear in the game.
2. **Image pre-processing** — the image is converted to grayscale, upscaled (2×), contrast-boosted, lightly blurred to reduce noise and binarized (`OpenCV`), all to maximize OCR accuracy.
3. **OCR** — the text is extracted with [Tesseract](https://github.com/tesseract-ocr/tesseract) (via `tesserocr`).
4. **Local database lookup** — the recognized text is normalized (lowercase, no accents/punctuation) and compared against the question database using *fuzzy matching* ([RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)), which tolerates OCR errors. The comparison runs in parallel (`ThreadPoolExecutor`) to stay fast.
5. **AI fallback** — if the question is not in the local database, the four options are also read via OCR and sent, together with the question, to **Google Gemini**, which picks the correct answer.
6. **Self-feeding database** — every new answer obtained from the AI is written back to the CSV, so the local database grows and gets more complete with use.
7. **Display** — the identified question and matching answer are shown in a small window that can be pinned always on top.

---

## The two versions

The project ships two versions, in separate folders. They share the same core (fixed-area capture → OCR → fuzzy CSV lookup → Gemini fallback → self-feeding database) and differ essentially in **language**:

### `OpenRokEN` — English

- **English** question database (`perguntas_respostas_en.csv`).
- OCR in English (`eng`) and Gemini prompt / interface in English.
- Includes a PyInstaller *spec* (`main.spec`) to build a `.exe`.

### `OpenRokPTBR` — Portuguese

- **Portuguese** question database (`perguntas_respostas.csv`).
- OCR in Portuguese (`por`) and Gemini prompt / interface in Portuguese.

---

## Requirements

- **Windows** — the project targets Windows (the bundled `tesserocr` wheel is `cp312 / win_amd64`, plus the use of `PIL.ImageGrab`, `pywin32`, etc.).
- **Python 3.12** (compatible with the bundled `tesserocr` wheel).
- **[Tesseract-OCR](https://github.com/tesseract-ocr/tesseract)** installed, with the language data:
  - `eng` for the EN version;
  - `por` for the PTBR version.
- A **Google Gemini API key** (both versions use the AI fallback).
- A game running at **1920×1080** (the capture coordinates are mapped for that resolution).

---

## Installation

Pick the folder for the version you want. Example with the English version:

```bash
cd OpenRokEN

# (recommended) create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# install the dependencies
pip install -r requirements.txt
```

For the Portuguese version, use `OpenRokPTBR/requeriments.txt`.

> The `tesserocr-2.7.1-cp312-cp312-win_amd64.whl` wheel is bundled in each folder and is used to install `tesserocr` without compiling.

---

## Configuration

In `OpenRokEN/main.py` (or `OpenRokPTBR/main.py`):

- Set your Gemini API key:
  ```python
  client = genai.Client(api_key="YOUR_API_KEY_HERE")
  ```
- The capture areas live in the `tamanhos` dictionary (resolution `1920x1080`). If your game runs at a different resolution or position, adjust the `(x, y, width, height)` coordinates for `Pergunta` (question), `A`, `B`, `C` and `D`.

---

## Usage

```bash
cd OpenRokEN      # or: cd OpenRokPTBR
python main.py
```

1. Keep the game open at **1920×1080**, on the Lyceum of Wisdom question screen.
2. Click **Search** (**Pesquisar** in the PT version).
3. The question and answer appear in the window. If the question is new, Gemini answers it and the question is saved to the database for next time.
4. Use **Pin Window** to keep OpenRok always visible on top of the game.

---

## Project structure

```
OpenRok/
├── OpenRokEN/                     # English version
│   ├── main.py                    # Main app (Tkinter + OCR + CSV + Gemini)
│   ├── perguntas_respostas_en.csv # Local question/answer database (EN)
│   ├── requirements.txt           # Dependencies
│   ├── main.spec                  # PyInstaller .exe build spec
│   └── tesserocr-*.whl            # tesserocr wheel for Windows
│
└── OpenRokPTBR/                   # Portuguese version
    ├── main.py                    # Main app (Tkinter + OCR + CSV + Gemini)
    ├── perguntas_respostas.csv    # Local question/answer database (PT)
    ├── requeriments.txt           # Dependencies
    └── tesserocr-*.whl            # tesserocr wheel for Windows
```

---

## Tech stack

- **Python** + **Tkinter** (interface)
- **OpenCV** and **Pillow** (screen capture and image pre-processing)
- **Tesseract / tesserocr** (OCR)
- **RapidFuzz** (approximate matching, tolerant to OCR errors)
- **Google Gemini** (AI fallback for unknown questions)
- **PyInstaller** (packaging into an `.exe` — EN version)

---

## Disclaimer

This project was built for study purposes and as a personal helper tool. Use it at your own risk and in accordance with the Rise of Kingdoms terms of service.

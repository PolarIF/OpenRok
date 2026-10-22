> **Language:** **English** · [Português](README.pt-BR.md)

# OpenRok

**A helper for the *Lyceum of Wisdom* (Peerless Scholar) event in Rise of Kingdoms.**

OpenRok watches the game, reads each question as it appears and outlines the right option directly on the game screen, in a fraction of a second, so you can answer before the timer runs out. It learns from the game itself: every answer the game confirms in green makes it more reliable.

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

OpenRok watches the game on its own: there is nothing to click.

1. **Finds the game window** ("Rise of Kingdoms") and looks at it about 15 times per second, only while the game is the active window.
2. **Detects a new question.** A fingerprint of the question text tells a new question from the same one, even with compression or lighting changes.
3. **Reads it** with [Tesseract](https://github.com/tesseract-ocr/tesseract) (via `tesserocr`), with the question and the four options in parallel. The Tesseract models are loaded once and bundled with the app.
4. **Finds the answer:**
   - first in an image cache of questions already seen on this computer, which skips the OCR;
   - then in the question database, using fuzzy matching ([RapidFuzz](https://github.com/rapidfuzz/RapidFuzz)) that tolerates OCR errors without mixing up questions that differ in one word;
   - only if both fail, it asks an **AI** from the provider you choose for the letter (optional).
5. **Marks it in the game:** a glowing outline around the right option. It is **green** when the answer comes from the database and **yellow** when it is an AI suggestion. Clicks go straight through the outline to the game.
6. **Learns from the game.** When the game shows the official answer in green, OpenRok stores *that* answer in a local SQLite database. Nothing the AI says is saved unless the game confirms it, and wrong database answers are corrected automatically (with undo).

OpenRok only looks at the screen. It does not read or change the game's memory or files, and it never clicks or types for you.

**Speed** (replay of a real game video): about 60–70 ms from the question appearing to the outline on an idle computer, and about 20–30 ms for questions already seen. With the game itself running on the same computer, the OCR competes for the CPU and it can take up to about 0.3 s.

---

## Languages

| Language | OCR | Database |
|---|---|---|
| English | `eng` | `data/perguntas_respostas_en.csv` |
| Português | `por` | `data/perguntas_respostas_pt.csv` |

Switch in **Settings**. The default follows the system language.

---

## Requirements

- **Python 3.12**.
- **Windows** or **Linux**:
  - On Linux the game runs through Wine (e.g. [Rise-of-Kingdoms-Linux-Installer](https://github.com/limeskat/Rise-of-Kingdoms-Linux-Installer)). OpenRok works on X11 and on Wayland desktops through XWayland; it was tested on KDE Plasma.
  - The Windows build is written but **not tested yet**.
- An **AI** is optional, for questions that are not in the database: Gemini, Groq and OpenRouter have free plans, and Ollama/LM Studio run on your computer.

The Tesseract `eng`/`por` models ship inside the app.

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

On Windows the bundled `wheels/tesserocr-*.whl` installs `tesserocr` without compiling.

---

## Usage

```bash
python -m openrok
```

1. Open the game on a Lyceum of Wisdom exam.
2. OpenRok's **Home** tab shows "Watching". As each question appears, the right option gets the outline.
3. The **Database** tab lists every question with its status (confirmed by the game, corrected, or original). From there you can search, export confirmed answers, import a CSV and undo the last correction.
4. The **Settings** tab has the language, outline opacity, keep on top, start with the system and **Calibrate areas**. Calibrating is only needed if the outline doesn't match the boxes at your window size: drag a rectangle around the question and the four options.

Closing the window keeps OpenRok in the system tray; use **Quit** there to exit.

### AI (optional)

In the **AI** tab, pick a provider, paste the key and click **Test**: OpenRok asks a known question from the database and shows whether the AI got it right and how long it took. The key is kept in the system vault (Credential Manager on Windows, KWallet/Secret Service on Linux), never in a file.

| Provider | Free | Notes |
|---|---|---|
| Google Gemini | yes | key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Groq | yes | key at [console.groq.com/keys](https://console.groq.com/keys) |
| OpenRouter | yes | `:free` models; key at [openrouter.ai/keys](https://openrouter.ai/keys) |
| Ollama / LM Studio | yes | run on your computer, no key |
| OpenAI, Anthropic, DeepSeek | no | pay per use |
| Custom | — | any server compatible with the OpenAI API |

The **Model** field takes any model of the provider; empty means the default. The AI only suggests (yellow outline) and never writes to the database. An existing `GEMINI_API_KEY` keeps working with Gemini.

### Building the executable

```bash
pyinstaller main.spec
```

### Tests

```bash
pytest                       # unit, interface and X11 tests + replay of a real game video
python -m bench.replay       # what the watcher does with the video, and how long each answer took
python -m bench.comparar_v1  # before/after benchmark against the first version
```

---

## Project structure

```
OpenRok/
├── openrok/            # The app
│   ├── vigia.py        # Watcher: detects questions, suggests, learns from the game's green
│   ├── tela.py         # Reads option colors and the question fingerprint
│   ├── ocr.py          # Tesseract (bundled models in tessdata/)
│   ├── conhecimento.py # Database + what this computer learned (SQLite, armazem.py)
│   ├── plataforma.py   # Game window and capture (X11 on Linux, Win32 on Windows)
│   ├── ia.py           # AI providers (OpenAI-compatible); the key lives in the vault (cofre.py)
│   └── ui/             # Qt interface: tabs, overlay, calibration
├── data/               # Question/answer databases (EN, PT)
├── tests/              # Tests, with real screenshots and video in tests/fixtures/
├── bench/              # Replay and benchmarks
└── docs/superpowers/   # Design spec and implementation plans
```

---

## Tech stack

- **Python** + **PySide6 (Qt)** for the interface and overlay
- **Tesseract / tesserocr**, **OpenCV**, **Pillow** for reading the screen
- **RapidFuzz** for fuzzy matching
- **SQLite** for what OpenRok learns
- **python-xlib** (Linux) and **mss** (Windows) for window capture
- **httpx** for the optional AI (any OpenAI-compatible provider) and **keyring** to store the key
- **pytest** + **pytest-qt** for tests, and **PyInstaller** for packaging

---

## Disclaimer

This project was built for study purposes and as a personal helper tool. Use it at your own risk and in accordance with the Rise of Kingdoms terms of service.

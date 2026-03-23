<div align="center">

<img src="https://img.shields.io/badge/S.T.R.I.X-ROG%20AI-ff0033?style=for-the-badge&logo=asus&logoColor=white"/>

# S.T.R.I.X
### Strategic Tactical Response Intelligence Xystem

![Python](https://img.shields.io/badge/Python-3.11+-00e5ff?style=for-the-badge&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-GUI-ff0033?style=for-the-badge&logo=qt&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local_AI-ffd700?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-0088cc?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-ff0033?style=for-the-badge)

**A cinematic ROG-themed AI desktop assistant with a tactical HUD.**  
**Runs 100% locally on your PC using Ollama — no cloud, no subscriptions.**

</div>

---

## Preview

> Tactical HUD interface · Voice input · Real-time system stats · Live APIs

```
[STRIX] STRIX reporting for duty. All models hot, all tools sharp. Let's go.
[YOU]   weather
[STRIX] Weather in Pune, IN — Clear Sky | Temp: 31.2°C (feels 29.1°C) | Humidity: 13%
[YOU]   bitcoin price
[STRIX] Bitcoin is currently at USD 67,420 | INR 56,23,450
[YOU]   create a file on desktop named strix-notes
[STRIX] Done. Created strix-notes.txt on your Desktop.
[YOU]   system status
[STRIX] CPU: 0.5% | 32 Cores | RAM: 9.17 / 16.33 GB | PWR: 43% CHARGING | NET: 192.168.1.9
```

---

## Screenshot

![STRIX GUI](screenshot.png)

> *STRIX HUD — Communication Channel, System Metrics, Quick Access panel, and the tactical radar display running live on Windows.*

---

## Features

| Category | What STRIX Can Do |
|---|---|
| **AI Chat** | Natural conversation using local Ollama models (phi3, llama3.1, qwen2.5-coder) |
| **Voice** | Speak to STRIX, hear responses via TTS |
| **Desktop Control** | Create files, folders, open apps on Windows |
| **Weather** | Live weather for your city (OpenWeatherMap) |
| **News** | Latest tech headlines via NewsAPI |
| **Crypto** | Live Bitcoin, Ethereum, and top coin prices |
| **Wikipedia** | Instant knowledge lookup |
| **Currency** | Real-time exchange rates (USD, INR, EUR, etc.) |
| **NASA** | Astronomy Picture of the Day |
| **GitHub** | Look up any GitHub profile |
| **IP Info** | Your public IP and location |
| **System Stats** | Live CPU, RAM, Battery, Network — shown on HUD |
| **Projects** | Generate Java, Python, C, C++ project templates |
| **Memory** | Remembers your preferences across sessions |
| **Export Chat** | Export your full conversation log |

---

## AI Models

STRIX uses three specialized local models via Ollama:

| Role | Model | Purpose |
|---|---|---|
| **Chat** | `phi3:latest` | Fast general conversation |
| **Reasoning** | `llama3.1` | Deep thinking and analysis |
| **Coding** | `qwen2.5-coder` | Code generation and debugging |

Switch the active model from the HUD's **AI MODELS** panel at any time.

---

## Project Structure

```
strix/
├── strix.py                # Entry point
├── strix_gui.py            # Tactical ROG-themed PySide6 HUD
├── strix_tts.py            # Text-to-speech
├── START_STRIX.bat         # One-click launcher (starts Ollama + STRIX)
├── CREATE_SHORTCUT.bat     # Creates Desktop shortcut
├── requirements.txt
├── .env                    # Your API keys (not in git)
├── .env.example            # Template
│
├── api/
│   ├── weather.py          # OpenWeatherMap
│   ├── news.py             # NewsAPI
│   └── extras.py           # Crypto, Wikipedia, NASA, IP, Currency, GitHub
│
├── brain/
│   ├── core.py             # Central brain controller
│   ├── input_processor.py  # Voice + text processing
│   ├── planner.py          # LLM task planner
│   ├── router.py           # Routes to tools or LLM
│   └── executor.py         # Executes task plans
│
├── memory/
│   ├── memory_db.py        # SQLite memory system
│   └── strix_memory.db     # Auto-created
│
├── models/
│   └── llm_interface.py    # Ollama API calls
│
└── tools/
    ├── system_tools.py     # CPU, RAM, battery, network
    ├── search_tools.py     # File search and reading
    ├── project_tools.py    # Project generators
    └── windows_tools.py    # Desktop file and app control
```

---

## Installation

### Requirements
- Windows 10 or 11
- Python 3.11 or newer
- [Ollama](https://ollama.com) installed

### Step 1 — Clone the repo
```bash
git clone https://github.com/prahaldgadekar/strix-ai.git
cd strix-ai
```

### Step 2 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Pull Ollama models
```bash
ollama pull phi3
ollama pull llama3.1
ollama pull qwen2.5-coder:7b
```

### Step 4 — Set up your API keys
```bash
copy .env.example .env
```
Open `.env` and fill in your keys (see API Keys section below).

### Step 5 — Create Desktop shortcut (one time only)
```
Double-click CREATE_SHORTCUT.bat
```

### Step 6 — Launch STRIX
```
Double-click the STRIX shortcut on your Desktop
```
STRIX starts Ollama automatically every time.

---

## API Keys

All APIs have free tiers. No credit card required.

| API | Get Key | Free Limit |
|---|---|---|
| OpenWeatherMap | [openweathermap.org/api](https://openweathermap.org/api) | 1,000 calls/day |
| NewsAPI | [newsapi.org](https://newsapi.org) | 100 calls/day |
| NASA | [api.nasa.gov](https://api.nasa.gov) | Unlimited |
| GitHub | [github.com/settings/tokens](https://github.com/settings/tokens) | 5,000/hour |

> Crypto, Wikipedia, IP info, Currency, and Jokes work with **no API key at all**.

---

## Configuration

Edit your `.env` file:

```env
OPENWEATHER_API_KEY=your_key
NEWS_API_KEY=your_key
DEFAULT_CITY=Pune
OLLAMA_BASE_URL=http://localhost:11434
CHAT_MODEL=phi3
REASONING_MODEL=llama3.1
CODING_MODEL=qwen2.5-coder:7b
NASA_KEY=DEMO_KEY
GITHUB_USERNAME=your_github_username
WAKE_WORD=strix
```

---

## Usage Examples

Just type or speak naturally:

```
weather                          → Live weather for your city
bitcoin price                    → Current BTC price in USD and INR
top crypto                       → Top 5 coins by market cap
who is APJ Abdul Kalam           → Wikipedia summary
tell me a joke                   → Programming joke
NASA picture today               → Astronomy Picture of the Day
my ip address                    → Your public IP and location
USD to INR                       → Live exchange rate
latest tech news                 → Top 5 headlines
system status                    → CPU, RAM, battery info
create file on desktop named X   → Creates X.txt on Desktop
create folder named Projects     → Creates folder on Desktop
open notepad                     → Opens Notepad
write a Python function for X    → AI generates code
```

---

## Voice Mode

Click the **VOICE** button or use the wake word. STRIX will:
1. Listen for your command
2. Process it through the active model
3. Speak the response out loud

Toggle voice output anytime with the **VOL ON / VOL OFF** button on the HUD.

---

## Quick Access Panel

The right-side panel gives you one-click shortcuts:

| Key | Action |
|---|---|
| `W` | Weather |
| `N` | Tech News |
| `S` | System Status |
| `C` | Crypto Prices |
| `P` | Projects |

---

## Built With

- [PySide6](https://doc.qt.io/qtforpython/) — Desktop GUI (ROG tactical theme)
- [Ollama](https://ollama.com) — Local AI models
- [phi3](https://ollama.com/library/phi3) — Fast chat model
- [llama3.1](https://ollama.com/library/llama3.1) — Reasoning model
- [qwen2.5-coder](https://ollama.com/library/qwen2.5-coder) — Coding model
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) — Voice input
- [pyttsx3](https://pypi.org/project/pyttsx3/) — Text to speech
- [SQLite](https://www.sqlite.org/) — Session memory

---

## Made By

**Prahlad Gadekar** — Computer Engineering Student, Pune, India

[![GitHub](https://img.shields.io/badge/GitHub-prahaldgadekar-181717?style=flat-square&logo=github)](https://github.com/prahaldgadekar)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-prahladgadekar-0077B5?style=flat-square&logo=linkedin)](https://linkedin.com/in/prahladgadekar)

---

<div align="center">
<i>STRIX reporting for duty. All models hot, all tools sharp. Let's go.</i>
</div>

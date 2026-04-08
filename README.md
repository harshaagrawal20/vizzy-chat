<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/SQLite-Embedded-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />

</p>

# 🎨 Vizzy Chat — Creative Operating System

> A single conversational interface to **create, transform, iterate, and deploy** visual, narrative, and experiential content — for homes and businesses.

Vizzy Chat is an creative co-pilot that interprets your intent, selects the right creative pathway, generates multiple outputs, allows iterative refinement, and remembers your taste over time.

---

## ✨ Features

### For Homes
- 🎨 **Personal Painting** — "Paint something that feels like how my last year felt."
- 🖼️ **Photo Reimagination** — Upload a photo and transform it into any style (renaissance, dreamlike, etc.)
- 📖 **Story Visualization** — Generate stories and visualize them scene by scene
- 💬 **Quote Posters** — Design typographic art for your walls
- 🧠 **Taste Memory** — Vizzy learns your aesthetic preferences over time

### For Businesses
- 💎 **Campaign Visuals** — Premium brand-aligned imagery without looking cheap
- 🏷️ **In-Store Signage** — Posters, menus, seasonal displays
- 📊 **Multi-Surface Deploy** — Export to frame, social, email, and print
- 🎯 **Brand Kit** — Store your brand voice, colours, tagline, and values
- 📋 **Campaign Management** — Organize assets into named campaigns

### Platform Features
- 🔄 **Iterative Refinement** — Refine, regenerate, adjust tone from any output card
- 🖼️ **Image Lightbox** — Click any generated image for fullscreen preview + download
- 💬 **Typing Indicator** — bouncing dots while generating
- 🔔 **Toast Notifications** — Visual feedback on every action
- 📁 **Conversation History** — All chats are saved and reloadable
- 📎 **Image Uploads** — Upload reference images for img2img transformations
- ⌨️ **Keyboard Shortcuts** — `Ctrl + Enter` to send

---

## 📁 Project Structure

```
vizzyyyy/
├── app/
│   ├── static/              # Frontend (HTML, CSS, JS)
│   │   ├── index.html       # Main UI shell
│   │   ├── styles.css       # Premium dark theme + animations
│   │   └── script.js        # Chat logic, lightbox, toasts, state
│   ├── services/
│   │   ├── chat.py          # Conversation orchestration + Claude integration
│   │   └── generator.py     # Image generation pipeline (HF, A1111, ComfyUI, SVG)
│   ├── crud.py              # Database operations
│   ├── db.py                # SQLite schema + migrations
│   ├── main.py              # FastAPI routes
│   ├── schemas.py           # Pydantic models
│   └── settings.py          # Config from .env
├── data/                    # SQLite database (auto-created)
├── generated/               # Generated image outputs (auto-created)
├── uploads/                 # User-uploaded reference images (auto-created)
├── exports/                 # ZIP and export bundles (auto-created)
├── .env                     # Your local config (DO NOT COMMIT)
├── .env.example             # Template for .env
├── requirements.txt         # Python dependencies
├── start.ps1                # Quick-start script (Windows PowerShell)
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** — [Download Python](https://www.python.org/downloads/)
- **Git** — [Download Git](https://git-scm.com/downloads)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/vizzyyyy.git
cd vizzyyyy
```

### 2. Create a Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example env file and add your API keys:

```bash
cp .env.example .env
```

Then edit `.env` with your details:

```env
# ─── Image Generation Backend ───────────────────────────
# Options: huggingface | comfyui | automatic1111 | svg
VIZZY_IMAGE_BACKEND=huggingface

# ─── HuggingFace (recommended for quick start) ──────────
HF_TOKEN=hf_your_token_here
HF_MODEL=black-forest-labs/FLUX.1-schnell

# ─── Local Backends (optional) ──────────────────────────
COMFYUI_BASE_URL=http://127.0.0.1:8188
A1111_BASE_URL=http://127.0.0.1:7860

# ─── Image Settings ────────────────────────────────────
VIZZY_IMAGE_WIDTH=512
VIZZY_IMAGE_HEIGHT=512
VIZZY_IMAGE_STEPS=12

# ─── Claude for Copy/Story Generation (optional) ────
# ANTHROPIC_API_KEY=sk-ant-your-key-here
```

> **Note:** If no image backend is configured, Vizzy falls back to generative SVG artwork — the app is still fully functional.

### 5. Run the Server

```bash
uvicorn app.main:app --reload
```

Or use the PowerShell quick-start script:

```powershell
.\start.ps1
```

### 6. Open in Browser

Navigate to **[http://localhost:8000](http://localhost:8000)** and start creating!

---

## 🔧 Configuration Guide

### Image Generation Backends

| Backend | Setup | Best For |
|---|---|---|
| **`huggingface`** | Get a [free HF token](https://huggingface.co/settings/tokens), set `HF_TOKEN` | Quick start, cloud-based |
| **`automatic1111`** | Run [A1111 WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) locally with `--api` flag | Full control, local GPU |
| **`comfyui`** | Run [ComfyUI](https://github.com/comfyanonymous/ComfyUI) locally | Advanced workflows, local GPU |
| **`svg`** | No setup needed (default fallback) | Testing, no GPU required |

### Recommended HuggingFace Models

| Model | Speed | Quality | Notes |
|---|---|---|---|
| `black-forest-labs/FLUX.1-schnell` | ⚡ Fast (4 steps) | ★★★★☆ | **Recommended** — best speed/quality ratio |
| `stabilityai/stable-diffusion-xl-base-1.0` | 🐢 Slow (20 steps) | ★★★★★ | Highest quality, slower |
| `runwayml/stable-diffusion-v1-5` | ⚡ Fast | ★★★☆☆ | Legacy, lightweight |

### Claude (Optional)

For model-generated copy, headlines, story outlines, and CTAs, add your Anthropic API key:

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Without this key, Vizzy uses built-in templates for copy generation — still works, just less personalized.

---

## 🗄️ Database

Vizzy uses **SQLite** — no external database setup needed. The database is auto-created at `data/vizzy.db` on first run.

**Tables:**
| Table | Purpose |
|---|---|
| `conversations` | Chat sessions with title, mode, timestamps |
| `messages` | All conversation messages with assets |
| `home_profiles` | Taste memory (mood keywords, colour palette, favourites) |
| `business_profiles` | Brand kit (name, voice, colours, tagline, values) |
| `campaigns` | Named campaigns with goal, season, surfaces |
| `campaign_assets` | Assets attached to campaigns |
| `export_log` | Audit trail of all exports |

To reset the database, simply delete `data/vizzy.db` and restart the server.

---

## 🛣️ API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serve the chat interface |
| `POST` | `/api/chat` | Send a prompt, get creative directions |
| `GET` | `/api/conversations` | List all conversations |
| `GET` | `/api/conversations/{id}` | Load a specific conversation |
| `POST` | `/api/uploads` | Upload a reference image |
| `GET` | `/api/memory/home/profile` | Get home taste profile |
| `POST` | `/api/memory/home/feedback` | Send like/dislike feedback |
| `GET` | `/api/memory/business/profile` | Get business brand kit |
| `POST` | `/api/memory/business/profile` | Update business brand kit |
| `GET` | `/api/campaigns` | List all campaigns |
| `POST` | `/api/campaigns` | Create a new campaign |
| `POST` | `/api/campaigns/{id}/assets` | Attach assets to a campaign |
| `POST` | `/api/export` | Export assets (ZIP, frame, social, email, print) |

---

## 🧪 Troubleshooting

### "No images are generated"
- Check that your `HF_TOKEN` is valid and has read access
- Ensure `VIZZY_IMAGE_BACKEND` matches your setup
- The app will fall back to SVG art if the backend is unreachable

### "ModuleNotFoundError"
- Make sure your virtual environment is activated
- Run `pip install -r requirements.txt`

### "Port 8000 already in use"
```bash
uvicorn app.main:app --reload --port 8001
```

### "Database locked"
- Only one instance of the server should run at a time
- Stop any background uvicorn processes and restart

---


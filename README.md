<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Groq-LLaMA--3.3--70B-f55036?style=for-the-badge&logo=groq&logoColor=white" alt="Groq" />
  <img src="https://img.shields.io/badge/SQLite-Embedded-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
</p>

# 🎨 AtelierAI — AI Creative Studio

> A full-stack generative AI platform with a multi-backend image pipeline, MCP agentic tool calling, interactive Knowledge Graph extraction, and persistent taste memory.

AtelierAI is a single conversational workspace to **create, transform, iterate, and deploy** visual, narrative, and experiential content — for both personal expression and commercial brand applications.

---

## ✨ Key Features

### 🎨 Multi-Backend Generative Image Pipeline
- **Adaptive Backend Switching**: Supports fal.ai (FLUX.1-schnell), HuggingFace Inference, Automatic1111, ComfyUI, and Groq-powered AI SVG vector artwork.
- **Graceful Fallback Chains**: Seamlessly falls back through backends if an API limit or network error occurs.
- **Image-to-Image (img2img)**: Upload reference photos for style transfer and reimagination.

### 🤖 MCP Agentic Tool-Calling Loop
- Powered by **Groq (LLaMA 3.3-70B)** with up to 6 autonomous reasoning iterations.
- Integrated Tools:
  - 📖 `wikipedia_lookup` — Fetch topic summaries from MediaWiki API.
  - 🧮 `calculator` — Safely evaluate mathematical expressions.
  - 🔍 `web_search` — Real-time web inquiry and search snippets.
  - 📄 `file_reader` — Inspect generated SVGs, text, and upload assets.

### 🕸️ Knowledge Graph Extraction
- Extracts factual `(subject, predicate, object)` triples from conversations using LLM NLP analysis.
- Builds dynamic graph structures using **NetworkX** and renders interactive HTML visual widgets via **PyVis**.

### 🧠 Taste Memory & Brand Kit
- **Home Mode**: Learns personal aesthetic preferences, mood keywords, and favourite color palettes over time.
- **Business Mode**: Brand Kit management (tone, voice, logo, tagline, brand colors) for campaign-ready assets across frame, social, email, and print.

---

## 📁 Project Structure

```
atelier-ai/
├── app/
│   ├── static/              # Frontend UI (HTML, CSS, JS)
│   │   ├── index.html       # Shell interface
│   │   ├── styles.css       # Dark theme design system
│   │   └── script.js        # State, lightboxes, toasts, chat
│   ├── services/
│   │   ├── chat.py          # Conversation orchestration
│   │   ├── generator.py     # Multi-backend image pipeline (FLUX, SVG)
│   │   ├── mcp_tools.py     # MCP Agentic tool execution loop
│   │   └── knowledge_graph.py # Entity triple extraction & PyVis rendering
│   ├── crud.py              # SQLite database operations
│   ├── db.py                # Database schema & migrations
│   ├── main.py              # FastAPI application routes
│   ├── schemas.py           # Pydantic data models
│   └── settings.py          # Config loader (.env)
├── data/                    # SQLite database (auto-created)
├── generated/               # Generated image & graph outputs
├── uploads/                 # User-uploaded reference images
├── exports/                 # Export bundles & ZIP files
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/atelier-ai.git
cd atelier-ai
```

### 2. Set Up Virtual Environment

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

Create a `.env` file based on `.env.example`:

```env
VIZZY_IMAGE_BACKEND=huggingface

# Groq API Key (For MCP Agent, SVG Generation & Knowledge Graph)
GROQ_API_KEY=gsk_your_groq_key_here

# HuggingFace Token (Optional for FLUX image gen)
HF_TOKEN=hf_your_token_here
HF_MODEL=black-forest-labs/FLUX.1-schnell

# fal.ai Key (Optional)
FAL_KEY=your_fal_key_here
```

### 5. Run the Server

```bash
uvicorn app.main:app --reload
```

Open **[http://localhost:8000](http://localhost:8000)** in your browser!

---

## 📄 License

MIT License. Designed and built with Python, FastAPI, and Groq.


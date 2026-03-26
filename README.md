# Vizzy Chat

Vizzy Chat is a CPU-friendly full-stack creative chat app built with FastAPI, SQLite, and a static chat UI. It supports home and business modes, saves conversations locally, and generates free local SVG visuals for each prompt without needing any paid API.

## What this version includes

- Python backend with `FastAPI`
- Local persistence with `SQLite`
- Chat history and saved conversations
- Home and business creative modes
- Free image generation using deterministic SVG artwork
- Static frontend served by the backend

## Run locally

1. Create a virtual environment:

```powershell
py -m venv .venv
```

2. Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Start the server:

```powershell
uvicorn app.main:app --reload
```

5. Open:

```text
http://127.0.0.1:8000
```

## Notes

- Generated visuals are saved in `generated/`
- Chat data is stored in `data/vizzy.db`
- The current generator is intentionally free and CPU-friendly. Later, you can swap it with Stable Diffusion, ComfyUI, or an external API without changing the chat UX much.

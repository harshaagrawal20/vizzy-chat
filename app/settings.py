from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


def load_dotenv() -> None:
    if not ENV_PATH.exists():
        return

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


load_dotenv()


def _default_steps() -> str:
    model = os.getenv("HF_MODEL", "black-forest-labs/FLUX.1-schnell").lower()
    if "flux.1-schnell" in model:
        return "4"
    return "20"


@dataclass(frozen=True)
class Settings:
    image_backend: str = os.getenv("VIZZY_IMAGE_BACKEND", "svg")
    comfyui_base_url: str = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
    a1111_base_url: str = os.getenv("A1111_BASE_URL", "http://127.0.0.1:7860")
    hf_token: str = os.getenv("HF_TOKEN", "")
    hf_model: str = os.getenv("HF_MODEL", "black-forest-labs/FLUX.1-schnell")
    image_width: int = int(os.getenv("VIZZY_IMAGE_WIDTH", "512"))
    image_height: int = int(os.getenv("VIZZY_IMAGE_HEIGHT", "512"))
    image_steps: int = int(os.getenv("VIZZY_IMAGE_STEPS", _default_steps()))


settings = Settings()

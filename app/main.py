from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import crud
from app.db import init_db
from app.schemas import (
    BusinessProfileUpdateRequest,
    CampaignAssetUpdateRequest,
    CampaignCreateRequest,
    ChatRequest,
    ChatResponse,
    Conversation,
    ConversationDetail,
    CreateConversationRequest,
    ExportRequest,
    FeedbackRequest,
    MemorySnapshot,
    Message,
    UploadResponse,
)
from app.services.chat import build_assistant_reply, handle_export, suggest_title
from app.services.generator import GENERATED_DIR, ensure_generated_dir
from app.settings import settings


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
EXPORTS_DIR = BASE_DIR / "exports"
ensure_generated_dir()
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Vizzy Chat", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    ensure_generated_dir()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "image_backend": settings.image_backend,
        "hf_model": settings.hf_model,
        "hf_token_configured": bool(settings.hf_token),
        "comfyui_base_url": settings.comfyui_base_url,
        "a1111_base_url": settings.a1111_base_url,
    }


@app.get("/api/memory/{mode}", response_model=MemorySnapshot)
def api_get_memory(mode: str) -> MemorySnapshot:
    if mode not in {"home", "business"}:
        raise HTTPException(status_code=400, detail="Invalid mode")
    return MemorySnapshot(**crud.get_memory(mode))


@app.get("/api/memory/home/profile")
def api_get_home_profile() -> dict:
    return crud.get_home_profile()


@app.post("/api/memory/home/feedback")
def api_record_home_feedback(payload: FeedbackRequest) -> dict:
    return crud.record_feedback(payload.prompt, payload.asset_filename, payload.signal)


@app.get("/api/memory/business/profile")
def api_get_business_profile() -> dict:
    return crud.get_business_profile()


@app.post("/api/memory/business/profile")
def api_upsert_business_profile(payload: BusinessProfileUpdateRequest) -> dict:
    return crud.upsert_business_profile(**payload.model_dump())


@app.get("/api/campaigns")
def api_list_campaigns() -> list[dict]:
    return crud.list_campaigns()


@app.post("/api/campaigns")
def api_create_campaign(payload: CampaignCreateRequest) -> dict:
    return crud.create_campaign(
        name=payload.name,
        goal=payload.goal,
        season=payload.season,
        surfaces=payload.surfaces,
    )


@app.post("/api/campaigns/{campaign_id}/assets")
def api_update_campaign_assets(campaign_id: int, payload: CampaignAssetUpdateRequest) -> dict:
    campaign = crud.update_campaign_assets(
        campaign_id=campaign_id,
        asset_filenames=payload.asset_filenames,
        copy_snippets=payload.copy_snippets,
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@app.post("/api/export")
def api_export_assets(payload: ExportRequest) -> dict:
    result = handle_export(
        surface=payload.surface,
        asset_filenames=payload.asset_filenames,
        conversation_id=payload.conversation_id,
    )

    if result.get("file_path"):
        crud.record_export(payload.conversation_id, payload.surface, result["file_path"])
    elif result.get("download_urls"):
        for url in result["download_urls"]:
            crud.record_export(payload.conversation_id, payload.surface, url)

    return result


@app.post("/api/uploads", response_model=UploadResponse)
async def api_upload(file: UploadFile = File(...)) -> UploadResponse:
    suffix = Path(file.filename or "upload").suffix.lower() or ".png"
    safe_name = hashlib.sha1(f"{file.filename}-{suffix}".encode("utf-8")).hexdigest()[:12] + suffix
    filepath = UPLOADS_DIR / safe_name
    content = await file.read()
    filepath.write_bytes(content)
    return UploadResponse(attachment={"name": file.filename or safe_name, "url": f"/uploads/{safe_name}", "kind": "image"})


@app.get("/api/conversations", response_model=list[Conversation])
def api_list_conversations() -> list[Conversation]:
    return [Conversation(**item) for item in crud.list_conversations()]


@app.post("/api/conversations", response_model=Conversation)
def api_create_conversation(payload: CreateConversationRequest) -> Conversation:
    record = crud.create_conversation(title=payload.title, mode=payload.mode)
    record["message_count"] = 0
    return Conversation(**record)


@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
def api_get_conversation(conversation_id: int) -> ConversationDetail:
    conversation = crud.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = [Message(**item) for item in crud.get_messages(conversation_id)]
    conversation["message_count"] = len(messages)
    return ConversationDetail(conversation=Conversation(**conversation), messages=messages)


@app.post("/api/chat", response_model=ChatResponse)
def api_chat(payload: ChatRequest) -> ChatResponse:
    conversation = None
    if payload.conversation_id is not None:
        conversation = crud.get_conversation(payload.conversation_id)

    if conversation is None:
        conversation = crud.create_conversation(
            title=suggest_title(payload.prompt, payload.mode),
            mode=payload.mode,
        )

    user_message = crud.add_message(
        conversation_id=conversation["id"],
        role="user",
        tag="Prompt" if payload.mode == "home" else "Brief",
        text=payload.prompt,
        attachments=[item.model_dump() for item in payload.attachments],
    )

    memory = crud.update_memory(payload.mode, payload.prompt)
    brand_context = crud.get_business_profile() if payload.mode == "business" else None
    assistant_tag, assistant_text, assets = build_assistant_reply(
        prompt=payload.prompt,
        mode=payload.mode,
        memory_keywords=memory["keywords"],
        attachments=[item.model_dump() for item in payload.attachments],
        brand_context=brand_context,
        conversation_id=conversation["id"],
    )
    assistant_message = crud.add_message(
        conversation_id=conversation["id"],
        role="assistant",
        tag=assistant_tag,
        text=assistant_text,
        assets=assets,
    )

    conversation["message_count"] = len(crud.get_messages(conversation["id"]))

    return ChatResponse(
        conversation=Conversation(**conversation),
        user_message=Message(**user_message),
        assistant_message=Message(**assistant_message),
        memory=MemorySnapshot(**memory),
    )


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/generated", StaticFiles(directory=GENERATED_DIR), name="generated")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/exports", StaticFiles(directory=EXPORTS_DIR), name="exports")

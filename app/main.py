from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import crud
from app.db import init_db
from app.schemas import (
    ChatRequest,
    ChatResponse,
    Conversation,
    ConversationDetail,
    CreateConversationRequest,
    Message,
)
from app.services.chat import build_assistant_reply, suggest_title
from app.services.generator import GENERATED_DIR, ensure_generated_dir


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"
ensure_generated_dir()

app = FastAPI(title="Vizzy Chat", version="1.0.0")

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


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok"}


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
    return ConversationDetail(
        conversation=Conversation(**conversation),
        messages=messages,
    )


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
    )

    assistant_tag, assistant_text, assets = build_assistant_reply(
        prompt=payload.prompt,
        mode=payload.mode,
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
    )


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/generated", StaticFiles(directory=GENERATED_DIR), name="generated")

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Mode = Literal["home", "business"]


class AssetAction(BaseModel):
    label: str


class Asset(BaseModel):
    type: str
    title: str
    description: str
    preview_url: str
    actions: list[AssetAction]


class Message(BaseModel):
    id: int
    conversation_id: int
    role: str
    tag: str
    text: str
    created_at: str
    assets: list[Asset] = Field(default_factory=list)


class Conversation(BaseModel):
    id: int
    title: str
    mode: Mode
    created_at: str
    message_count: int | None = None


class CreateConversationRequest(BaseModel):
    title: str = "Untitled chat"
    mode: Mode


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    mode: Mode
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    conversation: Conversation
    user_message: Message
    assistant_message: Message


class ConversationDetail(BaseModel):
    conversation: Conversation
    messages: list[Message]

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Mode = Literal["home", "business"]
AttachmentKind = Literal["image", "file"]
FeedbackSignal = Literal["like", "dislike", "refine"]


class Attachment(BaseModel):
    name: str
    url: str
    kind: AttachmentKind = "image"


class AssetAction(BaseModel):
    label: str
    prompt_suffix: str | None = None
    intent: str | None = None
    action: str | None = None


class Asset(BaseModel):
    type: str
    title: str
    description: str
    preview_url: str | None = None
    text_content: str | None = None
    filename: str | None = None
    task_type: str | None = None
    asset_filenames: list[str] = Field(default_factory=list)
    conversation_id: int | None = None
    actions: list[AssetAction] = Field(default_factory=list)


class Message(BaseModel):
    id: int
    conversation_id: int
    role: str
    tag: str
    text: str
    created_at: str
    assets: list[Asset] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)


class Conversation(BaseModel):
    id: int
    title: str
    mode: Mode
    created_at: str
    message_count: int | None = None


class MemorySnapshot(BaseModel):
    mode: Mode
    keywords: list[str] = Field(default_factory=list)
    updated_at: str | None = None


class CreateConversationRequest(BaseModel):
    title: str = "Untitled chat"
    mode: Mode


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    mode: Mode
    conversation_id: int | None = None
    attachments: list[Attachment] = Field(default_factory=list)


class ChatResponse(BaseModel):
    conversation: Conversation
    user_message: Message
    assistant_message: Message
    memory: MemorySnapshot


class ConversationDetail(BaseModel):
    conversation: Conversation
    messages: list[Message]


class UploadResponse(BaseModel):
    attachment: Attachment


class FeedbackRequest(BaseModel):
    prompt: str = ""
    asset_filename: str = ""
    signal: FeedbackSignal


class BusinessProfileUpdateRequest(BaseModel):
    business_name: str = ""
    business_type: str = ""
    brand_voice: str = ""
    primary_colours: list[str] = Field(default_factory=list)
    secondary_colours: list[str] = Field(default_factory=list)
    logo_url: str = ""
    font_preference: str = ""
    tagline: str = ""
    values_keywords: list[str] = Field(default_factory=list)


class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    goal: str = ""
    season: str = ""
    surfaces: list[str] = Field(default_factory=list)


class CampaignAssetUpdateRequest(BaseModel):
    asset_filenames: list[str] = Field(default_factory=list)
    copy_snippets: list[str] = Field(default_factory=list)


class ExportRequest(BaseModel):
    surface: str
    asset_filenames: list[str] = Field(default_factory=list)
    conversation_id: int | None = None


class GenericDictResponse(BaseModel):
    data: dict[str, Any]

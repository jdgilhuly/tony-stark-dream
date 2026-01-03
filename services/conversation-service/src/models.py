from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    id: str
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class ConversationRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context_hints: list[str] = Field(default_factory=list)
    include_briefing: bool = False


class ConversationResponse(BaseModel):
    id: str
    conversation_id: str
    message: Message
    suggested_actions: list[dict] = Field(default_factory=list)
    processing_time_ms: int = 0


class Conversation(BaseModel):
    id: str
    user_id: str
    messages: list[Message] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: datetime = Field(default_factory=datetime.utcnow)
    summary: Optional[str] = None


class UserContext(BaseModel):
    user_id: str
    preferred_title: str = "sir"
    timezone: str = "UTC"
    location: Optional[str] = None
    preferences: dict = Field(default_factory=dict)


class BedrockMessage(BaseModel):
    role: str
    content: str


class BedrockRequest(BaseModel):
    anthropic_version: str = "bedrock-2023-05-31"
    max_tokens: int = 4096
    system: str = ""
    messages: list[BedrockMessage]


class BedrockResponse(BaseModel):
    id: str
    type: str
    role: str
    content: list[dict]
    model: str
    stop_reason: str
    usage: dict

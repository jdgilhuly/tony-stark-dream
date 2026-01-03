"""JARVIS Notification Service - Push notifications and real-time updates."""

import logging
import uuid
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Any
from functools import lru_cache
from enum import Enum
import json

from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import redis.asyncio as redis
from jose import jwt, JWTError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    service_name: str = "notification-service"
    host: str = "0.0.0.0"
    port: int = 8008

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "development-secret-change-in-production"
    jwt_algorithm: str = "HS256"

    # Firebase configuration (optional)
    firebase_credentials_path: Optional[str] = None

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


# Enums
class NotificationType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    BRIEFING = "briefing"
    REMINDER = "reminder"
    TASK_UPDATE = "task_update"
    SYSTEM = "system"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DeliveryChannel(str, Enum):
    WEBSOCKET = "websocket"
    PUSH = "push"
    EMAIL = "email"
    ALL = "all"


# Models
class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str
    message: str
    data: dict = Field(default_factory=dict)
    channel: DeliveryChannel = DeliveryChannel.WEBSOCKET
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class CreateNotificationRequest(BaseModel):
    user_id: str
    type: NotificationType = NotificationType.INFO
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str
    message: str
    data: dict = Field(default_factory=dict)
    channel: DeliveryChannel = DeliveryChannel.WEBSOCKET


class DeviceToken(BaseModel):
    user_id: str
    token: str
    platform: str  # ios, android, web
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RegisterDeviceRequest(BaseModel):
    token: str
    platform: str


# Redis client
_redis: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


# Auth
async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return {"user_id": payload.get("userId")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_user_from_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return {"user_id": payload.get("userId")}
    except JWTError:
        return None


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected via WebSocket")

    async def disconnect(self, user_id: str, websocket: WebSocket):
        async with self.lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_to_user(self, user_id: str, message: dict) -> bool:
        if user_id not in self.active_connections:
            return False

        disconnected = []
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(user_id, ws)

        return len(self.active_connections.get(user_id, [])) > 0

    async def broadcast(self, message: dict):
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)

    def is_user_connected(self, user_id: str) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


manager = ConnectionManager()


# Notification storage
class NotificationStore:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def init(self):
        self.redis = await get_redis()

    def _key(self, notification_id: str) -> str:
        return f"notification:{notification_id}"

    def _user_key(self, user_id: str) -> str:
        return f"user:{user_id}:notifications"

    def _device_key(self, user_id: str) -> str:
        return f"user:{user_id}:devices"

    async def save(self, notification: Notification) -> None:
        await self.redis.set(
            self._key(notification.id),
            notification.model_dump_json(),
            ex=86400 * 7  # 7 days TTL
        )
        await self.redis.lpush(self._user_key(notification.user_id), notification.id)
        await self.redis.ltrim(self._user_key(notification.user_id), 0, 99)  # Keep last 100

    async def get(self, notification_id: str) -> Optional[Notification]:
        data = await self.redis.get(self._key(notification_id))
        if data:
            return Notification.model_validate_json(data)
        return None

    async def get_user_notifications(
        self,
        user_id: str,
        limit: int = 20,
        unread_only: bool = False
    ) -> list[Notification]:
        notification_ids = await self.redis.lrange(self._user_key(user_id), 0, limit - 1)
        notifications = []
        for nid in notification_ids:
            notification = await self.get(nid)
            if notification:
                if unread_only and notification.read:
                    continue
                notifications.append(notification)
        return notifications

    async def mark_as_read(self, notification_id: str) -> bool:
        notification = await self.get(notification_id)
        if notification:
            notification.read = True
            await self.redis.set(
                self._key(notification_id),
                notification.model_dump_json(),
                ex=86400 * 7
            )
            return True
        return False

    async def save_device_token(self, device: DeviceToken) -> None:
        await self.redis.hset(
            self._device_key(device.user_id),
            device.token,
            json.dumps({"platform": device.platform, "created_at": device.created_at.isoformat()})
        )

    async def get_device_tokens(self, user_id: str) -> list[DeviceToken]:
        devices = await self.redis.hgetall(self._device_key(user_id))
        tokens = []
        for token, data in devices.items():
            info = json.loads(data)
            tokens.append(DeviceToken(
                user_id=user_id,
                token=token,
                platform=info["platform"],
                created_at=datetime.fromisoformat(info["created_at"])
            ))
        return tokens

    async def remove_device_token(self, user_id: str, token: str) -> None:
        await self.redis.hdel(self._device_key(user_id), token)


notification_store = NotificationStore()


# Push notification sender (Firebase)
async def send_push_notification(notification: Notification) -> bool:
    """Send push notification via Firebase Cloud Messaging."""
    if not settings.firebase_credentials_path:
        logger.warning("Firebase not configured, skipping push notification")
        return False

    try:
        # In production, this would use firebase-admin
        # from firebase_admin import messaging
        # message = messaging.Message(
        #     notification=messaging.Notification(
        #         title=notification.title,
        #         body=notification.message,
        #     ),
        #     data=notification.data,
        #     token=device_token,
        # )
        # messaging.send(message)
        logger.info(f"Push notification sent for {notification.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return False


# Notification delivery
async def deliver_notification(notification: Notification) -> dict:
    """Deliver notification through configured channels."""
    results = {"websocket": False, "push": False}

    # Always try WebSocket first
    if notification.channel in [DeliveryChannel.WEBSOCKET, DeliveryChannel.ALL]:
        results["websocket"] = await manager.send_to_user(
            notification.user_id,
            {
                "type": "notification",
                "data": notification.model_dump(mode="json")
            }
        )

    # Send push notification if configured and user not connected via WebSocket
    if notification.channel in [DeliveryChannel.PUSH, DeliveryChannel.ALL]:
        if not results["websocket"] or notification.priority in [NotificationPriority.HIGH, NotificationPriority.URGENT]:
            results["push"] = await send_push_notification(notification)

    return results


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.service_name}")
    await notification_store.init()
    yield
    if _redis:
        await _redis.close()
    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="JARVIS Notification Service",
    description="Push notifications and real-time updates",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "active_connections": sum(len(c) for c in manager.active_connections.values())
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """WebSocket endpoint for real-time notifications."""
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    user = get_user_from_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return

    user_id = user["user_id"]
    await manager.connect(user_id, websocket)

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to JARVIS notification service",
            "timestamp": datetime.utcnow().isoformat()
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()

                # Handle ping/pong for keepalive
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                # Handle mark as read
                elif data.get("type") == "mark_read":
                    notification_id = data.get("notification_id")
                    if notification_id:
                        await notification_store.mark_as_read(notification_id)
                        await websocket.send_json({
                            "type": "read_confirmed",
                            "notification_id": notification_id
                        })

            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                break

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(user_id, websocket)


@app.post("/notifications", response_model=Notification)
async def create_notification(request: CreateNotificationRequest):
    """Create and deliver a notification (internal service use)."""
    notification = Notification(
        user_id=request.user_id,
        type=request.type,
        priority=request.priority,
        title=request.title,
        message=request.message,
        data=request.data,
        channel=request.channel
    )

    await notification_store.save(notification)
    delivery_results = await deliver_notification(notification)

    logger.info(f"Notification {notification.id} created and delivered: {delivery_results}")
    return notification


@app.get("/notifications", response_model=list[Notification])
async def list_notifications(
    limit: int = 20,
    unread_only: bool = False,
    user: dict = Depends(get_current_user)
):
    """List user's notifications."""
    return await notification_store.get_user_notifications(
        user["user_id"],
        limit=limit,
        unread_only=unread_only
    )


@app.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: dict = Depends(get_current_user)
):
    """Mark a notification as read."""
    notification = await notification_store.get(notification_id)

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    await notification_store.mark_as_read(notification_id)
    return {"success": True}


@app.post("/notifications/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    """Mark all notifications as read."""
    notifications = await notification_store.get_user_notifications(
        user["user_id"],
        limit=100,
        unread_only=True
    )

    for notification in notifications:
        await notification_store.mark_as_read(notification.id)

    return {"success": True, "count": len(notifications)}


@app.post("/devices")
async def register_device(
    request: RegisterDeviceRequest,
    user: dict = Depends(get_current_user)
):
    """Register a device for push notifications."""
    device = DeviceToken(
        user_id=user["user_id"],
        token=request.token,
        platform=request.platform
    )

    await notification_store.save_device_token(device)
    logger.info(f"Registered device for user {user['user_id']}: {request.platform}")

    return {"success": True}


@app.delete("/devices/{token}")
async def unregister_device(
    token: str,
    user: dict = Depends(get_current_user)
):
    """Unregister a device from push notifications."""
    await notification_store.remove_device_token(user["user_id"], token)
    return {"success": True}


@app.get("/devices")
async def list_devices(user: dict = Depends(get_current_user)):
    """List registered devices."""
    devices = await notification_store.get_device_tokens(user["user_id"])
    return {"devices": [d.model_dump(mode="json") for d in devices]}


@app.get("/status/{user_id}")
async def get_user_status(user_id: str):
    """Check if a user is currently connected (internal service use)."""
    return {
        "user_id": user_id,
        "connected": manager.is_user_connected(user_id),
        "connections": len(manager.active_connections.get(user_id, []))
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)

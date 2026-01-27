"""
Wake Word Streaming WebSocket Handler

Handles real-time audio streaming for wake word detection.
"""

import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
import numpy as np

from .wake_word import WakeWordDetector, WakeWordConfig, WakeWordEvent

logger = logging.getLogger(__name__)


class WakeWordStreamHandler:
    """Handles WebSocket streaming for wake word detection."""

    def __init__(self, websocket: WebSocket, user_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.detector: Optional[WakeWordDetector] = None
        self.is_active = False
        self.config = WakeWordConfig(
            model_paths=[],
            threshold=0.5,
            trigger_level=1,
            refractory_period_ms=2000,
            sample_rate=16000,
            chunk_size=1280
        )

    async def initialize(self) -> None:
        """Initialize the wake word detector."""
        self.detector = WakeWordDetector(self.config)

        # Register callback
        self.detector.on_wake_word(self._on_wake_word)

        try:
            await self.detector.initialize()
        except Exception as e:
            logger.warning(f"Wake word model initialization failed, using fallback: {e}")

    def _on_wake_word(self, event: WakeWordEvent) -> None:
        """Handle wake word detection event."""
        asyncio.create_task(self._send_detection(event))

    async def _send_detection(self, event: WakeWordEvent) -> None:
        """Send detection event to client."""
        try:
            await self.websocket.send_json({
                "type": "wake_word_detected",
                "wake_word": event.wake_word,
                "confidence": event.confidence,
                "timestamp": event.timestamp
            })
            logger.info(f"Wake word '{event.wake_word}' detected for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to send detection: {e}")

    async def handle_message(self, data: bytes) -> None:
        """Handle incoming message (audio or config)."""
        # Check if it's JSON (config message)
        if data.startswith(b'{'):
            try:
                message = json.loads(data.decode('utf-8'))
                await self._handle_config(message)
                return
            except json.JSONDecodeError:
                pass

        # Otherwise treat as audio data
        if self.detector and self.is_active:
            self.detector.process_audio(data)

    async def _handle_config(self, config: dict) -> None:
        """Handle configuration update."""
        msg_type = config.get('type')

        if msg_type == 'config':
            if 'threshold' in config:
                self.config.threshold = config['threshold']
                if self.detector:
                    self.detector.set_threshold(config['threshold'])

            if 'refractory_period_ms' in config:
                self.config.refractory_period_ms = config['refractory_period_ms']
                if self.detector:
                    self.detector.set_refractory_period(config['refractory_period_ms'])

            await self.websocket.send_json({
                "type": "config_updated",
                "threshold": self.config.threshold,
                "refractory_period_ms": self.config.refractory_period_ms
            })

        elif msg_type == 'start':
            self.start_detection()
            await self.websocket.send_json({"type": "started"})

        elif msg_type == 'stop':
            self.stop_detection()
            await self.websocket.send_json({"type": "stopped"})

    def start_detection(self) -> None:
        """Start wake word detection."""
        if self.detector:
            self.detector.start()
            self.is_active = True
            logger.info(f"Wake word detection started for user {self.user_id}")

    def stop_detection(self) -> None:
        """Stop wake word detection."""
        if self.detector:
            self.detector.stop()
            self.is_active = False
            logger.info(f"Wake word detection stopped for user {self.user_id}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_detection()


async def handle_wake_word_websocket(websocket: WebSocket, user_id: str) -> None:
    """
    Handle wake word detection WebSocket connection.

    Protocol:
    - Send {"type": "config", "threshold": 0.5} to configure
    - Send {"type": "start"} to begin detection
    - Send binary audio chunks (16-bit PCM, 16kHz, mono)
    - Send {"type": "stop"} to stop detection
    - Receive {"type": "wake_word_detected", "wake_word": "...", "confidence": 0.9}
    """
    handler = WakeWordStreamHandler(websocket, user_id)

    try:
        await handler.initialize()
        handler.start_detection()  # Auto-start on connection

        # Send ready message
        await websocket.send_json({
            "type": "ready",
            "message": "Wake word detection ready. Listening for 'Hey JARVIS'..."
        })

        while True:
            # Receive message (text or binary)
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            if "text" in message:
                data = message["text"].encode('utf-8')
            elif "bytes" in message:
                data = message["bytes"]
            else:
                continue

            await handler.handle_message(data)

    except WebSocketDisconnect:
        logger.info(f"Wake word WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"Wake word WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        await handler.cleanup()

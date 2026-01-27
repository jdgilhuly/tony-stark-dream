"""
Wake Word Detection Service

Uses openWakeWord for customizable wake word detection.
Supports "Hey JARVIS", "JARVIS", and custom wake words.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, List
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class WakeWordConfig:
    """Configuration for wake word detection."""
    model_paths: List[str]  # Paths to .onnx or .tflite models
    threshold: float = 0.5  # Detection threshold (0-1)
    trigger_level: int = 1  # Number of consecutive detections needed
    refractory_period_ms: int = 2000  # Cooldown between activations
    sample_rate: int = 16000
    chunk_size: int = 1280  # ~80ms of audio at 16kHz


@dataclass
class WakeWordEvent:
    """Event emitted when wake word is detected."""
    wake_word: str
    confidence: float
    timestamp: float
    audio_context: Optional[bytes] = None  # Audio around detection


class WakeWordDetector:
    """
    Wake word detector using openWakeWord.

    Supports multiple wake words simultaneously and provides
    callbacks on detection with configurable sensitivity.
    """

    def __init__(self, config: WakeWordConfig):
        self.config = config
        self.model = None
        self.is_listening = False
        self.last_activation_time = 0
        self.callbacks: List[Callable[[WakeWordEvent], None]] = []
        self.audio_buffer: List[bytes] = []
        self.buffer_max_chunks = 20  # Keep ~1.6s of audio context
        self._detection_counts: dict[str, int] = {}

    async def initialize(self) -> None:
        """Initialize the wake word model."""
        try:
            # Import here to avoid loading at module level
            from openwakeword.model import Model

            # Load models - openWakeWord supports multiple wake words
            self.model = Model(
                wakeword_models=self.config.model_paths,
                inference_framework="onnx"
            )

            logger.info(f"Wake word detector initialized with models: {self.config.model_paths}")

        except ImportError:
            logger.warning("openWakeWord not installed, using fallback keyword detection")
            self.model = None
        except Exception as e:
            logger.error(f"Failed to initialize wake word model: {e}")
            raise

    def on_wake_word(self, callback: Callable[[WakeWordEvent], None]) -> None:
        """Register a callback for wake word detection."""
        self.callbacks.append(callback)

    def off_wake_word(self, callback: Callable[[WakeWordEvent], None]) -> None:
        """Unregister a callback."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def _emit_detection(self, event: WakeWordEvent) -> None:
        """Emit detection event to all callbacks."""
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in wake word callback: {e}")

    def process_audio(self, audio_chunk: bytes) -> Optional[WakeWordEvent]:
        """
        Process an audio chunk for wake word detection.

        Args:
            audio_chunk: Raw PCM audio bytes (16-bit, 16kHz, mono)

        Returns:
            WakeWordEvent if wake word detected, None otherwise
        """
        if not self.is_listening:
            return None

        # Add to buffer for context
        self.audio_buffer.append(audio_chunk)
        if len(self.audio_buffer) > self.buffer_max_chunks:
            self.audio_buffer.pop(0)

        # Check refractory period
        current_time = time.time() * 1000
        if current_time - self.last_activation_time < self.config.refractory_period_ms:
            return None

        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0

        if self.model is not None:
            # Use openWakeWord model
            predictions = self.model.predict(audio_array)

            for wake_word, confidence in predictions.items():
                if confidence >= self.config.threshold:
                    # Track consecutive detections
                    self._detection_counts[wake_word] = self._detection_counts.get(wake_word, 0) + 1

                    if self._detection_counts[wake_word] >= self.config.trigger_level:
                        self.last_activation_time = current_time
                        self._detection_counts[wake_word] = 0

                        # Get audio context
                        audio_context = b''.join(self.audio_buffer)

                        event = WakeWordEvent(
                            wake_word=wake_word,
                            confidence=confidence,
                            timestamp=time.time(),
                            audio_context=audio_context
                        )

                        self._emit_detection(event)
                        logger.info(f"Wake word detected: {wake_word} (confidence: {confidence:.2f})")
                        return event
                else:
                    # Reset count if below threshold
                    self._detection_counts[wake_word] = 0
        else:
            # Fallback: simple energy-based detection (for testing)
            energy = np.sqrt(np.mean(audio_array ** 2))
            if energy > 0.1:  # Simple threshold
                logger.debug(f"Fallback detection: energy={energy:.3f}")

        return None

    def start(self) -> None:
        """Start listening for wake words."""
        self.is_listening = True
        self.audio_buffer.clear()
        self._detection_counts.clear()
        logger.info("Wake word detection started")

    def stop(self) -> None:
        """Stop listening for wake words."""
        self.is_listening = False
        logger.info("Wake word detection stopped")

    def is_active(self) -> bool:
        """Check if detector is actively listening."""
        return self.is_listening

    def set_threshold(self, threshold: float) -> None:
        """Update detection threshold."""
        self.config.threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Wake word threshold set to {self.config.threshold}")

    def set_refractory_period(self, period_ms: int) -> None:
        """Update refractory period between activations."""
        self.config.refractory_period_ms = max(0, period_ms)
        logger.info(f"Refractory period set to {self.config.refractory_period_ms}ms")


class WakeWordService:
    """
    High-level service for wake word detection with streaming support.

    Manages the detector lifecycle and provides async streaming interface.
    """

    def __init__(self, config: Optional[WakeWordConfig] = None):
        self.config = config or self._default_config()
        self.detector = WakeWordDetector(self.config)
        self._stream_task: Optional[asyncio.Task] = None

    @staticmethod
    def _default_config() -> WakeWordConfig:
        """Get default configuration for JARVIS wake words."""
        # Default models path - users should download from openWakeWord
        models_dir = Path(__file__).parent.parent / "models" / "wake_words"

        return WakeWordConfig(
            model_paths=[
                str(models_dir / "hey_jarvis.onnx"),
            ],
            threshold=0.5,
            trigger_level=1,
            refractory_period_ms=2000,
            sample_rate=16000,
            chunk_size=1280
        )

    async def initialize(self) -> None:
        """Initialize the wake word service."""
        await self.detector.initialize()

    def on_detection(self, callback: Callable[[WakeWordEvent], None]) -> None:
        """Register detection callback."""
        self.detector.on_wake_word(callback)

    async def start_listening(self, audio_stream: asyncio.Queue) -> None:
        """
        Start listening on an audio stream.

        Args:
            audio_stream: Async queue providing audio chunks
        """
        self.detector.start()

        async def process_stream():
            while self.detector.is_active():
                try:
                    # Get audio chunk with timeout
                    chunk = await asyncio.wait_for(audio_stream.get(), timeout=0.1)
                    self.detector.process_audio(chunk)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing audio stream: {e}")
                    break

        self._stream_task = asyncio.create_task(process_stream())

    async def stop_listening(self) -> None:
        """Stop listening for wake words."""
        self.detector.stop()
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None

    def get_status(self) -> dict:
        """Get current service status."""
        return {
            "is_listening": self.detector.is_active(),
            "threshold": self.config.threshold,
            "refractory_period_ms": self.config.refractory_period_ms,
            "models": self.config.model_paths
        }


# Singleton instance for the service
_wake_word_service: Optional[WakeWordService] = None


def get_wake_word_service() -> WakeWordService:
    """Get or create the wake word service singleton."""
    global _wake_word_service
    if _wake_word_service is None:
        _wake_word_service = WakeWordService()
    return _wake_word_service

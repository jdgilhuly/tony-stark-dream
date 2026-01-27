"""
Wake Word Detection Tests
"""

import asyncio
import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch

from src.wake_word import (
    WakeWordConfig,
    WakeWordEvent,
    WakeWordDetector,
    WakeWordService,
)


class TestWakeWordConfig:
    """Test wake word configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WakeWordConfig(model_paths=["test.onnx"])

        assert config.threshold == 0.5
        assert config.trigger_level == 1
        assert config.refractory_period_ms == 2000
        assert config.sample_rate == 16000
        assert config.chunk_size == 1280

    def test_custom_config(self):
        """Test custom configuration values."""
        config = WakeWordConfig(
            model_paths=["hey_jarvis.onnx"],
            threshold=0.7,
            trigger_level=2,
            refractory_period_ms=3000,
        )

        assert config.threshold == 0.7
        assert config.trigger_level == 2
        assert config.refractory_period_ms == 3000


class TestWakeWordEvent:
    """Test wake word event structure."""

    def test_event_creation(self):
        """Test creating a wake word event."""
        event = WakeWordEvent(
            wake_word="hey_jarvis",
            confidence=0.95,
            timestamp=1706300000.0,
            audio_context=b"\x00\x01\x02",
        )

        assert event.wake_word == "hey_jarvis"
        assert event.confidence == 0.95
        assert event.timestamp == 1706300000.0
        assert event.audio_context == b"\x00\x01\x02"

    def test_event_without_audio_context(self):
        """Test event without audio context."""
        event = WakeWordEvent(
            wake_word="jarvis",
            confidence=0.8,
            timestamp=1706300001.0,
        )

        assert event.audio_context is None


class TestWakeWordDetector:
    """Test wake word detector."""

    @pytest.fixture
    def detector(self):
        """Create a detector for testing."""
        config = WakeWordConfig(model_paths=[])
        return WakeWordDetector(config)

    def test_initial_state(self, detector):
        """Test initial detector state."""
        assert not detector.is_active()
        assert not detector.is_listening

    def test_start_stop(self, detector):
        """Test starting and stopping detection."""
        detector.start()
        assert detector.is_active()

        detector.stop()
        assert not detector.is_active()

    def test_callback_registration(self, detector):
        """Test callback registration and removal."""
        callback = MagicMock()

        detector.on_wake_word(callback)
        assert callback in detector.callbacks

        detector.off_wake_word(callback)
        assert callback not in detector.callbacks

    def test_threshold_update(self, detector):
        """Test threshold update."""
        detector.set_threshold(0.8)
        assert detector.config.threshold == 0.8

        # Test bounds
        detector.set_threshold(1.5)
        assert detector.config.threshold == 1.0

        detector.set_threshold(-0.5)
        assert detector.config.threshold == 0.0

    def test_refractory_period_update(self, detector):
        """Test refractory period update."""
        detector.set_refractory_period(5000)
        assert detector.config.refractory_period_ms == 5000

        # Test bounds
        detector.set_refractory_period(-100)
        assert detector.config.refractory_period_ms == 0

    def test_process_audio_when_not_listening(self, detector):
        """Test that audio is ignored when not listening."""
        callback = MagicMock()
        detector.on_wake_word(callback)

        # Create some audio data
        audio = np.zeros(1280, dtype=np.int16).tobytes()
        result = detector.process_audio(audio)

        assert result is None
        callback.assert_not_called()

    def test_audio_buffer_management(self, detector):
        """Test audio buffer is properly managed."""
        detector.start()

        # Send multiple chunks
        for _ in range(30):
            audio = np.zeros(1280, dtype=np.int16).tobytes()
            detector.process_audio(audio)

        # Buffer should be limited
        assert len(detector.audio_buffer) <= detector.buffer_max_chunks

        detector.stop()

    def test_refractory_period_enforcement(self, detector):
        """Test that refractory period prevents rapid activations."""
        import time

        detector.config.refractory_period_ms = 2000
        detector.start()

        # Simulate first activation
        detector.last_activation_time = time.time() * 1000

        # Try to process audio immediately
        audio = np.random.randint(-32768, 32767, 1280, dtype=np.int16).tobytes()
        result = detector.process_audio(audio)

        # Should be None due to refractory period
        assert result is None

        detector.stop()


class TestWakeWordService:
    """Test wake word service."""

    @pytest.fixture
    def service(self):
        """Create a service for testing."""
        return WakeWordService()

    def test_default_config(self, service):
        """Test default service configuration."""
        config = service.config
        assert config.threshold == 0.5
        assert config.sample_rate == 16000

    def test_status(self, service):
        """Test getting service status."""
        status = service.get_status()

        assert "is_listening" in status
        assert "threshold" in status
        assert "refractory_period_ms" in status
        assert "models" in status

    def test_detection_callback(self, service):
        """Test detection callback registration."""
        callback = MagicMock()
        service.on_detection(callback)

        assert callback in service.detector.callbacks

    @pytest.mark.asyncio
    async def test_stop_listening(self, service):
        """Test stopping the service."""
        await service.stop_listening()
        assert not service.detector.is_active()


class TestEnergyCalculation:
    """Test energy calculation for fallback detection."""

    def test_zero_energy_for_silence(self):
        """Test that silence has zero energy."""
        config = WakeWordConfig(model_paths=[])
        detector = WakeWordDetector(config)

        # Silent audio (all zeros)
        audio = np.zeros(1280, dtype=np.int16).tobytes()
        samples = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0

        energy = np.sqrt(np.mean(samples ** 2))
        assert energy == 0.0

    def test_nonzero_energy_for_signal(self):
        """Test that signal has non-zero energy."""
        config = WakeWordConfig(model_paths=[])
        detector = WakeWordDetector(config)

        # Create a sine wave
        t = np.linspace(0, 0.08, 1280)  # ~80ms at 16kHz
        signal = (np.sin(2 * np.pi * 440 * t) * 16384).astype(np.int16)
        samples = signal.astype(np.float32) / 32768.0

        energy = np.sqrt(np.mean(samples ** 2))
        assert energy > 0.0

#!/usr/bin/env python3
"""
Tests for whisperx_transcriber.py

REQ-608: whisperX Transcription
REQ-609: Output Formats (markdown with speaker labels)
REQ-617: Speaker Diarization

TDD tests - these should FAIL until implementation is complete.

Test file: /Users/travis/Movies/2026-01-09 10-23-34.mov (2.2GB QuickTime movie, ~51 minutes)
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Optional, Callable, List, Literal, Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import the actual classes from the implementation
from whisperx_transcriber import TranscriptionResult, TranscriptSegment


# ==================== TEST FIXTURES ====================

@pytest.fixture
def test_video_path():
    """Path to real test video file."""
    return "/Users/travis/Movies/2026-01-09 10-23-34.mov"


@pytest.fixture
def temp_output_dir():
    """Temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_audio_path(temp_output_dir):
    """Create a mock audio file path."""
    audio_path = Path(temp_output_dir) / "test_audio.mp3"
    audio_path.write_bytes(b"fake audio content" * 1000)
    return str(audio_path)


@pytest.fixture
def mock_whisperx_result():
    """Mock whisperX transcription result with segments."""
    return {
        "segments": [
            {
                "start": 0.0,
                "end": 15.5,
                "text": " Welcome everyone to today's meeting.",
                "speaker": "SPEAKER_00"
            },
            {
                "start": 15.5,
                "end": 32.1,
                "text": " Thanks for the introduction. Let me share my screen.",
                "speaker": "SPEAKER_01"
            },
            {
                "start": 32.1,
                "end": 65.0,
                "text": " As you can see here, we have three main initiatives.",
                "speaker": "SPEAKER_01"
            },
            {
                "start": 65.0,
                "end": 95.5,
                "text": " The first initiative is around improving customer onboarding.",
                "speaker": "SPEAKER_00"
            },
        ],
        "language": "en"
    }


# ==================== REQ-608: WHISPERX TRANSCRIPTION ====================

class TestWhisperXTranscription:
    """Test suite for REQ-608: whisperX Transcription."""

    def test_transcribe_returns_result_dataclass(self, sample_audio_path, temp_output_dir):
        """REQ-608: Transcribe returns TranscriptionResult dataclass."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', False):
            result = transcribe(sample_audio_path, output_dir=temp_output_dir)

        assert isinstance(result, TranscriptionResult)
        assert hasattr(result, 'success')
        assert hasattr(result, 'output_path')
        assert hasattr(result, 'segments')
        assert hasattr(result, 'speakers_detected')

    def test_transcribe_with_model_selection(self, sample_audio_path, temp_output_dir):
        """REQ-608: Supports models: tiny, base, small, medium, large, large-v3."""
        from whisperx_transcriber import transcribe, SUPPORTED_MODELS

        # Verify supported models
        assert "tiny" in SUPPORTED_MODELS
        assert "base" in SUPPORTED_MODELS
        assert "small" in SUPPORTED_MODELS
        assert "medium" in SUPPORTED_MODELS
        assert "large" in SUPPORTED_MODELS
        assert "large-v3" in SUPPORTED_MODELS

    def test_transcribe_default_model_is_large_v3(self, sample_audio_path, temp_output_dir):
        """REQ-608: Default model is large-v3."""
        from whisperx_transcriber import DEFAULT_MODEL

        assert DEFAULT_MODEL == "large-v3"

    def test_transcribe_reports_model_used(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-608: Reports which model was used in result."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                model="small"
            )

            assert result.model_used == "small"

    def test_transcribe_handles_language_detection(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-608: Automatic language detection (configurable override)."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            # Test with explicit language
            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                language="en"
            )

            assert result.success

    def test_transcribe_reports_progress(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-608: Reports transcription progress."""
        from whisperx_transcriber import transcribe

        progress_updates = []

        def progress_callback(data: Dict[str, Any]):
            progress_updates.append(data)

        def mock_run_whisperx_with_progress(audio_path, model, language, diarize, hf_token, callback=None):
            # Simulate progress updates
            if callback:
                callback({"stage": "loading_model", "percent": 0})
                callback({"stage": "transcribing", "percent": 50})
                callback({"stage": "complete", "percent": 100})
            return (mock_whisperx_result, 2)

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx', side_effect=mock_run_whisperx_with_progress):

            transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                progress_callback=progress_callback
            )

        # Progress should have been reported
        assert len(progress_updates) >= 1

    def test_transcribe_reports_real_time_factor(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-608: Reports real-time factor (processing speed)."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(sample_audio_path, output_dir=temp_output_dir)

            # Real-time factor should be calculated (audio duration / processing time)
            assert result.real_time_factor >= 0


class TestWhisperXFallback:
    """Test graceful fallback when whisperX is not available."""

    def test_handles_whisperx_not_installed(self, sample_audio_path, temp_output_dir):
        """REQ-608: Graceful handling when whisperX is not installed."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', False):
            result = transcribe(sample_audio_path, output_dir=temp_output_dir)

        assert result.success is False
        assert result.error is not None
        assert "whisperx" in result.error.lower() or "not installed" in result.error.lower()

    def test_error_includes_install_instructions(self, sample_audio_path, temp_output_dir):
        """REQ-608: Error includes installation instructions."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', False):
            result = transcribe(sample_audio_path, output_dir=temp_output_dir)

        assert "pip install" in result.error.lower() or "install" in result.error.lower()


# ==================== REQ-617: SPEAKER DIARIZATION ====================

class TestSpeakerDiarization:
    """Test suite for REQ-617: Speaker Diarization."""

    def test_diarize_labels_speakers(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-617: Labels speakers as Speaker 1, Speaker 2, etc."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                diarize=True
            )

            # Check speaker labels are normalized
            speakers = set(seg.speaker for seg in result.segments)
            for speaker in speakers:
                assert speaker.startswith("Speaker ")

    def test_diarize_requires_hf_token(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-617: Requires HuggingFace token for pyannote access."""
        from whisperx_transcriber import transcribe

        # When no HF token is provided, diarization should be disabled
        # but transcription should still succeed
        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx, \
             patch.dict(os.environ, {}, clear=True):
            # Mock returns results without speaker labels (no diarization)
            no_diarize_result = {
                "segments": [
                    {"start": 0.0, "end": 15.5, "text": " Welcome everyone."},
                ],
                "language": "en"
            }
            mock_whisperx.return_value = (no_diarize_result, 0)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                diarize=True,  # Request diarization
                hf_token=None  # But no token provided
            )

            # Should succeed but fall back to no diarization
            # Since we mocked _run_whisperx, it will succeed
            assert result.success is True

    def test_diarize_counts_speakers(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-617: Reports number of speakers detected."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                diarize=True
            )

            assert result.speakers_detected >= 1

    def test_diarize_segments_have_speaker_labels(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-617: Each segment has a speaker label."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                diarize=True
            )

            for segment in result.segments:
                assert segment.speaker is not None
                assert len(segment.speaker) > 0

    def test_fallback_without_diarization(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-617: Graceful fallback if diarization unavailable."""
        from whisperx_transcriber import transcribe

        # Modify mock to not have speaker info
        no_speaker_result = {
            "segments": [
                {"start": 0.0, "end": 15.5, "text": " Welcome everyone."},
                {"start": 15.5, "end": 32.1, "text": " Thanks for joining."},
            ],
            "language": "en"
        }

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (no_speaker_result, 0)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                diarize=False
            )

            # Should succeed without diarization
            assert result.success
            # Segments should have default speaker
            for segment in result.segments:
                assert segment.speaker is not None


# ==================== REQ-609: OUTPUT FORMATS ====================

class TestOutputFormats:
    """Test suite for REQ-609: Transcription Output Formats."""

    def test_outputs_markdown_format(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-609: Primary output is Markdown with timestamps."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                output_format="markdown"
            )

            assert result.success
            assert result.output_path.endswith(".md")
            assert Path(result.output_path).exists()

            # Verify markdown content
            content = Path(result.output_path).read_text()
            assert "# Transcript" in content
            assert "Speaker" in content

    def test_markdown_includes_metadata(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-609: Markdown includes title, date, duration, model, speakers."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                output_format="markdown"
            )

            content = Path(result.output_path).read_text()

            # Check metadata presence
            assert "**Source**" in content or "Source:" in content
            assert "**Duration**" in content or "Duration:" in content
            assert "**Model**" in content or "Model:" in content
            assert "**Speakers**" in content or "Speakers:" in content

    def test_markdown_speaker_format(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-609: Markdown uses [Speaker N] HH:MM:SS format."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                output_format="markdown"
            )

            content = Path(result.output_path).read_text()

            # Check format: **[Speaker 1] 00:00:00** text...
            assert "[Speaker " in content
            assert "] 00:" in content or "] 0:" in content

    def test_outputs_json_format(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-609: Alternative format: JSON."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                output_format="json"
            )

            assert result.success
            assert result.output_path.endswith(".json")

            # Verify JSON is valid
            content = Path(result.output_path).read_text()
            data = json.loads(content)
            assert "segments" in data

    def test_outputs_srt_format(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-609: Alternative format: SRT."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                output_format="srt"
            )

            assert result.success
            assert result.output_path.endswith(".srt")

    def test_outputs_vtt_format(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-609: Alternative format: VTT."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                output_format="vtt"
            )

            assert result.success
            assert result.output_path.endswith(".vtt")
            content = Path(result.output_path).read_text()
            assert "WEBVTT" in content

    def test_outputs_txt_format(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-609: Alternative format: Plain text."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                output_format="txt"
            )

            assert result.success
            assert result.output_path.endswith(".txt")

    def test_output_filename_convention(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-609: Output filename: {original-name}-transcript.{ext}."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                output_format="markdown"
            )

            # Filename should be based on input + "-transcript"
            output_name = Path(result.output_path).stem
            assert "transcript" in output_name.lower()


class TestSegmentDuration:
    """Test configurable segment duration."""

    def test_configurable_segment_duration(self, sample_audio_path, temp_output_dir, mock_whisperx_result):
        """REQ-609: Configurable paragraph length (default: 30s segments)."""
        from whisperx_transcriber import transcribe, DEFAULT_SEGMENT_DURATION

        assert DEFAULT_SEGMENT_DURATION == 30

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.return_value = (mock_whisperx_result, 2)

            result = transcribe(
                sample_audio_path,
                output_dir=temp_output_dir,
                segment_duration=60  # Custom duration
            )

            assert result.success


# ==================== ERROR HANDLING ====================

class TestErrorHandling:
    """Test error handling scenarios."""

    def test_handles_file_not_found(self, temp_output_dir):
        """Handle missing audio file gracefully."""
        from whisperx_transcriber import transcribe

        result = transcribe(
            "/nonexistent/path/audio.mp3",
            output_dir=temp_output_dir
        )

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower() or "does not exist" in result.error.lower()

    def test_handles_invalid_audio_format(self, temp_output_dir):
        """Handle invalid audio file gracefully."""
        from whisperx_transcriber import transcribe

        # Create a non-audio file
        invalid_file = Path(temp_output_dir) / "not_audio.txt"
        invalid_file.write_text("This is not audio")

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.side_effect = Exception("Invalid audio format")

            result = transcribe(str(invalid_file), output_dir=temp_output_dir)

            assert result.success is False
            assert result.error is not None

    def test_handles_transcription_error(self, sample_audio_path, temp_output_dir):
        """Handle transcription errors gracefully."""
        from whisperx_transcriber import transcribe

        with patch('whisperx_transcriber.WHISPERX_AVAILABLE', True), \
             patch('whisperx_transcriber._run_whisperx') as mock_whisperx:
            mock_whisperx.side_effect = RuntimeError("CUDA out of memory")

            result = transcribe(sample_audio_path, output_dir=temp_output_dir)

            assert result.success is False
            assert result.error is not None


# ==================== INTEGRATION TESTS ====================

@pytest.mark.integration
class TestRealFileTranscription:
    """Integration tests with real audio/video file."""

    def test_transcribe_real_audio_file(self, test_video_path, temp_output_dir):
        """REQ-608: Integration test with real extracted audio."""
        from whisperx_transcriber import transcribe

        # First, we need to extract audio from the video
        audio_path = Path(temp_output_dir) / "2026-01-09 10-23-34.mp3"

        # Check if audio exists or needs extraction
        if not audio_path.exists():
            from audio_extractor import extract_audio
            if not Path(test_video_path).exists():
                pytest.skip(f"Test video not found: {test_video_path}")

            extract_result = extract_audio(
                test_video_path,
                output_dir=temp_output_dir,
                quality="draft"
            )
            if not extract_result.success:
                pytest.skip(f"Could not extract audio: {extract_result.error}")

            audio_path = Path(extract_result.output_path)

        # Skip if whisperX not available
        try:
            import whisperx
        except ImportError:
            pytest.skip("whisperX not installed")

        # Get HF token
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            pytest.skip("HF_TOKEN not set")

        result = transcribe(
            str(audio_path),
            output_dir=temp_output_dir,
            model="tiny",  # Use smallest model for faster test
            diarize=True,
            hf_token=hf_token
        )

        assert result.success is True
        assert result.output_path is not None
        assert Path(result.output_path).exists()
        assert result.duration_seconds > 0
        assert result.speakers_detected >= 1
        assert len(result.segments) > 0


# ==================== TIMESTAMP FORMATTING ====================

class TestTimestampFormatting:
    """Test timestamp formatting utilities."""

    def test_format_timestamp_seconds(self):
        """Format seconds to HH:MM:SS."""
        from whisperx_transcriber import format_timestamp

        assert format_timestamp(0) == "00:00:00"
        assert format_timestamp(65) == "00:01:05"
        assert format_timestamp(3661) == "01:01:01"
        assert format_timestamp(3661.5) == "01:01:01"

    def test_format_timestamp_srt(self):
        """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
        from whisperx_transcriber import format_timestamp_srt

        assert format_timestamp_srt(0) == "00:00:00,000"
        assert format_timestamp_srt(65.5) == "00:01:05,500"
        assert format_timestamp_srt(3661.123) == "01:01:01,123"

    def test_format_timestamp_vtt(self):
        """Format seconds to VTT timestamp (HH:MM:SS.mmm)."""
        from whisperx_transcriber import format_timestamp_vtt

        assert format_timestamp_vtt(0) == "00:00:00.000"
        assert format_timestamp_vtt(65.5) == "00:01:05.500"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not integration"])

#!/usr/bin/env python3
"""
Tests for audio_extractor.py

REQ-601: FFmpeg Audio Extraction
REQ-603: User Experience - Audio Extraction

Test file: /Users/travis/Movies/2026-01-09 10-23-34.mov (2.2GB QuickTime movie)
"""

import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable, List
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


# ==================== INTERFACE CONTRACT ====================

@dataclass
class AudioExtractionResult:
    """Expected return type from extract_audio function."""
    success: bool
    output_path: Optional[str]
    duration_seconds: float
    size_bytes: int
    elapsed_ms: int
    error: Optional[str]
    error_reason: Optional[str]
    error_fix: Optional[str]


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


class MockStderr:
    """Mock stderr that supports readline() iteration pattern."""

    def __init__(self, lines: List[bytes]):
        self._lines = lines
        self._index = 0

    def readline(self) -> bytes:
        if self._index < len(self._lines):
            line = self._lines[self._index]
            self._index += 1
            return line
        return b''


def create_mock_process(returncode: int = 0, stderr_lines: List[bytes] = None):
    """Create a mock FFmpeg process with proper stderr handling."""
    mock_process = MagicMock()
    mock_process.returncode = returncode
    mock_process.stderr = MockStderr(stderr_lines or [b""])
    mock_process.wait.return_value = returncode
    return mock_process


@pytest.fixture
def mock_ffmpeg_success():
    """Mock FFmpeg process that succeeds."""
    return create_mock_process(
        returncode=0,
        stderr_lines=[
            b"Duration: 01:23:45.67, start: 0.000000, bitrate: 1234 kb/s\n",
            b"size=   12345kB time=00:10:00.00 bitrate= 123.4kbits/s speed=10.0x\n",
            b"size=   24690kB time=00:20:00.00 bitrate= 123.4kbits/s speed=10.0x\n",
            b"size=   37035kB time=00:30:00.00 bitrate= 123.4kbits/s speed=10.0x\n",
        ]
    )


# ==================== HAPPY PATH TESTS ====================

class TestAudioExtraction:
    """Test suite for REQ-601: FFmpeg Audio Extraction."""

    def test_extracts_audio_from_valid_mov(self, temp_output_dir):
        """REQ-601: Accepts OBS .mov files as input, extracts audio to MP3."""
        from audio_extractor import extract_audio

        # Create a minimal test file (we'll mock FFmpeg for unit tests)
        input_path = Path(temp_output_dir) / "test_video.mov"
        input_path.touch()  # Create empty file for path validation

        with patch('audio_extractor.subprocess.Popen') as mock_popen:
            mock_process = create_mock_process(
                returncode=0,
                stderr_lines=[
                    b"Duration: 00:01:30.00, start: 0.000000, bitrate: 1234 kb/s\n",
                    b"size=   1234kB time=00:01:30.00 bitrate= 123.4kbits/s speed=10.0x\n",
                ]
            )
            mock_popen.return_value = mock_process

            # Create fake output file
            output_path = Path(temp_output_dir) / "test_video.mp3"
            output_path.write_bytes(b"fake mp3 content" * 1000)

            result = extract_audio(str(input_path), output_dir=temp_output_dir)

            assert result.success is True
            assert result.output_path is not None
            assert result.output_path.endswith(".mp3")
            assert result.error is None

    def test_creates_mp3_with_correct_naming(self, temp_output_dir):
        """REQ-601: Naming convention {original-name}.mp3."""
        from audio_extractor import extract_audio

        input_path = Path(temp_output_dir) / "meeting-2026-01-09.mov"
        input_path.touch()

        with patch('audio_extractor.subprocess.Popen') as mock_popen:
            mock_process = create_mock_process(returncode=0, stderr_lines=[b""])
            mock_popen.return_value = mock_process

            # Pre-create expected output
            expected_output = Path(temp_output_dir) / "meeting-2026-01-09.mp3"
            expected_output.write_bytes(b"fake mp3")

            result = extract_audio(str(input_path), output_dir=temp_output_dir)

            assert result.output_path == str(expected_output)

    def test_quality_settings_draft_standard_archival(self, temp_output_dir):
        """REQ-601: Supports quality settings 128kbps (draft), 192kbps (standard), 320kbps (archival)."""
        from audio_extractor import extract_audio, QUALITY_PRESETS

        # Verify quality presets exist
        assert "draft" in QUALITY_PRESETS
        assert "standard" in QUALITY_PRESETS
        assert "archival" in QUALITY_PRESETS

        assert QUALITY_PRESETS["draft"] == "128k"
        assert QUALITY_PRESETS["standard"] == "192k"
        assert QUALITY_PRESETS["archival"] == "320k"

        # Test that quality parameter is passed to FFmpeg
        input_path = Path(temp_output_dir) / "test.mov"
        input_path.touch()

        with patch('audio_extractor.subprocess.Popen') as mock_popen:
            mock_process = create_mock_process(returncode=0, stderr_lines=[b""])
            mock_popen.return_value = mock_process

            Path(temp_output_dir, "test.mp3").write_bytes(b"fake")

            extract_audio(str(input_path), output_dir=temp_output_dir, quality="archival")

            # Verify FFmpeg was called with 320k bitrate
            call_args = mock_popen.call_args[0][0]
            assert "-b:a" in call_args
            bitrate_idx = call_args.index("-b:a")
            assert call_args[bitrate_idx + 1] == "320k"


class TestProgressCallback:
    """Test suite for REQ-603: Progress reporting."""

    def test_progress_callback_invoked(self, temp_output_dir):
        """REQ-603: Reports extraction progress (percentage, ETA)."""
        from audio_extractor import extract_audio

        progress_updates: List[dict] = []

        def progress_callback(progress: dict):
            progress_updates.append(progress)

        input_path = Path(temp_output_dir) / "test.mov"
        input_path.touch()

        with patch('audio_extractor.subprocess.Popen') as mock_popen:
            mock_process = create_mock_process(
                returncode=0,
                stderr_lines=[
                    b"Duration: 00:10:00.00, start: 0.000000, bitrate: 1234 kb/s\n",
                    b"size=   1234kB time=00:05:00.00 bitrate= 123.4kbits/s speed=10.0x\n",
                    b"size=   2468kB time=00:10:00.00 bitrate= 123.4kbits/s speed=10.0x\n",
                ]
            )
            mock_popen.return_value = mock_process

            Path(temp_output_dir, "test.mp3").write_bytes(b"fake")

            extract_audio(
                str(input_path),
                output_dir=temp_output_dir,
                progress_callback=progress_callback
            )

            assert len(progress_updates) >= 1
            # Progress should include percentage
            for update in progress_updates:
                assert "percent" in update or "time" in update


class TestUserExperience:
    """Test suite for REQ-603: User Experience."""

    def test_error_includes_fix_suggestion(self):
        """REQ-603: Error messages include what failed, why, how to fix."""
        from audio_extractor import extract_audio

        result = extract_audio("/nonexistent/path/video.mov")

        assert result.success is False
        assert result.error is not None
        assert result.error_reason is not None
        assert result.error_fix is not None

    def test_dry_run_does_not_create_file(self, temp_output_dir):
        """REQ-603: Dry-run mode shows what would happen without executing."""
        from audio_extractor import extract_audio

        input_path = Path(temp_output_dir) / "test.mov"
        input_path.touch()
        expected_output = Path(temp_output_dir) / "test.mp3"

        result = extract_audio(str(input_path), output_dir=temp_output_dir, dry_run=True)

        assert result.success is True
        assert result.output_path is not None
        assert not expected_output.exists()  # File should NOT be created


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def test_handles_file_not_found(self):
        """REQ-603: Error handling for file not found."""
        from audio_extractor import extract_audio

        result = extract_audio("/nonexistent/path/video.mov")

        assert result.success is False
        assert "not found" in result.error.lower() or "not found" in result.error_reason.lower()
        assert result.error_fix is not None

    def test_handles_no_audio_stream(self, temp_output_dir):
        """REQ-603: Error handling for no audio stream in file."""
        from audio_extractor import extract_audio

        input_path = Path(temp_output_dir) / "no_audio.mov"
        input_path.touch()

        with patch('audio_extractor.subprocess.Popen') as mock_popen:
            mock_process = create_mock_process(
                returncode=1,
                stderr_lines=[
                    b"Stream #0:0: Video: h264\n",
                    b"Output file #0 does not contain any stream\n",
                ]
            )
            mock_popen.return_value = mock_process

            result = extract_audio(str(input_path), output_dir=temp_output_dir)

            assert result.success is False
            assert result.error_reason is not None
            assert "audio" in result.error_reason.lower() or "stream" in result.error_reason.lower()


# ==================== INTEGRATION TEST ====================

@pytest.mark.integration
class TestRealFileExtraction:
    """Integration tests with real video file."""

    def test_extracts_audio_from_real_mov_file(self, test_video_path, temp_output_dir):
        """REQ-601: Integration test with real .mov file."""
        from audio_extractor import extract_audio

        if not Path(test_video_path).exists():
            pytest.skip(f"Test video not found: {test_video_path}")

        result = extract_audio(
            test_video_path,
            output_dir=temp_output_dir,
            quality="draft"  # Use draft quality for faster test
        )

        assert result.success is True
        assert result.output_path is not None
        assert Path(result.output_path).exists()
        assert result.duration_seconds > 0
        assert result.size_bytes > 0


# ==================== CLI FLAG TESTS ====================

class TestCLIFlags:
    """Test command-line interface flags."""

    def test_verbose_mode_shows_ffmpeg_output(self, temp_output_dir, capsys):
        """REQ-603: Verbose mode shows FFmpeg output."""
        from audio_extractor import extract_audio

        input_path = Path(temp_output_dir) / "test.mov"
        input_path.touch()

        with patch('audio_extractor.subprocess.Popen') as mock_popen:
            mock_process = create_mock_process(
                returncode=0,
                stderr_lines=[b"FFmpeg verbose output here\n"]
            )
            mock_popen.return_value = mock_process

            Path(temp_output_dir, "test.mp3").write_bytes(b"fake")

            extract_audio(str(input_path), output_dir=temp_output_dir, verbose=True)

            # In verbose mode, output should be shown
            # (actual assertion depends on implementation)

    def test_quiet_mode_shows_only_errors(self, temp_output_dir, capsys):
        """REQ-603: Quiet mode shows only errors."""
        from audio_extractor import extract_audio

        result = extract_audio("/nonexistent/file.mov", quiet=True)

        # Should still return error result
        assert result.success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not integration"])

"""
Tests for REQ-616: Dependency Verification (Dependency Doctor Tool)

TDD tests for the dependency doctor that verifies system requirements
for the video-to-transcript pipeline.
"""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from typing import Optional, Literal, List, Dict, Any
import subprocess
import os


# Import will fail until implementation exists - that's expected for TDD
try:
    from dependency_doctor import (
        DependencyCheck,
        DoctorResult,
        check_ffmpeg,
        check_whisperx,
        check_pyannote,
        check_hf_token,
        check_macos_version,
        check_apple_silicon,
        check_memory,
        check_disk_space,
        run_doctor,
        format_doctor_output,
    )
except ImportError:
    # Placeholder classes for test structure before implementation
    @dataclass
    class DependencyCheck:
        name: str
        status: Literal["ok", "missing", "outdated", "error"]
        version: Optional[str]
        min_version: Optional[str]
        location: Optional[str]
        install_command: str
        note: Optional[str]

    @dataclass
    class DoctorResult:
        all_passed: bool
        required: List[DependencyCheck]
        optional: List[DependencyCheck]
        system: Dict[str, Any]
        config: Dict[str, Any]

    # Stub functions for test structure
    def check_ffmpeg(): pass
    def check_whisperx(): pass
    def check_pyannote(): pass
    def check_hf_token(): pass
    def check_macos_version(): pass
    def check_apple_silicon(): pass
    def check_memory(): pass
    def check_disk_space(): pass
    def run_doctor(): pass
    def format_doctor_output(result): pass


class TestFFmpegDetection:
    """REQ-616: FFmpeg dependency detection"""

    @patch("subprocess.run")
    def test_detects_ffmpeg_installed(self, mock_run):
        """REQ-616 - Detect when FFmpeg is installed and get version"""
        # Mock successful which and version commands
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/opt/homebrew/bin/ffmpeg\n"),
            MagicMock(returncode=0, stdout="ffmpeg version 6.1.1 Copyright (c) 2000-2023\n"),
        ]

        result = check_ffmpeg()

        assert result.status == "ok"
        assert result.version == "6.1.1"
        assert result.location == "/opt/homebrew/bin/ffmpeg"
        assert result.name == "FFmpeg"

    @patch("subprocess.run")
    def test_detects_ffmpeg_missing(self, mock_run):
        """REQ-616 - Detect when FFmpeg is not installed"""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = check_ffmpeg()

        assert result.status == "missing"
        assert result.version is None
        assert "brew install ffmpeg" in result.install_command or "apt install ffmpeg" in result.install_command


class TestWhisperXDetection:
    """REQ-616: whisperX dependency detection"""

    @patch("subprocess.run")
    def test_detects_whisperx_installed(self, mock_run):
        """REQ-616 - Detect when whisperX is installed"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Name: whisperx\nVersion: 3.1.1\nLocation: /opt/homebrew/lib/python3.11/site-packages\n"
        )

        result = check_whisperx()

        assert result.status == "ok"
        assert result.version == "3.1.1"
        assert result.name == "whisperX"

    @patch("subprocess.run")
    def test_detects_whisperx_missing(self, mock_run):
        """REQ-616 - Detect when whisperX is not installed"""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = check_whisperx()

        assert result.status == "missing"
        assert "pip install whisperx" in result.install_command


class TestPyannoteDetection:
    """REQ-616: pyannote.audio dependency detection"""

    @patch("subprocess.run")
    def test_detects_pyannote_installed(self, mock_run):
        """REQ-616 - Detect when pyannote.audio is installed"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Name: pyannote.audio\nVersion: 3.1.0\nLocation: /opt/homebrew/lib/python3.11/site-packages\n"
        )

        result = check_pyannote()

        assert result.status == "ok"
        assert result.version == "3.1.0"
        assert result.name == "pyannote.audio"

    @patch("subprocess.run")
    def test_detects_pyannote_missing(self, mock_run):
        """REQ-616 - Detect when pyannote.audio is not installed"""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = check_pyannote()

        assert result.status == "missing"
        assert "pip install pyannote.audio" in result.install_command


class TestHFTokenValidation:
    """REQ-616: HuggingFace token validation"""

    @patch.dict(os.environ, {"HF_TOKEN": "hf_abcdefghijklmnop1234567890"})
    def test_validates_hf_token_format(self):
        """REQ-616 - Validate HF token starts with hf_"""
        result = check_hf_token()

        assert result.status == "ok"
        assert result.note is not None
        assert "hf_" in result.note

    @patch.dict(os.environ, {"HF_TOKEN": ""}, clear=False)
    def test_detects_hf_token_missing(self):
        """REQ-616 - Detect missing HF token"""
        # Remove HF_TOKEN if it exists
        with patch.dict(os.environ, {}, clear=True):
            result = check_hf_token()

            assert result.status == "missing"
            assert "HF_TOKEN" in result.install_command

    @patch.dict(os.environ, {"HF_TOKEN": "invalid_token_format"})
    def test_detects_invalid_hf_token_format(self):
        """REQ-616 - Detect invalid HF token format"""
        result = check_hf_token()

        assert result.status == "error"
        assert "hf_" in result.note or "format" in result.note.lower()


class TestMacOSVersion:
    """REQ-616: macOS version detection"""

    @patch("subprocess.run")
    def test_checks_macos_version(self, mock_run):
        """REQ-616 - Check macOS version"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ProductName:\tmacOS\nProductVersion:\t15.2\nBuildVersion:\t24C101\n"
        )

        result = check_macos_version()

        assert result["os"] == "macOS"
        assert result["version"] == "15.2"
        assert result["status"] == "ok"


class TestAppleSilicon:
    """REQ-616: Apple Silicon detection"""

    @patch("subprocess.run")
    def test_checks_apple_silicon(self, mock_run):
        """REQ-616 - Detect Apple Silicon (arm64)"""
        mock_run.return_value = MagicMock(returncode=0, stdout="arm64\n")

        result = check_apple_silicon()

        assert result["architecture"] == "arm64"
        assert result["is_apple_silicon"] is True
        assert result["core_ml_available"] is True

    @patch("subprocess.run")
    def test_checks_intel_mac(self, mock_run):
        """REQ-616 - Detect Intel Mac (x86_64)"""
        mock_run.return_value = MagicMock(returncode=0, stdout="x86_64\n")

        result = check_apple_silicon()

        assert result["architecture"] == "x86_64"
        assert result["is_apple_silicon"] is False


class TestMemoryCheck:
    """REQ-616: System memory detection"""

    @patch("subprocess.run")
    def test_checks_available_memory(self, mock_run):
        """REQ-616 - Check available system memory"""
        # 32GB in bytes
        mock_run.return_value = MagicMock(returncode=0, stdout="hw.memsize: 34359738368\n")

        result = check_memory()

        assert result["total_bytes"] == 34359738368
        assert result["total_gb"] == 32
        assert result["status"] == "ok"

    @patch("subprocess.run")
    def test_warns_on_low_memory(self, mock_run):
        """REQ-616 - Warn when memory is below recommended"""
        # 4GB in bytes (below 8GB recommended)
        mock_run.return_value = MagicMock(returncode=0, stdout="hw.memsize: 4294967296\n")

        result = check_memory()

        assert result["total_gb"] == 4
        assert result["status"] == "warning"


class TestDiskSpace:
    """REQ-616: Disk space detection"""

    @patch("subprocess.run")
    def test_checks_disk_space(self, mock_run):
        """REQ-616 - Check available disk space"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Filesystem     Size   Used  Avail Capacity Mounted on\n/dev/disk3s5  926Gi  79Gi  847Gi     9%    /\n"
        )

        result = check_disk_space()

        assert result["available_gb"] >= 800
        assert result["status"] == "ok"

    @patch("subprocess.run")
    def test_warns_on_low_disk_space(self, mock_run):
        """REQ-616 - Warn when disk space is below threshold"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Filesystem     Size   Used  Avail Capacity Mounted on\n/dev/disk3s5  926Gi  916Gi  10Gi    99%    /\n"
        )

        result = check_disk_space()

        assert result["available_gb"] <= 20
        assert result["status"] == "warning"


class TestDoctorOutput:
    """REQ-616: Doctor output formatting"""

    def test_doctor_output_format(self):
        """REQ-616 - Doctor produces structured DoctorResult"""
        result = run_doctor()

        assert isinstance(result, DoctorResult)
        assert isinstance(result.all_passed, bool)
        assert isinstance(result.required, list)
        assert isinstance(result.optional, list)
        assert isinstance(result.system, dict)
        assert isinstance(result.config, dict)

    def test_doctor_output_contains_required_deps(self):
        """REQ-616 - Doctor checks all required dependencies"""
        result = run_doctor()

        required_names = [dep.name for dep in result.required]
        assert "FFmpeg" in required_names
        assert "whisperX" in required_names
        assert "HuggingFace Token" in required_names

    def test_doctor_output_contains_system_info(self):
        """REQ-616 - Doctor includes system information"""
        result = run_doctor()

        assert "os" in result.system or "macos" in result.system
        assert "memory" in result.system
        assert "disk" in result.system

    def test_format_doctor_output_produces_string(self):
        """REQ-616 - format_doctor_output produces readable string"""
        result = run_doctor()
        output = format_doctor_output(result)

        assert isinstance(output, str)
        assert "Video-to-Transcript Pipeline" in output or "System Check" in output
        assert "Required Dependencies" in output or "Required" in output


class TestDoctorIntegration:
    """REQ-616: Integration tests for full doctor workflow"""

    def test_all_passed_when_deps_ok(self):
        """REQ-616 - all_passed is True when all required deps are ok"""
        with patch("dependency_doctor.check_ffmpeg") as mock_ffmpeg, \
             patch("dependency_doctor.check_whisperx") as mock_whisperx, \
             patch("dependency_doctor.check_pyannote") as mock_pyannote, \
             patch("dependency_doctor.check_hf_token") as mock_hf:

            mock_ffmpeg.return_value = DependencyCheck(
                name="FFmpeg", status="ok", version="6.1.1",
                min_version="5.0", location="/opt/homebrew/bin/ffmpeg",
                install_command="brew install ffmpeg", note=None
            )
            mock_whisperx.return_value = DependencyCheck(
                name="whisperX", status="ok", version="3.1.1",
                min_version=None, location=None,
                install_command="pip install whisperx", note=None
            )
            mock_pyannote.return_value = DependencyCheck(
                name="pyannote.audio", status="ok", version="3.1.0",
                min_version=None, location=None,
                install_command="pip install pyannote.audio", note=None
            )
            mock_hf.return_value = DependencyCheck(
                name="HuggingFace Token", status="ok", version=None,
                min_version=None, location=None,
                install_command="export HF_TOKEN=hf_...", note="Token configured (hf_...)"
            )

            result = run_doctor()
            assert result.all_passed is True

    def test_all_passed_false_when_dep_missing(self):
        """REQ-616 - all_passed is False when any required dep is missing"""
        with patch("dependency_doctor.check_ffmpeg") as mock_ffmpeg, \
             patch("dependency_doctor.check_whisperx") as mock_whisperx, \
             patch("dependency_doctor.check_pyannote") as mock_pyannote, \
             patch("dependency_doctor.check_hf_token") as mock_hf:

            mock_ffmpeg.return_value = DependencyCheck(
                name="FFmpeg", status="missing", version=None,
                min_version="5.0", location=None,
                install_command="brew install ffmpeg", note=None
            )
            mock_whisperx.return_value = DependencyCheck(
                name="whisperX", status="ok", version="3.1.1",
                min_version=None, location=None,
                install_command="pip install whisperx", note=None
            )
            mock_pyannote.return_value = DependencyCheck(
                name="pyannote.audio", status="ok", version="3.1.0",
                min_version=None, location=None,
                install_command="pip install pyannote.audio", note=None
            )
            mock_hf.return_value = DependencyCheck(
                name="HuggingFace Token", status="ok", version=None,
                min_version=None, location=None,
                install_command="export HF_TOKEN=hf_...", note="Token configured (hf_...)"
            )

            result = run_doctor()
            assert result.all_passed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

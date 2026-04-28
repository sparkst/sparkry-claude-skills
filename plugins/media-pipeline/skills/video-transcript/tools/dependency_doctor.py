#!/usr/bin/env python3
"""
REQ-616: Dependency Verification (Dependency Doctor Tool)

Verifies system requirements for the video-to-transcript pipeline.
Checks FFmpeg, whisperX, pyannote.audio, HuggingFace token, and system specs.
"""

import os
import re
import subprocess
import platform
from dataclasses import dataclass, field
from typing import Optional, Literal, List, Dict, Any

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


@dataclass
class DependencyCheck:
    """Result of checking a single dependency."""
    name: str
    status: Literal["ok", "missing", "outdated", "error"]
    version: Optional[str]
    min_version: Optional[str]
    location: Optional[str]
    install_command: str
    note: Optional[str]


@dataclass
class DoctorResult:
    """Complete result of running the dependency doctor."""
    all_passed: bool
    required: List[DependencyCheck] = field(default_factory=list)
    optional: List[DependencyCheck] = field(default_factory=list)
    system: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)


def run_command(cmd: List[str], capture_stderr: bool = False) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return subprocess.CompletedProcess(
            cmd,
            returncode=1,
            stdout="",
            stderr=str(e)
        )


def check_ffmpeg() -> DependencyCheck:
    """Check if FFmpeg is installed and get version."""
    which_result = run_command(["which", "ffmpeg"])

    if which_result.returncode != 0:
        return DependencyCheck(
            name="FFmpeg",
            status="missing",
            version=None,
            min_version="5.0",
            location=None,
            install_command="brew install ffmpeg" if platform.system() == "Darwin" else "apt install ffmpeg",
            note=None
        )

    location = which_result.stdout.strip()
    version_result = run_command(["ffmpeg", "-version"])

    version = None
    if version_result.returncode == 0:
        match = re.search(r"ffmpeg version (\d+\.\d+(?:\.\d+)?)", version_result.stdout)
        if match:
            version = match.group(1)

    return DependencyCheck(
        name="FFmpeg",
        status="ok",
        version=version,
        min_version="5.0",
        location=location,
        install_command="brew install ffmpeg" if platform.system() == "Darwin" else "apt install ffmpeg",
        note=None
    )


def check_whisperx() -> DependencyCheck:
    """Check if whisperX is installed."""
    result = run_command(["pip", "show", "whisperx"])

    if result.returncode != 0:
        result = run_command(["pip3", "show", "whisperx"])

    if result.returncode != 0:
        return DependencyCheck(
            name="whisperX",
            status="missing",
            version=None,
            min_version=None,
            location=None,
            install_command="pip install whisperx",
            note=None
        )

    version = None
    location = None
    for line in result.stdout.split("\n"):
        if line.startswith("Version:"):
            version = line.split(":", 1)[1].strip()
        elif line.startswith("Location:"):
            location = line.split(":", 1)[1].strip()

    return DependencyCheck(
        name="whisperX",
        status="ok",
        version=version,
        min_version=None,
        location=location,
        install_command="pip install whisperx",
        note=None
    )


def check_pyannote() -> DependencyCheck:
    """Check if pyannote.audio is installed."""
    result = run_command(["pip", "show", "pyannote.audio"])

    if result.returncode != 0:
        result = run_command(["pip3", "show", "pyannote.audio"])

    if result.returncode != 0:
        return DependencyCheck(
            name="pyannote.audio",
            status="missing",
            version=None,
            min_version=None,
            location=None,
            install_command="pip install pyannote.audio",
            note=None
        )

    version = None
    location = None
    for line in result.stdout.split("\n"):
        if line.startswith("Version:"):
            version = line.split(":", 1)[1].strip()
        elif line.startswith("Location:"):
            location = line.split(":", 1)[1].strip()

    return DependencyCheck(
        name="pyannote.audio",
        status="ok",
        version=version,
        min_version=None,
        location=location,
        install_command="pip install pyannote.audio",
        note=None
    )


def check_hf_token() -> DependencyCheck:
    """Check if HuggingFace token is configured."""
    token = os.environ.get("HF_TOKEN", "")

    if not token:
        return DependencyCheck(
            name="HuggingFace Token",
            status="missing",
            version=None,
            min_version=None,
            location=None,
            install_command="export HF_TOKEN=hf_your_token_here",
            note="Token not found in environment"
        )

    if not token.startswith("hf_"):
        return DependencyCheck(
            name="HuggingFace Token",
            status="error",
            version=None,
            min_version=None,
            location=None,
            install_command="export HF_TOKEN=hf_your_token_here",
            note="Token format invalid - must start with hf_"
        )

    masked_token = f"hf_...{token[-4:]}" if len(token) > 7 else "hf_..."

    return DependencyCheck(
        name="HuggingFace Token",
        status="ok",
        version=None,
        min_version=None,
        location=None,
        install_command="export HF_TOKEN=hf_your_token_here",
        note=f"Token configured ({masked_token})"
    )


def check_fswatch() -> DependencyCheck:
    """Check if fswatch is installed (optional)."""
    which_result = run_command(["which", "fswatch"])

    if which_result.returncode != 0:
        return DependencyCheck(
            name="fswatch",
            status="missing",
            version=None,
            min_version=None,
            location=None,
            install_command="brew install fswatch",
            note="Optional: enables watch mode"
        )

    location = which_result.stdout.strip()
    version_result = run_command(["fswatch", "--version"])

    version = None
    if version_result.returncode == 0:
        match = re.search(r"(\d+\.\d+(?:\.\d+)?)", version_result.stdout)
        if match:
            version = match.group(1)

    return DependencyCheck(
        name="fswatch",
        status="ok",
        version=version,
        min_version=None,
        location=location,
        install_command="brew install fswatch",
        note=None
    )


def check_macos_version() -> Dict[str, Any]:
    """Check macOS version."""
    result = run_command(["sw_vers"])

    if result.returncode != 0:
        return {
            "os": platform.system(),
            "version": platform.release(),
            "status": "ok"
        }

    os_name = None
    version = None
    build = None

    for line in result.stdout.split("\n"):
        if "ProductName" in line:
            os_name = line.split(":", 1)[1].strip() if ":" in line else None
        elif "ProductVersion" in line:
            version = line.split(":", 1)[1].strip() if ":" in line else None
        elif "BuildVersion" in line:
            build = line.split(":", 1)[1].strip() if ":" in line else None

    return {
        "os": os_name or platform.system(),
        "version": version or platform.release(),
        "build": build,
        "status": "ok"
    }


def check_apple_silicon() -> Dict[str, Any]:
    """Check if running on Apple Silicon."""
    result = run_command(["uname", "-m"])

    arch = result.stdout.strip() if result.returncode == 0 else platform.machine()
    is_apple_silicon = arch == "arm64"

    return {
        "architecture": arch,
        "is_apple_silicon": is_apple_silicon,
        "core_ml_available": is_apple_silicon,
        "status": "ok" if is_apple_silicon else "info"
    }


def check_memory() -> Dict[str, Any]:
    """Check available system memory."""
    result = run_command(["sysctl", "hw.memsize"])

    if result.returncode != 0:
        return {
            "total_bytes": 0,
            "total_gb": 0,
            "status": "error"
        }

    match = re.search(r"hw\.memsize:\s*(\d+)", result.stdout)
    if not match:
        return {
            "total_bytes": 0,
            "total_gb": 0,
            "status": "error"
        }

    total_bytes = int(match.group(1))
    total_gb = total_bytes // (1024 ** 3)

    status = "ok" if total_gb >= 8 else "warning"

    return {
        "total_bytes": total_bytes,
        "total_gb": total_gb,
        "status": status,
        "note": "Recommended: 8+ GB RAM" if status == "warning" else None
    }


def check_disk_space() -> Dict[str, Any]:
    """Check available disk space."""
    result = run_command(["df", "-h", "/"])

    if result.returncode != 0:
        return {
            "available_gb": 0,
            "status": "error"
        }

    lines = result.stdout.strip().split("\n")
    if len(lines) < 2:
        return {
            "available_gb": 0,
            "status": "error"
        }

    parts = lines[1].split()
    if len(parts) < 4:
        return {
            "available_gb": 0,
            "status": "error"
        }

    avail_str = parts[3]
    available_gb = 0

    match = re.search(r"(\d+(?:\.\d+)?)", avail_str)
    if match:
        value = float(match.group(1))
        if "Ti" in avail_str or "T" in avail_str:
            available_gb = int(value * 1024)
        elif "Gi" in avail_str or "G" in avail_str:
            available_gb = int(value)
        elif "Mi" in avail_str or "M" in avail_str:
            available_gb = int(value / 1024)

    status = "ok" if available_gb >= 50 else "warning"

    return {
        "available_gb": available_gb,
        "available_str": avail_str,
        "status": status,
        "note": "Recommended: 50+ GB free space" if status == "warning" else None
    }


def run_doctor() -> DoctorResult:
    """Run all dependency checks and return results."""
    ffmpeg = check_ffmpeg()
    whisperx = check_whisperx()
    pyannote = check_pyannote()
    hf_token = check_hf_token()
    fswatch = check_fswatch()

    macos = check_macos_version()
    silicon = check_apple_silicon()
    memory = check_memory()
    disk = check_disk_space()

    required = [ffmpeg, whisperx, pyannote, hf_token]
    optional = [fswatch]

    all_passed = all(dep.status == "ok" for dep in required)

    return DoctorResult(
        all_passed=all_passed,
        required=required,
        optional=optional,
        system={
            "os": macos.get("os"),
            "macos": macos,
            "architecture": silicon,
            "memory": memory,
            "disk": disk
        },
        config={}
    )


def format_doctor_output(result: DoctorResult) -> str:
    """Format doctor result as a readable string."""
    if RICH_AVAILABLE:
        return _format_rich_output(result)
    return _format_plain_output(result)


def _format_plain_output(result: DoctorResult) -> str:
    """Format output as plain text."""
    lines = []
    lines.append("Video-to-Transcript Pipeline - System Check")
    lines.append("=" * 44)
    lines.append("")
    lines.append("Required Dependencies:")

    for dep in result.required:
        status_icon = "[OK]" if dep.status == "ok" else f"[{dep.status.upper()}]"
        version_str = f" {dep.version}" if dep.version else ""
        min_ver_str = f" (min: {dep.min_version})" if dep.min_version else ""
        lines.append(f"  {status_icon} {dep.name}{version_str}{min_ver_str}")

        if dep.location:
            lines.append(f"       Location: {dep.location}")
        if dep.status == "missing":
            lines.append(f"       Install: {dep.install_command}")
        if dep.note:
            lines.append(f"       Note: {dep.note}")
        lines.append("")

    lines.append("Optional Dependencies:")
    for dep in result.optional:
        status_icon = "[OK]" if dep.status == "ok" else f"[{dep.status.upper()}]"
        version_str = f" {dep.version}" if dep.version else ""
        lines.append(f"  {status_icon} {dep.name}{version_str}")

        if dep.location:
            lines.append(f"       Location: {dep.location}")
        if dep.status == "missing":
            lines.append(f"       Install: {dep.install_command}")
        if dep.note:
            lines.append(f"       Note: {dep.note}")
        lines.append("")

    lines.append("System:")
    macos = result.system.get("macos", {})
    silicon = result.system.get("architecture", {})
    memory = result.system.get("memory", {})
    disk = result.system.get("disk", {})

    os_str = f"{macos.get('os', 'Unknown')} {macos.get('version', '')}"
    if macos.get("build"):
        os_str += f" ({macos.get('build')})"
    lines.append(f"  [OK] {os_str}")

    arch = silicon.get("architecture", "Unknown")
    core_ml = " (Core ML available)" if silicon.get("core_ml_available") else ""
    lines.append(f"  [OK] {arch}{core_ml}")

    mem_gb = memory.get("total_gb", 0)
    mem_status = "[OK]" if memory.get("status") == "ok" else "[WARN]"
    lines.append(f"  {mem_status} {mem_gb} GB RAM")

    disk_gb = disk.get("available_gb", 0)
    disk_status = "[OK]" if disk.get("status") == "ok" else "[WARN]"
    lines.append(f"  {disk_status} {disk_gb} GB free disk space")

    lines.append("")

    issues = sum(1 for dep in result.required if dep.status != "ok")
    if issues == 0:
        lines.append("Status: All checks passed!")
    else:
        lines.append(f"Status: {issues} issue(s) found. Run suggested install commands.")

    return "\n".join(lines)


def _format_rich_output(result: DoctorResult) -> str:
    """Format output using rich library."""
    console = Console(record=True, force_terminal=True)

    console.print()
    console.print(Panel.fit(
        "[bold blue]Video-to-Transcript Pipeline - System Check[/bold blue]",
        border_style="blue"
    ))
    console.print()

    req_table = Table(title="Required Dependencies", show_header=True, header_style="bold cyan")
    req_table.add_column("Status", style="dim", width=8)
    req_table.add_column("Name", width=20)
    req_table.add_column("Version", width=12)
    req_table.add_column("Details", width=40)

    for dep in result.required:
        if dep.status == "ok":
            status = "[green][OK][/green]"
        elif dep.status == "missing":
            status = "[red][MISSING][/red]"
        elif dep.status == "error":
            status = "[red][ERROR][/red]"
        else:
            status = f"[yellow][{dep.status.upper()}][/yellow]"

        version = dep.version or "-"
        details = []
        if dep.location:
            details.append(f"Location: {dep.location}")
        if dep.status == "missing":
            details.append(f"Install: {dep.install_command}")
        if dep.note:
            details.append(f"Note: {dep.note}")

        req_table.add_row(status, dep.name, version, "\n".join(details) if details else "-")

    console.print(req_table)
    console.print()

    opt_table = Table(title="Optional Dependencies", show_header=True, header_style="bold cyan")
    opt_table.add_column("Status", style="dim", width=8)
    opt_table.add_column("Name", width=20)
    opt_table.add_column("Version", width=12)
    opt_table.add_column("Details", width=40)

    for dep in result.optional:
        if dep.status == "ok":
            status = "[green][OK][/green]"
        else:
            status = f"[yellow][{dep.status.upper()}][/yellow]"

        version = dep.version or "-"
        details = []
        if dep.location:
            details.append(f"Location: {dep.location}")
        if dep.status == "missing":
            details.append(f"Install: {dep.install_command}")
        if dep.note:
            details.append(dep.note)

        opt_table.add_row(status, dep.name, version, "\n".join(details) if details else "-")

    console.print(opt_table)
    console.print()

    sys_table = Table(title="System", show_header=True, header_style="bold cyan")
    sys_table.add_column("Status", style="dim", width=8)
    sys_table.add_column("Component", width=20)
    sys_table.add_column("Value", width=40)

    macos = result.system.get("macos", {})
    silicon = result.system.get("architecture", {})
    memory = result.system.get("memory", {})
    disk = result.system.get("disk", {})

    os_str = f"{macos.get('os', 'Unknown')} {macos.get('version', '')}"
    if macos.get("build"):
        os_str += f" ({macos.get('build')})"
    sys_table.add_row("[green][OK][/green]", "Operating System", os_str)

    arch = silicon.get("architecture", "Unknown")
    core_ml = " (Core ML available)" if silicon.get("core_ml_available") else ""
    sys_table.add_row("[green][OK][/green]", "Architecture", f"{arch}{core_ml}")

    mem_gb = memory.get("total_gb", 0)
    mem_status = "[green][OK][/green]" if memory.get("status") == "ok" else "[yellow][WARN][/yellow]"
    sys_table.add_row(mem_status, "Memory", f"{mem_gb} GB RAM")

    disk_gb = disk.get("available_gb", 0)
    disk_status = "[green][OK][/green]" if disk.get("status") == "ok" else "[yellow][WARN][/yellow]"
    sys_table.add_row(disk_status, "Disk Space", f"{disk_gb} GB free")

    console.print(sys_table)
    console.print()

    issues = sum(1 for dep in result.required if dep.status != "ok")
    if issues == 0:
        console.print("[bold green]Status: All checks passed![/bold green]")
    else:
        console.print(f"[bold red]Status: {issues} issue(s) found. Run suggested install commands.[/bold red]")

    console.print()
    return console.export_text()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Video-to-Transcript Pipeline - Dependency Doctor"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show issues"
    )
    args = parser.parse_args()

    result = run_doctor()

    if args.json:
        import json
        output = {
            "all_passed": result.all_passed,
            "required": [
                {
                    "name": d.name,
                    "status": d.status,
                    "version": d.version,
                    "min_version": d.min_version,
                    "location": d.location,
                    "install_command": d.install_command,
                    "note": d.note
                }
                for d in result.required
            ],
            "optional": [
                {
                    "name": d.name,
                    "status": d.status,
                    "version": d.version,
                    "location": d.location,
                    "install_command": d.install_command,
                    "note": d.note
                }
                for d in result.optional
            ],
            "system": result.system
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_doctor_output(result))

    return 0 if result.all_passed else 1


if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
"""
Audio Extractor

Extracts audio from video files (OBS .mov recordings) to MP3 format using FFmpeg.

REQ-601: FFmpeg Audio Extraction
REQ-603: User Experience - Audio Extraction

Usage:
    python audio_extractor.py input.mov [--output-dir DIR] [--quality draft|standard|archival]
    python audio_extractor.py input.mov --dry-run
    python audio_extractor.py input.mov --verbose
    python audio_extractor.py input.mov --quiet

Output (JSON):
    {
      "success": true,
      "output_path": "/path/to/output.mp3",
      "duration_seconds": 5025.67,
      "size_bytes": 127400000,
      "elapsed_ms": 12345,
      "error": null,
      "error_reason": null,
      "error_fix": null
    }
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Iterator

# Import notification tool
sys.path.insert(0, str(Path.home() / ".claude" / "tools"))
try:
    from notify import notify_file_ready, notify_error
    NOTIFY_AVAILABLE = True
except ImportError:
    NOTIFY_AVAILABLE = False

try:
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Quality presets (bitrate)
QUALITY_PRESETS: Dict[str, str] = {
    "draft": "128k",
    "standard": "192k",
    "archival": "320k",
}

DEFAULT_QUALITY = "standard"


@dataclass
class AudioExtractionResult:
    """Result of audio extraction operation."""
    success: bool
    output_path: Optional[str]
    duration_seconds: float
    size_bytes: int
    elapsed_ms: int
    error: Optional[str]
    error_reason: Optional[str]
    error_fix: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def parse_duration(duration_str: str) -> float:
    """Parse FFmpeg duration string (HH:MM:SS.ms) to seconds."""
    match = re.match(r'(\d+):(\d+):(\d+)\.?(\d*)', duration_str)
    if match:
        hours, minutes, seconds = int(match.group(1)), int(match.group(2)), int(match.group(3))
        ms = int(match.group(4)) if match.group(4) else 0
        return hours * 3600 + minutes * 60 + seconds + ms / 100
    return 0.0


def parse_time_from_progress(line: str) -> Optional[float]:
    """Parse current time from FFmpeg progress line."""
    match = re.search(r'time=(\d+):(\d+):(\d+)\.?(\d*)', line)
    if match:
        hours, minutes, seconds = int(match.group(1)), int(match.group(2)), int(match.group(3))
        ms = int(match.group(4)) if match.group(4) else 0
        return hours * 3600 + minutes * 60 + seconds + ms / 100
    return None


def get_total_duration(stderr_line: str) -> Optional[float]:
    """Extract total duration from FFmpeg's initial output."""
    match = re.search(r'Duration:\s*(\d+:\d+:\d+\.\d+)', stderr_line)
    if match:
        return parse_duration(match.group(1))
    return None


def extract_audio(
    input_path: str,
    output_dir: Optional[str] = None,
    quality: str = DEFAULT_QUALITY,
    dry_run: bool = False,
    verbose: bool = False,
    quiet: bool = False,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> AudioExtractionResult:
    """
    Extract audio from video file to MP3.

    Args:
        input_path: Path to input video file
        output_dir: Directory for output (default: same as input)
        quality: Quality preset (draft, standard, archival)
        dry_run: If True, show what would happen without executing
        verbose: If True, show FFmpeg output
        quiet: If True, show only errors
        progress_callback: Optional callback for progress updates

    Returns:
        AudioExtractionResult with success status and metadata
    """
    start_time = time.time()
    input_file = Path(input_path)

    # Validate input file exists
    if not input_file.exists():
        return AudioExtractionResult(
            success=False,
            output_path=None,
            duration_seconds=0.0,
            size_bytes=0,
            elapsed_ms=int((time.time() - start_time) * 1000),
            error=f"Could not extract audio from {input_file.name}",
            error_reason="File not found",
            error_fix=f"Check that the file exists at: {input_path}"
        )

    # Validate quality preset
    if quality not in QUALITY_PRESETS:
        return AudioExtractionResult(
            success=False,
            output_path=None,
            duration_seconds=0.0,
            size_bytes=0,
            elapsed_ms=int((time.time() - start_time) * 1000),
            error=f"Invalid quality preset: {quality}",
            error_reason=f"Quality must be one of: {', '.join(QUALITY_PRESETS.keys())}",
            error_fix=f"Use --quality draft, --quality standard, or --quality archival"
        )

    # Determine output path
    if output_dir:
        output_path = Path(output_dir) / f"{input_file.stem}.mp3"
    else:
        output_path = input_file.with_suffix(".mp3")

    # Dry run mode
    if dry_run:
        if not quiet:
            print(f"[DRY RUN] Would extract audio from: {input_path}")
            print(f"[DRY RUN] Output would be: {output_path}")
            print(f"[DRY RUN] Quality: {quality} ({QUALITY_PRESETS[quality]})")

        return AudioExtractionResult(
            success=True,
            output_path=str(output_path),
            duration_seconds=0.0,
            size_bytes=0,
            elapsed_ms=int((time.time() - start_time) * 1000),
            error=None,
            error_reason=None,
            error_fix=None
        )

    # Build FFmpeg command
    bitrate = QUALITY_PRESETS[quality]
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-vn",  # No video
        "-acodec", "libmp3lame",
        "-b:a", bitrate,
        "-y",  # Overwrite output
        str(output_path)
    ]

    if verbose:
        print(f"Executing: {' '.join(cmd)}")

    # Run FFmpeg
    try:
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE
        )

        total_duration: Optional[float] = None
        stderr_output = []

        # Process stderr for progress
        if process.stderr:
            for line in iter(process.stderr.readline, b''):
                line_str = line.decode('utf-8', errors='replace')
                stderr_output.append(line_str)

                if verbose:
                    print(line_str, end='')

                # Parse total duration
                if total_duration is None:
                    duration = get_total_duration(line_str)
                    if duration:
                        total_duration = duration

                # Parse progress
                current_time = parse_time_from_progress(line_str)
                if current_time is not None and total_duration and progress_callback:
                    percent = min(100, (current_time / total_duration) * 100)
                    progress_callback({
                        "percent": percent,
                        "time": current_time,
                        "total": total_duration,
                    })

        process.wait()

        # Check for errors
        if process.returncode != 0:
            stderr_text = ''.join(stderr_output)

            # Detect specific error types
            if "does not contain any stream" in stderr_text or "no audio" in stderr_text.lower():
                error_reason = "No audio stream found in file"
                error_fix = "Open file in VLC to verify it contains audio"
            elif "Invalid data found" in stderr_text:
                error_reason = "File is corrupted or in an unsupported format"
                error_fix = "Try re-recording the file or check if it plays in VLC"
            else:
                error_reason = "FFmpeg extraction failed"
                error_fix = "Run with --verbose to see detailed FFmpeg output"

            return AudioExtractionResult(
                success=False,
                output_path=None,
                duration_seconds=0.0,
                size_bytes=0,
                elapsed_ms=int((time.time() - start_time) * 1000),
                error=f"Could not extract audio from {input_file.name}",
                error_reason=error_reason,
                error_fix=error_fix
            )

        # Success - get output file stats
        if output_path.exists():
            size_bytes = output_path.stat().st_size
        else:
            size_bytes = 0

        elapsed_ms = int((time.time() - start_time) * 1000)

        if not quiet:
            print(f"Success: {output_path.name} ({size_bytes / 1024 / 1024:.1f} MB)")
            print(f"         Saved to: {output_path.parent}")

        return AudioExtractionResult(
            success=True,
            output_path=str(output_path),
            duration_seconds=total_duration or 0.0,
            size_bytes=size_bytes,
            elapsed_ms=elapsed_ms,
            error=None,
            error_reason=None,
            error_fix=None
        )

    except FileNotFoundError:
        return AudioExtractionResult(
            success=False,
            output_path=None,
            duration_seconds=0.0,
            size_bytes=0,
            elapsed_ms=int((time.time() - start_time) * 1000),
            error="FFmpeg not found",
            error_reason="FFmpeg is not installed or not in PATH",
            error_fix="Install FFmpeg with: brew install ffmpeg"
        )

    except Exception as e:
        return AudioExtractionResult(
            success=False,
            output_path=None,
            duration_seconds=0.0,
            size_bytes=0,
            elapsed_ms=int((time.time() - start_time) * 1000),
            error=f"Unexpected error during extraction",
            error_reason=str(e),
            error_fix="Check file permissions and disk space"
        )


def extract_audio_with_progress(
    input_path: str,
    output_dir: Optional[str] = None,
    quality: str = DEFAULT_QUALITY,
    dry_run: bool = False,
    verbose: bool = False,
    quiet: bool = False
) -> AudioExtractionResult:
    """Extract audio with rich progress bar display."""
    if not RICH_AVAILABLE or quiet or dry_run:
        return extract_audio(input_path, output_dir, quality, dry_run, verbose, quiet)

    console = Console()
    input_file = Path(input_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Extracting: {input_file.name}", total=100)

        def update_progress(data: Dict[str, Any]):
            if "percent" in data:
                progress.update(task, completed=data["percent"])

        result = extract_audio(
            input_path,
            output_dir,
            quality,
            dry_run,
            verbose,
            quiet,
            progress_callback=update_progress
        )

        progress.update(task, completed=100)

    return result


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract audio from video files to MP3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.mov                          # Standard quality, same directory
  %(prog)s video.mov --quality archival       # High quality (320k)
  %(prog)s video.mov --output-dir ~/audio     # Custom output directory
  %(prog)s video.mov --dry-run                # Show what would happen
  %(prog)s video.mov --verbose                # Show FFmpeg output
        """
    )

    parser.add_argument("input", help="Input video file path")
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory (default: same as input)"
    )
    parser.add_argument(
        "--quality", "-q",
        choices=["draft", "standard", "archival"],
        default="standard",
        help="Quality preset: draft (128k), standard (192k), archival (320k)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show FFmpeg output"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Show only errors"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON"
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send notification when MP3 is ready"
    )

    args = parser.parse_args()

    # Run extraction
    result = extract_audio_with_progress(
        args.input,
        args.output_dir,
        args.quality,
        args.dry_run,
        args.verbose,
        args.quiet
    )

    # Output result
    if args.json:
        print(result.to_json())
    elif not result.success and not args.quiet:
        print(f"\nError: {result.error}", file=sys.stderr)
        print(f"       Reason: {result.error_reason}", file=sys.stderr)
        print(f"       Fix: {result.error_fix}", file=sys.stderr)

    # Send notification if requested
    if args.notify and NOTIFY_AVAILABLE:
        if result.success and result.output_path:
            size_mb = result.size_bytes / 1024 / 1024
            notify_file_ready(
                result.output_path,
                f"MP3 ready for Gemini transcription ({size_mb:.1f} MB)"
            )
        elif not result.success:
            notify_error(f"Audio extraction failed: {result.error}")
    elif args.notify and not NOTIFY_AVAILABLE:
        print("Warning: --notify requested but notify module not available", file=sys.stderr)

    # Exit code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
whisperX Transcriber

Transcribes audio files using whisperX with optional speaker diarization.

REQ-608: whisperX Transcription
REQ-609: Output Formats (markdown with speaker labels)
REQ-617: Speaker Diarization

Usage:
    python whisperx_transcriber.py audio.mp3 [--output-dir DIR] [--model large-v3]
    python whisperx_transcriber.py audio.mp3 --diarize --hf-token $HF_TOKEN
    python whisperx_transcriber.py audio.mp3 --format markdown|srt|vtt|txt|json

Output (JSON):
    {
      "success": true,
      "output_path": "/path/to/output-transcript.md",
      "duration_seconds": 3075.67,
      "speakers_detected": 2,
      "model_used": "large-v3",
      "elapsed_ms": 12345,
      "real_time_factor": 25.5,
      "error": null
    }
"""

# CRITICAL: Patch torch.load BEFORE importing anything else
# PyTorch 2.6+ changed weights_only default to True, breaking pyannote/speechbrain
# PyTorch 2.8+ requires explicit safe_globals for omegaconf classes
try:
    import torch
    import torch.serialization

    # Add omegaconf classes to safe globals for PyTorch 2.8+
    try:
        import omegaconf
        import omegaconf.base
        import omegaconf.listconfig
        import omegaconf.dictconfig
        from omegaconf import DictConfig, ListConfig, OmegaConf
        safe_classes = [
            omegaconf.listconfig.ListConfig,
            omegaconf.dictconfig.DictConfig,
            omegaconf.base.ContainerMetadata,
            omegaconf.base.Metadata,
            omegaconf.base.Node,
            DictConfig,
            ListConfig,
        ]
        # Add any other omegaconf classes we can find
        for name in dir(omegaconf.base):
            obj = getattr(omegaconf.base, name, None)
            if isinstance(obj, type) and obj not in safe_classes:
                safe_classes.append(obj)
        if hasattr(torch.serialization, 'add_safe_globals'):
            torch.serialization.add_safe_globals(safe_classes)
    except (ImportError, AttributeError):
        pass

    _original_torch_load = torch.serialization.load
    def _patched_torch_load(*args, **kwargs):
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _original_torch_load(*args, **kwargs)
    # Patch both locations
    torch.serialization.load = _patched_torch_load
    torch.load = _patched_torch_load
except ImportError:
    pass

import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Literal, Tuple

try:
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Check if whisperX is available
try:
    import whisperx
    from whisperx.diarize import DiarizationPipeline
    WHISPERX_AVAILABLE = True
    DIARIZATION_AVAILABLE = True
except ImportError:
    WHISPERX_AVAILABLE = False
    DIARIZATION_AVAILABLE = False


# Constants
SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large", "large-v3"]
DEFAULT_MODEL = "large-v3"
DEFAULT_SEGMENT_DURATION = 30
DEFAULT_OUTPUT_FORMAT = "markdown"


@dataclass
class TranscriptSegment:
    """A single segment of the transcript."""
    start_time: float
    end_time: float
    speaker: str
    text: str
    confidence: Optional[float] = None


@dataclass
class TranscriptionResult:
    """Result of transcription operation."""
    success: bool
    output_path: str
    duration_seconds: float
    speakers_detected: int
    segments: List[TranscriptSegment] = field(default_factory=list)
    model_used: str = ""
    elapsed_ms: int = 0
    real_time_factor: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['segments'] = [asdict(seg) for seg in self.segments]
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ==================== TIMESTAMP FORMATTING ====================

def format_timestamp(seconds: float) -> str:
    """Format seconds to HH:MM:SS."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_timestamp_srt(seconds: float) -> str:
    """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """Format seconds to VTT timestamp (HH:MM:SS.mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


# ==================== OUTPUT FORMATTERS ====================

def _format_markdown(
    segments: List[TranscriptSegment],
    source_name: str,
    duration_seconds: float,
    model_used: str,
    speakers_detected: int
) -> str:
    """Format transcript as markdown with speaker labels."""
    lines = []

    # Extract date from filename if possible
    date_str = datetime.now().strftime("%Y-%m-%d")
    stem = Path(source_name).stem
    if stem and len(stem) >= 10:
        try:
            date_str = stem[:10]
        except Exception:
            pass

    # Header
    lines.append(f"# Transcript: {stem}")
    lines.append("")
    lines.append(f"**Source**: {source_name}")
    lines.append(f"**Date**: {date_str}")
    lines.append(f"**Duration**: {format_timestamp(duration_seconds)}")
    lines.append(f"**Model**: whisperX {model_used}")
    lines.append(f"**Speakers**: {speakers_detected}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Transcript")
    lines.append("")

    # Segments
    for segment in segments:
        timestamp = format_timestamp(segment.start_time)
        lines.append(f"**[{segment.speaker}] {timestamp}** {segment.text.strip()}")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Generated by video-transcript-pipeline v1.0.0*")

    return "\n".join(lines)


def _format_json(
    segments: List[TranscriptSegment],
    source_name: str,
    duration_seconds: float,
    model_used: str,
    speakers_detected: int
) -> str:
    """Format transcript as JSON."""
    data = {
        "source": source_name,
        "duration_seconds": duration_seconds,
        "model": model_used,
        "speakers_detected": speakers_detected,
        "segments": [
            {
                "start": seg.start_time,
                "end": seg.end_time,
                "speaker": seg.speaker,
                "text": seg.text.strip(),
                "confidence": seg.confidence
            }
            for seg in segments
        ]
    }
    return json.dumps(data, indent=2)


def _format_srt(segments: List[TranscriptSegment]) -> str:
    """Format transcript as SRT subtitle file."""
    lines = []
    for i, segment in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{format_timestamp_srt(segment.start_time)} --> {format_timestamp_srt(segment.end_time)}")
        speaker_prefix = f"[{segment.speaker}] " if segment.speaker else ""
        lines.append(f"{speaker_prefix}{segment.text.strip()}")
        lines.append("")
    return "\n".join(lines)


def _format_vtt(segments: List[TranscriptSegment]) -> str:
    """Format transcript as WebVTT subtitle file."""
    lines = ["WEBVTT", ""]
    for i, segment in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{format_timestamp_vtt(segment.start_time)} --> {format_timestamp_vtt(segment.end_time)}")
        speaker_prefix = f"[{segment.speaker}] " if segment.speaker else ""
        lines.append(f"{speaker_prefix}{segment.text.strip()}")
        lines.append("")
    return "\n".join(lines)


def _format_txt(segments: List[TranscriptSegment]) -> str:
    """Format transcript as plain text."""
    lines = []
    current_speaker = None
    for segment in segments:
        if segment.speaker != current_speaker:
            if current_speaker is not None:
                lines.append("")
            lines.append(f"[{segment.speaker}]")
            current_speaker = segment.speaker
        lines.append(segment.text.strip())
    return "\n".join(lines)


# ==================== WHISPERX INTEGRATION ====================

def _normalize_speaker_label(speaker_id: str, speaker_map: Dict[str, int]) -> str:
    """Convert SPEAKER_00 format to Speaker 1 format."""
    if speaker_id not in speaker_map:
        speaker_map[speaker_id] = len(speaker_map) + 1
    return f"Speaker {speaker_map[speaker_id]}"


def _run_whisperx(
    audio_path: str,
    model: str,
    language: Optional[str],
    diarize: bool,
    hf_token: Optional[str],
    num_speakers: Optional[int] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Tuple[Dict[str, Any], int]:
    """
    Run whisperX transcription and optional diarization.

    Returns:
        Tuple of (result dict with segments, number of speakers)
    """
    if not WHISPERX_AVAILABLE:
        raise ImportError("whisperX is not installed. Install with: pip install whisperx")

    # Device selection: CUDA > CPU (MPS not supported by whisperX)
    if torch.cuda.is_available():
        device = "cuda"
        compute_type = "float16"
    else:
        device = "cpu"
        compute_type = "int8"

    if progress_callback:
        progress_callback({"stage": "loading_model", "percent": 0})

    # Load model
    whisper_model = whisperx.load_model(model, device, compute_type=compute_type)

    if progress_callback:
        progress_callback({"stage": "loading_audio", "percent": 10})

    # Load audio
    audio = whisperx.load_audio(audio_path)

    if progress_callback:
        progress_callback({"stage": "transcribing", "percent": 20})

    # Transcribe
    result = whisper_model.transcribe(audio, batch_size=16, language=language)

    if progress_callback:
        progress_callback({"stage": "aligning", "percent": 60})

    # Align whisper output
    model_a, metadata = whisperx.load_align_model(
        language_code=result.get("language", "en"),
        device=device
    )
    result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False
    )

    speakers_detected = 0

    # Diarization (if requested and token available)
    if diarize:
        token = hf_token or os.environ.get("HF_TOKEN")
        if token:
            if progress_callback:
                progress_callback({"stage": "diarizing", "percent": 80})

            try:
                print("Loading diarization pipeline...", file=sys.stderr)
                diarize_model = DiarizationPipeline(use_auth_token=token, device=device)
                print("Running diarization...", file=sys.stderr)

                # Build diarization kwargs
                diarize_kwargs = {}
                if num_speakers is not None:
                    diarize_kwargs["num_speakers"] = num_speakers
                    print(f"Constraining to {num_speakers} speakers", file=sys.stderr)
                if min_speakers is not None:
                    diarize_kwargs["min_speakers"] = min_speakers
                if max_speakers is not None:
                    diarize_kwargs["max_speakers"] = max_speakers

                diarize_segments = diarize_model(audio, **diarize_kwargs)
                print(f"Diarization complete", file=sys.stderr)
                result = whisperx.assign_word_speakers(diarize_segments, result)

                # Count unique speakers
                speakers = set()
                for seg in result.get("segments", []):
                    if "speaker" in seg:
                        speakers.add(seg["speaker"])
                speakers_detected = len(speakers)
                print(f"Detected {speakers_detected} speakers: {speakers}", file=sys.stderr)
            except Exception as e:
                # Diarization failed, continue without it
                import traceback
                print(f"Diarization failed: {type(e).__name__}: {e}", file=sys.stderr)
                traceback.print_exc()

    if progress_callback:
        progress_callback({"stage": "complete", "percent": 100})

    return result, speakers_detected


def _get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds using ffprobe or whisperx."""
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass

    # Fallback: estimate from file size (rough approximation)
    try:
        size_bytes = Path(audio_path).stat().st_size
        # Assume ~192kbps MP3 = 24KB/s
        return size_bytes / 24000
    except Exception:
        return 0.0


# ==================== MAIN TRANSCRIBE FUNCTION ====================

def transcribe(
    audio_path: str,
    output_dir: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    language: Optional[str] = None,
    diarize: bool = True,
    hf_token: Optional[str] = None,
    output_format: Literal["markdown", "srt", "vtt", "txt", "json"] = DEFAULT_OUTPUT_FORMAT,
    segment_duration: int = DEFAULT_SEGMENT_DURATION,
    num_speakers: Optional[int] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> TranscriptionResult:
    """
    Transcribe audio file using whisperX with optional speaker diarization.

    Args:
        audio_path: Path to input audio file
        output_dir: Directory for output (default: same as input)
        model: Whisper model to use (tiny, base, small, medium, large, large-v3)
        language: Language code (auto-detect if None)
        diarize: Whether to perform speaker diarization
        hf_token: HuggingFace token for pyannote (env: HF_TOKEN)
        output_format: Output format (markdown, srt, vtt, txt, json)
        segment_duration: Target segment duration in seconds
        num_speakers: Exact number of speakers (if known)
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers
        progress_callback: Optional callback for progress updates

    Returns:
        TranscriptionResult with success status, output path, and segments
    """
    start_time = time.time()
    audio_file = Path(audio_path)

    # Validate input file exists
    if not audio_file.exists():
        return TranscriptionResult(
            success=False,
            output_path="",
            duration_seconds=0.0,
            speakers_detected=0,
            segments=[],
            model_used=model,
            elapsed_ms=int((time.time() - start_time) * 1000),
            real_time_factor=0.0,
            error=f"Audio file not found: {audio_path}. Check that the file exists."
        )

    # Check if whisperX is available
    if not WHISPERX_AVAILABLE:
        return TranscriptionResult(
            success=False,
            output_path="",
            duration_seconds=0.0,
            speakers_detected=0,
            segments=[],
            model_used=model,
            elapsed_ms=int((time.time() - start_time) * 1000),
            real_time_factor=0.0,
            error="whisperX is not installed. Install with: pip install whisperx torch torchaudio"
        )

    # Check diarization requirements
    if diarize:
        token = hf_token or os.environ.get("HF_TOKEN")
        if not token:
            # Fall back to no diarization instead of failing
            diarize = False

    # Determine output path
    if output_dir:
        output_base = Path(output_dir) / f"{audio_file.stem}-transcript"
    else:
        output_base = audio_file.parent / f"{audio_file.stem}-transcript"

    # Add extension based on format
    ext_map = {
        "markdown": ".md",
        "srt": ".srt",
        "vtt": ".vtt",
        "txt": ".txt",
        "json": ".json"
    }
    output_path = str(output_base) + ext_map.get(output_format, ".md")

    # Get audio duration
    audio_duration = _get_audio_duration(audio_path)

    try:
        # Run whisperX transcription
        result, speakers_detected = _run_whisperx(
            audio_path,
            model,
            language,
            diarize,
            hf_token,
            num_speakers=num_speakers,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            progress_callback=progress_callback
        )

        # Convert to TranscriptSegment objects
        segments = []
        speaker_map: Dict[str, int] = {}

        for seg in result.get("segments", []):
            speaker_id = seg.get("speaker", "SPEAKER_00")
            speaker_label = _normalize_speaker_label(speaker_id, speaker_map)

            segments.append(TranscriptSegment(
                start_time=seg.get("start", 0.0),
                end_time=seg.get("end", 0.0),
                speaker=speaker_label,
                text=seg.get("text", ""),
                confidence=seg.get("confidence")
            ))

        # If no speakers were detected from diarization, count from segments
        if speakers_detected == 0:
            speakers_detected = len(speaker_map) if speaker_map else 1

        # Calculate duration from segments if not available
        if audio_duration == 0 and segments:
            audio_duration = max(seg.end_time for seg in segments)

        # Format output
        source_name = audio_file.name
        if output_format == "markdown":
            content = _format_markdown(segments, source_name, audio_duration, model, speakers_detected)
        elif output_format == "json":
            content = _format_json(segments, source_name, audio_duration, model, speakers_detected)
        elif output_format == "srt":
            content = _format_srt(segments)
        elif output_format == "vtt":
            content = _format_vtt(segments)
        elif output_format == "txt":
            content = _format_txt(segments)
        else:
            content = _format_markdown(segments, source_name, audio_duration, model, speakers_detected)

        # Write output file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(content)

        elapsed_ms = int((time.time() - start_time) * 1000)
        elapsed_seconds = elapsed_ms / 1000

        # Calculate real-time factor
        real_time_factor = audio_duration / elapsed_seconds if elapsed_seconds > 0 else 0.0

        return TranscriptionResult(
            success=True,
            output_path=output_path,
            duration_seconds=audio_duration,
            speakers_detected=speakers_detected,
            segments=segments,
            model_used=model,
            elapsed_ms=elapsed_ms,
            real_time_factor=real_time_factor,
            error=None
        )

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return TranscriptionResult(
            success=False,
            output_path="",
            duration_seconds=0.0,
            speakers_detected=0,
            segments=[],
            model_used=model,
            elapsed_ms=elapsed_ms,
            real_time_factor=0.0,
            error=str(e)
        )


def transcribe_with_progress(
    audio_path: str,
    output_dir: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    language: Optional[str] = None,
    diarize: bool = True,
    hf_token: Optional[str] = None,
    output_format: Literal["markdown", "srt", "vtt", "txt", "json"] = DEFAULT_OUTPUT_FORMAT,
    segment_duration: int = DEFAULT_SEGMENT_DURATION,
    num_speakers: Optional[int] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None
) -> TranscriptionResult:
    """Transcribe with rich progress display."""
    if not RICH_AVAILABLE:
        return transcribe(audio_path, output_dir, model, language, diarize, hf_token, output_format, segment_duration, num_speakers, min_speakers, max_speakers)

    console = Console()
    audio_file = Path(audio_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Transcribing: {audio_file.name}", total=100)

        def update_progress(data: Dict[str, Any]):
            if "percent" in data:
                progress.update(task, completed=data["percent"])
            if "stage" in data:
                stage_names = {
                    "loading_model": "Loading model...",
                    "loading_audio": "Loading audio...",
                    "transcribing": "Transcribing...",
                    "aligning": "Aligning timestamps...",
                    "diarizing": "Detecting speakers...",
                    "complete": "Complete!"
                }
                progress.update(task, description=f"Transcribing: {stage_names.get(data['stage'], data['stage'])}")

        result = transcribe(
            audio_path,
            output_dir,
            model,
            language,
            diarize,
            hf_token,
            output_format,
            segment_duration,
            num_speakers=num_speakers,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            progress_callback=update_progress
        )

        progress.update(task, completed=100)

    return result


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Transcribe audio using whisperX with speaker diarization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s audio.mp3                              # Default settings (large-v3, markdown)
  %(prog)s audio.mp3 --model small                # Use smaller model
  %(prog)s audio.mp3 --diarize --hf-token $HF_TOKEN  # With speaker diarization
  %(prog)s audio.mp3 --format srt                 # Output as SRT subtitles
  %(prog)s audio.mp3 --output-dir ~/transcripts   # Custom output directory
        """
    )

    parser.add_argument("audio", help="Input audio file path")
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory (default: same as input)"
    )
    parser.add_argument(
        "--model", "-m",
        choices=SUPPORTED_MODELS,
        default=DEFAULT_MODEL,
        help=f"Whisper model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--language", "-l",
        help="Language code (auto-detect if not specified)"
    )
    parser.add_argument(
        "--diarize",
        action="store_true",
        default=True,
        help="Perform speaker diarization (default: True)"
    )
    parser.add_argument(
        "--no-diarize",
        action="store_true",
        help="Skip speaker diarization"
    )
    parser.add_argument(
        "--hf-token",
        help="HuggingFace token for pyannote (or set HF_TOKEN env var)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "srt", "vtt", "txt", "json"],
        default=DEFAULT_OUTPUT_FORMAT,
        help=f"Output format (default: {DEFAULT_OUTPUT_FORMAT})"
    )
    parser.add_argument(
        "--segment-duration",
        type=int,
        default=DEFAULT_SEGMENT_DURATION,
        help=f"Target segment duration in seconds (default: {DEFAULT_SEGMENT_DURATION})"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Show only errors"
    )
    parser.add_argument(
        "--num-speakers",
        type=int,
        help="Exact number of speakers (if known)"
    )
    parser.add_argument(
        "--min-speakers",
        type=int,
        help="Minimum number of speakers"
    )
    parser.add_argument(
        "--max-speakers",
        type=int,
        help="Maximum number of speakers"
    )

    args = parser.parse_args()

    # Handle diarize flags
    diarize = args.diarize and not args.no_diarize

    # Run transcription
    result = transcribe_with_progress(
        args.audio,
        args.output_dir,
        args.model,
        args.language,
        diarize,
        args.hf_token,
        args.format,
        args.segment_duration,
        num_speakers=args.num_speakers,
        min_speakers=args.min_speakers,
        max_speakers=args.max_speakers
    )

    # Output result
    if args.json:
        print(result.to_json())
    elif result.success:
        if not args.quiet:
            print(f"\nTranscription complete!")
            print(f"  Output: {result.output_path}")
            print(f"  Duration: {format_timestamp(result.duration_seconds)}")
            print(f"  Speakers: {result.speakers_detected}")
            print(f"  Model: {result.model_used}")
            print(f"  Processing time: {result.elapsed_ms / 1000:.1f}s")
            print(f"  Real-time factor: {result.real_time_factor:.1f}x")
    else:
        print(f"\nError: {result.error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

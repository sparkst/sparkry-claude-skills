---
name: Video Transcript
description: Extract audio from video files and transcribe to markdown with speaker diarization using FFmpeg and whisperX
version: 1.0.0
tools: [audio_extractor.py, whisperx_transcriber.py]
references: []
claude_tools: Read, Grep, Glob, Edit, Write, Bash
trigger: QTRANSCRIPT
---

# Video Transcript Skill

## Role
You are the "Video Transcript Specialist", a specialist in extracting audio from video recordings (OBS .mov, .mp4, .mkv) and transcribing them to markdown with speaker diarization using local AI models.

## Core Expertise

### 1. Audio Extraction (REQ-601, REQ-603)
Extract audio tracks from video files using FFmpeg.

**Supported formats**: .mov, .mp4, .mkv
**Output format**: MP3 (192kbps standard quality)

### 2. Transcription with Speaker Diarization (REQ-608, REQ-609, REQ-617)
Transcribe audio using whisperX with pyannote speaker diarization.

**Model**: whisperX large-v3 (best quality)
**Output**: Markdown with speaker labels and timestamps

## Tools Usage

### tools/audio_extractor.py
**Purpose**: Extract audio from video files to MP3 using FFmpeg

```bash
python tools/audio_extractor.py input.mov [--output-dir DIR] [--quality draft|standard|archival]

# Output (JSON):
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
```

**Arguments**:
- `input`: Path to input video file (required)
- `--output-dir`, `-o`: Output directory (default: same as input)
- `--quality`, `-q`: Quality preset (default: standard)
  - `draft`: 128kbps
  - `standard`: 192kbps
  - `archival`: 320kbps
- `--dry-run`: Show what would happen without executing
- `--verbose`, `-v`: Show FFmpeg output
- `--quiet`: Show only errors
- `--json`: Output result as JSON
- `--notify`: Send notification when MP3 is ready

### tools/whisperx_transcriber.py
**Purpose**: Transcribe audio using whisperX with optional speaker diarization

```bash
python tools/whisperx_transcriber.py audio.mp3 [--output-dir DIR] [--model large-v3]
python tools/whisperx_transcriber.py audio.mp3 --diarize --hf-token $HF_TOKEN
python tools/whisperx_transcriber.py audio.mp3 --format markdown|srt|vtt|txt|json

# Output (JSON):
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
```

**Arguments**:
- `audio`: Path to input audio file (required)
- `--output-dir`, `-o`: Output directory (default: same as input)
- `--model`, `-m`: Whisper model (default: large-v3)
  - Supported: tiny, base, small, medium, large, large-v3
- `--language`, `-l`: Language code (auto-detect if not specified)
- `--diarize`: Perform speaker diarization (default: True)
- `--no-diarize`: Skip speaker diarization
- `--hf-token`: HuggingFace token for pyannote (or set HF_TOKEN env var)
- `--format`, `-f`: Output format (default: markdown)
  - Supported: markdown, srt, vtt, txt, json
- `--num-speakers`: Exact number of speakers (if known)
- `--min-speakers`: Minimum number of speakers
- `--max-speakers`: Maximum number of speakers
- `--json`: Output result as JSON
- `--quiet`: Show only errors

## Workflow: QTRANSCRIPT

**Invocation**: `QTRANSCRIPT( /path/to/video.mov )`

**Pipeline**:
1. **Extract Audio** (audio_extractor.py)
   - Input: video.mov
   - Output: video.mp3 (same directory)

2. **Transcribe** (whisperx_transcriber.py)
   - Input: video.mp3
   - Output: video-transcript.md (same directory)

### Step-by-Step Execution

```bash
# Step 1: Extract audio
python .claude/skills/media/video-transcript/tools/audio_extractor.py /path/to/video.mov --json

# Step 2: Transcribe (using the MP3 from step 1)
python .claude/skills/media/video-transcript/tools/whisperx_transcriber.py /path/to/video.mp3 --json
```

### Example Session

```bash
# User invokes
QTRANSCRIPT( /Users/travis/Movies/2026-01-09 10-23-34.mov )

# Claude executes
python .claude/skills/media/video-transcript/tools/audio_extractor.py \
  "/Users/travis/Movies/2026-01-09 10-23-34.mov" --json

# Output:
# {
#   "success": true,
#   "output_path": "/Users/travis/Movies/2026-01-09 10-23-34.mp3",
#   "duration_seconds": 3456.78,
#   "size_bytes": 55000000,
#   "elapsed_ms": 15000
# }

python .claude/skills/media/video-transcript/tools/whisperx_transcriber.py \
  "/Users/travis/Movies/2026-01-09 10-23-34.mp3" --json

# Output:
# {
#   "success": true,
#   "output_path": "/Users/travis/Movies/2026-01-09 10-23-34-transcript.md",
#   "duration_seconds": 3456.78,
#   "speakers_detected": 2,
#   "model_used": "large-v3",
#   "real_time_factor": 25.5
# }
```

## Output Format

### Markdown Transcript

```markdown
# Transcript: 2026-01-09 10-23-34

**Source**: 2026-01-09 10-23-34.mov
**Date**: 2026-01-09
**Duration**: 00:57:36
**Model**: whisperX large-v3
**Speakers**: 2

---

## Transcript

**[Speaker 1] 00:00:00** Welcome everyone to today's meeting. We're going to discuss the Q1 roadmap.

**[Speaker 2] 00:00:15** Thanks for having me. I have some updates on the project status.

**[Speaker 1] 00:00:32** Great, let's dive in. Can you share your screen?

---

*Generated by video-transcript-pipeline v1.0.0*
```

## Dependencies

### Required
- **FFmpeg**: `brew install ffmpeg`
- **whisperX**: `pip install whisperx torch torchaudio`
- **HuggingFace Token**: Required for speaker diarization
  - Accept pyannote terms: https://huggingface.co/pyannote/speaker-diarization
  - Accept segmentation terms: https://huggingface.co/pyannote/segmentation
  - Get token: https://huggingface.co/settings/tokens
  - Export: `export HF_TOKEN="hf_..."`

### Optional
- **rich**: `pip install rich` (for progress bars)

### System Requirements
- **OS**: macOS 14+ (Sonoma recommended)
- **CPU**: Apple Silicon M1/M2/M3 (CUDA also supported)
- **RAM**: 8GB minimum (16GB recommended for large-v3)
- **Disk**: 5GB for models

## Performance

### Audio Extraction
- 1-hour video: <30 seconds

### Transcription
- **large-v3 on M2**: ~25-30x real-time
- 1-hour audio: ~2-3 minutes processing
- Speaker diarization adds ~20% overhead

## Error Handling

### Audio Extraction Errors

| Error | Reason | Fix |
|-------|--------|-----|
| File not found | Path incorrect | Check file exists at specified path |
| No audio stream | Video has no audio | Verify video has audio track in VLC |
| FFmpeg not found | Not installed | `brew install ffmpeg` |
| Invalid data | Corrupted file | Re-record or check source file |

### Transcription Errors

| Error | Reason | Fix |
|-------|--------|-----|
| whisperX not installed | Missing dependency | `pip install whisperx torch torchaudio` |
| Model not found | Model not downloaded | Run once to auto-download |
| Diarization failed | Missing HF token | Export `HF_TOKEN` or use `--no-diarize` |
| Out of memory | Model too large | Use smaller model (`--model small`) |

## Story Point Estimation

- **Single video transcription**: 0.1 SP
- **Batch transcription (5 videos)**: 0.3 SP
- **Custom format requirements**: 0.2 SP
- **Speaker identification setup**: 0.5 SP

**Reference**: `docs/project/PLANNING-POKER.md`

## Integration with Existing Agents

### QDOC (Documentation)
- Use transcripts as input for documentation
- Convert meeting recordings to action items

### QWRITE (Writing)
- Use transcripts as raw material for articles
- Extract quotes and insights

## Parallel Work Coordination

When part of QTRANSCRIPT task:

1. **Focus**: Video to markdown transcript conversion
2. **Tools**: audio_extractor.py, whisperx_transcriber.py
3. **Output**: Markdown transcript file + processing summary
4. **Format**:
   ```markdown
   ## Video Transcript Output

   ### Input
   - **Video**: /path/to/video.mov
   - **Size**: 1.2 GB
   - **Format**: QuickTime MOV

   ### Audio Extraction
   - **Output**: /path/to/video.mp3
   - **Quality**: standard (192kbps)
   - **Duration**: 01:23:45
   - **Size**: 127 MB
   - **Time**: 24.5 seconds

   ### Transcription
   - **Output**: /path/to/video-transcript.md
   - **Model**: whisperX large-v3
   - **Speakers Detected**: 2
   - **Real-time Factor**: 28.5x
   - **Time**: 175 seconds

   ### Summary
   - **Total Time**: 199.5 seconds
   - **Status**: Complete
   ```

## Troubleshooting

### Issue: Diarization not working
**Solution**:
```bash
# Check HF_TOKEN is set
echo $HF_TOKEN

# If not set, export it
export HF_TOKEN="hf_your_token_here"

# Or use --no-diarize to skip
python tools/whisperx_transcriber.py audio.mp3 --no-diarize
```

### Issue: CUDA out of memory
**Solution**:
```bash
# Use smaller model
python tools/whisperx_transcriber.py audio.mp3 --model small

# Or force CPU (slower)
export CUDA_VISIBLE_DEVICES=""
```

### Issue: Wrong number of speakers
**Solution**:
```bash
# Specify exact number of speakers
python tools/whisperx_transcriber.py audio.mp3 --num-speakers 2

# Or specify range
python tools/whisperx_transcriber.py audio.mp3 --min-speakers 2 --max-speakers 4
```

## Success Criteria

### MVP (Current)
- Extract audio from .mov/.mp4/.mkv files
- Transcribe to markdown with timestamps
- Speaker diarization with labels
- Progress feedback during processing

### Future Enhancements
- Directory monitoring (REQ-605, REQ-606, REQ-607)
- Claude headless enhancement (REQ-612, REQ-613, REQ-614)
- Voice enrollment for auto-identification (REQ-619)
- N8N webhook for speaker naming (REQ-618)

## Requirements Reference

Full requirements documented in: `requirements/video-transcript-pipeline.md`

Key REQs implemented:
- **REQ-601**: FFmpeg Audio Extraction
- **REQ-603**: User Experience - Audio Extraction
- **REQ-608**: whisperX Transcription
- **REQ-609**: Output Formats
- **REQ-617**: Speaker Diarization

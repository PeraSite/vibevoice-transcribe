---
name: vibevoice-transcribe
description: Transcribes batches of audio or video locally on Apple Silicon with VibeVoice ASR. Use for Korean interviews or other recordings that need channel-aware mono conversion, timestamps, speaker labels, terminology review, and auditable raw/final outputs.
compatibility: macOS Apple Silicon, uv, ffmpeg
license: MIT
---

# VibeVoice Transcription

This is an Agent Skill, not a Pi extension. Resolve commands relative to this
`SKILL.md`, so the same skill works from any compatible agent harness.

## Before running

Confirm from the request or source directory:

- input directory and one or more top-level filename globs
- language and terminology context
- output directory
- whether reviewed results should be published anywhere

Never alter source media. Do not include files outside the requested globs.

## Setup

From the directory containing this file:

```bash
uv sync --locked
uv run --locked pi-vibevoice-transcribe --download-model
```

The default model is `mlx-community/VibeVoice-ASR-4bit`. Runtime files are
stored outside the repository under:

```text
${VIBEVOICE_HOME:-${XDG_CACHE_HOME:-~/.cache}/pi-vibevoice-transcribe}
```

Set `VIBEVOICE_HOME` to use another disk. Allow roughly 10 GB free space.
Do not put downloaded models in the Git repository.

Do not automatically select a larger model from hardware capacity. The tested
4-bit model is the default because it is faster and uses less memory with
nearly identical output. Use `--model 8bit`, another Hugging Face repository,
or a local model path only when explicitly requested.

## Transcribe

```bash
uv run --locked pi-vibevoice-transcribe \
  --input "/path/to/media" \
  --output "/path/to/output" \
  --glob "C0*.MP4" \
  --language ko \
  --context "한국어 인터뷰입니다. 고유명사는 반드시 정확히 표기합니다."
```

Repeat `--glob` when more than one pattern is requested.

The command:

1. Selects only top-level files matching the globs.
2. Measures stereo channel loudness.
3. Uses the active channel if the other is effectively silent; otherwise uses
   a normal 50/50 mono downmix.
4. Creates mono 24 kHz FLAC under `audio/`.
5. Loads the model once and processes files sequentially.
6. Preserves VibeVoice JSON under `raw/` and writes readable text under
   `draft/`.
7. Writes `channel-analysis.json` and `logs/transcription.json`.
8. Resumes by skipping existing audio and raw results. Use `--force` only when
   explicitly reprocessing.

## Review

Review every file before creating `final/`:

- Preserve `[HH:MM:SS] [화자 N] 문구` formatting and timestamps.
- Compare uncertain passages with neighboring context and, when needed, the
  corresponding source audio.
- Correct names and domain terms only when evidence is clear.
- Mark unintelligible material instead of inventing words.
- Keep `raw/` and `draft/` unchanged.
- Save reviewed transcripts to `final/<source-stem>.txt`.
- Record substantive corrections in `correction-log.json` with filename,
  timestamp, original text, corrected text, and reason.

Do not use loudness-normalized audio by default. Try it only for demonstrably
quiet recordings and keep it as a separate comparison pass.

## Validate and optionally publish

Before completion, verify:

- selected source, audio, raw, draft, and final file sets match exactly
- every final transcript is non-empty and timestamp/speaker lines are valid
- ordering matches source filenames
- requested terminology errors are absent

Publish only when explicitly requested. If publishing, use each source
filename as an H1 followed by one plain-text code block, then fetch the target
again and verify first/last filenames, heading count, code-block count, and
last transcript cue.

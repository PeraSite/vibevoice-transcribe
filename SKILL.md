---
name: vibevoice-transcribe
description: Transcribes audio and video locally with VibeVoice ASR on Apple Silicon. Use for single files or batches that need speaker-aware timestamps, channel-safe mono conversion, and auditable raw output.
compatibility: macOS Apple Silicon, uv, ffmpeg
license: MIT
---

# VibeVoice Transcribe

This is a standard Agent Skill, not an extension for a specific agent. Resolve
commands relative to this `SKILL.md`.

## Inputs

Determine from the request:

- input directory
- one or more top-level filename globs
- output directory
- optional vocabulary, names, or domain context

Never alter source media or include files outside the requested globs.

## Setup

From the directory containing this file:

```bash
uv sync --locked
uv run --locked vibevoice-transcribe --download-model
```

The skill uses the pinned `mlx-community/VibeVoice-ASR-4bit` model. Runtime
files are stored outside the repository under:

```text
${VIBEVOICE_HOME:-${XDG_CACHE_HOME:-~/.cache}/vibevoice-transcribe}
```

Set `VIBEVOICE_HOME` to use another disk. Allow roughly 10 GB free space. Do
not put downloaded models in the Git repository.

## Transcribe

```bash
uv run --locked vibevoice-transcribe \
  --input "/path/to/media" \
  --output "/path/to/output" \
  --glob "*.mp4" \
  --context "Optional names, vocabulary, or domain information"
```

Repeat `--glob` for additional patterns. Omit `--context` when it is not
needed.

The command:

1. Selects only top-level files matching the globs.
2. Measures stereo channel loudness.
3. Uses the active channel if the other is effectively silent; otherwise uses
   a 50/50 mono downmix.
4. Creates mono 24 kHz FLAC under `audio/`.
5. Loads the model once and processes files sequentially.
6. Preserves VibeVoice JSON under `raw/`.
7. Writes timestamped, speaker-labelled text under `draft/`.
8. Writes `channel-analysis.json` and `logs/transcription.json`.
9. Resumes by skipping existing audio and raw results. Use `--force` only when
   explicitly reprocessing.

## Verify

Before reporting completion, verify:

- selected source, audio, raw, and draft file sets match
- every raw and draft output is non-empty
- draft lines use `[HH:MM:SS] [Speaker N] text` or
  `[HH:MM:SS] [Event] description`
- source files remain unchanged

If the user requests editorial correction or external publishing, preserve
`raw/` and `draft/`, write reviewed copies separately, and verify the final
destination after publishing.

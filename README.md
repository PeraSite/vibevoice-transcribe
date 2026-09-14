# vibevoice-transcribe

A reusable [Agent Skill](https://agentskills.io/) for local, speaker-aware
batch transcription with VibeVoice ASR and MLX on Apple Silicon.

It selects media by explicit top-level globs, detects silent stereo channels,
creates mono 24 kHz FLAC, loads the model once, and preserves raw and readable
outputs.

## Requirements

- macOS on Apple Silicon
- [uv](https://docs.astral.sh/uv/)
- FFmpeg (`brew install ffmpeg`)
- About 10 GB of free disk space for the model and environment

## Install for compatible agents

Clone the repository and expose it through the shared Agent Skills directory:

```bash
git clone https://github.com/PeraSite/vibevoice-transcribe \
  ~/PythonProjects/vibevoice-transcribe
mkdir -p ~/.agents/skills
ln -s ~/PythonProjects/vibevoice-transcribe \
  ~/.agents/skills/vibevoice-transcribe
```

Pi discovers `~/.agents/skills/`; run `/reload` after installation. For an
agent harness that uses another skills directory, symlink this repository into
that directory instead.

## Setup

```bash
cd ~/PythonProjects/vibevoice-transcribe
uv sync --locked
uv run --locked vibevoice-transcribe --download-model
```

The skill uses the pinned `mlx-community/VibeVoice-ASR-4bit` model. Models are
not stored in the repository. Runtime data defaults to:

```text
~/.cache/vibevoice-transcribe/
```

Use another disk when needed:

```bash
VIBEVOICE_HOME=/Volumes/FastSSD/vibevoice-cache \
  uv run --locked vibevoice-transcribe --download-model
```

## Use

Normally, invoke the skill from your agent:

```text
/skill:vibevoice-transcribe "Transcribe *.mp4 files in /path/to/media"
```

The CLI is also usable directly:

```bash
uv run --locked vibevoice-transcribe \
  --input "/path/to/media" \
  --output "/path/to/output" \
  --glob "*.mp4" \
  --context "Optional names, vocabulary, or domain information"
```

Repeat `--glob` to select multiple patterns. Only files directly inside the
input directory are selected. `--context` is optional.

## Output

```text
output/
├── audio/                    # mono 24 kHz FLAC
├── raw/                      # untouched VibeVoice JSON
├── draft/                    # timestamped speaker-labelled text
├── logs/transcription.json
└── channel-analysis.json
```

Draft lines use this format:

```text
[00:00:13] [Speaker 1] Transcribed text
[00:00:18] [Event] [Environmental Sounds]
```

## Development

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests
uv run --locked vibevoice-transcribe --self-check
```

The test suite does not download the model. Full ASR is intentionally an
opt-in local smoke test because the model is several gigabytes.

## Privacy

Transcription runs locally. Setup contacts Hugging Face to download model and
tokenizer files. Uploading or publishing transcripts is never automatic.

## License

The project code and skill instructions are MIT licensed. Downloaded models
and dependencies retain their upstream licenses; see
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

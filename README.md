# pi-vibevoice-transcribe

A reusable [Agent Skill](https://agentskills.io/) for local, speaker-aware
batch transcription on Apple Silicon with VibeVoice ASR and MLX.

It selects media by explicit top-level globs, detects silent stereo channels,
creates mono 24 kHz FLAC, loads the model once, and preserves raw and readable
outputs for human review.

## Requirements

- macOS on Apple Silicon
- [uv](https://docs.astral.sh/uv/)
- FFmpeg (`brew install ffmpeg`)
- About 10 GB of free disk space for the default model and environment

## Install for compatible agents

Clone the repository and expose it through the shared Agent Skills directory:

```bash
git clone https://github.com/PeraSite/pi-vibevoice-transcribe \
  ~/PythonProjects/pi-vibevoice-transcribe
mkdir -p ~/.agents/skills
ln -s ~/PythonProjects/pi-vibevoice-transcribe \
  ~/.agents/skills/vibevoice-transcribe
```

Pi discovers `~/.agents/skills/`; run `/reload` after installation. For an
agent harness that uses another skills directory, symlink this repository into
that directory instead.

## Setup

```bash
cd ~/PythonProjects/pi-vibevoice-transcribe
uv sync --locked
uv run --locked pi-vibevoice-transcribe --download-model
```

The default is `mlx-community/VibeVoice-ASR-4bit`. Models are not stored in the
repository. Runtime data defaults to:

```text
~/.cache/pi-vibevoice-transcribe/
```

Use another disk when needed:

```bash
VIBEVOICE_HOME=/Volumes/FastSSD/vibevoice-cache \
  uv run --locked pi-vibevoice-transcribe --download-model
```

## Use

Normally, invoke the skill from your agent:

```text
/skill:vibevoice-transcribe "/path/to/videos에서 C0*.MP4를 한국어로 전사해줘"
```

The underlying CLI is also usable directly:

```bash
uv run --locked pi-vibevoice-transcribe \
  --input "/path/to/videos" \
  --output "/path/to/transcripts" \
  --glob "C0*.MP4" \
  --language ko \
  --context "한국어 인터뷰입니다. 서비스 이름은 부카(Booka)입니다."
```

Repeat `--glob` to select multiple patterns. Only files directly inside the
input directory are selected.

### Model selection

The CLI deliberately does not guess from installed RAM. The tested 4-bit
model is faster and lighter with nearly identical transcript quality, so it
is the default.

```bash
--model 4bit                                  # default
--model 8bit                                  # optional larger model
--model mlx-community/another-vibevoice-model # Hugging Face repository
--model /path/to/local/model                   # local model directory
```

## Output

```text
output/
├── audio/                    # mono 24 kHz FLAC
├── raw/                      # untouched VibeVoice JSON
├── draft/                    # timestamped speaker-labelled text
├── logs/transcription.json
└── channel-analysis.json
```

Reviewed text belongs in `final/`; substantive corrections should be recorded
in `correction-log.json`. The skill instructs the agent to preserve raw and
draft output for auditability.

## Development

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests
uv run --locked pi-vibevoice-transcribe --self-check
```

The test suite does not download the model. Full ASR is intentionally an
opt-in local smoke test because the model is several gigabytes.

## Privacy

Transcription runs locally. Setup contacts Hugging Face to download model and
tokenizer files. Publishing transcripts is never automatic and requires an
explicit request to the agent.

## License

The project code and skill instructions are MIT licensed. Downloaded models
and dependencies retain their upstream licenses; see
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

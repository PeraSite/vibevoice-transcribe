<div align="center">

# vibevoice-transcribe

**Local, speaker-aware transcription for AI agents on Apple Silicon.**

[![Agent Skill](https://img.shields.io/badge/Agent-Skill-6E56CF)](https://agentskills.io/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![macOS](https://img.shields.io/badge/macOS-Apple%20Silicon-000000?logo=apple)](https://support.apple.com/en-us/116943)
[![Tests](https://github.com/PeraSite/vibevoice-transcribe/actions/workflows/test.yml/badge.svg)](https://github.com/PeraSite/vibevoice-transcribe/actions/workflows/test.yml)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Install](#install) · [Use with an agent](#use-with-an-agent) · [CLI](#cli) · [Output](#output)

</div>

A standard [Agent Skill](https://agentskills.io/) that transcribes audio and
video locally with [VibeVoice ASR](https://huggingface.co/mlx-community/VibeVoice-ASR-4bit)
and MLX. It handles batches, speaker labels, timestamps, mono conversion, and
silent-channel detection while keeping raw output available for auditing.

> [!NOTE]
> Transcription runs locally. The network is only needed to install dependencies
> and download the model once.

## What it does

| Capability | Behavior |
| --- | --- |
| Batch selection | Processes explicit, repeatable top-level globs |
| Channel safety | Detects effectively silent left or right channels before downmixing |
| Audio preparation | Creates mono 24 kHz FLAC without changing source media |
| Efficient inference | Loads the pinned 4-bit model once per batch |
| Speaker-aware output | Produces timestamped `Speaker N` and `Event` lines |
| Resumability | Skips completed audio and raw transcript files |
| Auditability | Keeps converted audio, raw JSON, readable drafts, and logs separately |

## Requirements

- macOS on Apple Silicon
- [uv](https://docs.astral.sh/uv/)
- [FFmpeg](https://ffmpeg.org/) (`brew install ffmpeg`)
- About 10 GB of free disk space

## Install

```bash
git clone https://github.com/PeraSite/vibevoice-transcribe \
  ~/PythonProjects/vibevoice-transcribe
cd ~/PythonProjects/vibevoice-transcribe
uv sync --locked
uv run --locked vibevoice-transcribe --download-model
```

The pinned `mlx-community/VibeVoice-ASR-4bit` model is downloaded outside the
repository to:

```text
~/.cache/vibevoice-transcribe/
```

Use another disk by setting `VIBEVOICE_HOME`:

```bash
VIBEVOICE_HOME=/Volumes/FastSSD/vibevoice-cache \
  uv run --locked vibevoice-transcribe --download-model
```

## Use with an agent

Expose the repository through the shared Agent Skills directory:

```bash
mkdir -p ~/.agents/skills
ln -s ~/PythonProjects/vibevoice-transcribe \
  ~/.agents/skills/vibevoice-transcribe
```

Pi discovers `~/.agents/skills/`; run `/reload` after installation. If another
agent uses its own skills directory, symlink the same repository there.

Then ask the agent naturally or invoke the skill directly:

```text
/skill:vibevoice-transcribe "Transcribe *.mp4 files in /path/to/media"
```

The skill gathers the input directory, globs, output directory, and optional
vocabulary context before running the CLI. It also verifies output completeness
and leaves source files unchanged.

## CLI

```bash
uv run --locked vibevoice-transcribe \
  --input "/path/to/media" \
  --output "/path/to/output" \
  --glob "*.mp4" \
  --context "Optional names, vocabulary, or domain information"
```

- Repeat `--glob` to select additional patterns.
- Only files directly inside `--input` are selected.
- `--context` is optional.
- Use `--force` only when existing output should be replaced.

```text
usage: vibevoice-transcribe [-h] [--input INPUT] [--output OUTPUT]
                            [--glob PATTERN] [--context CONTEXT]
                            [--download-model] [--force] [--self-check]
```

## Output

```text
output/
├── audio/                    # mono 24 kHz FLAC
├── raw/                      # untouched VibeVoice JSON
├── draft/                    # timestamped, speaker-labelled text
├── logs/
│   └── transcription.json
└── channel-analysis.json
```

Drafts are intentionally simple and diff-friendly:

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

The automated tests do not download the multi-gigabyte model. Full ASR remains
an opt-in local smoke test.

## Privacy

Media and transcripts stay local. Setup contacts Hugging Face to download the
model and tokenizer. Nothing uploads or publishes output automatically.

## License

Project code and skill instructions are available under the [MIT License](LICENSE).
Downloaded models and dependencies retain their upstream licenses; see
[Third-party notices](THIRD_PARTY_NOTICES.md).

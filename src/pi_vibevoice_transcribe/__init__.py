import argparse
import gc
import json
import os
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path
from shutil import which

DEFAULT_MODEL = "mlx-community/VibeVoice-ASR-4bit"
MODEL_ALIASES = {
    "4bit": DEFAULT_MODEL,
    "8bit": "mlx-community/VibeVoice-ASR-8bit",
}
MODEL_REVISIONS = {
    DEFAULT_MODEL: "a1a15cb6c7b70f76b588af7e12f6fab34d5ab654",
    MODEL_ALIASES["8bit"]: "725c72e54d6ef875472c27fbc50fab470a960940",
}
QWEN_TOKENIZER = "Qwen/Qwen2.5-7B"
QWEN_REVISION = "d149729398750b98c0af14eb82c78cfe92750796"
TOKENIZER_FILES = ("tokenizer_config.json", "tokenizer.json", "vocab.json", "merges.txt")
EVENTS = {
    "Environmental Sounds": "환경음",
    "Unintelligible Speech": "알아들을 수 없는 말",
    "Human Sounds": "사람 소리",
    "Silence": "침묵",
    "Music": "음악",
    "Cough": "기침",
    "Laughter": "웃음",
    "Applause": "박수",
}


def cache_home() -> Path:
    if value := os.environ.get("VIBEVOICE_HOME"):
        return Path(value).expanduser().resolve()
    root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return (root / "pi-vibevoice-transcribe").resolve()


def configure_huggingface(cache: Path) -> None:
    home = cache / "huggingface"
    os.environ["HF_HOME"] = str(home)
    os.environ["HF_HUB_CACHE"] = str(home / "hub")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def probe_channels(media: Path) -> int:
    result = run([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=channels", "-of", "json", str(media),
    ])
    streams = json.loads(result.stdout).get("streams", [])
    if not streams:
        raise ValueError(f"No audio stream: {media}")
    return int(streams[0]["channels"])


def mean_volume(media: Path, channel: int) -> float:
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(media),
        "-map", "0:a:0", "-vn", "-af",
        f"pan=mono|c0=c{channel},volumedetect", "-f", "null", "-",
    ], text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    match = re.search(r"mean_volume:\s*(-?inf|-?\d+(?:\.\d+)?) dB", result.stderr)
    if not match:
        raise ValueError(f"ffmpeg did not report mean volume: {media}")
    return -999.0 if match.group(1) == "-inf" else float(match.group(1))


def choose_mix(left: float, right: float) -> str:
    loud, quiet = max(left, right), min(left, right)
    if quiet <= -55 and loud - quiet >= 20:
        return "left" if left > right else "right"
    return "stereo"


def convert(media: Path, target: Path) -> dict:
    channels = probe_channels(media)
    analysis = {"file": media.name, "channels": channels}
    if channels == 2:
        left, right = mean_volume(media, 0), mean_volume(media, 1)
        mix = choose_mix(left, right)
        analysis.update(left_mean_db=left, right_mean_db=right, mix=mix)
        filters = {
            "left": "pan=mono|c0=c0",
            "right": "pan=mono|c0=c1",
            "stereo": "pan=mono|c0=0.5*c0+0.5*c1",
        }
        audio_filter = ["-af", filters[mix]]
    else:
        analysis["mix"] = "mono" if channels == 1 else "ffmpeg-downmix"
        audio_filter = []
    target.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(media),
        "-map", "0:a:0", "-vn", *audio_filter, "-ac", "1", "-ar", "24000",
        "-c:a", "flac", str(target),
    ])
    return analysis


def timestamp(seconds: float) -> str:
    value = max(0, int(float(seconds)))
    return f"{value // 3600:02d}:{value % 3600 // 60:02d}:{value % 60:02d}"


def localize_events(text: str) -> str:
    return re.sub(r"\[([^]]+)]", lambda match: f"[{EVENTS.get(match.group(1), match.group(1))}]", text)


def render_draft(raw_path: Path, draft_path: Path) -> None:
    segments = json.loads(raw_path.read_text())["segments"]
    lines = []
    for segment in segments:
        text = localize_events(segment["text"].strip())
        who = f"화자 {int(segment['speaker_id']) + 1}" if "speaker_id" in segment else "비언어음"
        lines.append(f"[{timestamp(segment['start'])}] [{who}] {text}")
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text("\n".join(lines) + "\n")


def model_is_complete(model: Path, repo: str, revision: str | None) -> bool:
    try:
        marker = json.loads((model / ".complete.json").read_text())
        index = json.loads((model / "model.safetensors.index.json").read_text())
        weights = {model / name for name in index["weight_map"].values()}
        tokenizer = [model / name for name in TOKENIZER_FILES]
        return (
            marker == {"repo": repo, "revision": revision}
            and bool(weights)
            and all(path.is_file() and path.stat().st_size for path in (*weights, *tokenizer))
        )
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return False


def download_model(repo: str, revision: str | None, cache: Path) -> Path:
    from huggingface_hub import snapshot_download

    model = cache / "models" / repo.replace("/", "--")
    if model_is_complete(model, repo, revision):
        return model
    model.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=repo, revision=revision, local_dir=model)
    snapshot_download(
        repo_id=QWEN_TOKENIZER,
        revision=QWEN_REVISION,
        local_dir=model,
        allow_patterns=list(TOKENIZER_FILES),
    )
    (model / ".complete.json").write_text(
        json.dumps({"repo": repo, "revision": revision}, indent=2) + "\n"
    )
    if not model_is_complete(model, repo, revision):
        raise RuntimeError(f"Downloaded model is incomplete: {model}")
    for partial in model.rglob("*.incomplete"):
        partial.unlink()
    return model


def resolve_model(spec: str, cache: Path) -> Path:
    candidate = Path(spec).expanduser()
    if candidate.exists():
        if not candidate.is_dir():
            raise ValueError(f"Model path is not a directory: {candidate}")
        return candidate.resolve()
    repo = MODEL_ALIASES.get(spec, spec)
    if "/" not in repo:
        raise ValueError(f"Unknown model alias or path: {spec}")
    revision = MODEL_REVISIONS.get(repo)
    return download_model(repo, revision, cache)


def select_media(source: Path, patterns: list[str]) -> list[Path]:
    files = sorted({path for pattern in patterns for path in source.glob(pattern) if path.is_file()})
    stems = [path.stem for path in files]
    if len(stems) != len(set(stems)):
        raise ValueError("Selected files contain duplicate stems and would overwrite each other")
    return files


def self_check() -> None:
    assert choose_mix(-21.2, -75.7) == "left"
    assert choose_mix(-75.7, -21.2) == "right"
    assert choose_mix(-30, -38) == "stereo"
    assert timestamp(3661.9) == "01:01:01"
    assert localize_events("[Cough][Unintelligible Speech]") == "[기침][알아들을 수 없는 말]"
    print("self-check passed")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch transcription with VibeVoice ASR on Apple Silicon")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--glob", action="append", dest="patterns")
    parser.add_argument("--language", default="ko")
    parser.add_argument("--context", default="")
    parser.add_argument("--model", default="4bit", help="4bit, 8bit, a Hugging Face repo, or a local path")
    parser.add_argument("--download-model", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.self_check:
        self_check()
        return

    cache = cache_home()
    configure_huggingface(cache)
    if args.download_model:
        print(resolve_model(args.model, cache))
        return
    if not args.input or not args.output or not args.patterns:
        raise SystemExit("--input, --output, and at least one --glob are required")
    if sys.platform != "darwin" or os.uname().machine != "arm64":
        raise SystemExit("MLX requires macOS on Apple Silicon")
    for command in ("ffmpeg", "ffprobe"):
        if not which(command):
            raise SystemExit(f"{command} is required")

    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"Input directory not found: {source}")
    media_files = select_media(source, args.patterns)
    if not media_files:
        raise SystemExit(f"No top-level files matched {args.patterns!r} in {source}")
    model_path = resolve_model(args.model, cache)
    for name in ("audio", "raw", "draft", "logs"):
        output.joinpath(name).mkdir(parents=True, exist_ok=True)

    analysis_path = output / "channel-analysis.json"
    previous_analysis = {}
    if analysis_path.exists() and not args.force:
        previous_analysis = {item["file"]: item for item in json.loads(analysis_path.read_text())}
    analysis = []
    for index, media in enumerate(media_files, 1):
        audio = output / "audio" / f"{media.stem}.flac"
        if audio.exists() and not args.force:
            record = previous_analysis.get(media.name, {"file": media.name, "mix": "existing-audio"})
        else:
            print(f"[{index:02d}/{len(media_files)}] converting {media.name}", flush=True)
            record = convert(media, audio)
        analysis.append(record)
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n")

    pending = [
        media for media in media_files
        if args.force or not output.joinpath("raw", f"{media.stem}.json").exists()
    ]
    model = None
    if pending:
        from mlx_audio.stt.generate import generate_transcription
        from mlx_audio.stt.utils import load_model
        model = load_model(model_path)

    log_path = output / "logs" / "transcription.json"
    entries = {} if args.force or not log_path.exists() else {
        item["file"]: item for item in json.loads(log_path.read_text())
    }
    failures = 0
    for index, media in enumerate(media_files, 1):
        audio = output / "audio" / f"{media.stem}.flac"
        raw_base = output / "raw" / media.stem
        raw_path = raw_base.with_suffix(".json")
        if raw_path.exists() and not args.force:
            print(f"[{index:02d}/{len(media_files)}] {media.name}: already done", flush=True)
        else:
            started = time.monotonic()
            try:
                result = generate_transcription(
                    model=model,
                    audio=str(audio),
                    output_path=str(raw_base),
                    format="json",
                    verbose=False,
                    max_tokens=8192,
                    language=args.language,
                    context=args.context,
                )
                entries[media.name] = {
                    "file": media.name,
                    "status": "ok",
                    "seconds": round(time.monotonic() - started, 2),
                    "segments": len(result.segments or []),
                }
                print(f"[{index:02d}/{len(media_files)}] {media.name}: done", flush=True)
            except Exception as exc:
                failures += 1
                entries[media.name] = {
                    "file": media.name,
                    "status": "error",
                    "error": repr(exc),
                    "traceback": traceback.format_exc(),
                }
                print(f"[{index:02d}/{len(media_files)}] {media.name}: ERROR {exc!r}", file=sys.stderr)
            log_path.write_text(json.dumps(list(entries.values()), ensure_ascii=False, indent=2) + "\n")
            gc.collect()
            try:
                import mlx.core as mx
                mx.clear_cache()
            except ImportError:
                pass
        if raw_path.exists():
            render_draft(raw_path, output / "draft" / f"{media.stem}.txt")
    if failures:
        raise SystemExit(f"{failures} transcription(s) failed; see {log_path}")




if __name__ == "__main__":
    main()

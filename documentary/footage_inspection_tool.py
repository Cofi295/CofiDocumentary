from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Iterable
import warnings


def _existing_files(paths: Iterable[str | Path]) -> list[Path]:
    resolved: list[Path] = []
    for value in paths:
        path = Path(value).resolve()
        if path.exists() and path.is_file():
            resolved.append(path)
    return resolved


def detect_scene_ranges(
    media_path: str | Path,
    *,
    threshold: float = 27.0,
    limit: int = 24,
    detector: Callable[[Path, float], list[tuple[Any, Any]]] | None = None,
) -> list[dict[str, Any]]:
    path = Path(media_path).resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    if detector is None:
        from scenedetect import ContentDetector, detect

        def detector(video_path: Path, detector_threshold: float):
            return detect(
                str(video_path),
                ContentDetector(threshold=float(detector_threshold)),
                start_in_scene=True,
            )

    def seconds(value: Any) -> float:
        direct = getattr(value, "seconds", None)
        return float(direct if direct is not None else value.get_seconds())

    rows: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(detector(path, float(threshold)), start=1):
        start_sec = round(seconds(start), 3)
        end_sec = round(seconds(end), 3)
        rows.append({
            "index": index,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "duration_sec": round(max(0.0, end_sec - start_sec), 3),
        })
        if len(rows) >= max(1, int(limit)):
            break
    return rows


def _default_image_hasher(path: Path) -> str:
    import imagehash
    from PIL import Image

    with Image.open(path) as image:
        return str(imagehash.phash(image.convert("RGB")))


def _hash_distance(left: str, right: str) -> int:
    width = max(len(left), len(right))
    return (int(left.zfill(width), 16) ^ int(right.zfill(width), 16)).bit_count()


def find_near_duplicate_images(
    image_paths: Iterable[str | Path],
    *,
    max_distance: int = 6,
    hasher: Callable[[Path], str] | None = None,
) -> dict[str, Any]:
    hasher = hasher or _default_image_hasher
    unique: list[tuple[Path, str]] = []
    duplicates: list[dict[str, Any]] = []
    for path in _existing_files(image_paths):
        current_hash = str(hasher(path))
        matched = None
        for kept_path, kept_hash in unique:
            distance = _hash_distance(current_hash, kept_hash)
            if distance <= max(0, int(max_distance)):
                matched = (kept_path, distance)
                break
        if matched is None:
            unique.append((path, current_hash))
        else:
            duplicates.append({
                "path": str(path),
                "duplicate_of": str(matched[0]),
                "distance": matched[1],
            })
    return {
        "unique": [str(path) for path, _ in unique],
        "duplicates": duplicates,
    }


def _subprocess_runner(command: list[str], cwd: Path):
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
    return subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
        startupinfo=startupinfo,
    )


def gallery_download(
    url: str,
    output_dir: str | Path,
    *,
    limit: int = 3,
    runner: Callable[[list[str], Path], Any] | None = None,
) -> dict[str, Any]:
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    before = {path.resolve() for path in destination.rglob("*") if path.is_file()}
    command = [
        sys.executable,
        "-m",
        "gallery_dl",
        "--quiet",
        "--range",
        f"1-{max(1, int(limit))}",
        str(url),
    ]
    result = (runner or _subprocess_runner)(command, destination)
    after = {path.resolve() for path in destination.rglob("*") if path.is_file()}
    files = sorted(str(path) for path in after - before)
    return {
        "returncode": int(getattr(result, "returncode", 1)),
        "files": files[:max(1, int(limit))],
        "error": str(getattr(result, "stderr", "") or "")[-500:],
    }


def _default_whisper_model_factory(model_name: str, device: str, compute_type: str):
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    logging.getLogger("huggingface_hub.utils._http").setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", message=".*unauthenticated requests to the HF Hub.*")
    from faster_whisper import WhisperModel

    return WhisperModel(model_name, device=device, compute_type=compute_type)


def transcribe_clip(
    media_path: str | Path,
    *,
    language: str | None = None,
    max_segments: int = 80,
    model_factory: Callable[[str, str, str], Any] | None = None,
) -> dict[str, Any]:
    path = Path(media_path).resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    model_name = str(os.getenv("COFI_FASTER_WHISPER_MODEL", "base") or "base").strip()
    device = str(os.getenv("COFI_FASTER_WHISPER_DEVICE", "cpu") or "cpu").strip()
    compute_type = str(os.getenv("COFI_FASTER_WHISPER_COMPUTE_TYPE", "int8") or "int8").strip()
    model = (model_factory or _default_whisper_model_factory)(model_name, device, compute_type)
    segments, info = model.transcribe(
        str(path),
        language=(language or None),
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    compact: list[dict[str, Any]] = []
    for segment in segments:
        text = " ".join(str(getattr(segment, "text", "") or "").split())
        if not text:
            continue
        compact.append({
            "start_sec": round(float(getattr(segment, "start", 0.0) or 0.0), 2),
            "end_sec": round(float(getattr(segment, "end", 0.0) or 0.0), 2),
            "text": text[:320],
        })
        if len(compact) >= max(1, int(max_segments)):
            break
    return {
        "model": model_name,
        "device": device,
        "compute_type": compute_type,
        "language": str(getattr(info, "language", "") or ""),
        "language_probability": round(float(getattr(info, "language_probability", 0.0) or 0.0), 4),
        "segments": compact,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="On-demand footage inspection helpers for Codex/Gemini.")
    sub = parser.add_subparsers(dest="command", required=True)

    scenes = sub.add_parser("scenes", help="Detect scene/shot boundaries with PySceneDetect.")
    scenes.add_argument("--input", required=True)
    scenes.add_argument("--threshold", type=float, default=27.0)
    scenes.add_argument("--limit", type=int, default=24)

    dedupe = sub.add_parser("dedupe", help="Remove near-duplicate frames with perceptual ImageHash.")
    dedupe.add_argument("--image", action="append", required=True)
    dedupe.add_argument("--max-distance", type=int, default=6)

    gallery = sub.add_parser("gallery", help="Download media from gallery-dl supported URLs.")
    gallery.add_argument("--url", required=True)
    gallery.add_argument("--output-dir", required=True)
    gallery.add_argument("--limit", type=int, default=3)

    transcribe = sub.add_parser("transcribe", help="Transcribe an inspection clip with faster-whisper.")
    transcribe.add_argument("--input", required=True)
    transcribe.add_argument("--language", default="")
    transcribe.add_argument("--max-segments", type=int, default=80)

    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "scenes":
        payload: Any = {"scenes": detect_scene_ranges(args.input, threshold=args.threshold, limit=args.limit)}
    elif args.command == "dedupe":
        payload = find_near_duplicate_images(args.image, max_distance=args.max_distance)
    elif args.command == "gallery":
        payload = gallery_download(args.url, args.output_dir, limit=args.limit)
    elif args.command == "transcribe":
        payload = transcribe_clip(
            args.input,
            language=(args.language or None),
            max_segments=args.max_segments,
        )
    else:
        raise RuntimeError(f"Unsupported command: {args.command}")
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from documentary.footage_inspection_tool import (
    detect_scene_ranges,
    find_near_duplicate_images,
    gallery_download,
    transcribe_clip,
)


class _Timecode:
    def __init__(self, seconds: float):
        self._seconds = seconds

    def get_seconds(self) -> float:
        return self._seconds


def test_detect_scene_ranges_returns_compact_timestamps(tmp_path: Path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    rows = detect_scene_ranges(
        video,
        limit=2,
        detector=lambda _path, _threshold: [
            (_Timecode(0.0), _Timecode(4.25)),
            (_Timecode(4.25), _Timecode(9.75)),
            (_Timecode(9.75), _Timecode(14.0)),
        ],
    )
    assert rows == [
        {"index": 1, "start_sec": 0.0, "end_sec": 4.25, "duration_sec": 4.25},
        {"index": 2, "start_sec": 4.25, "end_sec": 9.75, "duration_sec": 5.5},
    ]


def test_find_near_duplicate_images_groups_similar_hashes(tmp_path: Path):
    paths = [tmp_path / name for name in ("a.jpg", "b.jpg", "c.jpg")]
    for path in paths:
        path.write_bytes(b"image")
    hashes = {
        "a.jpg": "0000000000000000",
        "b.jpg": "0000000000000001",
        "c.jpg": "ffffffffffffffff",
    }
    result = find_near_duplicate_images(
        paths,
        max_distance=2,
        hasher=lambda path: hashes[path.name],
    )
    assert result["unique"] == [str(paths[0]), str(paths[2])]
    assert result["duplicates"] == [{
        "path": str(paths[1]),
        "duplicate_of": str(paths[0]),
        "distance": 1,
    }]


def test_gallery_download_limits_files_and_reports_new_paths(tmp_path: Path):
    output = tmp_path / "gallery"

    def fake_runner(command: list[str], cwd: Path):
        assert "gallery_dl" in command
        assert "1-2" in command
        target = cwd / "site"
        target.mkdir(parents=True)
        (target / "one.jpg").write_bytes(b"1")
        (target / "two.jpg").write_bytes(b"2")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = gallery_download(
        "https://example.test/gallery/1",
        output,
        limit=2,
        runner=fake_runner,
    )
    assert result["returncode"] == 0
    assert len(result["files"]) == 2
    assert all(Path(path).exists() for path in result["files"])


def test_transcribe_clip_uses_light_default_model_and_compact_segments(tmp_path: Path, monkeypatch):
    media = tmp_path / "candidate.mp4"
    media.write_bytes(b"video")
    captured = {}

    class FakeModel:
        def transcribe(self, path: str, **kwargs):
            captured["path"] = path
            captured["kwargs"] = kwargs
            return (
                iter([
                    SimpleNamespace(start=1.0, end=3.2, text=" Treaty of Versailles "),
                    SimpleNamespace(start=3.2, end=5.0, text=" President Wilson "),
                ]),
                SimpleNamespace(language="en", language_probability=0.98),
            )

    def factory(model_name: str, device: str, compute_type: str):
        captured["model"] = (model_name, device, compute_type)
        return FakeModel()

    monkeypatch.delenv("COFI_FASTER_WHISPER_MODEL", raising=False)
    result = transcribe_clip(media, model_factory=factory)
    assert captured["model"] == ("base", "cpu", "int8")
    assert captured["kwargs"]["beam_size"] == 1
    assert result["language"] == "en"
    assert result["segments"][0]["text"] == "Treaty of Versailles"

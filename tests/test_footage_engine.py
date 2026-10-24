import json
from pathlib import Path
import threading
import time

from documentary.footage_engine import FootageEngine, MediaRetriever, best_transcript_window, parse_webvtt


def test_footage_engine_materializes_candidates_in_bounded_parallel(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COFI_FOOTAGE_DOWNLOAD_WORKERS", "3")
    lock = threading.Lock()
    active = 0
    peak = 0

    class Discovery:
        last_diagnostics = {}

        def discover_for_beats(self, job, beats, workspace):
            return {
                "B001": [
                    {"provider": "test", "source_url": f"https://source.test/{index}", "title": str(index), "kind": "video"}
                    for index in range(3)
                ]
            }

    class Retriever:
        def prepare(self, candidate, beat, workspace, job):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            try:
                time.sleep(0.05)
                return {
                    "local_path": str(tmp_path / f"{candidate['title']}.mp4"),
                    "frames": [],
                    "transcript": candidate["title"],
                    "timestamp_range": "00:00:00-00:00:08",
                    "metadata": {"title": candidate["title"]},
                }
            finally:
                with lock:
                    active -= 1

    engine = FootageEngine(
        source_discovery=Discovery(),
        retriever=Retriever(),
        max_candidates_per_provider=3,
    )
    payload = engine.prepare(
        {"id": "job-parallel"},
        [{"beat_id": "B001", "narration_text": "parallel", "visual_description": "parallel"}],
        tmp_path,
    )

    assert peak == 3
    assert [row["source_url"] for row in payload["candidates"]] == [
        "https://source.test/0",
        "https://source.test/1",
        "https://source.test/2",
    ]


def test_media_retriever_duration_uses_ffprobe_output(tmp_path: Path, monkeypatch):
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"clip")

    class Result:
        returncode = 0
        stdout = "12.75\n"
        stderr = ""

    seen = []
    def fake_runner(command, **kwargs):
        seen.append((command, kwargs.get("timeout")))
        return Result()

    retriever = MediaRetriever(runner=fake_runner, library_root=tmp_path / "library")
    monkeypatch.setattr("documentary.footage_engine._tool", lambda name: "ffprobe.exe" if name == "ffprobe.exe" else None)

    assert retriever._duration(clip) == 12.75
    assert seen[0][0][-1] == str(clip)


def test_media_retriever_does_not_full_download_archive_after_section_failure(tmp_path: Path, monkeypatch):
    class Result:
        returncode = 1
        stdout = ""
        stderr = "section download failed"

    seen = []

    def fake_runner(command, **kwargs):
        seen.append(list(command))
        return Result()

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "files": [
                    {"name": "master.mov", "format": "QuickTime", "source": "original", "size": "9000000000"},
                    {"name": "derivative.mp4", "format": "h.264", "source": "derivative", "size": "120000000"},
                ]
            }

    class Client:
        def get(self, *args, **kwargs):
            return Response()

    retriever = MediaRetriever(runner=fake_runner, library_root=tmp_path / "library", client=Client())
    monkeypatch.setattr(
        "documentary.footage_engine._tool",
        lambda name: name if name in {"yt-dlp.exe", "ffmpeg.exe"} else None,
    )

    root = tmp_path / "cache"
    root.mkdir()
    try:
        retriever._download_window(
            "https://archive.org/details/large-historical-reel",
            root,
            0.0,
            8.0,
        )
    except RuntimeError as exc:
        assert "section" in str(exc).lower()
    else:
        raise AssertionError("Archive candidate should fail fast after bounded section download fails")

    assert len(seen) == 1
    assert "source_full.%(ext)s" not in " ".join(seen[0])
    assert seen[0][-1].endswith("/derivative.mp4")


def test_media_retriever_archive_prefers_small_mp4_derivative(tmp_path: Path):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "files": [
                    {"name": "giant master.mov", "format": "QuickTime", "source": "original", "size": "12000000000"},
                    {"name": "small video.mp4", "format": "MPEG4", "source": "derivative", "size": "90000000"},
                    {"name": "medium.webm", "format": "WebM", "source": "derivative", "size": "60000000"},
                ]
            }

    class Client:
        def get(self, url, **kwargs):
            assert url.endswith("/historical-reel")
            return Response()

    retriever = MediaRetriever(library_root=tmp_path / "library", client=Client())

    resolved = retriever._archive_derivative_url("https://archive.org/details/historical-reel")

    assert resolved == "https://archive.org/download/historical-reel/small%20video.mp4"


def test_footage_engine_limits_materialization_before_download_without_local_vision(tmp_path: Path):
    calls = []

    class Discovery:
        last_diagnostics = {}

        def discover_for_beats(self, job, beats, workspace):
            rows = []
            for index in range(20):
                rows.append({
                    "provider": f"p{index % 4}",
                    "source_url": f"https://source.test/{index}",
                    "title": str(index),
                    "kind": "video",
                    "semantic_score": 1.0 - index / 100,
                })
            return {"B001": rows}

    class Retriever:
        def prepare(self, candidate, beat, workspace, job):
            calls.append(candidate["source_url"])
            return {
                "local_path": str(tmp_path / f"{len(calls)}.mp4"),
                "frames": [],
                "transcript": candidate["title"],
                "timestamp_range": "00:00:00-00:00:08",
                "metadata": {"title": candidate["title"]},
            }

    engine = FootageEngine(source_discovery=Discovery(), retriever=Retriever(), vision_provider=None)
    payload = engine.prepare(
        {"id": "job-bounded"},
        [{"beat_id": "B001", "narration_text": "bounded", "visual_description": "bounded"}],
        tmp_path,
    )

    assert len(calls) == 4
    assert len(payload["candidates"]) == 4


def test_media_retriever_retries_youtube_with_bounded_embedded_section_without_full_download(tmp_path: Path, monkeypatch):
    class Result:
        returncode = 1
        stdout = ""
        stderr = "failed"

    seen = []

    def fake_runner(command, **kwargs):
        seen.append(list(command))
        return Result()

    retriever = MediaRetriever(runner=fake_runner, library_root=tmp_path / "library")
    monkeypatch.setattr(
        "documentary.footage_engine._tool",
        lambda name: name if name in {"yt-dlp.exe", "ffmpeg.exe"} else None,
    )

    root = tmp_path / "cache"
    root.mkdir()
    try:
        retriever._download_window("https://www.youtube.com/watch?v=abc123", root, 0.0, 8.0)
    except RuntimeError:
        pass

    assert len(seen) == 2
    second = " ".join(seen[1])
    assert "youtube:player_client=web_embedded" in second
    assert "--download-sections" in second
    assert "source_full.%(ext)s" not in second


def test_webvtt_window_prefers_segment_matching_voice_and_visual_context():
    cues = parse_webvtt(
        """WEBVTT

00:00:01.000 --> 00:00:05.000
Generic opening titles

00:01:10.000 --> 00:01:16.000
SK hynix is building the Yongin semiconductor cluster.

00:02:20.000 --> 00:02:25.000
Cars drive through central Seoul.
"""
    )

    window = best_transcript_window(
        cues,
        voice_text="SK hynix expands semiconductor production in Yongin.",
        visual_description="SK hynix Yongin semiconductor construction site",
        target_duration_sec=10,
    )

    assert 68 <= window["start_sec"] <= 72
    assert window["end_sec"] >= 76
    assert "yongin" in window["text"].lower()


def test_media_retriever_uses_shared_source_cache_and_separate_timestamp_windows(tmp_path: Path):
    retriever = MediaRetriever(library_root=tmp_path / "footage_library")
    source_a = retriever._cache_dir(tmp_path / "job-a", "https://source.test/video")
    source_b = retriever._cache_dir(tmp_path / "job-b", "https://source.test/video")
    first = retriever._window_dir(source_a, 10.0, 20.0)
    second = retriever._window_dir(source_a, 40.0, 50.0)

    assert source_a == source_b
    assert tmp_path / "footage_library" in source_a.parents
    assert first != second


def test_footage_engine_prepares_local_vision_verified_candidate_for_ai_review(tmp_path: Path):
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"frame")
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"clip")

    class Discovery:
        last_diagnostics = {"fake": {"status": "ok", "count": 1}}

        def discover_for_beats(self, job, beats, workspace):
            return {
                "B001": [{
                    "provider": "yt_dlp",
                    "source_url": "https://www.youtube.com/watch?v=abc",
                    "title": "SK hynix Yongin construction",
                    "kind": "video",
                    "discovery_score": 42,
                }]
            }

    class Retriever:
        def prepare(self, candidate, beat, workspace, job):
            return {
                "local_path": str(clip),
                "frames": [str(frame)],
                "transcript": "SK hynix Yongin semiconductor cluster construction",
                "timestamp_range": "00:01:10-00:01:20",
                "metadata": {"title": candidate["title"]},
            }

    class Vision:
        name = "local-vision-test"

        def verify(self, *, voice_text, frames, transcript, metadata, contract):
            assert contract.required_fields["visual_context"] == "SK hynix Yongin semiconductor construction site"
            return {
                "semantic_score": 0.94,
                "fields": {
                    "visual_context": {
                        "status": "CONFIRMED",
                        "evidence": "factory construction and SK hynix signage",
                    },
                },
                "forbidden_detected": [],
                "summary": "Correct facility context.",
            }

    engine = FootageEngine(
        source_discovery=Discovery(),
        retriever=Retriever(),
        vision_provider=Vision(),
        max_candidates_per_beat=2,
    )
    payload = engine.prepare(
        {"id": "job-1", "title": "Semiconductors", "language": "ko"},
        [{
            "beat_id": "B001",
            "source_priority": "must_real",
            "visual_type": "sourced_video",
            "narration_text": "SK hynix is expanding in Yongin.",
            "visual_description": "SK hynix Yongin semiconductor construction site",
            "target_duration_sec": 10,
        }],
        tmp_path,
    )

    assert payload["status"] == "completed"
    assert payload["candidates"][0]["decision"] == "REVIEW"
    assert payload["candidates"][0]["local_vision_decision"] == "ACCEPT"
    assert payload["candidates"][0]["visually_inspected_actual_content"] is True
    assert payload["candidates"][0]["timestamp_range"] == "00:01:10-00:01:20"
    queue = json.loads((tmp_path / "footage_candidate_queue.json").read_text(encoding="utf-8"))
    assert queue["beats"][0]["beat_id"] == "B001"
    assert queue["beats"][0]["candidates"][0]["verification_provider"] == "local-vision-test"


def test_footage_engine_skips_local_vision_rejected_candidate_and_tries_next(tmp_path: Path):
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"frame")
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"clip")

    class Discovery:
        last_diagnostics = {}

        def discover_for_beats(self, job, beats, workspace):
            return {
                "B001": [
                    {"source_url": "https://source.test/wrong", "title": "wrong", "kind": "video"},
                    {"source_url": "https://source.test/right", "title": "right", "kind": "video"},
                ]
            }

    class Retriever:
        def prepare(self, candidate, beat, workspace, job):
            return {
                "local_path": str(clip),
                "frames": [str(frame)],
                "transcript": candidate["title"],
                "timestamp_range": "00:00:00-00:00:10",
                "metadata": {"title": candidate["title"]},
            }

    class Vision:
        name = "local-vision-test"

        def verify(self, *, voice_text, frames, transcript, metadata, contract):
            if metadata["title"] == "wrong":
                return {
                    "semantic_score": 0.99,
                    "fields": {"visual_context": {"status": "CONTRADICTED", "evidence": "wrong factory"}},
                    "forbidden_detected": [],
                }
            return {
                "semantic_score": 0.92,
                "fields": {"visual_context": {"status": "CONFIRMED", "evidence": "correct factory"}},
                "forbidden_detected": [],
            }

    engine = FootageEngine(
        source_discovery=Discovery(),
        retriever=Retriever(),
        vision_provider=Vision(),
        max_candidates_per_beat=2,
    )
    payload = engine.prepare(
        {"id": "job-1"},
        [{
            "beat_id": "B001",
            "source_priority": "prefer_real",
            "narration_text": "correct factory",
            "visual_description": "correct factory",
            "target_duration_sec": 8,
        }],
        tmp_path,
    )

    assert len(payload["candidates"]) == 1
    assert payload["candidates"][0]["source_url"].endswith("/right")


def test_footage_engine_keeps_multiple_local_vision_candidates_for_ai_fallback(tmp_path: Path):
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"frame")
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"clip")

    class Discovery:
        last_diagnostics = {}

        def discover_for_beats(self, job, beats, workspace):
            return {
                "B001": [
                    {"source_url": "https://source.test/one", "title": "one", "kind": "video"},
                    {"source_url": "https://source.test/two", "title": "two", "kind": "video"},
                    {"source_url": "https://source.test/three", "title": "three", "kind": "video"},
                ]
            }

    class Retriever:
        def prepare(self, candidate, beat, workspace, job):
            return {
                "local_path": str(clip),
                "frames": [str(frame)],
                "transcript": candidate["title"],
                "timestamp_range": "00:00:00-00:00:08",
                "metadata": {"title": candidate["title"]},
            }

    class Vision:
        name = "local-vision-test"

        def verify(self, *, voice_text, frames, transcript, metadata, contract):
            return {
                "semantic_score": 0.93,
                "fields": {"visual_context": {"status": "CONFIRMED", "evidence": metadata["title"]}},
                "forbidden_detected": [],
            }

    engine = FootageEngine(
        source_discovery=Discovery(),
        retriever=Retriever(),
        vision_provider=Vision(),
        max_candidates_per_beat=3,
    )
    payload = engine.prepare(
        {"id": "job-1"},
        [{
            "beat_id": "B001",
            "source_priority": "prefer_real",
            "narration_text": "factory",
            "visual_description": "factory",
            "target_duration_sec": 8,
        }],
        tmp_path,
    )

    assert [item["source_url"] for item in payload["candidates"]] == [
        "https://source.test/one",
        "https://source.test/two",
        "https://source.test/three",
    ]


def test_footage_engine_does_not_retry_an_unavailable_source_for_every_beat(tmp_path: Path):
    class Discovery:
        last_diagnostics = {}

        def discover_for_beats(self, job, beats, workspace):
            source = {"source_url": "https://archive.test/broken", "kind": "video"}
            return {beat["beat_id"]: [source] for beat in beats}

    class Retriever:
        calls = 0

        def prepare(self, candidate, beat, workspace, job):
            self.calls += 1
            raise RuntimeError("source has no video formats")

    retriever = Retriever()
    engine = FootageEngine(
        source_discovery=Discovery(),
        retriever=retriever,
        max_candidates_per_beat=1,
    )
    beats = [
        {"beat_id": "B001", "narration_text": "one"},
        {"beat_id": "B002", "narration_text": "two"},
    ]

    payload = engine.prepare({"id": "job-1"}, beats, tmp_path)

    assert retriever.calls == 1
    assert len(payload["failures"]) == 2
    assert payload["failures"][1]["cached"] is True


def test_footage_engine_without_local_vision_materializes_semantic_shortlist_for_ai_review(tmp_path: Path):
    clip = tmp_path / "clip.mp4"
    frame = tmp_path / "frame.jpg"
    clip.write_bytes(b"clip")
    frame.write_bytes(b"frame")

    class SemanticReranker:
        def health(self):
            return {"ok": True, "provider": "openclip"}

    class Discovery:
        semantic_reranker = SemanticReranker()
        last_diagnostics = {}

        def discover_for_beats(self, job, beats, workspace):
            return {
                "B001": [
                    {
                        "provider": "alpha",
                        "source_url": "https://example.test/one",
                        "title": "right visual",
                        "kind": "video",
                        "semantic_score": 0.91,
                        "semantic_provider": "openclip",
                    },
                    {
                        "provider": "alpha",
                        "source_url": "https://example.test/two",
                        "title": "second visual",
                        "kind": "video",
                        "semantic_score": 0.86,
                        "semantic_provider": "openclip",
                    },
                ]
            }

    class Retriever:
        def prepare(self, candidate, beat, workspace, job):
            return {
                "local_path": str(clip),
                "frames": [str(frame)],
                "transcript": candidate["title"],
                "transcript_score": 0.7,
                "timestamp_range": "00:00:00-00:00:08",
                "metadata": {"title": candidate["title"]},
            }

    engine = FootageEngine(
        source_discovery=Discovery(),
        retriever=Retriever(),
        max_candidates_per_provider=2,
    )
    payload = engine.prepare(
        {"id": "job-1"},
        [{"beat_id": "B001", "narration_text": "matching narration"}],
        tmp_path,
    )

    assert len(payload["candidates"]) == 2
    assert all(item["verification_provider"] == "openclip" for item in payload["candidates"])
    assert all(item["decision"] == "REVIEW" for item in payload["candidates"])
    assert all("local_vision_decision" not in item for item in payload["candidates"])
    assert engine.health()["ok"] is True

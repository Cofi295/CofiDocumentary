from __future__ import annotations

import json
from pathlib import Path

import pytest

from documentary.ai_visual import AI_VISUAL_GENERATION_PROFILE, AIVisualCoordinator, CofiFlowToolRunner, _write_json


class FakeFlowRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, scene, request_path):
        self.calls.append(dict(scene))
        output_dir = Path(scene["_output_directory"])
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = ".mp4" if scene["task_type"] == "image_to_video" else ".jpg"
        output = output_dir / f"{scene['_output_stem']}{suffix}"
        output.write_bytes(b"generated-media")
        return str(output)


def test_write_json_retries_transient_windows_replace_denial(tmp_path: Path, monkeypatch):
    destination = tmp_path / 'ai_visual_manifest.json'
    original_replace = Path.replace
    calls = 0

    def flaky_replace(self, target):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PermissionError(5, 'Access is denied')
        return original_replace(self, target)

    monkeypatch.setattr(Path, 'replace', flaky_replace)

    _write_json(destination, {'status': 'running'})

    assert json.loads(destination.read_text(encoding='utf-8')) == {'status': 'running'}
    assert calls == 2


class InterruptAfterFirstImageRunner(FakeFlowRunner):
    def __call__(self, scene, request_path):
        if scene["id"] == "B002_ai_image":
            raise KeyboardInterrupt("simulated process interruption")
        return super().__call__(scene, request_path)


class VideoFailRunner(FakeFlowRunner):
    def __call__(self, scene, request_path):
        if scene["task_type"] == "image_to_video":
            self.calls.append(dict(scene))
            raise RuntimeError("Veo provider unavailable")
        return super().__call__(scene, request_path)


def test_media_factory_runner_defaults_to_documentary_embed_port(tmp_path: Path, monkeypatch):
    monkeypatch.delenv('COFI_STUDIO_API', raising=False)
    monkeypatch.delenv('COFI_STUDIO_EMBED_PORT', raising=False)

    runner = CofiFlowToolRunner(studio_root=tmp_path / 'CofiStudio')

    assert runner.studio_api == 'http://127.0.0.1:8894'


def test_media_factory_runner_creates_visible_scene_runs_queue_job_and_polls_output(tmp_path: Path, monkeypatch):
    studio_root = tmp_path / 'CofiStudio'
    (studio_root / 'backend').mkdir(parents=True)
    runner = CofiFlowToolRunner(studio_root=studio_root)
    output = tmp_path / 'generated.jpg'
    output.write_bytes(b'generated')
    calls = []

    def fake_request(method, path, payload=None, *, timeout=30):
        calls.append((method, path, payload))
        if method == 'GET' and path == '/api/scenes':
            return []
        if method == 'POST' and path == '/api/scenes':
            assert payload['name'] == 'AI bổ sung · B001'
            assert payload['task_type'] == 'image_generation'
            return {'id': 'scene-1', 'name': payload['name']}
        if method == 'POST' and path == '/api/scenes/scene-1/run':
            return {'id': 'job-1', 'status': 'queued'}
        if method == 'GET' and path == '/api/jobs':
            return [{'id': 'job-1', 'status': 'completed', 'output_path': str(output)}]
        raise AssertionError(f'unexpected Media Factory request: {method} {path}')

    monkeypatch.setattr(runner, '_request_json', fake_request)

    result = runner(
        {
            'id': 'B001_ai_image',
            'name': 'AI bổ sung · B001',
            'task_type': 'image_generation',
            'prompt': 'Documentary still',
            'model': 'nano_banana_2',
            'aspect_ratio': '16:9',
        },
        tmp_path / 'request.json',
    )

    assert result == str(output)
    assert ('POST', '/api/scenes/scene-1/run', None) in calls
    assert any(method == 'GET' and path == '/api/jobs' for method, path, _ in calls)
    assert all('/api/providers/' not in path for _, path, _ in calls)


def test_media_factory_runner_starts_embedded_factory_before_submitting(tmp_path: Path, monkeypatch):
    started = []
    runner = CofiFlowToolRunner(
        studio_root=tmp_path / 'CofiStudio',
        studio_api='http://127.0.0.1:8896',
        ensure_available=lambda: started.append('started'),
    )
    output = tmp_path / 'generated.jpg'
    output.write_bytes(b'generated')

    def fake_request(method, path, payload=None, *, timeout=30):
        assert started == ['started']
        if method == 'GET' and path == '/api/scenes':
            return []
        if method == 'POST' and path == '/api/scenes':
            return {'id': 'scene-1', 'name': payload['name']}
        if method == 'POST' and path == '/api/scenes/scene-1/run':
            return {'id': 'job-1', 'status': 'queued'}
        if method == 'GET' and path == '/api/jobs':
            return [{'id': 'job-1', 'status': 'completed', 'output_path': str(output)}]
        raise AssertionError(f'unexpected Media Factory request: {method} {path}')

    monkeypatch.setattr(runner, '_request_json', fake_request)
    result = runner(
        {
            'id': 'B001_ai_image',
            'name': 'AI bổ sung · B001',
            'task_type': 'image_generation',
            'prompt': 'Documentary still',
        },
        tmp_path / 'request.json',
    )

    assert result == str(output)
    assert started == ['started']


def test_media_factory_runner_reuses_latest_matching_failed_scene_on_retry(tmp_path: Path, monkeypatch):
    studio_root = tmp_path / 'CofiStudio'
    (studio_root / 'backend').mkdir(parents=True)
    runner = CofiFlowToolRunner(studio_root=studio_root)
    calls = []

    existing_scenes = [
        {
            'id': 'scene-old',
            'name': 'AI chuyển động · B001-V01',
            'task_type': 'image_to_video',
            'status': 'failed',
            'created_at': '2026-09-20T22:25:20+07:00',
        },
        {
            'id': 'scene-latest',
            'name': 'AI chuyển động · B001-V01',
            'task_type': 'image_to_video',
            'status': 'failed',
            'created_at': '2026-09-20T23:36:15+07:00',
        },
    ]

    def fake_request(method, path, payload=None, *, timeout=30):
        calls.append((method, path, payload))
        if method == 'GET' and path == '/api/scenes':
            return existing_scenes
        if method == 'PATCH' and path == '/api/scenes/scene-latest':
            return {'id': 'scene-latest', 'name': payload['name'], 'status': 'failed'}
        if method == 'POST' and path == '/api/scenes/scene-latest/run':
            return {'id': 'job-retry', 'scene_id': 'scene-latest', 'status': 'queued'}
        if method == 'POST' and path == '/api/scenes':
            raise AssertionError('retry must reuse the latest matching scene instead of creating a duplicate')
        raise AssertionError(f'unexpected Media Factory request: {method} {path}')

    monkeypatch.setattr(runner, '_request_json', fake_request)

    request_path = tmp_path / 'request.json'
    request_path.write_text(
        json.dumps({'scene_id': 'scene-latest', 'job_id': 'job-failed', 'status': 'failed'}),
        encoding='utf-8',
    )

    ticket = runner.submit(
        {
            'id': 'B001-V01_ai_video',
            'name': 'AI chuyển động · B001-V01',
            'task_type': 'image_to_video',
            'prompt': 'Animate the documentary keyframe',
            'model': 'veo_31_lite_relaxed',
            'aspect_ratio': '16:9',
            'duration_seconds': 8,
            'reference_image': str(tmp_path / 'keyframe.jpg'),
            'reference_images': [str(tmp_path / 'keyframe.jpg')],
        },
        request_path,
    )

    assert ticket['scene_id'] == 'scene-latest'
    assert ticket['job_id'] == 'job-retry'
    assert any(method == 'PATCH' and path == '/api/scenes/scene-latest' for method, path, _ in calls)
    assert not any(method == 'POST' and path == '/api/scenes' for method, path, _ in calls)


def test_media_factory_runner_does_not_timeout_while_job_is_queued(tmp_path: Path, monkeypatch):
    runner = CofiFlowToolRunner(studio_root=tmp_path / 'CofiStudio')
    runner.timeout_seconds = 1
    runner.queue_timeout_seconds = 0
    runner.poll_interval = 0.01
    output = tmp_path / 'generated.jpg'
    output.write_bytes(b'generated')
    states = iter([
        [{'id': 'job-1', 'status': 'queued', 'progress': 0}],
        [{'id': 'job-1', 'status': 'queued', 'progress': 0}],
        [{'id': 'job-1', 'status': 'completed', 'progress': 100, 'output_path': str(output)}],
    ])
    clock = iter([0.0, 10.0, 20.0, 30.0])

    monkeypatch.setattr(runner, '_request_json', lambda *args, **kwargs: next(states))
    monkeypatch.setattr('documentary.ai_visual.time.monotonic', lambda: next(clock))
    monkeypatch.setattr('documentary.ai_visual.time.sleep', lambda _seconds: None)

    result = runner.wait({'job_id': 'job-1', 'status': 'queued'})

    assert result == str(output)


def test_media_factory_runner_wait_retries_temporary_connection_error(tmp_path: Path, monkeypatch):
    runner = CofiFlowToolRunner(studio_root=tmp_path / 'CofiStudio')
    runner.poll_interval = 0.01
    runner.connection_timeout_seconds = 1
    output = tmp_path / 'generated.jpg'
    output.write_bytes(b'generated')
    states = iter([
        RuntimeError('Không kết nối được Media Factory tại http://127.0.0.1:8896: connection refused'),
        {'id': 'job-1', 'status': 'completed', 'progress': 100, 'output_path': str(output)},
    ])

    def inspect(_ticket):
        state = next(states)
        if isinstance(state, Exception):
            raise state
        return state

    monkeypatch.setattr(runner, 'inspect', inspect)
    monkeypatch.setattr('documentary.ai_visual.time.sleep', lambda _seconds: None)

    result = runner.wait({'job_id': 'job-1', 'status': 'running'})

    assert result == str(output)


def test_media_factory_runner_follows_auto_retry_for_same_scene(tmp_path: Path, monkeypatch):
    runner = CofiFlowToolRunner(studio_root=tmp_path / 'CofiStudio')
    jobs = [
        {
            'id': 'job-old',
            'scene_id': 'scene-1',
            'status': 'failed',
            'created_at': '2026-09-09T06:00:00+07:00',
            'error': 'temporary provider error',
        },
        {
            'id': 'job-retry',
            'scene_id': 'scene-1',
            'status': 'running',
            'created_at': '2026-09-09T06:00:20+07:00',
        },
    ]
    monkeypatch.setattr(runner, '_request_json', lambda *args, **kwargs: jobs)
    ticket = {'scene_id': 'scene-1', 'job_id': 'job-old', 'status': 'queued'}

    live = runner.inspect(ticket)

    assert live['id'] == 'job-retry'
    assert ticket['job_id'] == 'job-retry'
    assert ticket['status'] == 'running'


def test_media_factory_runner_spaces_prompt_submissions_with_random_delay(tmp_path: Path):
    now = [100.0]
    sleeps = []
    scene_index = [0]

    def fake_sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    runner = CofiFlowToolRunner(
        studio_root=tmp_path / 'CofiStudio',
        submission_delay_min_seconds=10,
        submission_delay_max_seconds=15,
        submission_jitter=lambda minimum, maximum: 12.0,
        submission_sleep=fake_sleep,
        submission_monotonic=lambda: now[0],
    )

    def fake_request(method, path, payload=None, *, timeout=30):
        if method == 'GET' and path == '/api/scenes':
            return []
        if method == 'POST' and path == '/api/scenes':
            scene_index[0] += 1
            return {'id': f'scene-{scene_index[0]}', 'name': payload['name']}
        if method == 'POST' and path.startswith('/api/scenes/') and path.endswith('/run'):
            return {'id': f'job-{scene_index[0]}', 'status': 'queued'}
        raise AssertionError(f'unexpected Media Factory request: {method} {path}')

    runner._request_json = fake_request
    scene = {
        'id': 'B001_ai_image',
        'name': 'AI bổ sung',
        'task_type': 'image_generation',
        'prompt': 'documentary prompt',
        'model': 'nano_banana_2',
        'aspect_ratio': '16:9',
    }

    runner.submit(scene, tmp_path / 'one.json')
    now[0] += 2
    runner.submit({**scene, 'id': 'B002_ai_image'}, tmp_path / 'two.json')

    assert sleeps == [10.0]


class FakeQueueRunner:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.events = []
        self.scenes = {}

    def submit(self, scene, request_path):
        scene = dict(scene)
        scene_id = f"scene-{scene['id']}"
        job_id = f"job-{scene['id']}"
        self.events.append(('submit', scene['id']))
        self.scenes[job_id] = scene
        if scene['task_type'] == 'image_to_video':
            manifest = json.loads((self.workspace / 'ai_visual_manifest.json').read_text(encoding='utf-8'))
            beat_id = scene['id'].removesuffix('_ai_video')
            generated = next(item for item in manifest['generated'] if item['beat_id'] == beat_id)
            assert generated['image_path']
        return {'scene_id': scene_id, 'job_id': job_id, 'name': scene.get('name', ''), 'status': 'queued'}

    def wait(self, ticket):
        job_id = ticket['job_id']
        scene = self.scenes[job_id]
        self.events.append(('wait', scene['id']))
        output_dir = self.workspace / 'media' / 'ai'
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = '.mp4' if scene['task_type'] == 'image_to_video' else '.jpg'
        output = output_dir / f"{scene['_output_stem']}{suffix}"
        output.write_bytes(b'generated-media')
        return str(output)


class WindowTrackingQueueRunner(FakeQueueRunner):
    def __init__(self, workspace: Path):
        super().__init__(workspace)
        self.outstanding = 0
        self.max_outstanding = 0

    def submit(self, scene, request_path):
        ticket = super().submit(scene, request_path)
        self.outstanding += 1
        self.max_outstanding = max(self.max_outstanding, self.outstanding)
        return ticket

    def wait(self, ticket):
        output = super().wait(ticket)
        self.outstanding -= 1
        return output


class PreparedQueueRunner(WindowTrackingQueueRunner):
    def __init__(self, workspace: Path):
        super().__init__(workspace)
        self.prepared = {}

    def prepare_scene(self, scene, request_path):
        scene = dict(scene)
        scene_id = f"scene-{scene['id']}"
        self.events.append(('prepare', scene['id']))
        self.prepared[scene_id] = scene
        return {'scene_id': scene_id, 'job_id': '', 'name': scene.get('name', ''), 'status': 'prepared'}

    def run_prepared(self, scene, request_path, ticket=None):
        scene = dict(scene)
        scene_id = str((ticket or {}).get('scene_id') or f"scene-{scene['id']}")
        job_id = f"job-{scene['id']}"
        self.events.append(('submit', scene['id']))
        self.scenes[job_id] = scene
        if scene['task_type'] == 'image_to_video':
            manifest = json.loads((self.workspace / 'ai_visual_manifest.json').read_text(encoding='utf-8'))
            beat_id = scene['id'].removesuffix('_ai_video')
            generated = next(item for item in manifest['generated'] if item['beat_id'] == beat_id)
            assert generated['image_path']
        self.outstanding += 1
        self.max_outstanding = max(self.max_outstanding, self.outstanding)
        return {'scene_id': scene_id, 'job_id': job_id, 'name': scene.get('name', ''), 'status': 'queued'}


class FailingPreparedQueueRunner(PreparedQueueRunner):
    def prepare_scene(self, scene, request_path):
        if scene['id'] == 'B003_ai_image':
            self.events.append(('prepare-failed', scene['id']))
            raise RuntimeError('temporary card creation failure')
        return super().prepare_scene(scene, request_path)


class ExternalOutputQueueRunner(FakeQueueRunner):
    def __init__(self, workspace: Path):
        super().__init__(workspace)
        self.external_dir = workspace / 'media-factory-output'

    def wait(self, ticket):
        job_id = ticket['job_id']
        scene = self.scenes[job_id]
        self.events.append(('wait', scene['id']))
        self.external_dir.mkdir(parents=True, exist_ok=True)
        suffix = '.mp4' if scene['task_type'] == 'image_to_video' else '.jpg'
        output = self.external_dir / f'generic-output{suffix}'
        output.write_bytes(scene['id'].encode('utf-8'))
        return str(output)


class RecoverCompletedQueueRunner(FakeQueueRunner):
    def __init__(self, workspace: Path, output: Path):
        super().__init__(workspace)
        self.output = output

    def inspect(self, ticket):
        self.events.append(('inspect', ticket['job_id']))
        ticket['status'] = 'completed'
        ticket['output_path'] = str(self.output)
        return {'id': ticket['job_id'], 'status': 'completed', 'output_path': str(self.output)}

    def wait(self, ticket):
        self.events.append(('wait-existing', ticket['job_id']))
        return str(self.output)


class MissingQueuedJobRunner(FakeQueueRunner):
    def inspect(self, ticket):
        self.events.append(('inspect', ticket['job_id']))
        return None


class TransientInspectQueueRunner(RecoverCompletedQueueRunner):
    def inspect(self, ticket):
        self.events.append(('inspect-offline', ticket['job_id']))
        raise RuntimeError('Không kết nối được Media Factory tại http://127.0.0.1:8896: connection refused')


class ExistingFactoryOrderRunner:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.events = []
        self.created_at = {
            'job-late': '2026-09-09T06:10:00+07:00',
            'job-early': '2026-09-09T06:00:00+07:00',
        }

    def submit(self, *_args, **_kwargs):
        raise AssertionError('existing Media Factory tickets must be reused')

    def inspect(self, ticket):
        job_id = ticket['job_id']
        ticket['status'] = 'queued'
        ticket['created_at'] = self.created_at[job_id]
        return {
            'id': job_id,
            'scene_id': ticket['scene_id'],
            'status': 'queued',
            'created_at': self.created_at[job_id],
        }

    def wait(self, ticket):
        job_id = ticket['job_id']
        self.events.append(('wait', job_id))
        output = self.workspace / 'factory' / f'{job_id}.jpg'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(job_id.encode('utf-8'))
        return str(output)


def write_workspace(
    workspace: Path,
    beats: list[dict],
    assets: list[dict] | None = None,
    native=None,
    ai_fallback_beats: list[str] | None = None,
):
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "visual_manifest.json").write_text(json.dumps({"beats": beats}), encoding="utf-8")
    (workspace / "asset_registry.json").write_text(json.dumps({
        "assets": assets or [],
        "native_treatments": native or [],
        "presentation_effects": [],
        "beat_coverage": {},
        "ai_fallback_beats": ai_fallback_beats or [],
        "ai_usage_notes": [
            {
                "beat_id": beat_id,
                "requires_ai": True,
                "reason": "Verified real video and real stills were unavailable or unusable.",
                "visual_language": {},
            }
            for beat_id in (ai_fallback_beats or [])
        ],
    }), encoding="utf-8")


def test_ai_visual_rejects_unnoted_uncovered_beats_including_legacy_native_motion(tmp_path: Path):
    existing = tmp_path / "media" / "real.mp4"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"real-footage")
    write_workspace(tmp_path, [
        {"beat_id": "B001", "visual_type": "sourced_video", "narration_text": "covered"},
        {"beat_id": "B002", "visual_type": "native_motion", "narration_text": "map"},
        {"beat_id": "B003", "visual_type": "sourced_video", "narration_text": "missing"},
    ], assets=[{"id": "real1", "beat_id": "B001", "kind": "sourced_video", "path": str(existing)}], native=[
        {"id": "N2", "beat_id": "B002", "kind": "remotion_native_motion", "description": "timeline"},
    ])
    runner = FakeFlowRunner()
    coordinator = AIVisualCoordinator(tool_runner=runner)

    with pytest.raises(RuntimeError, match="Footage must explicitly note"):
        coordinator.run({}, tmp_path)
    assert runner.calls == []


def test_ai_visual_publishes_keyframe_then_prioritizes_its_video(tmp_path: Path):
    write_workspace(tmp_path, [
        {"beat_id": "B001", "visual_type": "sourced_video", "narration_text": "October 1919 White House meeting", "ai_motion_required": True},
        {"beat_id": "B002", "visual_type": "sourced_video", "narration_text": "March 1921 Washington transition", "ai_motion_required": True},
    ], ai_fallback_beats=["B001", "B002"])
    runner = FakeQueueRunner(tmp_path)

    result = AIVisualCoordinator(tool_runner=runner).run({"ai_visual": {"veo_enabled": True}}, tmp_path)

    assert result.returncode == 0
    assert runner.events[:2] == [('submit', 'B001_ai_image'), ('submit', 'B002_ai_image')]
    assert runner.events.index(('wait', 'B001_ai_image')) < runner.events.index(('submit', 'B001_ai_video'))
    assert runner.events.index(('submit', 'B001_ai_video')) < runner.events.index(('wait', 'B001_ai_video'))
    assert ('submit', 'B002_ai_video') in runner.events
    assert ('wait', 'B002_ai_video') in runner.events
    manifest = json.loads((tmp_path / 'ai_visual_manifest.json').read_text(encoding='utf-8'))
    assert {item['beat_id'] for item in manifest['generated']} == {'B001', 'B002'}
    assert all(item['video_path'] for item in manifest['generated'])


def test_ai_visual_caps_media_factory_outstanding_jobs_at_ten(tmp_path: Path):
    beats = [
        {
            "beat_id": f"B{index:03d}",
            "visual_type": "sourced_still",
            "narration_text": f"beat {index}",
        }
        for index in range(1, 13)
    ]
    write_workspace(tmp_path, beats, ai_fallback_beats=[beat["beat_id"] for beat in beats])
    runner = WindowTrackingQueueRunner(tmp_path)

    result = AIVisualCoordinator(tool_runner=runner).run({}, tmp_path)

    assert result.returncode == 0
    assert runner.max_outstanding == 10
    eleventh_submit = runner.events.index(('submit', 'B011_ai_image'))
    first_wait = next(index for index, event in enumerate(runner.events) if event[0] == 'wait')
    assert first_wait < eleventh_submit


def test_ai_visual_video_mode_finishes_all_keyframes_before_starting_video(tmp_path: Path):
    beats = [
        {
            "beat_id": f"B{index:03d}",
            "visual_type": "sourced_video",
            "narration_text": f"beat {index}",
            "ai_motion_required": True,
        }
        for index in range(1, 13)
    ]
    write_workspace(tmp_path, beats, ai_fallback_beats=[beat["beat_id"] for beat in beats])
    runner = WindowTrackingQueueRunner(tmp_path)

    result = AIVisualCoordinator(tool_runner=runner).run(
        {"ai_visual": {"veo_enabled": True, "ai_media_mode": "video"}},
        tmp_path,
    )

    assert result.returncode == 0
    assert runner.max_outstanding == 10
    first_video_submit = runner.events.index(("submit", "B001_ai_video"))
    last_image_wait = max(
        index
        for index, event in enumerate(runner.events)
        if event[0] == "wait" and event[1].endswith("_ai_image")
    )
    assert last_image_wait < first_video_submit


def test_ai_visual_prepares_all_image_cards_then_all_video_cards_in_two_phases(tmp_path: Path):
    beats = [
        {
            "beat_id": f"B{index:03d}",
            "visual_type": "sourced_video",
            "narration_text": f"beat {index}",
            "ai_motion_required": True,
        }
        for index in range(1, 5)
    ]
    write_workspace(tmp_path, beats, ai_fallback_beats=[beat["beat_id"] for beat in beats])
    runner = PreparedQueueRunner(tmp_path)

    result = AIVisualCoordinator(tool_runner=runner).run(
        {"ai_visual": {"veo_enabled": True, "ai_media_mode": "video"}},
        tmp_path,
    )

    assert result.returncode == 0
    image_prepares = [i for i, event in enumerate(runner.events) if event[0] == 'prepare' and event[1].endswith('_ai_image')]
    image_submits = [i for i, event in enumerate(runner.events) if event[0] == 'submit' and event[1].endswith('_ai_image')]
    image_waits = [i for i, event in enumerate(runner.events) if event[0] == 'wait' and event[1].endswith('_ai_image')]
    video_prepares = [i for i, event in enumerate(runner.events) if event[0] == 'prepare' and event[1].endswith('_ai_video')]
    video_submits = [i for i, event in enumerate(runner.events) if event[0] == 'submit' and event[1].endswith('_ai_video')]

    assert len(image_prepares) == len(beats)
    assert len(video_prepares) == len(beats)
    assert max(image_prepares) < min(image_submits)
    assert max(image_waits) < min(video_prepares)
    assert max(video_prepares) < min(video_submits)


def test_ai_visual_does_not_start_generation_until_every_image_card_is_prepared(tmp_path: Path):
    beats = [
        {
            "beat_id": f"B{index:03d}",
            "visual_type": "sourced_video",
            "narration_text": f"beat {index}",
            "ai_motion_required": True,
        }
        for index in range(1, 5)
    ]
    write_workspace(tmp_path, beats, ai_fallback_beats=[beat["beat_id"] for beat in beats])
    runner = FailingPreparedQueueRunner(tmp_path)

    with pytest.raises(RuntimeError, match="chưa tạo đủ 1 card"):
        AIVisualCoordinator(tool_runner=runner).run(
            {"ai_visual": {"veo_enabled": True, "ai_media_mode": "video"}},
            tmp_path,
        )

    assert ('prepare-failed', 'B003_ai_image') in runner.events
    assert not any(event[0] == 'submit' for event in runner.events)


def test_ai_visual_copies_media_factory_outputs_to_beat_specific_workspace_files(tmp_path: Path):
    write_workspace(tmp_path, [
        {"beat_id": "B001", "visual_type": "sourced_video", "narration_text": "October 1919 White House meeting", "ai_motion_required": True},
        {"beat_id": "B002", "visual_type": "sourced_video", "narration_text": "March 1921 Washington transition", "ai_motion_required": True},
    ], ai_fallback_beats=["B001", "B002"])
    runner = ExternalOutputQueueRunner(tmp_path)

    result = AIVisualCoordinator(tool_runner=runner).run({"ai_visual": {"veo_enabled": True}}, tmp_path)

    assert result.returncode == 0
    manifest = json.loads((tmp_path / 'ai_visual_manifest.json').read_text(encoding='utf-8'))
    generated = {item['beat_id']: item for item in manifest['generated']}
    for beat_id in ('B001', 'B002'):
        image_path = Path(generated[beat_id]['image_path'])
        video_path = Path(generated[beat_id]['video_path'])
        assert image_path == tmp_path / 'media' / 'ai' / f'{beat_id}_ai_keyframe.jpg'
        assert video_path == tmp_path / 'media' / 'ai' / f'{beat_id}_ai_video.mp4'
        assert image_path.read_bytes() == f'{beat_id}_ai_image'.encode('utf-8')
        assert video_path.read_bytes() == f'{beat_id}_ai_video'.encode('utf-8')
    jobs = {(item['beat_id'], item['stage']): item for item in manifest['media_factory_jobs']}
    assert jobs[('B001', 'image')]['media_factory_output_path'].endswith('generic-output.jpg')
    assert jobs[('B001', 'image')]['output_path'].endswith('B001_ai_keyframe.jpg')


def test_ai_visual_recovers_factory_job_that_completed_after_documentary_timeout(tmp_path: Path):
    beats = [{"beat_id": "B001", "visual_type": "sourced_still", "narration_text": "October 1919 White House"}]
    write_workspace(tmp_path, beats, ai_fallback_beats=['B001'])
    external = tmp_path / 'factory' / 'late-output.jpg'
    external.parent.mkdir(parents=True)
    external.write_bytes(b'late-generated')
    coordinator = AIVisualCoordinator(tool_runner=RecoverCompletedQueueRunner(tmp_path, external))
    style = coordinator._build_visual_style({"beats": beats})
    (tmp_path / 'ai_visual_manifest.json').write_text(json.dumps({
        'provider': 'cofistudio_media_factory',
        'generation_profile': AI_VISUAL_GENERATION_PROFILE,
        'visual_style': style,
        'target_beat_ids': ['B001'],
        'generated': [],
        'errors': [{'beat_id': 'B001', 'stage': 'image', 'error': 'timeout'}],
        'media_factory_jobs': [{
            'beat_id': 'B001',
            'stage': 'image',
            'scene_id': 'scene-old',
            'job_id': 'job-old',
            'name': 'AI bổ sung · B001',
            'status': 'failed',
            'error': 'Media Factory job job-old quá thời gian chờ 900s',
        }],
    }), encoding='utf-8')

    result = coordinator.run({}, tmp_path)

    assert result.returncode == 0
    runner = coordinator.tool_runner
    assert ('inspect', 'job-old') in runner.events
    assert ('wait-existing', 'job-old') in runner.events
    assert not any(event[0] == 'submit' for event in runner.events)
    manifest = json.loads((tmp_path / 'ai_visual_manifest.json').read_text(encoding='utf-8'))
    job = next(item for item in manifest['media_factory_jobs'] if item['beat_id'] == 'B001' and item['stage'] == 'image')
    assert job['status'] == 'completed'
    assert job['media_factory_output_path'] == str(external)
    assert Path(job['output_path']).read_bytes() == b'late-generated'


def test_ai_visual_keeps_existing_factory_ticket_during_temporary_outage(tmp_path: Path):
    beats = [{"beat_id": "B001", "visual_type": "sourced_still", "narration_text": "October 1919 White House"}]
    write_workspace(tmp_path, beats, ai_fallback_beats=['B001'])
    external = tmp_path / 'factory' / 'late-output.jpg'
    external.parent.mkdir(parents=True)
    external.write_bytes(b'late-generated')
    runner = TransientInspectQueueRunner(tmp_path, external)
    coordinator = AIVisualCoordinator(tool_runner=runner)
    style = coordinator._build_visual_style({"beats": beats})
    (tmp_path / 'ai_visual_manifest.json').write_text(json.dumps({
        'provider': 'cofistudio_media_factory',
        'generation_profile': AI_VISUAL_GENERATION_PROFILE,
        'visual_style': style,
        'target_beat_ids': ['B001'],
        'generated': [],
        'errors': [{'beat_id': 'B001', 'stage': 'image', 'error': 'temporary outage'}],
        'media_factory_jobs': [{
            'beat_id': 'B001',
            'stage': 'image',
            'scene_id': 'scene-old',
            'job_id': 'job-old',
            'name': 'AI bổ sung · B001',
            'status': 'queued',
        }],
    }), encoding='utf-8')

    result = coordinator.run({}, tmp_path)

    assert result.returncode == 0
    assert ('inspect-offline', 'job-old') in runner.events
    assert ('wait-existing', 'job-old') in runner.events
    assert not any(event[0] == 'submit' for event in runner.events)
    manifest = json.loads((tmp_path / 'ai_visual_manifest.json').read_text(encoding='utf-8'))
    assert manifest['errors'] == []


def test_ai_visual_resubmits_stale_queued_factory_job_missing_from_live_queue(tmp_path: Path):
    beats = [{"beat_id": "B001", "visual_type": "sourced_still", "narration_text": "October 1919 White House"}]
    write_workspace(tmp_path, beats, ai_fallback_beats=['B001'])
    runner = MissingQueuedJobRunner(tmp_path)
    coordinator = AIVisualCoordinator(tool_runner=runner)
    style = coordinator._build_visual_style({"beats": beats})
    (tmp_path / 'ai_visual_manifest.json').write_text(json.dumps({
        'provider': 'cofistudio_media_factory',
        'generation_profile': AI_VISUAL_GENERATION_PROFILE,
        'visual_style': style,
        'target_beat_ids': ['B001'],
        'generated': [],
        'errors': [],
        'media_factory_jobs': [{
            'beat_id': 'B001',
            'stage': 'image',
            'scene_id': 'scene-old',
            'job_id': 'job-old',
            'name': 'AI bổ sung · B001',
            'status': 'queued',
        }],
    }), encoding='utf-8')

    result = coordinator.run({}, tmp_path)

    assert result.returncode == 0
    assert ('inspect', 'job-old') in runner.events
    assert ('submit', 'B001_ai_image') in runner.events
    manifest = json.loads((tmp_path / 'ai_visual_manifest.json').read_text(encoding='utf-8'))
    job = next(item for item in manifest['media_factory_jobs'] if item['beat_id'] == 'B001' and item['stage'] == 'image')
    assert job['status'] == 'completed'
    assert job['job_id'] == 'job-B001_ai_image'


def test_ai_visual_waits_for_existing_factory_jobs_in_queue_creation_order(tmp_path: Path):
    beats = [
        {"beat_id": "B001", "visual_type": "sourced_still", "narration_text": "late retry"},
        {"beat_id": "B002", "visual_type": "sourced_still", "narration_text": "older queued job"},
    ]
    write_workspace(tmp_path, beats, ai_fallback_beats=['B001', 'B002'])
    coordinator = AIVisualCoordinator(tool_runner=ExistingFactoryOrderRunner(tmp_path))
    style = coordinator._build_visual_style({"beats": beats})
    (tmp_path / 'ai_visual_manifest.json').write_text(json.dumps({
        'provider': 'cofistudio_media_factory',
        'generation_profile': AI_VISUAL_GENERATION_PROFILE,
        'visual_style': style,
        'target_beat_ids': ['B001', 'B002'],
        'generated': [],
        'errors': [],
        'media_factory_jobs': [
            {'beat_id': 'B001', 'stage': 'image', 'scene_id': 'scene-late', 'job_id': 'job-late', 'status': 'queued'},
            {'beat_id': 'B002', 'stage': 'image', 'scene_id': 'scene-early', 'job_id': 'job-early', 'status': 'queued'},
        ],
    }), encoding='utf-8')

    result = coordinator.run({}, tmp_path)

    assert result.returncode == 0
    assert coordinator.tool_runner.events == [('wait', 'job-early'), ('wait', 'job-late')]


def test_ai_visual_uses_one_persisted_historical_style_bible_across_beats(tmp_path: Path):
    write_workspace(tmp_path, [
        {
            "beat_id": "B001",
            "visual_type": "sourced_still",
            "narration_text": "On October 2, 1919, the president was in the White House.",
            "visual_description": "A black-and-white archival reference of the corridor.",
        },
        {
            "beat_id": "B002",
            "visual_type": "sourced_still",
            "narration_text": "On March 4, 1921, the administration left Washington.",
            "visual_description": "A restrained historical reconstruction outside the White House.",
        },
    ], ai_fallback_beats=["B001", "B002"])
    runner = FakeFlowRunner()

    result = AIVisualCoordinator(tool_runner=runner).run({}, tmp_path)

    assert result.returncode == 0
    manifest = json.loads((tmp_path / 'ai_visual_manifest.json').read_text(encoding='utf-8'))
    style = manifest['visual_style']
    assert style['period_start'] == 1919
    assert style['period_end'] == 1921
    assert '1919–1921' in style['directive']
    assert 'match the visual language of the nearest verified real footage/stills' in style['directive']
    prompts = [call['prompt'] for call in runner.calls if call['task_type'] == 'image_generation']
    assert len(prompts) == 2
    assert all(style['directive'] in prompt for prompt in prompts)


def test_ai_visual_prioritizes_explicit_footage_fallback_and_skips_already_covered_fallback(tmp_path: Path):
    existing = tmp_path / "media" / "real.mp4"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"real-footage")
    write_workspace(
        tmp_path,
        [
            {"beat_id": "B001", "visual_type": "sourced_video", "narration_text": "covered"},
            {"beat_id": "B003", "visual_type": "sourced_video", "narration_text": "explicit fallback"},
        ],
        assets=[{"id": "real1", "beat_id": "B001", "kind": "sourced_video", "path": str(existing)}],
        ai_fallback_beats=["B003", "B001"],
    )
    runner = FakeFlowRunner()
    coordinator = AIVisualCoordinator(tool_runner=runner)

    result = coordinator.run({}, tmp_path)

    assert result.returncode == 0
    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["target_beat_ids"] == ["B003"]
    assert [call["id"] for call in runner.calls] == ["B003_ai_image"]


def test_ai_visual_drops_stale_previous_target_when_real_footage_now_covers_beat(tmp_path: Path):
    existing = tmp_path / "media" / "real.mp4"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"real-footage")
    beats = [
        {"beat_id": "B001", "visual_type": "sourced_video", "narration_text": "now covered"},
        {"beat_id": "B002", "visual_type": "sourced_video", "narration_text": "still missing"},
    ]
    write_workspace(
        tmp_path,
        beats,
        assets=[{"id": "real1", "beat_id": "B001", "kind": "sourced_video", "path": str(existing)}],
        ai_fallback_beats=["B002"],
    )
    coordinator = AIVisualCoordinator(tool_runner=FakeFlowRunner())
    style = coordinator._build_visual_style({"beats": beats})
    (tmp_path / "ai_visual_manifest.json").write_text(json.dumps({
        "provider": "cofistudio_media_factory",
        "generation_profile": AI_VISUAL_GENERATION_PROFILE,
        "visual_style": style,
        "target_beat_ids": ["B001", "B002"],
        "generated": [],
        "errors": [],
        "media_factory_jobs": [],
    }), encoding="utf-8")

    result = coordinator.run({}, tmp_path)

    assert result.returncode == 0
    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["target_beat_ids"] == ["B002"]
    assert [call["id"] for call in coordinator.tool_runner.calls] == ["B002_ai_image"]


def test_ai_visual_does_not_replace_missing_must_real_subject_with_ai(tmp_path: Path):
    write_workspace(tmp_path, [
        {
            "beat_id": "B001",
            "visual_type": "sourced_video",
            "source_priority": "must_real",
            "narration_text": "The actual president enters the White House.",
        },
    ])
    runner = FakeFlowRunner()
    coordinator = AIVisualCoordinator(tool_runner=runner)

    with pytest.raises(RuntimeError, match="must_real"):
        coordinator.run({}, tmp_path)

    assert runner.calls == []


def test_ai_visual_is_noop_when_real_footage_already_covers_every_beat(tmp_path: Path):
    existing = tmp_path / "media" / "real.jpg"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"real-image")
    write_workspace(
        tmp_path,
        [{"beat_id": "B001", "visual_type": "sourced_still", "narration_text": "covered"}],
        assets=[{"id": "real1", "beat_id": "B001", "kind": "sourced_still", "path": str(existing)}],
    )
    runner = FakeFlowRunner()
    coordinator = AIVisualCoordinator(tool_runner=runner)

    result = coordinator.run({}, tmp_path)

    assert result.returncode == 0
    assert runner.calls == []
    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert manifest["target_beat_ids"] == []


def test_ai_visual_checkpoints_each_generated_beat_and_resumes_after_interruption(tmp_path: Path):
    write_workspace(tmp_path, [
        {"beat_id": "B001", "visual_type": "sourced_still", "narration_text": "first"},
        {"beat_id": "B002", "visual_type": "sourced_still", "narration_text": "second"},
    ], ai_fallback_beats=["B001", "B002"])
    interrupted_runner = InterruptAfterFirstImageRunner()

    with pytest.raises(KeyboardInterrupt, match="simulated process interruption"):
        AIVisualCoordinator(tool_runner=interrupted_runner).run({}, tmp_path)

    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    registry = json.loads((tmp_path / "asset_registry.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "running"
    assert [item["beat_id"] for item in manifest["generated"]] == ["B001"]
    assert manifest["remaining_missing_beats"] == ["B002"]
    assert any(item["beat_id"] == "B001" and item["source"]["generated_by"] == "cofi_ai_visual" for item in registry["assets"])

    resume_runner = FakeFlowRunner()
    result = AIVisualCoordinator(tool_runner=resume_runner).run({}, tmp_path)

    assert result.returncode == 0
    assert [call["id"] for call in resume_runner.calls] == ["B002_ai_image"]
    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert {item["beat_id"] for item in manifest["generated"]} == {"B001", "B002"}
    assert manifest["remaining_missing_beats"] == []


def test_ai_visual_adopts_existing_generated_file_without_regenerating_it(tmp_path: Path):
    write_workspace(
        tmp_path,
        [{"beat_id": "B001", "visual_type": "sourced_still", "narration_text": "existing AI file"}],
        ai_fallback_beats=["B001"],
    )
    media_dir = tmp_path / "media" / "ai"
    media_dir.mkdir(parents=True)
    existing = media_dir / "B001_ai_keyframe.jpg"
    existing.write_bytes(b"already-generated")
    runner = FakeFlowRunner()

    result = AIVisualCoordinator(tool_runner=runner).run({}, tmp_path)

    assert result.returncode == 0
    assert runner.calls == []
    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["generated"][0]["image_path"] == str(existing)
    registry = json.loads((tmp_path / "asset_registry.json").read_text(encoding="utf-8"))
    assert any(item["beat_id"] == "B001" for item in registry["assets"])


def test_ai_visual_regenerates_legacy_provider_assets_with_historical_profile(tmp_path: Path):
    write_workspace(
        tmp_path,
        [{"beat_id": "B001", "visual_type": "sourced_still", "narration_text": "Washington, 1919"}],
        ai_fallback_beats=["B001"],
    )
    media_dir = tmp_path / "media" / "ai"
    media_dir.mkdir(parents=True)
    legacy = media_dir / "B001_ai_keyframe.jpg"
    legacy.write_bytes(b"legacy-image")
    registry_path = tmp_path / "asset_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["assets"] = [{
        "id": "ai_B001_image",
        "beat_id": "B001",
        "kind": "ai_reconstruction_still",
        "path": str(legacy),
        "source": {"generated_by": "cofi_ai_visual", "provider": "google_flow"},
    }]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    (tmp_path / "ai_visual_manifest.json").write_text(json.dumps({
        "status": "running",
        "provider": "google_flow",
        "visual_style": None,
        "target_beat_ids": ["B001"],
        "generated": [{"beat_id": "B001", "image_path": str(legacy)}],
    }), encoding="utf-8")
    runner = FakeFlowRunner()

    result = AIVisualCoordinator(tool_runner=runner).run({}, tmp_path)

    assert result.returncode == 0
    assert [call["id"] for call in runner.calls] == ["B001_ai_image"]
    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["provider"] == "cofistudio_media_factory"
    assert manifest["generation_profile"] == AI_VISUAL_GENERATION_PROFILE
    assert manifest["visual_style"]["period_start"] == 1919
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    ai_asset = next(item for item in registry["assets"] if item["beat_id"] == "B001")
    assert ai_asset["source"]["provider"] == "cofistudio_media_factory"
    assert ai_asset["source"]["generation_profile"] == AI_VISUAL_GENERATION_PROFILE


def test_ai_visual_persists_video_error_and_keeps_generated_image(tmp_path: Path):
    write_workspace(
        tmp_path,
        [{"beat_id": "B001", "visual_type": "sourced_video", "narration_text": "needs motion", "ai_motion_required": True}],
        ai_fallback_beats=["B001"],
    )
    runner = VideoFailRunner()

    result = AIVisualCoordinator(tool_runner=runner).run({"ai_visual": {"veo_enabled": True}}, tmp_path)

    assert result.returncode == 0
    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert manifest["generated"][0]["video_path"] is None
    assert "Veo provider unavailable" in manifest["generated"][0]["video_error"]
    assert manifest["errors"] == [{"beat_id": "B001", "stage": "video", "error": "Veo provider unavailable"}]
    registry = json.loads((tmp_path / "asset_registry.json").read_text(encoding="utf-8"))
    ai_asset = next(item for item in registry["assets"] if item["beat_id"] == "B001")
    assert ai_asset["kind"] == "ai_reconstruction_still"


def test_ai_visual_full_ai_video_mode_allows_image_fallback_when_video_fails(tmp_path: Path):
    write_workspace(
        tmp_path,
        [{"beat_id": "B001", "visual_type": "sourced_video", "narration_text": "needs motion", "ai_motion_required": True}],
    )
    runner = VideoFailRunner()

    result = AIVisualCoordinator(tool_runner=runner).run(
        {"ai_visual": {"veo_enabled": True, "coverage_mode": "full_ai", "ai_media_mode": "video"}},
        tmp_path,
    )

    assert result.returncode == 0
    manifest = json.loads((tmp_path / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert manifest["remaining_missing_beats"] == []
    assert manifest["generated"][0]["video_path"] is None
    assert "Veo provider unavailable" in manifest["generated"][0]["video_error"]
    registry = json.loads((tmp_path / "asset_registry.json").read_text(encoding="utf-8"))
    ai_asset = next(item for item in registry["assets"] if item["beat_id"] == "B001")
    assert ai_asset["kind"] == "ai_reconstruction_still"


def test_media_factory_runner_times_out_on_stuck_queue_by_default(tmp_path: Path, monkeypatch):
    runner = CofiFlowToolRunner(studio_root=tmp_path / 'CofiStudio')
    runner.queue_timeout_seconds = 10
    runner.poll_interval = 0.01
    states = iter([
        [{'id': 'job-stuck', 'status': 'queued', 'progress': 0}],
        [{'id': 'job-stuck', 'status': 'queued', 'progress': 0}],
    ])
    clock = iter([0.0, 5.0, 15.0])

    monkeypatch.setattr(runner, '_request_json', lambda *args, **kwargs: next(states))
    monkeypatch.setattr('documentary.ai_visual.time.monotonic', lambda: next(clock))
    monkeypatch.setattr('documentary.ai_visual.time.sleep', lambda _seconds: None)

    with pytest.raises(RuntimeError, match="chờ hàng đợi quá 10s"):
        runner.wait({'job_id': 'job-stuck', 'status': 'queued'})


def test_media_factory_runner_fails_fast_on_paused_job(tmp_path: Path, monkeypatch):
    runner = CofiFlowToolRunner(studio_root=tmp_path / 'CofiStudio')
    runner.poll_interval = 0.01
    states = iter([
        [{'id': 'job-paused', 'status': 'paused', 'progress': 0}],
    ])

    monkeypatch.setattr(runner, '_request_json', lambda *args, **kwargs: next(states))

    with pytest.raises(RuntimeError, match="đang ở trạng thái tạm dừng"):
        runner.wait({'job_id': 'job-paused', 'status': 'paused'})


def test_ai_visual_coordinator_halts_when_queue_status_is_paused(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "visual_manifest.json").write_text(json.dumps({
        "target_duration_sec": 30,
        "beats": [{"beat_id": "B001", "visual_type": "ai_generated", "narration_text": "text"}],
    }), encoding="utf-8")
    (workspace / "asset_registry.json").write_text(json.dumps({
        "assets": [],
        "ai_fallback_beats": ["B001"],
        "ai_usage_notes": [{"beat_id": "B001", "role": "fallback"}],
    }), encoding="utf-8")

    class PausedQueueRunner:
        def queue_status(self):
            return {"paused": True, "concurrency": 2}

    coordinator = AIVisualCoordinator(tool_runner=PausedQueueRunner())
    job = {
        "id": "job-pause-test",
        "title": "Pause test",
        "workspace": str(workspace),
        "visual_strategy": "full_ai",
        "ai_visual": {"coverage_mode": "full_ai"},
        "ai_media_mode": "image_only",
    }

    with pytest.raises(RuntimeError, match="Media Factory queue đang tạm dừng"):
        coordinator.run(job, workspace)

    manifest = json.loads((workspace / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "paused"
    assert "tạm dừng" in manifest["pause_warning"]


def test_ai_visual_clears_foreign_old_job_scenes_when_starting_new_job(tmp_path: Path):
    workspace = tmp_path / "new-job-ws"
    write_workspace(
        workspace,
        [{"beat_id": "B001-V01", "visual_type": "sourced_still", "narration_text": "new job beat"}],
        ai_fallback_beats=["B001-V01"],
    )

    class ForeignSceneRunner(FakeFlowRunner):
        def __init__(self):
            super().__init__()
            self.cleared = False
            self.live_scenes = [
                {"id": "old-job-scene-1", "name": "AI bổ sung · B001-V01", "status": "completed"},
                {"id": "old-job-scene-2", "name": "AI bổ sung · B002-V01", "status": "completed"},
            ]

        def list_scenes(self):
            return list(self.live_scenes)

        def clear_all_scenes(self):
            self.cleared = True
            self.live_scenes = []
            return {"ok": True}

    runner = ForeignSceneRunner()
    result = AIVisualCoordinator(tool_runner=runner).run({"id": "new-job-id"}, workspace)
    assert result.returncode == 0
    assert runner.cleared is True
    manifest = json.loads((workspace / "ai_visual_manifest.json").read_text(encoding="utf-8"))
    assert manifest["job_id"] == "new-job-id"
    assert manifest["status"] == "completed"


def test_inspect_does_not_treat_failed_scene_stale_output_as_completed(tmp_path: Path):
    stale_out = tmp_path / "stale_prev_job.jpg"
    stale_out.write_bytes(b"old-job-image-bytes")

    runner = CofiFlowToolRunner(studio_root=tmp_path / "CofiStudio")

    def fake_request(method: str, path: str, payload=None, *, timeout: float = 30):
        if path == "/api/jobs":
            return [{"id": "job-new-1", "scene_id": "scene-1", "status": "failed", "error": "Flow HTTP 500"}]
        if path == "/api/scenes":
            return [{"id": "scene-1", "status": "failed", "output_path": str(stale_out)}]
        return []

    runner._request_json = fake_request  # type: ignore[method-assign]
    job = runner.inspect({"job_id": "job-new-1", "scene_id": "scene-1"})
    assert job is not None
    assert job["status"] == "failed"


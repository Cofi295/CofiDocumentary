from pathlib import Path
from types import SimpleNamespace

import pytest

from vendor.media_factory.backend.app.providers.base import ProviderError
from vendor.media_factory.backend.app.providers.google import (
    GoogleFlowBrowserClient,
    GoogleFlowHeadlessClient,
)


def _successful_poll(*, fife_url: str | None = None, media_generation_id: str | None = None) -> dict:
    generated: dict[str, str] = {}
    if fife_url:
        generated['fifeUrl'] = fife_url
    if media_generation_id:
        generated['mediaGenerationId'] = media_generation_id
    return {
        'media': [
            {
                'mediaMetadata': {
                    'mediaStatus': {
                        'mediaGenerationStatus': 'MEDIA_GENERATION_STATUS_SUCCESSFUL',
                    }
                },
                'video': {'generatedVideo': generated},
            }
        ]
    }


def test_successful_poll_prefers_fife_url(tmp_path: Path) -> None:
    client = GoogleFlowBrowserClient(tmp_path, session_worker=None)
    context = SimpleNamespace(pages=[SimpleNamespace(url='https://flow.google.com/project/project-1')])
    expected = tmp_path / 'from-fife.mp4'
    client._access_token = lambda _context: 'token'
    client._browser_post_json = lambda *_args, **_kwargs: _successful_poll(
        fife_url='https://example.invalid/video.mp4',
        media_generation_id='generated-1',
    )
    downloaded: list[str] = []
    client._download_video_url = lambda _context, url, _scene: downloaded.append(url) or expected

    result = client._poll_video_media_once(
        context,
        'submitted-1',
        {'_flow_project_id': 'project-1'},
    )

    assert result == expected
    assert downloaded == ['https://example.invalid/video.mp4']


def test_successful_poll_uses_media_generation_id_for_redirect(tmp_path: Path) -> None:
    client = GoogleFlowBrowserClient(tmp_path, session_worker=None)
    context = SimpleNamespace(pages=[SimpleNamespace(url='https://flow.google.com/project/project-1')])
    expected = tmp_path / 'from-redirect.mp4'
    client._access_token = lambda _context: 'token'
    client._browser_post_json = lambda *_args, **_kwargs: _successful_poll(
        media_generation_id='generated-2'
    )
    downloaded: list[str] = []
    client._download_video_media = (
        lambda _context, media_id, _scene, *, timeout_seconds:
        downloaded.append(f'{media_id}:{timeout_seconds}') or expected
    )

    result = client._poll_video_media_once(
        context,
        'submitted-2',
        {'_flow_project_id': 'project-1'},
    )

    assert result == expected
    assert downloaded == ['generated-2:30']


def test_cancelled_poll_is_terminal(tmp_path: Path) -> None:
    client = GoogleFlowBrowserClient(tmp_path, session_worker=None)
    context = SimpleNamespace(pages=[SimpleNamespace(url='https://flow.google.com/project/project-1')])
    client._access_token = lambda _context: 'token'
    client._browser_post_json = lambda *_args, **_kwargs: {
        'media': [
            {
                'mediaMetadata': {
                    'mediaStatus': {
                        'mediaGenerationStatus': 'MEDIA_GENERATION_STATUS_CANCELLED',
                    }
                }
            }
        ]
    }

    with pytest.raises(ProviderError, match='cancelled'):
        client._poll_video_media_once(
            context,
            'submitted-3',
            {'_flow_project_id': 'project-1'},
        )


def test_migrated_host_video_uses_visible_flow_dom(tmp_path: Path) -> None:
    class Worker:
        def execute_in_session(self, _account_id, callback, **_kwargs):
            context = SimpleNamespace(pages=[SimpleNamespace(url='https://flow.google.com/project/project-1')])
            return callback(context)

    manager = SimpleNamespace(login_worker=Worker())
    client = GoogleFlowHeadlessClient(tmp_path, account_manager=manager)
    reference = tmp_path / 'start.png'
    reference.write_bytes(b'png')
    expected = tmp_path / 'video.mp4'
    expected.write_bytes(b'video')
    calls: list[str] = []
    progress: list[tuple[int, str]] = []
    client._open_project = lambda _page, _account: 'project-1'
    client._generate_video_via_ui = (
        lambda _context, _page, _scene: calls.append('flow-dom-submit') or expected
    )
    client._persist_refreshed_session = lambda *_args, **_kwargs: None
    client._generate_video_migrated_split = lambda *_args, **_kwargs: pytest.fail(
        'migrated UI path must not be used for a migrated host session'
    )

    result = client._generate_video_direct_split(
        {
            'task_type': 'image_to_video',
            'model': 'veo_31_lite_relaxed',
            'reference_image': str(reference),
            'aspect_ratio': '16:9',
            'duration_seconds': 8,
            '_progress_callback': lambda value, stage: progress.append((value, stage)),
        },
        {'id': 'account-1', 'tier': 'ultra'},
        {'migrated_host': True},
    )

    assert result == str(expected)
    assert calls == ['flow-dom-submit']
    assert progress == [(5, 'flow-dom-start'), (100, 'flow-dom-complete')]

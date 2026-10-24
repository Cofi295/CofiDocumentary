from pathlib import Path
from types import SimpleNamespace

from vendor.media_factory.backend.app.providers.google import GoogleFlowHeadlessClient
from vendor.media_factory.backend.app.providers.google_flow_migrated import image_records


def test_image_records_decodes_completed_migrated_image() -> None:
    media_id = "11111111-1111-1111-1111-111111111111"
    workflow_id = "22222222-2222-2222-2222-222222222222"
    project_id = "33333333-3333-3333-3333-333333333333"
    details = [None] * 14
    details[1] = 987654
    details[7] = "documentary establishing shot"
    details[13] = "https://lh3.googleusercontent.com/generated-image"
    payload = [
        [workflow_id, None, None, ["Cofi image"], project_id],
        [media_id, None, workflow_id, None, None, None, [details, None, [1920, 1080]]],
    ]

    records = image_records("ogiZ0b", payload)

    assert len(records) == 1
    assert records[0].media_id == media_id
    assert records[0].workflow_id == workflow_id
    assert records[0].project_id == project_id
    assert records[0].image_url == details[13]
    assert records[0].dimensions == (1920, 1080)
    assert records[0].display_name == "Cofi image"


def test_migrated_host_image_uses_flow_composer_ui(tmp_path: Path) -> None:
    class Worker:
        def execute_in_session(self, _account_id, callback, **_kwargs):
            context = SimpleNamespace(pages=[SimpleNamespace(url="https://flow.google.com/project/project-1")])
            return callback(context)

    manager = SimpleNamespace(login_worker=Worker())
    client = GoogleFlowHeadlessClient(tmp_path, account_manager=manager)
    reference = tmp_path / "style.png"
    reference.write_bytes(b"png")
    expected = tmp_path / "generated.png"
    expected.write_bytes(b"image")
    calls: list[tuple[str, str, list[str]]] = []

    client._open_project = lambda _page, _account: "project-1"
    client._persist_refreshed_session = lambda *_args, **_kwargs: None
    client._start_image_generation_in_context = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("legacy labs.google image transport must not run for a migrated profile")
    )
    client._generate_image_via_ui = (
        lambda _context, _page, scene: calls.append(
            (scene["_flow_project_id"], scene["model"], list(scene["reference_images"]))
        )
        or expected
    )

    result = client._generate_image_direct_split(
        {
            "task_type": "image_generation",
            "model": "nano_banana_2",
            "prompt": "cinematic coast",
            "reference_image": str(reference),
            "aspect_ratio": "16:9",
        },
        {"id": "account-1", "tier": "ultra"},
        {"migrated_host": True},
    )

    assert result == str(expected)
    assert calls == [("project-1", "nano_banana_2", [str(reference)])]

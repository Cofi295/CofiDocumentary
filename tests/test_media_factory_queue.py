from __future__ import annotations

import asyncio

from vendor.media_factory.backend.app.db import Database
from vendor.media_factory.backend.app.providers.base import MediaProvider
from vendor.media_factory.backend.app.queue import QueueSupervisor
from vendor.media_factory.backend.app.schemas import JobStatus, SceneStatus


class _BlockingProvider(MediaProvider):
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def generate(self, scene: dict) -> str:
        self.started.set()
        await self.release.wait()
        return str(scene["_output_directory"] + "/unused.jpg")


def test_concurrency_one_does_not_reserve_entire_queue(tmp_path):
    async def run_case() -> None:
        db = Database(tmp_path / "media_factory.db")
        for index in range(10):
            scene = db.create_scene(
                {
                    "name": f"Scene {index}",
                    "task_type": "image_generation",
                    "prompt": f"Prompt {index}",
                    "negative_prompt": None,
                    "reference_image": None,
                    "reference_images": [],
                    "model": "test-model",
                    "aspect_ratio": "16:9",
                    "duration_seconds": None,
                }
            )
            db.create_job(scene["id"], batch_token="batch")

        provider = _BlockingProvider()
        supervisor = QueueSupervisor(db, provider, concurrency=1)
        await supervisor.start()
        try:
            await asyncio.wait_for(provider.started.wait(), timeout=1)
            await asyncio.sleep(0.05)
            assert supervisor._job_queue.qsize() >= 8
        finally:
            provider.release.set()
            await supervisor.stop()

    asyncio.run(run_case())


def test_enqueue_all_skips_completed_scene_with_existing_output(tmp_path):
    async def run_case() -> None:
        db = Database(tmp_path / "media_factory.db")
        output_path = tmp_path / "done.mp4"
        output_path.write_bytes(b"done")
        scene = db.create_scene(
            {
                "name": "Completed video",
                "task_type": "image_to_video",
                "prompt": "Already rendered",
                "negative_prompt": None,
                "reference_image": None,
                "reference_images": [],
                "model": "test-model",
                "aspect_ratio": "16:9",
                "duration_seconds": 8,
            }
        )
        job = db.create_job(scene["id"], batch_token="done-batch")
        db.update_job(
            job["id"],
            {
                "status": JobStatus.COMPLETED.value,
                "progress": 100,
                "output_path": str(output_path),
            },
        )
        db.set_scene_runtime(
            scene["id"],
            status=SceneStatus.COMPLETED.value,
            progress=100,
            output_path=str(output_path),
        )

        supervisor = QueueSupervisor(db, _BlockingProvider(), concurrency=1)
        enqueued = await supervisor.enqueue_all()

        assert enqueued == []
        assert len(db.list_jobs()) == 1
        refreshed = db.get_scene(scene["id"])
        assert refreshed is not None
        assert refreshed["status"] == SceneStatus.COMPLETED.value
        assert refreshed["output_path"] == str(output_path)

    asyncio.run(run_case())

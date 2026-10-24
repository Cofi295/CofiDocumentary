from __future__ import annotations

from typing import Any

from .base import MediaProvider, ProviderError


class ProviderRegistry(MediaProvider):
    def __init__(self, *, local_provider: MediaProvider, google_provider: MediaProvider):
        self.local_provider = local_provider
        self.google_provider = google_provider

    def resolve(self, scene: dict[str, Any]) -> MediaProvider:
        model = str(scene.get('model', '')).strip().lower()
        task_type = str(scene.get('task_type', '')).strip().lower()

        if model == 'local demo':
            return self.local_provider
        if task_type == 'image_generation' and model.startswith('nano_banana_'):
            return self.google_provider
        if task_type == 'image_to_video' and (model.startswith('veo_31_') or model == 'omni_flash'):
            return self.google_provider
        raise ProviderError(
            f"No provider route for task_type={scene.get('task_type')!r}, model={scene.get('model')!r}"
        )

    def requires_dispatch_pacing(self, scene: dict[str, Any]) -> bool:
        return self.resolve(scene) is self.google_provider

    def dispatch_pacing_key(self, scene: dict[str, Any], slot: Any) -> str | None:
        provider = self.resolve(scene)
        resolver = getattr(provider, 'dispatch_pacing_key', None)
        if not callable(resolver):
            return None
        value = resolver(scene, slot)
        return str(value) if value is not None else None

    async def acquire_job_slot(self, scene: dict[str, Any]) -> Any:
        return await self.resolve(scene).acquire_job_slot(scene)

    async def release_job_slot(self, scene: dict[str, Any], slot: Any) -> None:
        await self.resolve(scene).release_job_slot(scene, slot)

    async def generate(self, scene: dict[str, Any]) -> str:
        return await self.resolve(scene).generate(scene)

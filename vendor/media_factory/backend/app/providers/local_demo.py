from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from .base import MediaProvider, scene_output_directory, scene_output_stem


class LocalDemoProvider(MediaProvider):
    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(self, scene: dict[str, Any]) -> str:
        if scene['task_type'] == 'image_generation':
            return self._write_svg(scene)
        return self._write_video_manifest(scene)

    def _write_svg(self, scene: dict[str, Any]) -> str:
        path = (scene_output_directory(scene, self.output_dir) / f"{scene_output_stem(scene)}.svg").resolve()
        prompt = escape(scene['prompt'][:120])
        name = escape(scene['name'])
        model = escape(scene['model'])
        aspect_ratio = escape(scene['aspect_ratio'])
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#07101c"/>
      <stop offset="0.55" stop-color="#111b2a"/>
      <stop offset="1" stop-color="#24194d"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="720" rx="28" fill="url(#bg)"/>
  <circle cx="1030" cy="170" r="220" fill="#7c4dff" opacity="0.14"/>
  <text x="76" y="104" fill="#8e6aff" font-family="Segoe UI, sans-serif" font-size="26">COFI STUDIO · LOCAL DEMO</text>
  <text x="76" y="214" fill="#f4f7fb" font-family="Segoe UI, sans-serif" font-size="58" font-weight="700">{name}</text>
  <text x="76" y="280" fill="#b7c2d1" font-family="Segoe UI, sans-serif" font-size="28">{model} · {aspect_ratio}</text>
  <foreignObject x="76" y="360" width="1030" height="190">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font: 28px 'Segoe UI', sans-serif; line-height:1.45; color:#8491a3;">{prompt}</div>
  </foreignObject>
</svg>'''
        path.write_text(svg, encoding='utf-8')
        return str(path)

    def _write_video_manifest(self, scene: dict[str, Any]) -> str:
        resolution = str(scene.get('_video_resolution') or '720p')
        path = (scene_output_directory(scene, self.output_dir) / f"{scene_output_stem(scene)}_{resolution}.video.json").resolve()
        payload = {
            'scene_id': scene['id'],
            'reference_image': scene.get('reference_image'),
            'prompt': scene['prompt'],
            'model': scene['model'],
            'duration': scene.get('duration_seconds'),
            'provider': 'local_demo',
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(path)

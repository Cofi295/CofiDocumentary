from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .db import Database, utc_now


PRODUCTION_STAGES = (
    'radar',
    'research',
    'script',
    'voice',
    'scenes',
    'visuals',
    'footage',
    'editor',
    'qc',
    'export',
)


def _default_production_settings() -> dict[str, Any]:
    return {
        'script': {
            'length_mode': 'characters',
            'character_min': 11000,
            'character_max': 13000,
            'duration_minutes': 18,
            'language': 'ko',
            'dna_mode': 'channel',
            'structure': 'documentary',
            'custom_instructions': '',
            'visual_clean_output': True,
            'visual_break_mode': 'sentence_and_visual_clause',
        },
        'scenes': {
            'prompt_model': 'gemini-3.5-flash',
            'visual_style': 'Theo DNA kênh',
            'custom_style': '',
            'character_reference': '',
            'split_mode': 'visual_lines',
            'visual_lines_per_prompt': 1,
            'visual_instructions': '',
        },
        'automation': {
            'mode': 'controlled',
            'pause_after_script': True,
            'pause_after_scenes': True,
        },
    }


def _merge_production_settings(current: Any) -> dict[str, Any]:
    defaults = _default_production_settings()
    if not isinstance(current, dict):
        return defaults

    raw = {
        section: dict(values) if isinstance(values, dict) else {}
        for section, values in current.items()
    }
    script = raw.get('script', {})
    if 'target_characters' in script and 'character_min' not in script and 'character_max' not in script:
        try:
            center = max(1000, int(script['target_characters']))
        except (TypeError, ValueError):
            center = 12000
        script['character_min'] = max(1000, center - 1000)
        script['character_max'] = center + 1000
    if 'target_duration_minutes' in script and 'duration_minutes' not in script:
        try:
            script['duration_minutes'] = max(1, int(script['target_duration_minutes']))
        except (TypeError, ValueError):
            script['duration_minutes'] = 18
    script.pop('target_characters', None)
    script.pop('target_duration_minutes', None)

    scenes = raw.get('scenes', {})
    if scenes.get('split_mode') in {'one_sentence', 'fixed_seconds'}:
        scenes['split_mode'] = 'visual_lines'
    if 'sentences_per_prompt' in scenes and 'visual_lines_per_prompt' not in scenes:
        try:
            scenes['visual_lines_per_prompt'] = max(1, int(scenes['sentences_per_prompt']))
        except (TypeError, ValueError):
            scenes['visual_lines_per_prompt'] = 1
    scenes.pop('target_scene_seconds', None)
    scenes.pop('sentences_per_prompt', None)

    raw['script'] = script
    raw['scenes'] = scenes
    for section, section_defaults in defaults.items():
        incoming = raw.get(section)
        if isinstance(incoming, dict):
            section_defaults.update(incoming)

    script_settings = defaults['script']
    script_settings['length_mode'] = 'duration' if script_settings.get('length_mode') == 'duration' else 'characters'
    try:
        script_settings['character_min'] = max(1000, int(script_settings.get('character_min', 11000)))
    except (TypeError, ValueError):
        script_settings['character_min'] = 11000
    try:
        script_settings['character_max'] = max(script_settings['character_min'], int(script_settings.get('character_max', 13000)))
    except (TypeError, ValueError):
        script_settings['character_max'] = max(script_settings['character_min'], 13000)
    try:
        script_settings['duration_minutes'] = max(1, int(script_settings.get('duration_minutes', 18)))
    except (TypeError, ValueError):
        script_settings['duration_minutes'] = 18

    scene_settings = defaults['scenes']
    try:
        scene_settings['visual_lines_per_prompt'] = min(6, max(1, int(scene_settings.get('visual_lines_per_prompt', 1))))
    except (TypeError, ValueError):
        scene_settings['visual_lines_per_prompt'] = 1
    return defaults


class ProjectManifestStore:
    def __init__(self, db: Database, root: Path):
        self.db = db
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _project(self, project_id: str) -> dict[str, Any]:
        project = self.db.get_resource('projects', project_id)
        if project is None:
            raise KeyError(f'Unknown project: {project_id}')
        return project

    def _workspace(self, project: dict[str, Any]) -> Path:
        configured = str(project.get('workspace') or '').strip()
        workspace = Path(configured).expanduser() if configured else self.root / project['id']
        workspace = workspace.resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    @staticmethod
    def _default(project: dict[str, Any], workspace: Path) -> dict[str, Any]:
        return {
            'version': 1,
            'project_id': project['id'],
            'name': project.get('name', ''),
            'title': project.get('title') or project.get('name', ''),
            'channel': project.get('channel', ''),
            'workflow_mode': project.get('workflow_mode', 'ai-visual'),
            'current_stage': project.get('current_stage', 'radar'),
            'workspace': str(workspace),
            'manifest_path': str(workspace / 'project.manifest.json'),
            'production_settings': _default_production_settings(),
            'stages': {},
            'updated_at': utc_now(),
        }

    def ensure(self, project_id: str) -> dict[str, Any]:
        project = self._project(project_id)
        workspace = self._workspace(project)
        manifest = self._default(project, workspace)
        existing = project.get('manifest')
        if isinstance(existing, dict):
            manifest.update(existing)
            manifest['stages'] = dict(existing.get('stages') or {})
            manifest['production_settings'] = _merge_production_settings(existing.get('production_settings'))
        manifest.update({
            'project_id': project['id'],
            'name': project.get('name', ''),
            'workspace': str(workspace),
            'manifest_path': str(workspace / 'project.manifest.json'),
            'updated_at': utc_now(),
        })
        self._persist(project_id, manifest)
        return manifest

    def patch(self, project_id: str, values: dict[str, Any]) -> dict[str, Any]:
        manifest = self.ensure(project_id)
        if 'stages' in values and isinstance(values['stages'], dict):
            stages = dict(manifest.get('stages') or {})
            stages.update(values['stages'])
            values = {**values, 'stages': stages}
        if 'production_settings' in values:
            settings = _merge_production_settings(manifest.get('production_settings'))
            incoming = values.get('production_settings')
            if isinstance(incoming, dict):
                for section, section_values in incoming.items():
                    if section in settings and isinstance(section_values, dict):
                        patch_values = dict(section_values)
                        if section == 'script':
                            if 'target_characters' in patch_values and 'character_min' not in patch_values and 'character_max' not in patch_values:
                                try:
                                    center = max(1000, int(patch_values['target_characters']))
                                except (TypeError, ValueError):
                                    center = 12000
                                patch_values['character_min'] = max(1000, center - 1000)
                                patch_values['character_max'] = center + 1000
                            if 'target_duration_minutes' in patch_values and 'duration_minutes' not in patch_values:
                                patch_values['duration_minutes'] = patch_values['target_duration_minutes']
                            patch_values.pop('target_characters', None)
                            patch_values.pop('target_duration_minutes', None)
                        if section == 'scenes':
                            if patch_values.get('split_mode') in {'one_sentence', 'fixed_seconds'}:
                                patch_values['split_mode'] = 'visual_lines'
                            if 'sentences_per_prompt' in patch_values and 'visual_lines_per_prompt' not in patch_values:
                                patch_values['visual_lines_per_prompt'] = patch_values['sentences_per_prompt']
                            patch_values.pop('target_scene_seconds', None)
                            patch_values.pop('sentences_per_prompt', None)
                        settings[section].update(patch_values)
            settings = _merge_production_settings(settings)
            values = {**values, 'production_settings': settings}
        manifest.update(values)
        manifest['updated_at'] = utc_now()
        self._persist(project_id, manifest)
        return manifest

    def update_stage(self, project_id: str, stage: str, values: dict[str, Any], *, advance: bool = False) -> dict[str, Any]:
        normalized_stage = stage.strip().lower()
        manifest = self.ensure(project_id)
        stages = dict(manifest.get('stages') or {})
        current = dict(stages.get(normalized_stage) or {})
        current.update(values)
        current['updated_at'] = utc_now()
        stages[normalized_stage] = current
        manifest['stages'] = stages
        if advance and current.get('status') == 'completed' and normalized_stage in PRODUCTION_STAGES:
            automation = dict((manifest.get('production_settings') or {}).get('automation') or {})
            controlled = automation.get('mode') == 'controlled'
            requires_review = (
                controlled
                and not current.get('review_approved')
                and (
                    (normalized_stage == 'script' and bool(automation.get('pause_after_script')))
                    or (normalized_stage == 'scenes' and bool(automation.get('pause_after_scenes')))
                )
            )
            if requires_review:
                current['review_required'] = True
                manifest['current_stage'] = normalized_stage
            else:
                current['review_required'] = False
                index = PRODUCTION_STAGES.index(normalized_stage)
                if index + 1 < len(PRODUCTION_STAGES):
                    manifest['current_stage'] = PRODUCTION_STAGES[index + 1]
        manifest['updated_at'] = utc_now()
        self._persist(project_id, manifest)
        return manifest

    def _persist(self, project_id: str, manifest: dict[str, Any]) -> None:
        workspace = Path(manifest['workspace'])
        workspace.mkdir(parents=True, exist_ok=True)
        manifest_path = workspace / 'project.manifest.json'
        temp = workspace / 'project.manifest.json.tmp'
        temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(manifest_path)
        self.db.patch_resource(
            'projects',
            project_id,
            {
                'workspace': str(workspace),
                'current_stage': manifest.get('current_stage', 'radar'),
                'manifest': manifest,
            },
        )

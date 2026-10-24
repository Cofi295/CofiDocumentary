from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any
from uuid import uuid4

from .db import Database, utc_now
from .queue import QueueSupervisor
from .schemas import JobStatus, SceneStatus

REQUIRED_NODE_KINDS = (
    'prompt',
    'reference',
    'generate_image',
    'generate_video',
    'extract_frame',
    'remotion',
    'export',
)

REQUIRED_KIND_EDGES = tuple(zip(REQUIRED_NODE_KINDS, REQUIRED_NODE_KINDS[1:]))
SUPPORTED_NODE_KINDS = frozenset(REQUIRED_NODE_KINDS)
MEDIA_JOB_TIMEOUT_SECONDS = 60 * 60
MEDIA_JOB_POLL_SECONDS = 0.01

NODE_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ('prompt', 'Prompt', 'Defines the production prompt and variables.'),
    ('reference', 'Reference', 'Supplies the source or reference image.'),
    ('generate_image', 'Generate Image', 'Creates the key image for the scene.'),
    ('generate_video', 'Generate Video', 'Creates motion from the generated image.'),
    ('extract_frame', 'Extract Frame', 'Selects a reusable frame from video output.'),
    ('remotion', 'Remotion', 'Builds a local render plan for composition.'),
    ('export', 'Export', 'Produces the final export manifest.'),
)


def _node_id(kind: str) -> str:
    return kind.replace('_', '-')


def normalize_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        **workflow,
        'nodes': [
            {
                **node,
                'enabled': bool(node.get('enabled', True)),
            }
            for node in workflow.get('nodes', [])
        ],
        'edges': [dict(edge) for edge in workflow.get('edges', [])],
    }


def default_workflow(workflow_id: str) -> dict[str, Any]:
    settings_by_kind: dict[str, dict[str, Any]] = {
        'prompt': {'text': 'Cinematic product hero with controlled studio lighting.', 'negative_prompt': ''},
        'reference': {'path': ''},
        'generate_image': {'model': 'Local Demo', 'aspect_ratio': '16:9'},
        'generate_video': {'model': 'Local Demo', 'aspect_ratio': '16:9', 'duration_seconds': 8},
        'extract_frame': {'frame_position': 0.5},
        'remotion': {'composition': 'HeroVideo', 'aspect_ratio': '16:9'},
        'export': {'output_format': 'mp4', 'quality': 'high'},
    }
    nodes = [
        {
            'id': _node_id(kind),
            'kind': kind,
            'label': label,
            'description': description,
            'enabled': True,
            'position': {'x': index * 250, 'y': 160 if index % 2 == 0 else 190},
            'settings': settings_by_kind[kind],
        }
        for index, (kind, label, description) in enumerate(NODE_DEFINITIONS)
    ]
    edges = [
        {
            'id': f'edge-{source}-{target}',
            'source': _node_id(source),
            'target': _node_id(target),
        }
        for source, target in REQUIRED_KIND_EDGES
    ]
    return {
        'id': workflow_id,
        'name': 'Hero Video Pipeline',
        'nodes': nodes,
        'edges': edges,
        'settings': {'model_preset': 'Local Demo', 'aspect_ratio': '16:9', 'concurrency': 10, 'autosave': True},
    }


def validate_workflow(workflow: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    normalized = normalize_workflow(workflow)
    nodes = normalized.get('nodes', [])
    edges = normalized.get('edges', [])
    node_ids = [node.get('id') for node in nodes]
    edge_ids = [edge.get('id') for edge in edges]

    if len(set(node_ids)) != len(node_ids):
        errors.append('Node IDs must be unique')
    if len(set(edge_ids)) != len(edge_ids):
        errors.append('Edge IDs must be unique')
    if not any(node.get('enabled', True) for node in nodes):
        errors.append('Workflow must contain at least one enabled node')

    for node in nodes:
        kind = node.get('kind')
        if kind not in SUPPORTED_NODE_KINDS:
            errors.append(f'Unsupported node kind: {kind}')

    id_to_kind = {node.get('id'): node.get('kind') for node in nodes}
    adjacency: dict[str, list[str]] = {str(node_id): [] for node_id in node_ids if node_id is not None}
    indegree: dict[str, int] = {str(node_id): 0 for node_id in node_ids if node_id is not None}

    for edge in edges:
        source = edge.get('source')
        target = edge.get('target')
        if source == target:
            errors.append(f'Self edge is not allowed: {source}')
            continue
        if source not in id_to_kind:
            errors.append(f'Edge source does not exist: {source}')
            continue
        if target not in id_to_kind:
            errors.append(f'Edge target does not exist: {target}')
            continue
        if source in adjacency and target in indegree:
            adjacency[source].append(target)
            indegree[target] += 1

    queue = [node_id for node_id, degree in indegree.items() if degree == 0]
    visited = 0
    while queue:
        node_id = queue.pop(0)
        visited += 1
        for neighbor in adjacency[node_id]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)
    if indegree and visited != len(indegree):
        errors.append('Workflow graph must be acyclic')
    return errors


def topological_nodes(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = workflow['nodes']
    index_by_id = {node['id']: index for index, node in enumerate(nodes)}
    node_by_id = {node['id']: node for node in nodes}
    adjacency = {node['id']: [] for node in nodes}
    indegree = {node['id']: 0 for node in nodes}
    for edge in workflow['edges']:
        if edge['source'] in adjacency and edge['target'] in indegree:
            adjacency[edge['source']].append(edge['target'])
            indegree[edge['target']] += 1
    queue = sorted((node_id for node_id, degree in indegree.items() if degree == 0), key=index_by_id.get)
    ordered: list[dict[str, Any]] = []
    while queue:
        node_id = queue.pop(0)
        ordered.append(node_by_id[node_id])
        for neighbor in adjacency[node_id]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)
                queue.sort(key=index_by_id.get)
    return ordered


def _empty_execution_context() -> dict[str, list[dict[str, Any]]]:
    return {
        'prompts': [],
        'references': [],
        'images': [],
        'videos': [],
        'source_paths': [],
    }


def _context_record_key(field: str, record: dict[str, Any]) -> tuple[Any, ...]:
    if field == 'prompts':
        return (
            record.get('source_node_id'),
            record.get('value'),
            record.get('negative_prompt'),
        )
    return (record.get('source_node_id'), record.get('path'))


def _merge_execution_contexts(contexts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    merged = _empty_execution_context()
    for field in merged:
        seen: set[tuple[Any, ...]] = set()
        for context in contexts:
            for record in context.get(field, []):
                key = _context_record_key(field, record)
                if key in seen:
                    continue
                seen.add(key)
                merged[field].append(dict(record))
    return merged


def _incoming_node_ids(workflow: dict[str, Any]) -> dict[str, list[str]]:
    incoming: dict[str, list[str]] = {node['id']: [] for node in workflow['nodes']}
    for edge in workflow['edges']:
        if edge['source'] in incoming and edge['target'] in incoming:
            incoming[edge['target']].append(edge['source'])
    return incoming


def _require_prompt(context: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    prompts = context.get('prompts', [])
    if not prompts:
        raise RuntimeError(f'{node["label"]} requires an upstream Prompt node')
    if len(prompts) > 1:
        sources = ', '.join(str(prompt.get('source_node_id')) for prompt in prompts)
        raise RuntimeError(f'{node["label"]} has ambiguous upstream prompts: {sources}')
    return prompts[0]


def _require_single_source(context: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    sources = context.get('source_paths', [])
    if not sources:
        raise RuntimeError(f'{node["label"]} requires an upstream media source')
    if len(sources) > 1:
        source_ids = ', '.join(str(source.get('source_node_id')) for source in sources)
        raise RuntimeError(f'{node["label"]} has ambiguous upstream media sources: {source_ids}')
    return sources[0]


class WorkflowEngine:
    def __init__(self, db: Database, queue: QueueSupervisor):
        self.db = db
        self.queue = queue

    def get_or_create(self, workflow_id: str) -> dict[str, Any]:
        stored = self.db.get_workflow(workflow_id)
        if stored is not None:
            return normalize_workflow(stored)
        workflow = default_workflow(workflow_id)
        return self.db.save_workflow(workflow_id, workflow)

    def save(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workflow = normalize_workflow({**payload, 'id': workflow_id})
        return self.db.save_workflow(workflow_id, workflow)

    async def _await_terminal_media_job(self, scene_id: str, initial_job_id: str) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + MEDIA_JOB_TIMEOUT_SECONDS
        terminal_statuses = {JobStatus.COMPLETED.value, JobStatus.FAILED.value}

        while True:
            scene = self.db.get_scene(scene_id)
            if scene is None:
                raise RuntimeError(f'Workflow media scene disappeared: {scene_id}')

            scene_status = scene['status']
            if scene_status in {SceneStatus.COMPLETED.value, SceneStatus.FAILED.value}:
                for job in self.db.list_jobs():
                    if job['scene_id'] == scene_id and job['status'] == scene_status:
                        return job

                initial_job = self.db.get_job(initial_job_id)
                if initial_job is not None and initial_job['status'] in terminal_statuses:
                    return initial_job
                raise RuntimeError(f'Workflow media scene reached {scene_status} without a terminal job')

            remaining = deadline - loop.time()
            if remaining <= 0:
                raise TimeoutError(f'Workflow media job timed out: {initial_job_id}')
            await asyncio.sleep(min(MEDIA_JOB_POLL_SECONDS, remaining))

    async def run(self, workflow_id: str) -> dict[str, Any]:
        workflow = self.get_or_create(workflow_id)
        errors = validate_workflow(workflow)
        if errors:
            raise ValueError(errors)

        entries: list[dict[str, Any]] = []
        artifacts: list[dict[str, Any]] = []
        node_contexts: dict[str, dict[str, Any]] = {}
        incoming = _incoming_node_ids(workflow)
        run_id = uuid4().hex
        run_created_at = utc_now()

        def save_run(status: str) -> dict[str, Any]:
            run = {
                'id': run_id,
                'workflow_id': workflow_id,
                'status': status,
                'entries': entries,
                'artifacts': artifacts,
                'created_at': run_created_at,
            }
            return self.db.save_workflow_run(run_id, workflow_id, run)

        def fail_node(node: dict[str, Any], started_at: str, started_clock: float, error: str) -> dict[str, Any]:
            entries.append(
                {
                    'node_id': node['id'],
                    'node_kind': node['kind'],
                    'status': 'failed',
                    'started_at': started_at,
                    'finished_at': utc_now(),
                    'duration_ms': max(0, round((perf_counter() - started_clock) * 1000)),
                    'message': error,
                }
            )
            return save_run('failed')

        for node in topological_nodes(workflow):
            started_at = utc_now()
            started_clock = perf_counter()
            kind = node['kind']
            message = f'{node["label"]} completed'
            context = _merge_execution_contexts(
                [node_contexts[parent_id] for parent_id in incoming.get(node['id'], [])]
            )

            if not node.get('enabled', True):
                node_contexts[node['id']] = context
                entries.append(
                    {
                        'node_id': node['id'],
                        'node_kind': kind,
                        'status': 'skipped',
                        'started_at': started_at,
                        'finished_at': utc_now(),
                        'duration_ms': max(0, round((perf_counter() - started_clock) * 1000)),
                        'message': f'{node["label"]} skipped because it is disabled',
                    }
                )
                continue

            if kind == 'prompt':
                settings = node.get('settings', {})
                context['prompts'] = [
                    {
                        'source_node_id': node['id'],
                        'value': settings.get('text', ''),
                        'negative_prompt': settings.get('negative_prompt') or None,
                    }
                ]
            elif kind == 'reference':
                reference_path = node.get('settings', {}).get('path') or None
                if reference_path:
                    reference = {'source_node_id': node['id'], 'path': reference_path}
                    if _context_record_key('references', reference) not in {
                        _context_record_key('references', item) for item in context['references']
                    }:
                        context['references'].append(reference)
                    if not context['source_paths']:
                        context['source_paths'] = [dict(reference)]
            elif kind in {'generate_image', 'generate_video'}:
                settings = node.get('settings', {})
                task_type = 'image_generation' if kind == 'generate_image' else 'image_to_video'
                try:
                    prompt = _require_prompt(context, node)
                    if kind == 'generate_video':
                        images = context.get('images', [])
                        if len(images) > 1:
                            source_ids = ', '.join(str(image.get('source_node_id')) for image in images)
                            raise RuntimeError(f'{node["label"]} has ambiguous upstream generated images: {source_ids}')
                        media_references = [images[0]['path']] if images else [
                            reference['path'] for reference in context.get('references', [])
                        ]
                        if not media_references:
                            raise RuntimeError(f'{node["label"]} requires an upstream generated image or Reference node')
                    else:
                        media_references = [reference['path'] for reference in context.get('references', [])]
                except RuntimeError as exc:
                    return fail_node(node, started_at, started_clock, str(exc))

                media_reference = media_references[0] if media_references else None
                scene = self.db.create_scene(
                    {
                        'name': f'{workflow["name"]} · {node["label"]}',
                        'task_type': task_type,
                        'prompt': prompt.get('value', ''),
                        'negative_prompt': prompt.get('negative_prompt'),
                        'reference_image': media_reference,
                        'reference_images': media_references,
                        'model': settings.get('model', 'Local Demo'),
                        'aspect_ratio': settings.get('aspect_ratio', workflow.get('settings', {}).get('aspect_ratio', '16:9')),
                        'duration_seconds': settings.get('duration_seconds') if task_type == 'image_to_video' else None,
                    }
                )
                job: dict[str, Any] | None = None
                try:
                    job = await self.queue.enqueue_scene(scene['id'])
                    terminal_job = await self._await_terminal_media_job(scene['id'], job['id'])
                except Exception as exc:
                    error = str(exc) or exc.__class__.__name__
                    artifacts.append(
                        {
                            'node_id': node['id'],
                            'node_kind': kind,
                            'type': 'media_job',
                            'scene_id': scene['id'],
                            'job_id': job['id'] if job else None,
                            'status': 'failed',
                            'error': error,
                        }
                    )
                    return fail_node(node, started_at, started_clock, error)

                if terminal_job['status'] != JobStatus.COMPLETED.value:
                    error = terminal_job.get('error') or f'{node["label"]} media job failed'
                    artifacts.append(
                        {
                            'node_id': node['id'],
                            'node_kind': kind,
                            'type': 'media_job',
                            'scene_id': scene['id'],
                            'job_id': terminal_job['id'],
                            'status': terminal_job['status'],
                            'error': error,
                        }
                    )
                    return fail_node(node, started_at, started_clock, error)

                output_path = terminal_job.get('output_path')
                if not output_path:
                    error = f'{node["label"]} media job completed without an output path'
                    artifacts.append(
                        {
                            'node_id': node['id'],
                            'node_kind': kind,
                            'type': 'media_job',
                            'scene_id': scene['id'],
                            'job_id': terminal_job['id'],
                            'status': 'failed',
                            'error': error,
                        }
                    )
                    return fail_node(node, started_at, started_clock, error)

                artifact = {
                    'node_id': node['id'],
                    'node_kind': kind,
                    'type': 'media_job',
                    'scene_id': scene['id'],
                    'job_id': terminal_job['id'],
                    'status': terminal_job['status'],
                    'output_path': output_path,
                }
                artifacts.append(artifact)
                if kind == 'generate_image':
                    context['images'] = [
                        {'source_node_id': node['id'], 'path': output_path, 'artifact': artifact}
                    ]
                else:
                    context['videos'] = [
                        {'source_node_id': node['id'], 'path': output_path, 'artifact': artifact}
                    ]
                context['source_paths'] = [
                    {'source_node_id': node['id'], 'path': output_path, 'artifact': artifact}
                ]
                message = f'Completed {node["label"]} job {terminal_job["id"][:8]}'
            elif kind == 'extract_frame':
                try:
                    source = _require_single_source(context, node)
                except RuntimeError as exc:
                    return fail_node(node, started_at, started_clock, str(exc))
                artifact = {
                    'node_id': node['id'],
                    'node_kind': kind,
                    'type': 'frame_metadata',
                    'source_path': source['path'],
                    'source_artifact': source.get('artifact'),
                    'frame_position': node.get('settings', {}).get('frame_position', 0.5),
                }
                artifacts.append(artifact)
                context['source_paths'] = [
                    {**source, 'source_node_id': node['id'], 'artifact': artifact}
                ]
                message = 'Frame extraction metadata prepared'
            elif kind == 'remotion':
                try:
                    source = _require_single_source(context, node)
                except RuntimeError as exc:
                    return fail_node(node, started_at, started_clock, str(exc))
                artifact = {
                    'node_id': node['id'],
                    'node_kind': kind,
                    'type': 'remotion_plan',
                    'source_path': source['path'],
                    'source_artifact': source.get('artifact'),
                    **node.get('settings', {}),
                }
                artifacts.append(artifact)
                context['source_paths'] = [
                    {**source, 'source_node_id': node['id'], 'artifact': artifact}
                ]
                message = 'Remotion render plan prepared'
            elif kind == 'export':
                try:
                    source = _require_single_source(context, node)
                except RuntimeError as exc:
                    return fail_node(node, started_at, started_clock, str(exc))
                artifact = {
                    'node_id': node['id'],
                    'node_kind': kind,
                    'type': 'export_manifest',
                    'source_path': source['path'],
                    'source_artifact': source.get('artifact'),
                    **node.get('settings', {}),
                }
                artifacts.append(artifact)
                context['source_paths'] = [
                    {**source, 'source_node_id': node['id'], 'artifact': artifact}
                ]
                message = 'Export manifest prepared'

            node_contexts[node['id']] = context
            finished_at = utc_now()
            entries.append(
                {
                    'node_id': node['id'],
                    'node_kind': kind,
                    'status': 'completed',
                    'started_at': started_at,
                    'finished_at': finished_at,
                    'duration_ms': max(0, round((perf_counter() - started_clock) * 1000)),
                    'message': message,
                }
            )

        return save_run('completed')

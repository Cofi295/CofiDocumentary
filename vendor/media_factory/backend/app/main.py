from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .db import Database
from .agent_jobs import AgentJobSupervisor
from .codex_chat import CodexChatService
from .project_manifests import ProjectManifestStore
from .providers.google import GoogleFlowAccountManager, GoogleFlowHeadlessClient, GoogleMediaProvider
from .providers.local_demo import LocalDemoProvider
from .providers.registry import ProviderRegistry
from .queue import QueueSupervisor
from .routes.editor import router as editor_router
from .routes.agent_jobs import router as agent_jobs_router
from .routes.codex_chat import router as codex_chat_router
from .routes.integrations import router as integrations_router
from .routes.library import router as library_router
from .routes.media import router as media_router
from .routes.providers import router as providers_router
from .routes.project_manifests import router as project_manifests_router
from .routes.tools import router as tools_router
from .routes.workflows import router as workflows_router
from .secrets import KeyringSecretStore
from .static_server import install_frontend_routes
from .tool_supervisor import ToolSupervisor
from .workflow_engine import WorkflowEngine


def create_app(
    *,
    db_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    frontend_dist: str | Path | None = None,
    secret_store: KeyringSecretStore | None = None,
    google_provider=None,
    google_account_manager: GoogleFlowAccountManager | None = None,
) -> FastAPI:
    project_root = Path(__file__).resolve().parents[2]
    resolved_db_path = Path(db_path) if db_path is not None else project_root / 'data' / 'cofi_studio.db'
    resolved_output_dir = Path(output_dir) if output_dir is not None else project_root / 'data' / 'outputs'
    resolved_upload_dir = resolved_output_dir.parent / 'uploads'
    resolved_frontend_dist = Path(frontend_dist) if frontend_dist is not None else project_root / 'frontend' / 'dist'

    db = Database(resolved_db_path)
    resolved_secret_store = secret_store or KeyringSecretStore(
        storage_dir=resolved_output_dir.parent / 'secrets' / 'google-flow',
    )
    local_provider = LocalDemoProvider(resolved_output_dir)
    resolved_google_account_manager = google_account_manager or GoogleFlowAccountManager(
        db,
        resolved_secret_store,
        profile_root=resolved_output_dir.parent / 'google-flow-profiles',
    )
    resolved_google_provider = google_provider or GoogleMediaProvider(
        resolved_output_dir,
        resolved_google_account_manager,
        flow_client=GoogleFlowHeadlessClient(resolved_output_dir, resolved_google_account_manager),
    )
    provider_registry = ProviderRegistry(
        local_provider=local_provider,
        google_provider=resolved_google_provider,
    )
    current_settings = db.get_settings()
    queue = QueueSupervisor(
        db,
        provider_registry,
        concurrency=current_settings['default_concurrency'],
        worker_delay_seconds=current_settings['worker_delay_seconds'],
        worker_delay_min_seconds=current_settings['worker_delay_min_seconds'],
        worker_delay_max_seconds=current_settings['worker_delay_max_seconds'],
    )
    workflow_engine = WorkflowEngine(db, queue)
    tool_supervisor = ToolSupervisor(project_root)
    project_manifests = ProjectManifestStore(db, resolved_output_dir.parent / 'projects')
    agent_jobs = AgentJobSupervisor(project_root, manifest_store=project_manifests)
    codex_chat = CodexChatService(project_root, agent_jobs)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        resolved_google_account_manager.resume_saved_sessions()
        await queue.start()
        try:
            yield
        finally:
            await queue.stop()
            resolved_google_account_manager.shutdown()

    application = FastAPI(title='Cofi Studio', lifespan=lifespan)
    application.state.db = db
    application.state.queue = queue
    application.state.provider_registry = provider_registry
    application.state.secret_store = resolved_secret_store
    application.state.google_account_manager = resolved_google_account_manager
    application.state.google_provider = resolved_google_provider
    application.state.workflow_engine = workflow_engine
    application.state.tool_supervisor = tool_supervisor
    application.state.agent_jobs = agent_jobs
    application.state.codex_chat = codex_chat
    application.state.project_manifests = project_manifests
    application.state.output_dir = resolved_output_dir.resolve()
    application.state.upload_dir = resolved_upload_dir.resolve()
    application.state.cache_dir = (resolved_output_dir.parent / 'cache').resolve()

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            'http://localhost:5173',
            'http://127.0.0.1:5173',
        ],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @application.get('/api/health')
    def health() -> dict[str, str]:
        return {'status': 'ok', 'app': 'Cofi Studio', 'version': '0.1.0'}

    application.include_router(media_router)
    application.include_router(agent_jobs_router)
    application.include_router(codex_chat_router)
    application.include_router(integrations_router)
    application.include_router(workflows_router)
    application.include_router(editor_router)
    application.include_router(library_router)
    application.include_router(providers_router)
    application.include_router(project_manifests_router)
    application.include_router(tools_router)
    @application.post('/api/v1/accounts/google-flow/clean-cache')
    def google_flow_clean_cache_v1(request: Request):
        from .routes.providers import google_accounts_clean_cache
        return google_accounts_clean_cache(request)

    install_frontend_routes(application, resolved_frontend_dist)
    return application

app = create_app()

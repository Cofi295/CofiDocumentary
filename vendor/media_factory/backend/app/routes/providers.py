from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict

from ..providers.base import ProviderAuthError, ProviderError, ProviderQuotaError


router = APIRouter(prefix='/api/providers/google', tags=['providers'])


class GoogleLoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')


class GoogleAccountPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool | None = None
    image_enabled: bool | None = None
    video_enabled: bool | None = None


class GoogleGenerateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scene: dict[str, Any]


def get_account_manager(request: Request):
    return request.app.state.google_account_manager


def get_google_provider(request: Request):
    return request.app.state.google_provider


def provider_http_error(exc: ProviderError) -> HTTPException:
    if isinstance(exc, ProviderAuthError):
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, ProviderQuotaError):
        return HTTPException(status_code=429, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


@router.get('/status')
def google_status(request: Request):
    return get_account_manager(request).status()


@router.get('/models')
def google_models(request: Request):
    try:
        account_manager = get_account_manager(request)
        account_manager.refresh_account_credits()
        models = get_google_provider(request).list_models()
        models = [
            {
                **model,
                'available_account_count': account_manager.available_account_count(str(model['id'])),
            }
            for model in models
        ]
    except ProviderError as exc:
        raise provider_http_error(exc) from exc
    return {'provider': 'google_flow', 'models': models}


@router.get('/accounts')
def google_accounts(request: Request):
    return get_account_manager(request).list_accounts()


@router.post('/generate')
async def google_generate(payload: GoogleGenerateRequest, request: Request):
    try:
        output_path = await get_google_provider(request).generate(dict(payload.scene))
    except ProviderError as exc:
        raise provider_http_error(exc) from exc
    return {'output_path': str(output_path)}


@router.post('/accounts/login', status_code=status.HTTP_201_CREATED)
def google_account_login(_: GoogleLoginRequest, request: Request):
    return get_account_manager(request).start_login()


@router.post('/connect', status_code=status.HTTP_201_CREATED)
def google_connect_alias(_: GoogleLoginRequest, request: Request):
    return get_account_manager(request).start_login()


@router.post('/accounts/resume_all')
def google_accounts_resume_all(request: Request):
    mgr = get_account_manager(request)
    if hasattr(mgr, 'resume_all_accounts'):
        return mgr.resume_all_accounts()
    mgr.resume_saved_sessions()
    return {'status': 'resuming'}


@router.patch('/accounts/{account_id}')
def google_account_patch(account_id: str, payload: GoogleAccountPatch, request: Request):
    try:
        return get_account_manager(request).set_enabled(
            account_id,
            enabled=payload.enabled,
            image_enabled=payload.image_enabled,
            video_enabled=payload.video_enabled,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='Google Flow account not found') from exc


@router.post('/accounts/{account_id}/renew')
def google_account_renew(account_id: str, request: Request):
    try:
        return get_account_manager(request).renew(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='Google Flow account not found') from exc


@router.post('/accounts/{account_id}/verify')
def google_account_verify(account_id: str, request: Request):
    try:
        return get_account_manager(request).verify_interactively(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='Google Flow account not found') from exc


@router.delete('/accounts/{account_id}', status_code=status.HTTP_204_NO_CONTENT)
def google_account_remove(account_id: str, request: Request):
    if not get_account_manager(request).remove(account_id):
        raise HTTPException(status_code=404, detail='Google Flow account not found')
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post('/disconnect')
def google_disconnect_compat(request: Request):
    manager = get_account_manager(request)
    for account in manager.list_accounts():
        manager.remove(account['id'])
    return manager.status()


@router.delete('/disconnect')
def google_disconnect_delete_compat(request: Request):
    return google_disconnect_compat(request)


@router.post('/accounts/resume_all')
def google_accounts_resume_all(request: Request):
    """Mark all accounts ready in DB, with browser instances launched strictly on demand."""
    try:
        manager = get_account_manager(request)
        if hasattr(manager, 'resume_all_accounts'):
            return manager.resume_all_accounts()
        return {'status': 'ready'}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post('/accounts/cleanup_ram')
def google_accounts_cleanup_ram(request: Request):
    """Force kill all idle background Chrome instances and free RAM immediately."""
    try:
        manager = get_account_manager(request)
        killed = 0
        if hasattr(manager, 'cleanup_idle_sessions'):
            killed = manager.cleanup_idle_sessions(max_idle_seconds=0.0)
        return {'status': 'ok', 'killed_sessions': killed}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post('/accounts/{account_id}/check')
def google_account_check(account_id: str, request: Request):
    try:
        manager = get_account_manager(request)
        if hasattr(manager, 'check_account'):
            return manager.check_account(account_id)
        return manager.renew(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='Google Flow account not found') from exc


@router.post('/accounts/check_all')
def google_accounts_check_all(request: Request):
    """Check all Google Flow accounts, recover sessions from G-Labs/cookies, without deleting accounts."""
    try:
        manager = get_account_manager(request)
        if hasattr(manager, 'check_all_accounts'):
            return manager.check_all_accounts(prune_dead=False)
        if hasattr(manager, 'resume_all_accounts'):
            manager.resume_all_accounts()
        accounts = manager.list_accounts()
        return {
            'ok': True,
            'active_count': sum(1 for a in accounts if a.get('status') == 'ready' and a.get('enabled') is not False),
            'total_count': len(accounts),
            'accounts': accounts,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post('/accounts/prune_dead')
def google_accounts_prune_dead(request: Request):
    """Check all Google Flow accounts, keep valid ones, and delete dead/expired ones."""
    try:
        manager = get_account_manager(request)
        if hasattr(manager, 'prune_dead_accounts'):
            return manager.prune_dead_accounts()
        return {'ok': True, 'kept_count': len(manager.list_accounts()), 'deleted_count': 0, 'deleted': [], 'accounts': manager.list_accounts()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post('/accounts/clean-cache')
def google_accounts_clean_cache(request: Request):
    """Clean Chromium cache directories and remove orphan profiles to free disk space."""
    try:
        manager = get_account_manager(request)
        if hasattr(manager, 'clean_profile_caches'):
            return manager.clean_profile_caches()
        return {
            'ok': True,
            'status': 'success',
            'total_size_mb': 0.0,
            'freed_mb': 0.0,
            'orphan_profiles_removed': 0,
            'orphan_sessions_removed': 0,
            'cleaned_profiles_count': 0,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post('/clean-cache')
def google_clean_cache_alias(request: Request):
    return google_accounts_clean_cache(request)







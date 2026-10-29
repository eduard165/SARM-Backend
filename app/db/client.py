from functools import lru_cache
from fastapi import HTTPException
from supabase import Client, create_client
from app.core.config import get_settings


@lru_cache
def _public_client() -> Client:
    config = get_settings()
    config.ensure_public()
    return create_client(config.supabase_url, config.publishable_key)


@lru_cache
def _privileged_client() -> Client:
    config = get_settings()
    config.ensure_admin()
    # Esta clave omite RLS. Solo usar desde rutas con autorizacion en el backend.
    return create_client(config.supabase_url, config.secret_key)


def public_client() -> Client:
    try:
        return _public_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def admin_client() -> Client:
    try:
        return _privileged_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client
from app.db.client import admin_client

router = APIRouter(prefix='/catalogos', tags=['Catalogos geograficos'])


@router.get('/estados')
def estados(db: Client = Depends(admin_client)):
    try:
        return db.table('estados').select('id,nombre,clave_inegi').order('nombre').execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail='Error consultando estados') from exc


@router.get('/municipios')
def municipios(estado_id: int = Query(..., ge=1, le=32), db: Client = Depends(admin_client)):
    try:
        return db.table('municipios').select('id,estado_id,nombre,clave_inegi').eq('estado_id', estado_id).order('nombre').execute().data or []
    except Exception as exc:
        raise HTTPException(status_code=503, detail='Error consultando municipios') from exc

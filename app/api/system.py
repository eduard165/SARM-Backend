from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from app.db.client import admin_client

router = APIRouter(tags=['Sistema'])


@router.get('/health')
def health():
    return {'estado': 'ok', 'servicio': 'SARM API', 'version': '0.7.0'}


@router.get('/health/db')
def health_db(db: Client = Depends(admin_client)):
    try:
        result = db.table('estados').select('id', count='exact').limit(1).execute()
        return {'estado': 'ok', 'origen': 'Supabase', 'estados_registrados': result.count}
    except Exception as exc:
        raise HTTPException(status_code=503, detail='No fue posible consultar Supabase; revisa configuracion y permisos') from exc

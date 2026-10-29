from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from app.core.security import Identity, get_identity
from app.core.permissions import require_role
from app.db.client import admin_client
from app.schemas.accounts import NuevoNegocio

router = APIRouter(prefix='/negocios', tags=['Negocios'])


@router.get('')
def mis_negocios(identity: Identity = Depends(get_identity), db: Client = Depends(admin_client)):
    try:
        if identity.rol == 'superadministrador':
            return db.table('negocios').select('id,nombre,logo_url,estado_registro').order('nombre').execute().data or []
        memberships = db.table('usuario_negocios').select('negocio_id').eq('usuario_id', str(identity.id)).eq('estado_membresia', 'activo').execute().data or []
        ids = [m['negocio_id'] for m in memberships]
        if not ids:
            return []
        return db.table('negocios').select('id,nombre,logo_url,estado_registro').in_('id', ids).eq('estado_registro', 'activo').order('nombre').execute().data or []
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail='No se pudieron consultar negocios') from exc


@router.post('', status_code=201)
def crear_negocio(data: NuevoNegocio, actor: Identity = Depends(get_identity), db: Client = Depends(admin_client)):
    require_role(actor, 'superadministrador')
    try:
        result = db.rpc('sarm_crear_negocio', {
            'p_actor': str(actor.id), 'p_nombre': data.nombre,
            'p_municipio': data.ubicacion.municipio_id,
            'p_localidad': data.ubicacion.localidad,
            'p_cp': data.ubicacion.codigo_postal,
            'p_logo_url': data.logo_url,
        }).execute()
        return {'id': result.data, 'nombre': data.nombre, 'estado': 'activo'}
    except Exception as exc:
        raise HTTPException(409, 'No se pudo registrar el negocio; verifica municipio y permisos') from exc

from fastapi import HTTPException
from supabase import Client
from app.core.security import Identity


def require_role(actor: Identity, *roles: str) -> None:
    if actor.rol not in roles:
        raise HTTPException(403, "No tienes permiso para realizar esta operacion")


def own_admin_business(actor: Identity, db: Client) -> str:
    require_role(actor, 'administrador')
    memberships = db.table('usuario_negocios').select('negocio_id,estado_membresia').eq('usuario_id', str(actor.id)).execute().data or []
    if len(memberships) != 1 or memberships[0]['estado_membresia'] != 'activo':
        raise HTTPException(403, 'Administrador sin negocio activo')
    business_id = memberships[0]['negocio_id']
    businesses = db.table('negocios').select('estado_registro').eq('id', business_id).limit(1).execute().data or []
    if not businesses or businesses[0]['estado_registro'] != 'activo':
        raise HTTPException(403, 'Negocio suspendido o inexistente')
    return business_id


def check_business_active(db: Client, business_id: str) -> None:
    found = db.table('negocios').select('estado_registro').eq('id', business_id).limit(1).execute().data or []
    if not found:
        raise HTTPException(404, 'Negocio inexistente')
    if found[0]['estado_registro'] != 'activo':
        raise HTTPException(409, 'El negocio esta suspendido')

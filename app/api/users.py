from fastapi import APIRouter, Depends, HTTPException
from supabase import Client
from app.core.security import Identity, get_identity
from app.core.permissions import require_role, own_admin_business, check_business_active
from app.db.client import admin_client
from app.schemas.accounts import NuevoPerfil, NuevoAdministrador
from app.services.accounts import crear_cuenta

router = APIRouter(tags=['Administracion de cuentas'])


@router.post('/administradores', status_code=201)
def registrar_administrador(data: NuevoAdministrador, actor: Identity = Depends(get_identity), db: Client = Depends(admin_client)):
    require_role(actor, 'superadministrador')
    check_business_active(db, str(data.negocio_id))
    return crear_cuenta(db, actor, data, tipo='administrador', negocio_id=data.negocio_id)


@router.post('/usuarios', status_code=201)
def registrar_operativo(data: NuevoPerfil, actor: Identity = Depends(get_identity), db: Client = Depends(admin_client)):
    require_role(actor, 'superadministrador', 'administrador')
    if actor.rol == 'administrador':
        assigned = own_admin_business(actor, db)
        if data.negocio_id is not None and str(data.negocio_id) != assigned:
            raise HTTPException(403, 'Solo puedes crear usuarios en tu propio negocio')
        from uuid import UUID
        business_id = UUID(assigned)
    else:
        if data.negocio_id is None:
            raise HTTPException(422, 'negocio_id es obligatorio para el superadministrador')
        business_id = data.negocio_id
    check_business_active(db, str(business_id))
    return crear_cuenta(db, actor, data, tipo='usuario', negocio_id=business_id)

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client
from app.core.security import Identity, get_identity
from app.core.permissions import require_role, own_admin_business, check_business_active
from app.db.client import admin_client
from app.schemas.accounts import NuevoPerfil, NuevoAdministrador
from app.services.accounts import crear_cuenta
from app.services.user_listing import listar_usuarios
from app.schemas.user_listing import UsuariosListadoOut, RolUsuario, EstadoUsuario

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


@router.get('/usuarios', response_model=UsuariosListadoOut)
def consultar_usuarios(
    q: str | None = Query(None, max_length=100, description='Nombre o nombre de usuario; coincidencia literal sin distinguir mayusculas'),
    rol: RolUsuario | None = Query(None),
    negocio_id: UUID | None = Query(None),
    estado: EstadoUsuario | None = Query(None),
    pagina: int = Query(1, ge=1, le=1000000),
    tamano_pagina: int = Query(20, ge=1, le=100),
    actor: Identity = Depends(get_identity),
    db: Client = Depends(admin_client),
):
    return listar_usuarios(db, actor, busqueda=q, rol=rol, negocio_id=negocio_id,
                          estado=estado, pagina=pagina, tamano_pagina=tamano_pagina)

import logging
from uuid import UUID
from fastapi import HTTPException
from supabase import Client
from app.core.security import Identity
from app.core.permissions import require_role, own_admin_business
from app.schemas.user_listing import UsuariosListadoOut

log = logging.getLogger(__name__)


def listar_usuarios(db: Client, actor: Identity, *, busqueda: str | None,
                    rol: str | None, negocio_id: UUID | None,
                    estado: str | None, pagina: int, tamano_pagina: int) -> UsuariosListadoOut:
    require_role(actor, 'superadministrador', 'administrador')
    if actor.rol == 'administrador':
        assigned = UUID(str(own_admin_business(actor, db)))
        if negocio_id is not None and negocio_id != assigned:
            raise HTTPException(403, 'Solo puedes consultar usuarios de tu negocio')
        if rol is not None and rol != 'usuario':
            raise HTTPException(403, 'Solo puedes consultar usuarios operativos')
        negocio_id = assigned

    try:
        result = db.rpc('sarm_listar_usuarios', {
            # Siempre procede del JWT verificado. No se acepta actor en el formulario.
            'p_actor': str(actor.id),
            'p_busqueda': busqueda.strip() if busqueda else None,
            'p_rol': rol,
            'p_negocio': str(negocio_id) if negocio_id else None,
            'p_estado': estado,
            'p_pagina': pagina,
            'p_tamano': tamano_pagina,
        }).execute()
        # No devolver claves inesperadas (ej. contrasenas) desde la funcion.
        return UsuariosListadoOut.model_validate(result.data)
    except HTTPException:
        raise
    except Exception as exc:
        code = str(getattr(exc, 'code', ''))
        if code == '42501':
            raise HTTPException(403, 'No tienes permiso para consultar estos usuarios') from exc
        if code == '22023':
            raise HTTPException(422, 'Filtros o paginacion invalidos') from exc
        if code in ('PGRST202', '42883'):
            raise HTTPException(503, 'Listado no disponible: verifica migracion 10 y funcion expuesta en Data API') from exc
        log.warning('Fallo listado de usuarios (%s)', code or type(exc).__name__)
        raise HTTPException(502, 'No se pudo consultar el listado de usuarios') from exc

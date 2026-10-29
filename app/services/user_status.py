from uuid import UUID
from fastapi import HTTPException
from supabase import Client
from app.core.permissions import own_admin_business, require_role
from app.core.security import Identity
from app.schemas.user_status import CambioEstadoUsuario, EstadoUsuarioOut
from app.services.rpc import ejecutar_rpc


def cambiar_estado(db: Client, actor: Identity, usuario_id: UUID, data: CambioEstadoUsuario):
    require_role(actor, 'superadministrador', 'administrador')
    if usuario_id == actor.id:
        raise HTTPException(403, 'No puedes cambiar tu propio acceso')
    negocio = data.negocio_id
    if actor.rol == 'administrador':
        propio = UUID(str(own_admin_business(actor, db)))
        if negocio is not None and negocio != propio:
            raise HTTPException(403, 'Solo puedes gestionar usuarios de tu negocio')
        negocio = propio
    elif negocio is None:
        raise HTTPException(422, 'negocio_id es obligatorio para el superadministrador')
    result = ejecutar_rpc(db, 'sarm_cambiar_estado_usuario', {
        'p_actor': str(actor.id), 'p_usuario': str(usuario_id),
        'p_negocio': str(negocio), 'p_estado': data.estado, 'p_motivo': data.motivo,
    }, migracion='13')
    return EstadoUsuarioOut.model_validate(result)

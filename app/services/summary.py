import logging
from uuid import UUID
from fastapi import HTTPException
from pydantic import TypeAdapter, ValidationError
from app.core.permissions import require_role
from app.core.security import Identity
from app.schemas.summary import ResumenInicio
from app.services.rpc import ejecutar_rpc

log = logging.getLogger(__name__)


def resumen_inicio(db, actor: Identity, negocio_id: UUID | None):
    require_role(actor, 'superadministrador', 'administrador', 'usuario')
    if actor.rol == 'usuario' and negocio_id is None:
        raise HTTPException(422, 'Selecciona un negocio para consultar el inventario')
    if actor.rol == 'superadministrador' and negocio_id is not None:
        raise HTTPException(422, 'El resumen global del superadministrador no admite negocio_id')
    result = ejecutar_rpc(db, 'sarm_resumen_inicio', {
        'p_actor': str(actor.id), 'p_negocio': str(negocio_id) if negocio_id else None,
    }, migracion='14')
    if not isinstance(result, dict) or result.get('tipo') != actor.rol:
        raise HTTPException(502, 'El servidor devolvio un resumen incompatible con tu perfil')
    try:
        return TypeAdapter(ResumenInicio).validate_python(result)
    except ValidationError as exc:
        log.warning('Formato invalido en resumen de inicio')
        raise HTTPException(502, 'No se pudo interpretar el resumen de inicio') from exc

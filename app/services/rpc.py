"""Errores seguros y comunes para operaciones transaccionales."""
import logging
from fastapi import HTTPException
from supabase import Client

log = logging.getLogger(__name__)


def ejecutar_rpc(db: Client, nombre: str, params: dict, *, migracion: str):
    try:
        return db.rpc(nombre, params).execute().data
    except Exception as exc:
        code = str(getattr(exc, 'code', ''))
        if code == '42501':
            raise HTTPException(403, 'No tienes acceso a esta operacion o negocio') from exc
        if code == 'P0002':
            raise HTTPException(404, 'Registro no encontrado en el negocio indicado') from exc
        if code == '23505':
            raise HTTPException(409, 'Ya existe un registro con esa identificacion o nombre') from exc
        if code in {'23514', '23502', '23503', '22023', '22P02', '22007', '22008', '22001', '22003'}:
            raise HTTPException(422, 'Datos incompatibles: revisa fechas, relaciones, estado y campos obligatorios') from exc
        if code in {'PGRST202', '42883', '42P01'}:
            raise HTTPException(503, f'Operacion no disponible: verifica migracion {migracion} y funciones expuestas en Data API') from exc
        if code in {'40001', '40P01'}:
            raise HTTPException(409, 'Hubo un cambio simultaneo. Vuelve a intentar la operacion') from exc
        log.warning('Fallo RPC %s (%s)', nombre, code or type(exc).__name__)
        raise HTTPException(502, 'No se pudo completar la operacion en la base de datos') from exc

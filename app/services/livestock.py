from supabase import Client
from app.core.security import Identity
from app.core.permissions import require_role
from app.services.rpc import ejecutar_rpc


def operar(db: Client, actor: Identity, nombre: str, negocio_id, **params):
    # La autorizacion definitiva por permiso y membresia se repite dentro de SQL.
    require_role(actor, 'superadministrador', 'usuario')
    return ejecutar_rpc(db, nombre, {'p_actor': str(actor.id), 'p_negocio': str(negocio_id), **params}, migracion='11 y 12')


def consultar(db, actor, negocio_id, recurso, *, registro_id=None, filtros=None, pagina=1, tamano_pagina=20):
    return operar(db, actor, 'sarm_consultar_ganado', negocio_id,
                  p_recurso=recurso, p_id=str(registro_id) if registro_id else None,
                  p_filtros=filtros or {}, p_pagina=pagina, p_tamano=tamano_pagina)


def guardar(db, actor, negocio_id, recurso, data, registro_id=None):
    params = data.model_dump(mode='json', exclude_unset=True)
    motivo = params.pop('motivo', None)
    nombre = 'sarm_guardar_animal' if recurso == 'animales' else 'sarm_guardar_catalogo_ganado'
    args = {'p_datos': params, 'p_id': str(registro_id) if registro_id else None, 'p_motivo': motivo}
    if recurso != 'animales':
        args['p_recurso'] = recurso
    return operar(db, actor, nombre, negocio_id, **args)

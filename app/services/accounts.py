import logging
from uuid import UUID
from fastapi import HTTPException
from supabase import Client
from app.core.security import Identity
from app.schemas.accounts import NuevoPerfil

log = logging.getLogger(__name__)


def crear_cuenta(db: Client, actor: Identity, data: NuevoPerfil, *, tipo: str, negocio_id: UUID) -> dict:
    # Doble comprobacion: Python valida permisos y RPC verifica en PostgreSQL.
    try:
        # Cada identidad tiene email tecnico unico; no se pide correo al trabajador.
        import uuid
        auth_email = f'sarm-{uuid.uuid4().hex}@accounts.example.com'
        response = db.auth.admin.create_user({
            'email': auth_email,
            'password': data.password,
            'email_confirm': True,
        })
        user = response.user
        if user is None:
            raise RuntimeError('Supabase Auth no devolvio identidad')
    except Exception as exc:
        log.warning('Fallo la creacion de identidad en Supabase Auth: %s', type(exc).__name__)
        raise HTTPException(502, 'No se pudo crear la identidad en Supabase Auth') from exc

    params = {
        'p_actor': str(actor.id),
        'p_usuario': str(user.id),
        'p_tipo': tipo,
        'p_negocio': str(negocio_id),
        'p_nombre_usuario': data.nombre_usuario,
        'p_nombre': data.nombre,
        'p_apellido_paterno': data.apellido_paterno,
        'p_apellido_materno': data.apellido_materno,
        'p_fecha_nacimiento': data.fecha_nacimiento.isoformat() if data.fecha_nacimiento else None,
        'p_sexo': data.sexo,
        'p_telefono': data.telefono,
    }
    try:
        db.rpc('sarm_crear_cuenta', params).execute()
        return {'id': str(user.id), 'nombre_usuario': data.nombre_usuario,
                'rol': tipo, 'negocio_id': str(negocio_id), 'estado': 'creado'}
    except Exception as exc:
        # Compensacion: eliminamos SOLO la identidad recien creada, sin perfil.
        try:
            db.auth.admin.delete_user(str(user.id))
        except Exception:
            log.exception('IMPORTANTE: no se pudo limpiar identidad de Auth %s', user.id)
            raise HTTPException(500, f'No se pudo finalizar cuenta. Revisa en Auth el ID {user.id}') from exc
        log.warning('Error al registrar cuenta en PostgreSQL (Auth compensado): %s', str(exc)[:250])
        raise HTTPException(409, 'No se pudo registrar la cuenta: verifica usuario, negocio y permisos') from exc

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client, create_client
from app.core.security import Identity, get_identity
from app.db.client import admin_client
from app.core.config import get_settings
from app.schemas.accounts import LoginRequest

router = APIRouter(prefix='/auth', tags=['Autenticacion'])


@router.post('/login')
def login(body: LoginRequest, db: Client = Depends(admin_client)):
    # No revelar si existe el nombre de usuario.
    invalid = HTTPException(401, 'Credenciales incorrectas')
    try:
        records = db.table('usuarios').select('id,bloqueo_global').eq('nombre_usuario', body.nombre_usuario).limit(1).execute().data or []
        if not records or records[0]['bloqueo_global']:
            raise invalid
        auth_account = db.auth.admin.get_user_by_id(records[0]['id']).user
        if not auth_account or not auth_account.email:
            raise invalid
        settings = get_settings()
        # Cliente aislado por login: no mantener sesiones entre solicitudes.
        client = create_client(settings.supabase_url, settings.publishable_key)
        session = client.auth.sign_in_with_password({'email': auth_account.email, 'password': body.password}).session
        if not session:
            raise invalid
        from app.services.rpc import ejecutar_rpc
        enabled = ejecutar_rpc(db, 'sarm_comprobar_acceso', {'p_usuario': str(records[0]['id'])}, migracion='13')
        if enabled is not True:
            raise HTTPException(403, 'Cuenta sin acceso activo a un negocio')
        return {'access_token': session.access_token, 'refresh_token': session.refresh_token,
                'token_type': 'bearer', 'expires_in': session.expires_in}
    except HTTPException:
        raise
    except Exception as exc:
        raise invalid from exc


@router.get('/me')
def me(identity: Identity = Depends(get_identity), db: Client = Depends(admin_client)):
    try:
        found = db.table('usuarios').select('id,nombre_usuario,nombre,apellido_paterno,apellido_materno,bloqueo_global').eq('id', str(identity.id)).limit(1).execute().data or []
        if not found:
            raise HTTPException(403, 'Cuenta SARM no disponible')
        user = found[0]
        user['rol'] = identity.rol
        memberships = db.table('usuario_negocios').select('negocio_id,estado_membresia').eq('usuario_id', str(identity.id)).execute().data or []
        ids = [m['negocio_id'] for m in memberships]
        names = {}
        if ids:
            businesses = db.table('negocios').select('id,nombre,estado_registro').in_('id', ids).execute().data or []
            names = {b['id']: b for b in businesses}
        user['negocios'] = [{**m, 'nombre_negocio': names[m['negocio_id']]['nombre'], 'estado_registro': names[m['negocio_id']]['estado_registro']} for m in memberships if m['negocio_id'] in names]
        return user
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, 'Error consultando perfil') from exc

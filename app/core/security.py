from dataclasses import dataclass
from uuid import UUID
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client
from app.db.client import admin_client, public_client

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Identity:
    id: UUID
    rol: str
    nombre_usuario: str


def require_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Token Bearer requerido')
    return credentials.credentials


def get_identity(
    token: str = Depends(require_token),
    auth: Client = Depends(public_client),
    db: Client = Depends(admin_client),
) -> Identity:
    try:
        # Verifica el JWT contra Supabase Auth (no se confia en roles del JWT).
        auth_user = auth.auth.get_user(token).user
        if auth_user is None:
            raise HTTPException(status_code=401, detail='Token invalido')
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail='Token invalido o expirado') from exc

    try:
        users = db.table('usuarios').select('id,nombre_usuario,bloqueo_global,rol_id').eq('id', str(auth_user.id)).limit(1).execute().data or []
        if not users or users[0]['bloqueo_global']:
            raise HTTPException(status_code=403, detail='Cuenta SARM no habilitada')
        user = users[0]
        roles = db.table('roles').select('codigo').eq('id', user['rol_id']).limit(1).execute().data or []
        if not roles:
            raise HTTPException(status_code=403, detail='Rol SARM no valido')
        return Identity(id=UUID(str(user['id'])), rol=roles[0]['codigo'], nombre_usuario=user['nombre_usuario'])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail='No se pudo consultar el perfil SARM') from exc

from dataclasses import dataclass, field
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
    perfil: dict = field(default_factory=dict)


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
        from app.services.rpc import ejecutar_rpc
        profile=ejecutar_rpc(db,'sarm_perfil_acceso',{'p_usuario':str(auth_user.id)},migracion='15')
        if not isinstance(profile,dict) or profile.get('id')!=str(auth_user.id) or profile.get('rol') not in ('superadministrador','administrador','usuario'):
            raise HTTPException(502,'Perfil de acceso invalido')
        return Identity(UUID(profile['id']),profile['rol'],profile['nombre_usuario'],profile)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail='No se pudo consultar el perfil SARM') from exc

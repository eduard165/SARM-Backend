from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel

RolUsuario = Literal['superadministrador', 'administrador', 'usuario']
EstadoUsuario = Literal['activo', 'suspendido']


class NegocioUsuarioOut(BaseModel):
    negocio_id: UUID
    nombre: str
    estado_membresia: EstadoUsuario
    estado_negocio: EstadoUsuario


class UsuarioListadoOut(BaseModel):
    id: UUID
    nombre_usuario: str
    nombre: str
    apellido_paterno: str
    apellido_materno: str | None = None
    nombre_completo: str
    rol: RolUsuario
    estado: EstadoUsuario
    bloqueo_global: bool
    creado_en: datetime
    negocios: list[NegocioUsuarioOut]


class UsuariosListadoOut(BaseModel):
    items: list[UsuarioListadoOut]
    total: int
    pagina: int
    tamano_pagina: int
    total_paginas: int

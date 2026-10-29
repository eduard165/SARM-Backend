from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class EstadoOut(BaseModel):
    id: int
    nombre: str
    clave_inegi: str


class MunicipioOut(BaseModel):
    id: int
    estado_id: int
    nombre: str
    clave_inegi: str


class NegocioOut(BaseModel):
    id: UUID
    nombre: str
    logo_url: str | None
    estado_registro: str


class MembresiaOut(BaseModel):
    negocio_id: UUID
    nombre_negocio: str
    estado_membresia: str
    estado_registro: str


class UsuarioActualOut(BaseModel):
    id: UUID
    nombre_usuario: str
    nombre: str
    apellido_paterno: str
    apellido_materno: str | None
    rol: str
    bloqueo_global: bool
    negocios: list[MembresiaOut]

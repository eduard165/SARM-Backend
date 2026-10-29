from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CambioEstadoUsuario(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    negocio_id: UUID | None = None
    estado: Literal['activo', 'suspendido']
    motivo: str = Field(min_length=1, max_length=1000)


class EstadoUsuarioOut(BaseModel):
    usuario_id: UUID
    negocio_id: UUID
    estado_membresia: Literal['activo', 'suspendido']
    cambiado: bool

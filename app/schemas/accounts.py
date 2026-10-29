from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class NuevoPerfil(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nombre_usuario: str = Field(min_length=3, max_length=50, pattern=r'^[A-Za-z0-9._-]+$')
    password: str = Field(min_length=12, max_length=128)
    nombre: str = Field(min_length=1, max_length=100)
    apellido_paterno: str = Field(min_length=1, max_length=100)
    apellido_materno: str | None = Field(default=None, max_length=100)
    fecha_nacimiento: date | None = None
    sexo: str | None = Field(default=None, max_length=20)
    telefono: str | None = Field(default=None, max_length=20)
    negocio_id: UUID | None = None


class NuevoAdministrador(NuevoPerfil):
    negocio_id: UUID


class LoginRequest(BaseModel):
    nombre_usuario: str
    password: str


class NuevaUbicacionNegocio(BaseModel):
    municipio_id: int
    localidad: str = Field(min_length=1, max_length=150)
    codigo_postal: str = Field(pattern=r'^[0-9]{5}$')


class NuevoNegocio(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    ubicacion: NuevaUbicacionNegocio
    logo_url: str | None = None

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

Count = Annotated[int, Field(ge=0)]


class ResumenQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    negocio_id: UUID | None = None


class ConteosAcceso(BaseModel):
    total: Count
    activos: Count
    suspendidos: Count


class ConteosCuentas(ConteosAcceso):
    superadministradores: Count
    administradores: Count
    operativos: Count


class NegocioResumen(BaseModel):
    id: UUID
    nombre: str


class ResumenSuperadmin(BaseModel):
    tipo: Literal['superadministrador']
    actualizado_en: datetime
    negocio: None
    negocios: ConteosAcceso
    usuarios: ConteosCuentas


class ResumenAdmin(BaseModel):
    tipo: Literal['administrador']
    actualizado_en: datetime
    negocio: NegocioResumen
    usuarios: ConteosAcceso


class InventarioResumen(BaseModel):
    total: Count
    activos: Count
    bajas: Count
    hembras_activas: Count
    machos_activos: Count
    sin_categoria: Count
    sin_hato: Count
    sin_ubicacion: Count


class DistribucionResumen(BaseModel):
    id: UUID | None
    nombre: str
    total: Count


class AnimalReciente(BaseModel):
    id: UUID
    identificacion: str
    nombre: str | None
    sexo: Literal['macho','hembra']
    estado_registro: Literal['activo','baja']
    fecha_incorporacion: date
    creado_en: datetime


class ResumenOperativo(BaseModel):
    tipo: Literal['usuario']
    actualizado_en: datetime
    negocio: NegocioResumen
    inventario: InventarioResumen
    categorias: list[DistribucionResumen]
    hatos: list[DistribucionResumen]
    ubicaciones: list[DistribucionResumen]
    recientes: list[AnimalReciente]


ResumenInicio = Annotated[ResumenSuperadmin | ResumenAdmin | ResumenOperativo, Field(discriminator='tipo')]

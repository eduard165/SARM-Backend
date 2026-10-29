from datetime import date, datetime
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

Sexo = Literal['macho', 'hembra']
EstadoAnimal = Literal['activo', 'baja']
EstadoCatalogo = Literal['activo', 'archivado']
TipoLugar = Literal['potrero', 'corral', 'establo', 'otro']
Texto100 = Annotated[str, Field(min_length=1, max_length=100)]
Texto150 = Annotated[str, Field(min_length=1, max_length=150)]
Motivo = Annotated[str, Field(min_length=1, max_length=1000)]


class Entrada(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class CamposAnimal(Entrada):
    identificacion: Texto100 | None = None
    nombre: Texto150 | None = None
    sexo: Sexo | None = None
    categoria_id: UUID | None = None
    fecha_nacimiento: date | None = None
    nacimiento_estimado: bool = Field(default=False, strict=True)
    tipo_racial: Texto150 | None = None
    fecha_incorporacion: date | None = None
    tipo_incorporacion: Literal['nacimiento', 'compra', 'otro'] | None = None
    procedencia: str | None = Field(default=None, max_length=250)
    padre_id: UUID | None = None
    padre_externo_identificacion: Texto150 | None = None
    padre_externo_raza: Texto150 | None = None
    madre_id: UUID | None = None
    madre_externa_identificacion: Texto150 | None = None
    madre_externa_raza: Texto150 | None = None
    observaciones: str | None = Field(default=None, max_length=4000)

    @model_validator(mode='after')
    def validar_campos(self):
        obligatorios = {'identificacion', 'sexo', 'fecha_nacimiento', 'fecha_incorporacion', 'tipo_incorporacion'}
        if any(getattr(self, k) is None for k in self.model_fields_set & obligatorios):
            raise ValueError('Los campos obligatorios no admiten null')
        for k in ('fecha_nacimiento', 'fecha_incorporacion'):
            valor = getattr(self, k)
            if valor is not None and valor > date.today():
                raise ValueError('No se permiten fechas futuras')
        if self.fecha_nacimiento and self.fecha_incorporacion:
            if self.fecha_nacimiento > self.fecha_incorporacion:
                raise ValueError('Nacimiento posterior a incorporacion')
            if self.tipo_incorporacion == 'nacimiento' and self.fecha_nacimiento != self.fecha_incorporacion:
                raise ValueError('Para nacimiento las fechas deben coincidir')
        if self.padre_id and (self.padre_externo_identificacion or self.padre_externo_raza):
            raise ValueError('Elegir padre registrado o externo')
        if self.madre_id and (self.madre_externa_identificacion or self.madre_externa_raza):
            raise ValueError('Elegir madre registrada o externa')
        return self


class AnimalCrear(CamposAnimal):
    especie_id: UUID
    identificacion: Texto100
    sexo: Sexo
    fecha_nacimiento: date
    fecha_incorporacion: date
    tipo_incorporacion: Literal['nacimiento', 'compra', 'otro']


class AnimalActualizar(CamposAnimal):
    motivo: Motivo

    @model_validator(mode='after')
    def requiere_cambio(self):
        if not (self.model_fields_set - {'motivo'}):
            raise ValueError('Indique al menos un campo para corregir')
        return self


class CatalogoCrear(Entrada):
    nombre: Texto150
    descripcion: str | None = Field(default=None, max_length=2000)


class UbicacionCrear(CatalogoCrear):
    tipo: TipoLugar = 'otro'


class CatalogoActualizar(Entrada):
    nombre: Texto150 | None = None
    descripcion: str | None = Field(default=None, max_length=2000)
    estado_registro: EstadoCatalogo | None = None
    motivo: Motivo

    @model_validator(mode='after')
    def requiere_cambio(self):
        if not (self.model_fields_set - {'motivo'}):
            raise ValueError('Indique al menos un campo para corregir')
        if any(getattr(self, k) is None for k in self.model_fields_set & {'nombre', 'estado_registro', 'tipo'}):
            raise ValueError('El campo no admite null')
        return self


class UbicacionActualizar(CatalogoActualizar):
    tipo: TipoLugar | None = None


class MovimientoCrear(Entrada):
    fecha: date
    hato_id: UUID | None  # Ambos destinos obligatorios; null significa desasignar.
    ubicacion_ganadera_id: UUID | None
    motivo: Motivo

    @model_validator(mode='after')
    def fecha_valida(self):
        if self.fecha > date.today():
            raise ValueError('No se permiten fechas futuras')
        return self


class BajaCrear(Entrada):
    fecha: date
    motivo: Literal['venta', 'muerte', 'otro']
    observaciones: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def fecha_valida(self):
        if self.fecha > date.today():
            raise ValueError('No se permiten fechas futuras')
        return self


class BajaAnular(Entrada):
    motivo: Motivo


class RegistroOut(BaseModel):
    id: UUID
    negocio_id: UUID
    creado_en: datetime


class AnimalOut(RegistroOut):
    especie_id: UUID
    identificacion: str
    nombre: str | None = None
    sexo: Sexo
    categoria_id: UUID | None = None
    fecha_nacimiento: date
    nacimiento_estimado: bool
    tipo_racial: str | None = None
    fecha_incorporacion: date
    tipo_incorporacion: Literal['nacimiento', 'compra', 'otro']
    procedencia: str | None = None
    padre_id: UUID | None = None
    padre_externo_identificacion: str | None = None
    padre_externo_raza: str | None = None
    madre_id: UUID | None = None
    madre_externa_identificacion: str | None = None
    madre_externa_raza: str | None = None
    hato_id: UUID | None = None
    ubicacion_ganadera_id: UUID | None = None
    estado_registro: EstadoAnimal
    observaciones: str | None = None
    creado_por: UUID
    actualizado_en: datetime


class HatoOut(RegistroOut):
    nombre: str
    descripcion: str | None = None
    estado_registro: EstadoCatalogo
    creado_por: UUID
    actualizado_en: datetime


class UbicacionOut(HatoOut):
    tipo: TipoLugar


class MovimientoOut(RegistroOut):
    animal_id: UUID
    fecha: date
    hato_origen_id: UUID | None = None
    hato_destino_id: UUID | None = None
    ubicacion_origen_id: UUID | None = None
    ubicacion_destino_id: UUID | None = None
    motivo: str
    registrado_por: UUID


class BajaOut(RegistroOut):
    animal_id: UUID
    fecha: date
    motivo: Literal['venta', 'muerte', 'otro']
    observaciones: str | None = None
    registrado_por: UUID
    anulada_en: datetime | None = None
    anulada_por: UUID | None = None
    motivo_anulacion: str | None = None


class EspecieOut(BaseModel):
    id: UUID
    codigo: str
    nombre: str
    habilitada: bool


class CategoriaOut(BaseModel):
    id: UUID
    especie_id: UUID
    codigo: str
    nombre: str
    sexo: Sexo | None = None


T = TypeVar('T')


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int
    pagina: int
    tamano_pagina: int
    total_paginas: int

from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from supabase import Client
from app.core.security import Identity, get_identity
from app.db.client import admin_client
from app.schemas.livestock import (
    AnimalCrear, AnimalActualizar, AnimalOut, CatalogoCrear, CatalogoActualizar,
    UbicacionCrear, UbicacionActualizar, HatoOut, UbicacionOut,
    MovimientoCrear, MovimientoOut, BajaCrear, BajaOut, BajaAnular,
    EspecieOut, CategoriaOut, Pagina, Sexo, EstadoAnimal, EstadoCatalogo,
)
from app.services.livestock import consultar, guardar, operar

router = APIRouter(prefix='/negocios/{negocio_id}', tags=['Ganado'])
Actor = Annotated[Identity, Depends(get_identity)]
DB = Annotated[Client, Depends(admin_client)]


class Paginacion(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    q: str | None = Field(default=None, max_length=100)
    pagina: int = Field(default=1, ge=1, le=1000000)
    tamano_pagina: int = Field(default=20, ge=1, le=100)

    def filtros(self):
        return self.model_dump(mode='json', exclude_none=True, exclude={'pagina', 'tamano_pagina'})


class FiltrosAnimales(Paginacion):
    sexo: Sexo | None = None
    estado_registro: EstadoAnimal | None = None
    especie_id: UUID | None = None
    categoria_id: UUID | None = None
    hato_id: UUID | None = None
    ubicacion_ganadera_id: UUID | None = None


class FiltrosCatalogo(Paginacion):
    estado_registro: EstadoCatalogo | None = None


class FiltrosCategorias(Paginacion):
    especie_id: UUID | None = None


def listado(db, actor, negocio, recurso, query):
    return consultar(db, actor, negocio, recurso, filtros=query.filtros(), pagina=query.pagina, tamano_pagina=query.tamano_pagina)


@router.get('/animales', response_model=Pagina[AnimalOut])
def listar_animales(negocio_id: UUID, actor: Actor, db: DB, query: Annotated[FiltrosAnimales, Query()]):
    return listado(db, actor, negocio_id, 'animales', query)


@router.post('/animales', status_code=201, response_model=AnimalOut)
def crear_animal(negocio_id: UUID, data: AnimalCrear, actor: Actor, db: DB):
    return guardar(db, actor, negocio_id, 'animales', data)


@router.get('/animales/{animal_id}', response_model=AnimalOut)
def obtener_animal(negocio_id: UUID, animal_id: UUID, actor: Actor, db: DB):
    return consultar(db, actor, negocio_id, 'animales', registro_id=animal_id)


@router.patch('/animales/{animal_id}', response_model=AnimalOut)
def corregir_animal(negocio_id: UUID, animal_id: UUID, data: AnimalActualizar, actor: Actor, db: DB):
    return guardar(db, actor, negocio_id, 'animales', data, animal_id)


@router.post('/animales/{animal_id}/movimientos', status_code=201, response_model=MovimientoOut)
def mover_animal(negocio_id: UUID, animal_id: UUID, data: MovimientoCrear, actor: Actor, db: DB):
    return operar(db, actor, 'sarm_mover_animal', negocio_id, p_animal=str(animal_id), p_fecha=data.fecha.isoformat(),
                  p_hato=str(data.hato_id) if data.hato_id else None,
                  p_ubicacion=str(data.ubicacion_ganadera_id) if data.ubicacion_ganadera_id else None, p_motivo=data.motivo)


@router.get('/animales/{animal_id}/movimientos', response_model=Pagina[MovimientoOut])
def movimientos_animal(negocio_id: UUID, animal_id: UUID, actor: Actor, db: DB, query: Annotated[Paginacion, Query()]):
    consultar(db, actor, negocio_id, 'animales', registro_id=animal_id)
    return consultar(db, actor, negocio_id, 'movimientos_animales', filtros={**query.filtros(), 'animal_id': str(animal_id)},
                     pagina=query.pagina, tamano_pagina=query.tamano_pagina)


@router.post('/animales/{animal_id}/bajas', status_code=201, response_model=BajaOut)
def dar_baja_animal(negocio_id: UUID, animal_id: UUID, data: BajaCrear, actor: Actor, db: DB):
    return operar(db, actor, 'sarm_registrar_baja_animal', negocio_id, p_animal=str(animal_id),
                  p_fecha=data.fecha.isoformat(), p_motivo=data.motivo, p_observaciones=data.observaciones)


@router.get('/animales/{animal_id}/bajas', response_model=Pagina[BajaOut])
def bajas_animal(negocio_id: UUID, animal_id: UUID, actor: Actor, db: DB, query: Annotated[Paginacion, Query()]):
    consultar(db, actor, negocio_id, 'animales', registro_id=animal_id)
    return consultar(db, actor, negocio_id, 'bajas_animales', filtros={**query.filtros(), 'animal_id': str(animal_id)},
                     pagina=query.pagina, tamano_pagina=query.tamano_pagina)


@router.post('/bajas-animales/{baja_id}/anular', response_model=AnimalOut)
def anular_baja(negocio_id: UUID, baja_id: UUID, data: BajaAnular, actor: Actor, db: DB):
    return operar(db, actor, 'sarm_anular_baja_animal', negocio_id, p_baja=str(baja_id), p_motivo=data.motivo)


@router.get('/especies-animales', response_model=Pagina[EspecieOut])
def listar_especies(negocio_id: UUID, actor: Actor, db: DB, query: Annotated[Paginacion, Query()]):
    return listado(db, actor, negocio_id, 'especies_animales', query)


@router.get('/categorias-animales', response_model=Pagina[CategoriaOut])
def listar_categorias(negocio_id: UUID, actor: Actor, db: DB, query: Annotated[FiltrosCategorias, Query()]):
    return listado(db, actor, negocio_id, 'categorias_animales', query)


@router.get('/hatos', response_model=Pagina[HatoOut])
def listar_hatos(negocio_id: UUID, actor: Actor, db: DB, query: Annotated[FiltrosCatalogo, Query()]):
    return listado(db, actor, negocio_id, 'hatos', query)


@router.post('/hatos', status_code=201, response_model=HatoOut)
def crear_hato(negocio_id: UUID, data: CatalogoCrear, actor: Actor, db: DB):
    return guardar(db, actor, negocio_id, 'hatos', data)


@router.get('/hatos/{registro_id}', response_model=HatoOut)
def obtener_hato(negocio_id: UUID, registro_id: UUID, actor: Actor, db: DB):
    return consultar(db, actor, negocio_id, 'hatos', registro_id=registro_id)


@router.patch('/hatos/{registro_id}', response_model=HatoOut)
def corregir_hato(negocio_id: UUID, registro_id: UUID, data: CatalogoActualizar, actor: Actor, db: DB):
    return guardar(db, actor, negocio_id, 'hatos', data, registro_id)


@router.get('/ubicaciones-ganaderas', response_model=Pagina[UbicacionOut])
def listar_ubicaciones_ganaderas(negocio_id: UUID, actor: Actor, db: DB, query: Annotated[FiltrosCatalogo, Query()]):
    return listado(db, actor, negocio_id, 'ubicaciones_ganaderas', query)


@router.post('/ubicaciones-ganaderas', status_code=201, response_model=UbicacionOut)
def crear_ubicacion(negocio_id: UUID, data: UbicacionCrear, actor: Actor, db: DB):
    return guardar(db, actor, negocio_id, 'ubicaciones_ganaderas', data)


@router.get('/ubicaciones-ganaderas/{registro_id}', response_model=UbicacionOut)
def obtener_ubicacion(negocio_id: UUID, registro_id: UUID, actor: Actor, db: DB):
    return consultar(db, actor, negocio_id, 'ubicaciones_ganaderas', registro_id=registro_id)


@router.patch('/ubicaciones-ganaderas/{registro_id}', response_model=UbicacionOut)
def corregir_ubicacion(negocio_id: UUID, registro_id: UUID, data: UbicacionActualizar, actor: Actor, db: DB):
    return guardar(db, actor, negocio_id, 'ubicaciones_ganaderas', data, registro_id)

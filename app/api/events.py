from typing import Annotated
from uuid import UUID
from fastapi import APIRouter,Depends,Query,HTTPException,Response
from supabase import Client
from app.core.security import Identity,get_identity
from app.core.permissions import require_role
from app.db.client import admin_client
from app.schemas.events import EventInput,CancelInput,EventQuery
from app.services.rpc import ejecutar_rpc
router=APIRouter(prefix='/negocios/{negocio_id}',tags=['Eventos de ganado'])
def call(db,actor,name,negocio_id,**kw):
 require_role(actor,'superadministrador','usuario')
 return ejecutar_rpc(db,name,{'p_actor':str(actor.id),'p_negocio':str(negocio_id),**kw},migracion='16')
@router.get('/eventos')
def listing(negocio_id:UUID,query:Annotated[EventQuery,Query()],response:Response,actor:Identity=Depends(get_identity),db:Client=Depends(admin_client)):
 response.headers['Cache-Control']='no-store'
 return call(db,actor,'sarm_listar_eventos',negocio_id,p_animal=str(query.animal_id) if query.animal_id else None,p_tipo=query.tipo,p_desde=query.desde.isoformat() if query.desde else None,p_hasta=query.hasta.isoformat() if query.hasta else None,p_pagina=query.pagina,p_tamano=query.tamano_pagina,p_anulados=query.incluir_anulados)
@router.post('/animales/{animal_id}/eventos',status_code=201)
def create(negocio_id:UUID,animal_id:UUID,body:EventInput,actor:Identity=Depends(get_identity),db:Client=Depends(admin_client)):
 if body.version is not None or body.motivo is not None:raise HTTPException(422,'Version y motivo solo al corregir')
 return save(db,actor,negocio_id,animal_id,body)
@router.patch('/animales/{animal_id}/eventos/{evento_id}')
def correct(negocio_id:UUID,animal_id:UUID,evento_id:UUID,body:EventInput,actor:Identity=Depends(get_identity),db:Client=Depends(admin_client)):
 if body.version is None or not body.motivo:raise HTTPException(422,'Indique version y motivo')
 return save(db,actor,negocio_id,animal_id,body,evento_id)
def save(db,actor,negocio,animal,body,id=None):
 return call(db,actor,'sarm_guardar_evento',negocio,p_animal=str(animal),p_tipo=body.tipo,p_fecha=body.fecha.isoformat(),p_datos=body.datos,p_observaciones=body.observaciones,p_id=str(id) if id else None,p_version=body.version,p_motivo=body.motivo)
@router.post('/eventos/{evento_id}/anular')
def cancel(negocio_id:UUID,evento_id:UUID,body:CancelInput,actor:Identity=Depends(get_identity),db:Client=Depends(admin_client)):
 return call(db,actor,'sarm_anular_evento',negocio_id,p_id=str(evento_id),p_version=body.version,p_motivo=body.motivo)

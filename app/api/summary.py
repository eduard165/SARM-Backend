from typing import Annotated
from fastapi import APIRouter, Depends, Query, Response
from supabase import Client
from app.core.security import Identity, get_identity
from app.db.client import admin_client
from app.schemas.summary import ResumenInicio, ResumenQuery
from app.services.summary import resumen_inicio

router = APIRouter(prefix='/inicio', tags=['Inicio y reportes'])


@router.get('/resumen', response_model=ResumenInicio)
def consultar_resumen(response: Response, query: Annotated[ResumenQuery, Query()],
                      actor: Identity = Depends(get_identity), db: Client = Depends(admin_client)):
    response.headers['Cache-Control'] = 'no-store'
    return resumen_inicio(db, actor, query.negocio_id)

import time
from typing import Annotated,Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query,Response,HTTPException
from fastapi.responses import JSONResponse
from supabase import Client
from app.core.security import Identity,get_identity
from app.core.permissions import require_role
from app.db.client import admin_client
from app.schemas.events import ReportQuery
from app.services.rpc import ejecutar_rpc
from app.services.summary import resumen_inicio
from app.services.report_files import excel,pdf,administrative
router=APIRouter(tags=['Reportes Excel y PDF'])
def download(r,formato):
 if len(r['filas'])!=r['total']:raise HTTPException(422,'El reporte supera el limite de descarga; acota los filtros')
 blob=excel(r) if formato=='xlsx' else pdf(r)
 if len(blob)>3500000:raise HTTPException(413,'Archivo demasiado grande; acota los filtros')
 mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if formato=='xlsx' else 'application/pdf'
 return Response(blob,media_type=mime,headers={'Content-Disposition':f'attachment; filename="SARM-{r["reporte"]}.{formato}"','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
@router.get('/negocios/{negocio_id}/reportes')
def report(negocio_id:UUID,query:Annotated[ReportQuery,Query()],actor:Identity=Depends(get_identity),db:Client=Depends(admin_client)):
 require_role(actor,'superadministrador','usuario');start=time.perf_counter()
 limit=100 if query.formato=='json' else 500 if query.formato=='pdf' else 2000
 r=ejecutar_rpc(db,'sarm_reporte_ganado',{'p_actor':str(actor.id),'p_negocio':str(negocio_id),'p_reporte':query.reporte,'p_desde':query.desde.isoformat() if query.desde else None,'p_hasta':query.hasta.isoformat() if query.hasta else None,'p_animal':str(query.animal_id) if query.animal_id else None,'p_hato':str(query.hato_id) if query.hato_id else None,'p_ubicacion':str(query.ubicacion_id) if query.ubicacion_id else None,'p_limite':limit},migracion='17')
 if not isinstance(r,dict) or not isinstance(r.get('filas'),list):raise HTTPException(502,'Reporte invalido')
 if query.formato!='json':return download(r,query.formato)
 return JSONResponse(r,headers={'Cache-Control':'no-store','Server-Timing':f'reporte;dur={(time.perf_counter()-start)*1000:.1f}'})
@router.get('/inicio/exportar')
def export_home(formato:Literal['xlsx','pdf'],actor:Identity=Depends(get_identity),db:Client=Depends(admin_client)):
 require_role(actor,'superadministrador','administrador')
 return download(administrative(resumen_inicio(db,actor,None).model_dump(mode='json')),formato)

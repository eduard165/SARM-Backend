from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from app.main import app
from app.core.security import Identity,get_identity
from app.db.client import admin_client
from app.schemas.events import CATALOG
from app.services.report_files import excel,pdf
BIZ='00000000-0000-4000-8000-000000000010';ANIMAL='00000000-0000-4000-8000-000000000100'
ACTOR=Identity(UUID('00000000-0000-4000-8000-000000000003'),'usuario','prueba')
R={'reporte':'parto','generado_en':'2026-10-30T12:00:00Z','negocio':{'nombre':'Rancho prueba'},'filtros':{},'total':1,'filas':[{'id':ANIMAL,'fecha':'2026-03-01','identificacion':'=SUM(1)','nombre':'Luna & <Rey>','sexo':'hembra','hato':'Grupo A','ubicacion':'Corral A','grupo':'simple','datos':{'crias':[{'identificacion':'C1','sexo':'hembra','resultado':'viva'}]}}],'grupos':[{'grupo':'simple','total':1}],'meses':[{'mes':'2026-03','total':1}],'leche_por_modalidad':[],'distribuciones':{},'crias':1,'animal':None}
@pytest.fixture
def api():
 db=Mock();db.rpc.return_value.execute.return_value=SimpleNamespace(data=R)
 app.dependency_overrides[get_identity]=lambda:ACTOR;app.dependency_overrides[admin_client]=lambda:db
 with TestClient(app) as c:yield c,db
 app.dependency_overrides.clear()
def test_create(api):
 c,db=api;r=c.post(f'/negocios/{BIZ}/animales/{ANIMAL}/eventos',json={'tipo':'peso','fecha':'2026-01-01','datos':{'peso_kg':150,'etapa':'adulto'}});assert r.status_code==201;assert db.rpc.call_args.args[1]['p_actor']==str(ACTOR.id)
@pytest.mark.parametrize('data',[{'peso_kg':-1,'etapa':'adulto'},{'peso_kg':'150','etapa':'adulto'},{'peso_kg':True,'etapa':'adulto'},{'peso_kg':1,'etapa':'incorrecto'},{'peso_kg':1,'etapa':'adulto','x':1}])
def test_invalid(api,data):
 c,db=api;assert c.post(f'/negocios/{BIZ}/animales/{ANIMAL}/eventos',json={'tipo':'peso','fecha':'2026-01-01','datos':data}).status_code==422;db.rpc.assert_not_called()
def test_correction_requires_reason(api):
 c,db=api;assert c.patch(f'/negocios/{BIZ}/animales/{ANIMAL}/eventos/{ANIMAL}',json={'tipo':'peso','fecha':'2026-01-01','datos':{'peso_kg':1,'etapa':'adulto'}}).status_code==422
@pytest.mark.parametrize('format,magic',[('xlsx',b'PK'),('pdf',b'%P')])
def test_download(api,format,magic):
 c,db=api;r=c.get(f'/negocios/{BIZ}/reportes?reporte=parto&formato={format}');assert r.status_code==200;assert r.content[:2]==magic;assert 'attachment' in r.headers['content-disposition'];assert 'no-store' in r.headers['cache-control']
@pytest.mark.parametrize('query',['formato=csv','reporte=ficha','desde=2026-02-01&hasta=2026-01-01','actor_id='+ANIMAL,'reporte=inventado'])
def test_bad_query(api,query):
 c,db=api;assert c.get(f'/negocios/{BIZ}/reportes?{query}').status_code==422
@pytest.mark.parametrize('role',['administrador','otro'])
def test_forbidden_role(api,role):
 c,db=api;app.dependency_overrides[get_identity]=lambda:Identity(ACTOR.id,role,'test');assert c.get(f'/negocios/{BIZ}/reportes').status_code==403;db.rpc.assert_not_called()
def test_incomplete_download_denied(api):
 c,db=api;db.rpc.return_value.execute.return_value.data={**R,'total':501};assert c.get(f'/negocios/{BIZ}/reportes?formato=pdf').status_code==422
def test_excel_formula_and_charts():
 wb=load_workbook(BytesIO(excel(R)));assert wb['Detalle']['B2'].value=='=SUM(1)';assert wb['Detalle']['B2'].data_type=='s';assert wb['Detalle'].tables;assert wb['Por mes']._charts

def test_pdf_escaped():assert pdf(R).startswith(b'%PDF')
def test_two_identity_calls():
 db=Mock();auth=Mock();auth.auth.get_user.return_value.user=SimpleNamespace(id=str(ACTOR.id));db.rpc.return_value.execute.return_value.data={'id':str(ACTOR.id),'rol':'usuario','nombre_usuario':'test','negocios':[]};assert get_identity('test',auth,db).id==ACTOR.id;db.table.assert_not_called();db.rpc.assert_called_once_with('sarm_perfil_acceso',{'p_usuario':str(ACTOR.id)});auth.auth.get_user.assert_called_once_with('test')
def test_subject_mismatch():
 db=Mock();auth=Mock();auth.auth.get_user.return_value.user=SimpleNamespace(id=str(ACTOR.id));db.rpc.return_value.execute.return_value.data={'id':ANIMAL,'rol':'usuario','nombre_usuario':'test'}
 with pytest.raises(HTTPException) as e:get_identity('test',auth,db)
 assert e.value.status_code==502
@pytest.mark.parametrize('kind',list(CATALOG))
def test_catalog(kind):assert CATALOG[kind]['fields']

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import Identity, get_identity
from app.db.client import admin_client

ACTOR = Identity(UUID(int=1), 'usuario', 'operador')
BUSINESS, ANIMAL, SPECIES, HATO, LUGAR = [str(UUID(int=i)) for i in (10, 20, 30, 40, 50)]
BASE=f'/negocios/{BUSINESS}'
NOW='2026-10-29T00:00:00Z'
RECORD={'id': ANIMAL,'negocio_id':BUSINESS,'especie_id':SPECIES,'identificacion':'0001','sexo':'hembra',
 'fecha_nacimiento':'2020-01-01','fecha_incorporacion':'2026-01-01','tipo_incorporacion':'compra','nacimiento_estimado':False,
 'estado_registro':'activo','creado_por':str(ACTOR.id),'creado_en':NOW,'actualizado_en':NOW}
EMPTY={'items':[],'total':0,'pagina':1,'tamano_pagina':20,'total_paginas':0}
PAYLOAD={k:RECORD[k] for k in ('especie_id','identificacion','sexo','fecha_nacimiento','fecha_incorporacion','tipo_incorporacion')}
CAT={'id':HATO,'negocio_id':BUSINESS,'nombre':'Produccion','descripcion':None,'estado_registro':'activo','creado_por':str(ACTOR.id),'creado_en':NOW,'actualizado_en':NOW}


@pytest.fixture
def api():
    db=Mock(); db.rpc.return_value.execute.return_value=SimpleNamespace(data=EMPTY)
    app.dependency_overrides[admin_client]=lambda:db
    app.dependency_overrides[get_identity]=lambda:ACTOR
    with TestClient(app) as c: yield c,db
    app.dependency_overrides.clear()


def test_create_animal_verified_identity(api):
    c,db=api;db.rpc.return_value.execute.return_value.data={**RECORD,'password':'secret'}
    r=c.post(BASE+'/animales',json=PAYLOAD)
    assert r.status_code==201
    assert 'password' not in r.json()
    assert db.rpc.call_args.args==('sarm_guardar_animal',{'p_actor':str(ACTOR.id),'p_negocio':BUSINESS,'p_datos':PAYLOAD,'p_id':None,'p_motivo':None})


def test_list_filters_are_structured(api):
    c,db=api
    r=c.get(BASE+'/animales',params={'q':" O'Brien_% ",'sexo':'hembra','hato_id':HATO,'pagina':2,'tamano_pagina':50})
    assert r.status_code==200
    p=db.rpc.call_args.args[1]
    assert p['p_filtros']=={'q':"O'Brien_%",'sexo':'hembra','hato_id':HATO}
    assert p['p_pagina']==2 and p['p_tamano']==50


@pytest.mark.parametrize('query',[{'pagina':0},{'tamano_pagina':101},{'sexo':'otro'},{'hato_id':'invalid'},{'q':'a'*101},{'p_actor':ANIMAL},{'estado_registro':'archivado'}])
def test_bad_filters_not_sent(api,query):
    c,db=api;assert c.get(BASE+'/animales',params=query).status_code==422;db.rpc.assert_not_called()


@pytest.mark.parametrize('extra',[{'negocio_id':BUSINESS},{'p_actor':ANIMAL},{'estado_registro':'baja'},{'hato_id':HATO},{'especie_id':'not-uuid'}, {'sexo':'otro'}, {'fecha_nacimiento':'2099-01-01'}, {'fecha_nacimiento':None}, {'padre_id':ANIMAL,'padre_externo_identificacion':'x'}, {'nacimiento_estimado':'false'}])
def test_invalid_creation_not_sent(api,extra):
    c,db=api;assert c.post(BASE+'/animales',json={**PAYLOAD,**extra}).status_code==422;db.rpc.assert_not_called()


def test_patch_sends_only_explicit_fields_including_null(api):
    c,db=api;db.rpc.return_value.execute.return_value.data=RECORD
    assert c.patch(BASE+f'/animales/{ANIMAL}',json={'nombre':None,'motivo':'Corregir nombre'}).status_code==200
    p=db.rpc.call_args.args[1]
    assert p['p_datos']=={'nombre':None}
    assert p['p_motivo']=='Corregir nombre' and p['p_id']==ANIMAL


@pytest.mark.parametrize('data',[{'nombre':'x'},{'motivo':'x'},{'motivo':'x','sexo':None},{'motivo':'x','especie_id':SPECIES}])
def test_invalid_patch(api,data):
    c,db=api;assert c.patch(BASE+f'/animales/{ANIMAL}',json=data).status_code==422;db.rpc.assert_not_called()


@pytest.mark.parametrize('method,path,body',[('get','/animales',None),('post','/animales',PAYLOAD),('post','/hatos',{'nombre':'Hato'}),('patch',f'/animales/{ANIMAL}',{'nombre':'x','motivo':'x'})])
def test_admin_has_no_operations(api,method,path,body):
    c,db=api;app.dependency_overrides[get_identity]=lambda:Identity(UUID(int=2),'administrador','admin')
    assert c.request(method,BASE+path,json=body).status_code==403
    db.rpc.assert_not_called()


def test_superadmin_can_operate(api):
    c,db=api;app.dependency_overrides[get_identity]=lambda:Identity(UUID(int=2),'superadministrador','super')
    assert c.get(BASE+'/animales').status_code==200
    assert db.rpc.call_args.args[1]['p_actor']==str(UUID(int=2))


@pytest.mark.parametrize('path,resource',[('/hatos','hatos'),('/ubicaciones-ganaderas','ubicaciones_ganaderas'),('/especies-animales','especies_animales'),('/categorias-animales','categorias_animales')])
def test_catalog_list_routes(api,path,resource):
    c,db=api;assert c.get(BASE+path).status_code==200
    assert db.rpc.call_args.args[1]['p_recurso']==resource


@pytest.mark.parametrize('path,resource,data', [('/hatos','hatos',{'nombre':'Grupo 1'}),('/ubicaciones-ganaderas','ubicaciones_ganaderas',{'nombre':'Potrero 1','tipo':'potrero'})])
def test_catalog_creation(api,path,resource,data):
    c,db=api;db.rpc.return_value.execute.return_value.data={**CAT,'tipo':'potrero'}
    assert c.post(BASE+path,json=data).status_code==201
    assert db.rpc.call_args.args[1]['p_recurso']==resource
    assert db.rpc.call_args.args[1]['p_datos']==data


@pytest.mark.parametrize('path',[f'/hatos/{HATO}',f'/ubicaciones-ganaderas/{LUGAR}'])
def test_catalog_archive(api,path):
    c,db=api;db.rpc.return_value.execute.return_value.data={**CAT,'tipo':'potrero','estado_registro':'archivado'}
    assert c.patch(BASE+path,json={'estado_registro':'archivado','motivo':'Grupo cerrado'}).status_code==200
    assert db.rpc.call_args.args[1]['p_datos']=={'estado_registro':'archivado'}


def test_move_requires_both_destinations(api):
    c,db=api
    assert c.post(BASE+f'/animales/{ANIMAL}/movimientos',json={'fecha':'2026-02-01','hato_id':HATO,'motivo':'Cambio'}).status_code==422
    db.rpc.assert_not_called()


def test_move_explicit_null_unassigns(api):
    c,db=api;db.rpc.return_value.execute.return_value.data={'id':HATO,'negocio_id':BUSINESS,'animal_id':ANIMAL,'fecha':'2026-02-01','motivo':'Cambio','registrado_por':str(ACTOR.id),'creado_en':NOW}
    assert c.post(BASE+f'/animales/{ANIMAL}/movimientos',json={'fecha':'2026-02-01','hato_id':None,'ubicacion_ganadera_id':None,'motivo':'Cambio'}).status_code==201
    p=db.rpc.call_args.args[1]; assert p['p_hato'] is None and p['p_ubicacion'] is None
    assert p['p_animal']==ANIMAL


@pytest.mark.parametrize('suffix,resource',[('movimientos','movimientos_animales'),('bajas','bajas_animales')])
def test_history_checks_animal_and_scope(api,suffix,resource):
    c,db=api;db.rpc.return_value.execute.side_effect=[SimpleNamespace(data=RECORD),SimpleNamespace(data=EMPTY)]
    assert c.get(BASE+f'/animales/{ANIMAL}/{suffix}').status_code==200
    first,last=db.rpc.call_args_list
    assert first.args[1]['p_id']==ANIMAL
    assert last.args[1]['p_filtros']=={'animal_id':ANIMAL}
    assert last.args[1]['p_recurso']==resource


def test_baja_and_undo(api):
    c,db=api;db.rpc.return_value.execute.return_value.data={'id':HATO,'negocio_id':BUSINESS,'animal_id':ANIMAL,'fecha':'2026-02-01','motivo':'venta','registrado_por':str(ACTOR.id),'creado_en':NOW}
    assert c.post(BASE+f'/animales/{ANIMAL}/bajas',json={'fecha':'2026-02-01','motivo':'venta'}).status_code==201
    assert db.rpc.call_args.args[0]=='sarm_registrar_baja_animal'
    db.rpc.return_value.execute.return_value.data=RECORD
    assert c.post(BASE+f'/bajas-animales/{HATO}/anular',json={'motivo':'Error de captura'}).status_code==200
    assert db.rpc.call_args.args[1]['p_baja']==HATO


class DbError(Exception):
    def __init__(self,code):
        self.code=code
        super().__init__('INTERNAL_SQL_SECRET')


@pytest.mark.parametrize('code,status',[('42501',403),('P0002',404),('23505',409),('23503',422),('23514',422),('22P02',422),('22001',422),('PGRST202',503),('42883',503),('42P01',503),('40P01',409),('other',502)])
def test_database_failures_safe(api,code,status):
    c,db=api;db.rpc.return_value.execute.side_effect=DbError(code)
    r=c.get(BASE+'/animales');assert r.status_code==status;assert 'INTERNAL_SQL_SECRET' not in r.text


def test_missing_token_and_no_delete_routes():
    with TestClient(app) as c:
        assert c.get(BASE+'/animales').status_code==401
    paths=app.openapi()['paths']
    assert 'delete' not in paths['/negocios/{negocio_id}/animales/{animal_id}']
    assert 'patch' in paths['/usuarios/{usuario_id}/estado']

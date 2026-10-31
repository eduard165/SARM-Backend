from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import Identity, get_identity
from app.db.client import admin_client

BIZ=str(UUID(int=10))
ACTORS={role:Identity(UUID(int=i+1),role,role) for i,role in enumerate(('superadministrador','administrador','usuario'))}
TIME='2026-10-29T00:00:00Z'
COUNTS={'total':0,'activos':0,'suspendidos':0}
GLOBAL={'tipo':'superadministrador','actualizado_en':TIME,'negocio':None,'negocios':COUNTS,'usuarios':{**COUNTS,'superadministradores':0,'administradores':0,'operativos':0}}
ADMIN={'tipo':'administrador','actualizado_en':TIME,'negocio':{'id':BIZ,'nombre':'Rancho A'},'usuarios':COUNTS}
OPERATIVE={'tipo':'usuario','actualizado_en':TIME,'negocio':{'id':BIZ,'nombre':'Rancho A'},'inventario':{key:0 for key in ('total','activos','bajas','hembras_activas','machos_activos','sin_categoria','sin_hato','sin_ubicacion')},'categorias':[],'hatos':[],'ubicaciones':[],'recientes':[]}


@pytest.fixture
def api():
    db=Mock();db.rpc.return_value.execute.return_value=SimpleNamespace(data=GLOBAL)
    app.dependency_overrides[admin_client]=lambda:db
    app.dependency_overrides[get_identity]=lambda:ACTORS['superadministrador']
    with TestClient(app) as c:yield c,db
    app.dependency_overrides.clear()


def test_global_verified_actor(api):
    c,db=api;r=c.get('/inicio/resumen');assert r.status_code==200
    assert 'no-store' in r.headers['cache-control']
    assert db.rpc.call_args.args==('sarm_resumen_inicio',{'p_actor':str(ACTORS['superadministrador'].id),'p_negocio':None})


@pytest.mark.parametrize('role,result',[('administrador',ADMIN),('usuario',OPERATIVE)])
def test_role_response(api,role,result):
    c,db=api;app.dependency_overrides[get_identity]=lambda:ACTORS[role]
    db.rpc.return_value.execute.return_value.data=result
    r=c.get('/inicio/resumen',params={'negocio_id':BIZ});assert r.status_code==200
    assert r.json()['tipo']==role
    assert 'negocios' not in r.json()
    if role=='administrador':assert 'inventario' not in r.json()


def test_admin_scope_inferred_in_sql(api):
    c,db=api;app.dependency_overrides[get_identity]=lambda:ACTORS['administrador'];db.rpc.return_value.execute.return_value.data=ADMIN
    assert c.get('/inicio/resumen').status_code==200
    assert db.rpc.call_args.args[1]['p_negocio'] is None


def test_operative_needs_business(api):
    c,db=api;app.dependency_overrides[get_identity]=lambda:ACTORS['usuario']
    assert c.get('/inicio/resumen').status_code==422;db.rpc.assert_not_called()


def test_global_cannot_pass_ignored_scope(api):
    c,db=api;assert c.get('/inicio/resumen',params={'negocio_id':BIZ}).status_code==422;db.rpc.assert_not_called()


@pytest.mark.parametrize('query',[{'negocio_id':'mal'},{'actor':BIZ},{'rol':'usuario'},{'pagina':1}])
def test_unknown_or_bad_query(api,query):
    c,db=api;assert c.get('/inicio/resumen',params=query).status_code==422;db.rpc.assert_not_called()


@pytest.mark.parametrize('data',[ADMIN,None,{}, {'tipo':'superadministrador'}, {**GLOBAL,'usuarios':{**GLOBAL['usuarios'],'total':-1}}])
def test_wrong_or_malformed_response_fails_safely(api,data):
    c,db=api;db.rpc.return_value.execute.return_value.data=data
    r=c.get('/inicio/resumen');assert r.status_code==502
    assert 'ValidationError' not in r.text


def test_response_drops_unexpected_secrets(api):
    c,db=api;db.rpc.return_value.execute.return_value.data={**GLOBAL,'password':'private','access_token':'private'}
    assert c.get('/inicio/resumen').json()==GLOBAL


class DbError(Exception):
    def __init__(self,code):
        self.code=code
        super().__init__('INTERNAL_DB_SECRET')


@pytest.mark.parametrize('code,status',[('42501',403),('22023',422),('PGRST202',503),('42883',503),('other',502)])
def test_db_errors_safe(api,code,status):
    c,db=api;db.rpc.return_value.execute.side_effect=DbError(code)
    r=c.get('/inicio/resumen');assert r.status_code==status;assert 'INTERNAL_DB_SECRET' not in r.text


def test_no_token():
    with TestClient(app) as c:assert c.get('/inicio/resumen').status_code==401


def test_existing_routes_preserved():
    p=app.openapi()['paths'];assert 'patch' in p['/usuarios/{usuario_id}/estado'];assert 'post' in p['/negocios/{negocio_id}/animales'];assert 'get' in p['/usuarios']

import json
from pathlib import Path
from datetime import date
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,create_model,model_validator
CATALOG=json.loads(Path(__file__).with_name('event_catalog.json').read_text())
REPORT_NAMES={'inventario':'Inventario de animales','ficha':'Ficha individual','movimientos':'Movimientos','incorporaciones':'Incorporaciones','bajas':'Bajas, muertes y ventas',**{k:v['label'] for k,v in CATALOG.items()}}
class Strict(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True,allow_inf_nan=False)
class Cria(Strict):
 identificacion:str=Field(min_length=1,max_length=150)
 sexo:Literal['macho','hembra','sin_determinar']
 resultado:Literal['viva','muerta']
 animal_id:UUID|None=None
 peso_kg:float|None=Field(default=None,gt=0,le=3000,strict=True)
PAYLOADS={}
for kind,spec in CATALOG.items():
 fields={}
 for f in spec['fields']:
  t=f['type'];typ={'text':str,'uuid':UUID,'date':date,'number':float,'crias':list[Cria]}.get(t)
  if t=='select':typ=Literal[tuple(f['options'])]
  opts={'min_length':1,'max_length':1000} if t=='text' else {'ge':f['min'],'le':f['max'],'strict':True} if t=='number' else {'min_length':1,'max_length':8} if t=='crias' else {}
  fields[f['key']]=(typ if f['required'] else typ|None,Field(... if f['required'] else None,**opts))
 PAYLOADS[kind]=create_model(kind.title()+'Datos',__base__=Strict,**fields)
class EventInput(Strict):
 tipo:Literal[tuple(CATALOG)]
 fecha:date
 datos:dict
 observaciones:str|None=Field(default=None,max_length=4000)
 version:int|None=Field(default=None,ge=1)
 motivo:str|None=Field(default=None,min_length=1,max_length=1000)
 @model_validator(mode='after')
 def validate_data(self):
  self.datos=PAYLOADS[self.tipo].model_validate(self.datos).model_dump(mode='json',exclude_none=True)
  if self.fecha>date.today():raise ValueError('No se admiten eventos futuros')
  return self
class CancelInput(Strict):
 version:int=Field(ge=1)
 motivo:str=Field(min_length=1,max_length=1000)
class Period(Strict):
 desde:date|None=None
 hasta:date|None=None
 animal_id:UUID|None=None
 @model_validator(mode='after')
 def dates(self):
  if self.desde and self.hasta and self.desde>self.hasta:raise ValueError('Periodo invertido')
  return self
class EventQuery(Period):
 tipo:Literal[tuple(CATALOG)]|None=None
 pagina:int=Field(default=1,ge=1,le=1000000)
 tamano_pagina:int=Field(default=20,ge=1,le=100)
 incluir_anulados:bool=False
class ReportQuery(Period):
 reporte:Literal[tuple(REPORT_NAMES)]='inventario'
 hato_id:UUID|None=None
 ubicacion_id:UUID|None=None
 formato:Literal['json','xlsx','pdf']='json'
 @model_validator(mode='after')
 def animal_required(self):
  if self.reporte=='ficha' and not self.animal_id:raise ValueError('Seleccione animal para su ficha')
  return self

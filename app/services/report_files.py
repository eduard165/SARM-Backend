"""Archivos descriptivos. No calcula indicadores productivos sin validar."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,LongTable,TableStyle,PageBreak,KeepTogether
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill,Alignment
from openpyxl.chart import BarChart,Reference
from openpyxl.worksheet.table import Table,TableStyleInfo
from app.schemas.events import CATALOG,REPORT_NAMES
fonts=Path(reportlab.__file__).parent/'fonts'
pdfmetrics.registerFont(TTFont('Sarm',str(fonts/'Vera.ttf')));pdfmetrics.registerFont(TTFont('SarmBold',str(fonts/'VeraBd.ttf')))
pdfmetrics.registerFontFamily('Sarm',normal='Sarm',bold='SarmBold',italic='Sarm',boldItalic='SarmBold')
LABELS={'desde':'Desde','hasta':'Hasta','animal':'Animal','hato_actual':'Hato actual','ubicacion_actual':'Ubicación actual','fecha':'Fecha','identificacion':'Identificación','nombre':'Nombre','sexo':'Sexo','hato':'Hato actual','ubicacion':'Ubicación actual','grupo':'Registro / estado','motivo':'Motivo','observaciones':'Observaciones','categoria':'Categoría','fecha_nacimiento':'Nacimiento','nacimiento_estimado':'Nacimiento estimado','tipo_racial':'Raza o tipo racial','padre':'Padre','madre':'Madre','servicio_fecha':'Fecha de servicio','parto_fecha':'Fecha de parto','lactancia_fecha':'Inicio de lactancia','baja_fecha':'Fecha de venta','toro':'Toro registrado'}
for spec in CATALOG.values():
 for f in spec['fields']:LABELS.setdefault(f['key'],f['label'])
NOTES='Registros vigentes, sin eventos anulados. Hato y ubicación corresponden a la asignación actual. El periodo filtra la fecha del evento; en inventario filtra la incorporación. Sin registros no equivale a producción cero. Indicadores productivos pendientes de validación con el médico.'
def plain(v):
 if v is None:return ''
 if isinstance(v,bool):return 'Sí' if v else 'No'
 if isinstance(v,list):return '\n'.join(plain(x) for x in v)
 if isinstance(v,dict):return '; '.join(str(k).replace('_',' ')+': '+str(plain(x)) for k,x in v.items())
 return v
def flatten(report):
 rows=[{**{k:plain(x.get(k)) for k in ['fecha','identificacion','nombre','sexo','hato','ubicacion','grupo']},**{k:plain(v) for k,v in x['datos'].items()}} for x in report['filas']]
 return list(dict.fromkeys(k for row in rows for k in row)),rows
def administrative(summary):
 rows=[]
 for section in ['negocios','usuarios']:
  if isinstance(summary.get(section),dict):
   for name,total in summary[section].items():rows.append({'fecha':summary['actualizado_en'][:10],'identificacion':section,'nombre':name,'grupo':section,'datos':{'total':total}})
 return dict(reporte='administrativo',generado_en=summary['actualizado_en'],negocio=summary.get('negocio') or {'nombre':'SARM - resumen global'},filtros={},total=len(rows),filas=rows,grupos=[],meses=[],leche_por_modalidad=[],distribuciones={},animal=None)
def title(r):return REPORT_NAMES.get(r['reporte'],'Resumen administrativo')
def excel(r):
 wb=Workbook();ws=wb.active;ws.title='Resumen'
 for row in [['SARM | '+title(r)],['Rancho / alcance',r['negocio']['nombre']],['Generado',r['generado_en']],['Registros',r['total']],['Criterios',NOTES]]:ws.append(row)
 ws.column_dimensions['A'].width=30;ws.column_dimensions['B'].width=95;ws['A1'].font=Font(size=17,bold=True,color='173B2F');ws.row_dimensions[5].height=80
 for k,v in r.get('filtros',{}).items():ws.append([LABELS.get(k,k),plain(v)])
 if r.get('crias') is not None:ws.append(['Crías registradas',r['crias']])
 if r.get('animal'):
  sheet=wb.create_sheet('Ficha');sheet.append(['Campo','Valor'])
  for k,v in r['animal'].items():sheet.append([LABELS.get(k,k),plain(v)])
  sheet.column_dimensions['A'].width=28;sheet.column_dimensions['B'].width=80
 keys,rows=flatten(r);detail=wb.create_sheet('Detalle');detail.append([LABELS.get(k,k) for k in keys] or ['Sin registros'])
 for row in rows:detail.append([row.get(k,'') for k in keys])
 detail.freeze_panes='C2'
 if rows:
  table=Table(displayName='Registros',ref=detail.dimensions);table.tableStyleInfo=TableStyleInfo(name='TableStyleMedium4',showRowStripes=True);detail.add_table(table)
 for col in detail.columns:detail.column_dimensions[col[0].column_letter].width=min(50,max(16,len(str(col[0].value))+3))
 def graph_sheet(name,headers,values,chart_title):
  sheet=wb.create_sheet(name);sheet.append(headers)
  for row in values:sheet.append(row)
  sheet.column_dimensions['A'].width=30
  if values:
   chart=BarChart();chart.title=chart_title;chart.add_data(Reference(sheet,min_col=2,min_row=1,max_row=sheet.max_row),titles_from_data=True);chart.set_categories(Reference(sheet,min_col=1,min_row=2,max_row=sheet.max_row));sheet.add_chart(chart,'E2')
 graph_sheet('Por grupo',['Grupo','Registros'],[[x['grupo'],x['total']] for x in r['grupos']],'Registros por grupo')
 graph_sheet('Por mes',['Mes','Registros'],[[x['mes'],x['total']] for x in r['meses']],'Registros por mes')
 for name,items in r.get('distribuciones',{}).items():graph_sheet('Inventario '+name,['Grupo','Animales'],[[x['nombre'],x['total']] for x in items],'Animales por '+name)
 if r.get('leche_por_modalidad'):graph_sheet('Leche por modalidad',['Modalidad','Litros registrados','Registros'],[[x['modalidad'],x['litros'],x['registros']] for x in r['leche_por_modalidad']],'Litros por modalidad')
 for sheet in wb:
  sheet.freeze_panes=sheet.freeze_panes or 'A2'
  for row in sheet:
   for cell in row:
    if isinstance(cell.value,str):cell.data_type='s' # No ejecutar texto como formula/DDE.
    cell.alignment=Alignment(vertical='top',wrap_text=True)
  if sheet!=ws:
   for cell in sheet[1]:cell.fill=PatternFill('solid',fgColor='173B2F');cell.font=Font(color='FFFFFF',bold=True)
 stream=BytesIO();wb.save(stream);return stream.getvalue()
def pdf(r):
 stream=BytesIO();page=landscape(A4);doc=SimpleDocTemplate(stream,pagesize=page,leftMargin=30,rightMargin=30,topMargin=30,bottomMargin=35,title=title(r),author='SARM');styles=getSampleStyleSheet()
 for style in styles.byName.values():style.fontName='SarmBold' if style.name.startswith('Heading') or style.name=='Title' else 'Sarm'
 styles.add(ParagraphStyle(name='Cell',fontName='Sarm',fontSize=7,leading=10,wordWrap='CJK'));styles.add(ParagraphStyle(name='Fine',fontName='Sarm',fontSize=8,leading=11,textColor=colors.HexColor('#52645b')))
 def p(v,style='Cell'):return Paragraph(escape(str(plain(v))).replace('\n','<br/>'),styles[style])
 story=[p('SARM / '+title(r),'Title'),p(r['negocio']['nombre'],'Heading2'),p('Generado: '+r['generado_en']+' | Registros: '+str(r['total']),'Fine'),Spacer(1,8),p(NOTES,'Fine')]
 for k,v in r.get('filtros',{}).items():
  if v is not None:story.append(p(LABELS.get(k,k)+': '+str(v),'Fine'))
 if r.get('crias') is not None:story.append(p('Crías registradas: '+str(r['crias']),'Heading3'))
 def table(headers,rows,widths):
  if not rows:story.append(p('Sin registros para los filtros seleccionados.'));return
  t=LongTable([[p(x) for x in headers]]+[[p(x) for x in row] for row in rows],colWidths=widths,repeatRows=1,splitInRow=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dfead4')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f6f4')]),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.extend([Spacer(1,8),t,Spacer(1,8)])
 def chart(rows,label,value,heading):
  if not rows:return
  import math
  selected=rows[-12:];d=Drawing(740,145);c=HorizontalBarChart();c.x=160;c.y=20;c.height=105;c.width=525;c.data=[[float(x[value]) for x in selected]];c.categoryAxis.categoryNames=[str(x[label])[:38] for x in selected];c.categoryAxis.labels.fontSize=8;c.categoryAxis.labels.fontName=c.valueAxis.labels.fontName=c.barLabels.fontName='Sarm';c.valueAxis.valueMin=0;c.bars[0].fillColor=colors.HexColor('#315e46');c.barLabelFormat='%g';c.barLabels.fontSize=7
  if value=='total':c.valueAxis.valueStep=max(1,math.ceil(max(x[value] for x in selected)/5))
  d.add(c);story.append(KeepTogether([p(heading+(' (últimos 12)' if len(rows)>12 else ''),'Heading3'),d]))
 chart(r['grupos'],'grupo','total','Registros por grupo');chart(r['meses'],'mes','total','Registros por mes')
 if r.get('leche_por_modalidad'):chart(r['leche_por_modalidad'],'modalidad','litros','Litros registrados por modalidad')
 for name,items in r.get('distribuciones',{}).items():
  story.append(PageBreak());chart(items,'nombre','total','Animales por '+name);table(['Grupo','Animales'],[[x['nombre'],x['total']] for x in items],[550,230])
 if r.get('animal'):
  story.extend([PageBreak(),p('Ficha del animal','Heading2')]);table(['Campo','Valor'],[[LABELS.get(k,k),v] for k,v in r['animal'].items()],[170,doc.width-170])
 keys,rows=flatten(r)
 if rows and r['reporte']=='ficha':
  story.extend([PageBreak(),p('Historial vigente','Heading2')]);table(['Fecha','Registro','Datos'],[[x['fecha'],x['grupo'],'\n'.join(LABELS.get(k,k)+': '+str(plain(v)) for k,v in x['datos'].items() if v is not None)] for x in r['filas']],[80,135,doc.width-215])
 elif rows:
  remaining=[k for k in keys if k not in ['fecha','identificacion']]
  for start in range(0,len(remaining),5):
   band=['fecha','identificacion']+remaining[start:start+5];story.extend([PageBreak(),p('Detalle - sección '+str(start//5+1),'Heading2')]);table([LABELS.get(k,k) for k in band],[[row.get(k,'') for k in band] for row in rows],[doc.width/len(band)]*len(band))
 else:story.extend([Spacer(1,12),p('Sin registros para los filtros seleccionados.')])
 def footer(canvas,document):
  canvas.setFont('Sarm',8);canvas.drawString(30,18,'SARM | '+title(r));canvas.drawRightString(page[0]-30,18,'Página '+str(document.page))
 doc.build(story,onFirstPage=footer,onLaterPages=footer);return stream.getvalue()

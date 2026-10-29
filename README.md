# SARM API 0.5.0 — usuarios y ganado

FastAPI + Supabase. Conserva login, perfiles, altas y listado de usuarios; agrega suspension/reactivacion por negocio y la primera etapa operativa de ganado.

## Actualizar

1. En el proyecto separado **sarm-db**, agrega las migraciones 11, 12 y 13 del paquete de base de datos. Desde su raiz ejecuta `npx supabase db push --linked --dry-run` y despues `npx supabase db push --linked`. Si 11 y 12 ya estan aplicadas, solo debe proponerse la 13. No cambiar ni reaplicar manualmente migraciones anteriores.
2. Copia el backend sobre tu carpeta local, conservando `.env`, `.venv` y `.git`. No se incluye un archivo de entorno ni una carpeta de migraciones en este backend. No se agregan dependencias.
3. Con el entorno virtual activo: `python -m pytest -q` y despues `python -m uvicorn app.main:app --reload` (tambien funciona tu run.bat).
4. Abre http://127.0.0.1:8000/docs, inicia sesion con POST /auth/login y pulsa Authorize para ingresar el access_token como Bearer. Prueba antes de desplegar.

Aplicar SQL **antes de desplegar este backend**: login y peticiones autenticadas dependen ahora de sarm_comprobar_acceso (migracion 13). Si falta la funcion, la API devuelve 503 y no concede acceso. Si Data API tiene una lista de funciones permitidas, incluir las funciones sarm_* nuevas; nunca habilitarlas para anon/authenticated ni enviar la clave service_role al frontend.

## Roles

| Funcion | Superadministrador | Administrador | Usuario operativo |
|---|---|---|---|
| Crear negocios y administradores | Si | No | No |
| Crear/listar usuarios | Todos los negocios | Solo operativos de su negocio | No |
| Suspender/reactivar | Administradores y operativos por negocio | Solo operativos de su negocio | No |
| Ganado | Cualquier negocio activo | No, conserva su rol administrativo anterior | Solo negocios con membresia activa |

El actor se obtiene del JWT verificado contra Supabase Auth, no del cuerpo ni de un parametro de consulta. Las funciones SQL repiten la autorizacion y comprueban permisos/negocio. El usuario bloqueado globalmente no puede operar.

## Suspender y reactivar

```text
PATCH /usuarios/{usuario_id}/estado
```

```json
{
  "negocio_id": "11111111-1111-4111-8111-111111111111",
  "estado": "suspendido",
  "motivo": "Suspension temporal del acceso"
}
```

Para reactivar, usar `estado: "activo"`. El administrador puede omitir negocio_id: se obtiene de su unica membresia activa. Para superadministrador es obligatorio. Motivo obligatorio, 1–1000 caracteres. No se permite cambiar el acceso propio ni de un superadministrador; el administrador tampoco puede gestionar otros administradores. No crea membresias nuevas ni elimina cuentas.

Respuesta:

```json
{
  "usuario_id": "22222222-2222-4222-8222-222222222222",
  "negocio_id": "11111111-1111-4111-8111-111111111111",
  "estado_membresia": "suspendido",
  "cambiado": true
}
```

Repetir el mismo estado devuelve cambiado=false y no duplica auditoria. La transaccion modifica membresia y registra antes/despues, motivo y responsable. Reactivar una membresia no elimina un bloqueo global ni reactiva un negocio suspendido.

Cada peticion autenticada comprueba acceso actual en BD. Si la cuenta ya no tiene ningun negocio con membresia y negocio activos, se responde 403 aun con token vigente. Si conserva otro negocio activo, mantiene la sesion pero no puede operar en el suspendido. Superadministrador puede acceder sin negocio. La comprobacion no revoca tokens en Supabase Auth ni cambia contrasenas. Se evalua en la siguiente peticion; una accion ya en curso puede haber terminado antes de confirmar la suspension.

## Ganado: rutas

Todas llevan el prefijo **/negocios/{negocio_id}**, requieren Bearer y operan solo en ese negocio.

| Metodo | Ruta despues del prefijo | Accion |
|---|---|---|
| GET / POST | /animales | Listar / crear |
| GET / PATCH | /animales/{animal_id} | Consultar / corregir ficha |
| GET / POST | /hatos | Listar / crear grupos |
| GET / PATCH | /hatos/{registro_id} | Consultar / corregir o archivar |
| GET / POST | /ubicaciones-ganaderas | Listar / crear lugares fisicos |
| GET / PATCH | /ubicaciones-ganaderas/{registro_id} | Consultar / corregir o archivar |
| GET | /especies-animales | Especies habilitadas |
| GET | /categorias-animales | Categorias de especies habilitadas |
| GET / POST | /animales/{animal_id}/movimientos | Historial / registrar movimiento |
| GET / POST | /animales/{animal_id}/bajas | Historial / registrar baja |
| POST | /bajas-animales/{baja_id}/anular | Anular baja equivocada |

GET de listados devuelve `{items,total,pagina,tamano_pagina,total_paginas}`. Pagina 1–1000000; tamano_pagina 1–100 (20 por defecto). Filtro q literal por identificacion/nombre en animales, nombre en catalogos, motivo en historiales. Maximo 100 caracteres. Parametros desconocidos se rechazan.

Animales admite sexo (macho/hembra), estado_registro (activo/baja), especie_id, categoria_id, hato_id y ubicacion_ganadera_id. Hatos/ubicaciones admite estado_registro (activo/archivado); categorias admite especie_id. Sin filtro de estado se incluyen todos los estados autorizados. Los historiales de baja incluyen las anuladas.

### Crear animal

Obtener primero el UUID Bovino en GET /negocios/{negocio_id}/especies-animales. POST /negocios/{negocio_id}/animales:

```json
{
  "especie_id": "33333333-3333-4333-8333-333333333333",
  "identificacion": "000123",
  "sexo": "hembra",
  "fecha_nacimiento": "2022-04-10",
  "nacimiento_estimado": false,
  "fecha_incorporacion": "2026-01-15",
  "tipo_incorporacion": "compra",
  "tipo_racial": "Cruza"
}
```

Obligatorios: especie_id, identificacion, sexo, fecha_nacimiento, fecha_incorporacion y tipo_incorporacion (nacimiento/compra/otro). Si es nacimiento, ambas fechas coinciden. No se permiten fechas futuras. Identificacion es texto y conserva ceros; unica por negocio incluso en animales de baja. No se exige ni valida formato oficial SINIIGA.

Opcionales: nombre, categoria_id, nacimiento_estimado, tipo_racial (texto, sin porcentajes), procedencia, padre_id, madre_id, padre_externo_identificacion, padre_externo_raza, madre_externa_identificacion, madre_externa_raza, observaciones. No se obliga a recuperar historial anterior a la captura. Edad se calcula a partir de nacimiento; no se almacena.

Progenitores registrados deben pertenecer al negocio y especie y ser compatibles en sexo y fecha. No se permite padre/madre registrado junto con sus datos externos. Para sustituir un progenitor externo, limpiar sus campos con null en la misma correccion. Especie y negocio no se editan. Categoria opcional y manual, compatible con especie/sexo.

PATCH de animal contiene solo campos a corregir y `motivo`. Omitir campo conserva su valor; null limpia opcionales. Ejemplo: `{"nombre":"Luna","motivo":"Corregir nombre"}`. Campos protegidos/extra se rechazan. Todas las respuestas tienen modelos que descartan claves inesperadas de la base.

### Hatos y lugares

POST hato: `{"nombre":"Vacas de produccion","descripcion":"Grupo de ordeno"}`. POST ubicacion: `{"nombre":"Potrero norte","tipo":"potrero"}`. Tipos: potrero/corral/establo/otro. PATCH con motivo; archivar con `{"estado_registro":"archivado","motivo":"Cerrar grupo"}`. Se impide archivar mientras tenga animales activos.

Un hato es un grupo, no una ubicacion. ubicaciones_ganaderas no sustituye los domicilios de usuarios/negocios. Un animal nuevo queda sin asignacion; su primera asignacion se hace mediante movimiento independiente. Crear y mover son dos peticiones distintas, no una unica transaccion: si el movimiento falla, la ficha creada permanece disponible para asignarla despues.

### Movimiento

POST /animales/{animal_id}/movimientos:

```json
{
  "fecha": "2026-10-29",
  "hato_id": "44444444-4444-4444-8444-444444444444",
  "ubicacion_ganadera_id": null,
  "motivo": "Ingreso al grupo de produccion"
}
```

Ambos destinos se deben enviar: null significa desasignar. Para conservar un destino, enviar su UUID actual. La BD guarda origen/destino y actualiza la ficha atomica y auditadamente. No permite destino ajeno/archivado, animal de baja, fecha futura ni anterior a incorporacion/ultimo movimiento. Se corrige la asignacion con otro movimiento explicado, no editando el historial.

### Baja y anulacion

POST /animales/{animal_id}/bajas: `{"fecha":"2026-10-29","motivo":"venta","observaciones":"Salida del rancho"}`. Motivo: venta/muerte/otro. Conserva expediente, parentescos y movimientos. No permite baja duplicada vigente ni mover un animal de baja.

POST /bajas-animales/{baja_id}/anular: `{"motivo":"Baja capturada por error"}`. Conserva la baja con fecha, usuario y motivo de anulacion, y reactiva la ficha. Si su hato/lugar se archivo, reactivar ese catalogo antes de anular. No es un traslado automatico entre negocios ni un modulo de compraventa.

## Rutas anteriores conservadas

- POST /auth/login; GET /auth/me.
- GET /negocios; POST /negocios.
- POST /administradores; POST /usuarios; GET /usuarios.
- GET /catalogos/estados; GET /catalogos/municipios?estado_id=30.
- GET /health; GET /health/db (version 0.5.0).

GET /usuarios mantiene filtros q, rol, negocio_id, estado (activo/suspendido), pagina y tamano_pagina. Superadministrador ve todos incluido el propio; administrador solo operativos de su negocio, excluyendo su cuenta. El estado es acceso efectivo, que puede incluir bloqueo global o negocio suspendido, no solo estado_membresia.

## Errores

401 token/credenciales invalidos; 403 sin acceso, permiso o negocio activo; 404 registro no encontrado en el alcance; 409 duplicado o conflicto concurrente; 422 datos/filtros/relaciones incompatibles; 503 migracion o funcion faltante; 502 error de comunicacion/operacion inesperado. No se exponen errores SQL ni credenciales. Conflictos concurrentes 409 requieren volver a consultar e intentar la operacion.

## Validacion y limites de entrega

108 pruebas Python con pytest; 98 comprobaciones SQL de migraciones 01–13 en PostgreSQL embebido PGlite; 22 pasos HTTP contra ese SQL, con identidad/Auth simulados. Incluyen permisos, sesiones vigentes tras suspension, reactivacion, doble negocio, auditoria, roles, movimientos, bajas, filtros, errores y regresion de usuarios. No se probo con tus credenciales ni se modifico tu Supabase o despliegue. El paquete de base de datos incluye runners reproducibles de SQL e integracion.

Esta entrega no cambia frontend. Faltan sus botones de estado de usuario y pantallas de ganado. Reproduccion, leche/lactancias, pesajes, sanidad, condicion corporal, indicadores y graficas requieren las siguientes etapas. La base esta preparada para otras especies, pero solo bovinos esta habilitada. No se agregan eliminaciones fisicas, edicion general de perfiles, recuperacion de contrasena o renovacion de sesion.

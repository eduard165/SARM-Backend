# SARM Backend — listado de usuarios

FastAPI + Supabase. Conserva login y altas actuales; agrega `GET /usuarios` con filtros, paginación y control de acceso.

## Actualizar

1. Copia el contenido de esta carpeta sobre tu backend local. Conserva tu `.env`, `.venv` y `.git`. Este ZIP no incluye credenciales ni `.env.example`.
2. Aplica **una sola vez** `database/20261029001000_listado_usuarios.sql` en Supabase SQL Editor. También puedes copiarlo a `sarm-db/supabase/migrations/` y ejecutar `npx supabase db push` desde ese proyecto. No apliques por ambas vías sin registrar la migración en el historial del CLI.
3. Si tu proyecto usa una lista de funciones expuestas en Data API, agrega `sarm_listar_usuarios`, como se hizo con las funciones de creación. Sus permisos de ejecución son solo de `service_role`; no concedas acceso a `anon` o `authenticated`.
4. Prueba localmente con `run.bat` y abre http://127.0.0.1:8000/docs.
5. Sube los cambios a la rama `main` del repositorio para que Vercel despliegue la actualización.

La migración solo crea una función de consulta y sus permisos. No cambia las tablas, cuentas, negocios, membresías ni políticas RLS. Requiere tus migraciones 01–09 ya aplicadas. El propietario que ejecute la migración debe ser el propietario habitual de las migraciones (SQL Editor como postgres).

## GET /usuarios

Requiere `Authorization: Bearer <access_token>`.

| Rol autenticado | Alcance |
|---|---|
| superadministrador | Todas las cuentas, incluida la propia; puede filtrar por negocio. |
| administrador | Solo usuarios operativos de su único negocio activo. No se incluye a sí mismo ni a otros administradores. |
| usuario | 403. |

El administrador no puede ampliar su alcance indicando otro `negocio_id`. La API usa la identidad verificada por Supabase Auth y la función SQL vuelve a comprobar rol, bloqueo y negocio. Para cuentas compartidas preexistentes, el administrador solo recibe la membresía de su negocio, sin datos de los otros negocios.

### Parámetros opcionales

| Parámetro | Valores |
|---|---|
| `q` | Búsqueda literal por nombre o nombre de usuario; hasta 100 caracteres, sin distinguir mayúsculas. |
| `rol` | `superadministrador`, `administrador`, `usuario`. Un administrador solo puede solicitar `usuario`. |
| `negocio_id` | UUID. Para administrador se obtiene automáticamente y no puede apuntar a otro negocio. |
| `estado` | `activo` o `suspendido`. |
| `pagina` | Desde 1; máximo 1000000. Predeterminado 1. |
| `tamano_pagina` | De 1 a 100. Predeterminado 20. |

Ejemplos:

```text
GET /usuarios
GET /usuarios?q=Roberto
GET /usuarios?rol=administrador&pagina=1&tamano_pagina=20
GET /usuarios?rol=usuario&estado=activo
```

Respuesta:

```json
{
  "items": [],
  "total": 0,
  "pagina": 1,
  "tamano_pagina": 20,
  "total_paginas": 0
}
```

Cada elemento incluye `id`, `nombre_usuario`, `nombre`, apellidos, `nombre_completo`, `rol`, `estado`, `bloqueo_global`, `creado_en` y `negocios`. Cada negocio contiene `negocio_id`, `nombre`, `estado_membresia` y `estado_negocio`. No se consultan ni devuelven contraseñas, correos técnicos de Auth, claves o tokens.

`estado` describe el acceso efectivo: un bloqueo global, o la ausencia de una membresía y negocio activos en el alcance consultado, resulta en `suspendido`. El superadministrador sin negocio es `activo` si no tiene bloqueo global. Este filtro no suspende ni reactiva cuentas.

La búsqueda y los filtros se aplican **antes** de contar y paginar. Orden estable: nombre de usuario y UUID. Una página posterior a la última devuelve `items: []` conservando el total.

## Rutas conservadas

- `POST /auth/login`, `GET /auth/me`.
- `GET /negocios`, `POST /negocios`.
- `POST /administradores`, `POST /usuarios`.
- `GET /catalogos/estados`, `GET /catalogos/municipios?estado_id=30`.
- `GET /health`, `GET /health/db`.

No se agregan edición, eliminación, suspensión, recuperación de contraseña, renovación de sesión ni cambios de interfaz en esta entrega. Ocultar el menú al operativo corresponde al siguiente cambio del frontend; la API ya rechaza su acceso al listado.

## Validación

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Resultado local: **30 pruebas Python aprobadas**. Además, la función se validó con **34 comprobaciones SQL en PostgreSQL local mediante PGlite**, incluyendo RLS activado, permisos de ejecución, dos negocios, usuarios compartidos, bloqueos, filtros, paginación y denegaciones. No se usaron las credenciales ni se modificaron los datos de tu Supabase.

Después de aplicar la migración y desplegar, comprueba en Swagger:

1. Superadministrador: `GET /usuarios` incluye `superadmin`, ambos administradores y los operativos existentes.
2. Administrador A: solo operativos del negocio A; el propio administrador no aparece.
3. Administrador A indicando negocio B: 403.
4. Usuario operativo: 403.
5. Sin token: 401.
6. Filtros y paginación: los elementos y `total` corresponden al filtro.

Si devuelve 503, comprueba migración 10 y exposición de la función en Data API. Un 502 requiere revisar los logs del backend; no se exponen detalles internos al cliente.

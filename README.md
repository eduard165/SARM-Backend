# SARM Backend V1 — FastAPI + Supabase SDK

Backend modular de SARM. Conserva RLS y las reglas de las migraciones 01–08. **NO incluye credenciales**.

## Preparación en Windows

1. Extrae este ZIP y respalda tu `.env` existente antes de reemplazar la carpeta.
2. Copia `.env.example` como `.env`, completa los valores reales y **rota cualquier clave secreta compartida anteriormente**.
3. Ejecuta `setup.bat` y `run.bat`.
4. Abre `http://127.0.0.1:8000/docs`. Comprueba `GET /health/db` (32 estados).

## Paso obligatorio de BD: migración 09

**No basta con reemplazar los archivos Python.** Para que la creación de cuentas de administrador sea atómica frente a las restricciones diferidas de migración 07/08, necesitas aplicar la migración nueva:

1. Copia `database/20261012000900_operaciones_transaccionales.sql` al proyecto de migraciones existente `sarm-db/supabase/migrations/`.
2. Desde `sarm-db` ejecuta `npx supabase db push`.
3. En Supabase → Data API habilita las funciones `sarm_crear_cuenta`, `sarm_crear_negocio`, y las tablas necesarias: `usuarios`, `roles`, `usuario_negocios`, `negocios`, `estados`, `municipios` (la primera prueba solo requiere `estados`). Habilitarlas no concede acceso público: **mantén RLS y los permisos existentes**. No expongas otras tablas innecesarias.
4. Las funciones solo tienen permiso de ejecución concedido a `service_role`; el backend valida el token, el rol y el negocio y las funciones vuelven a comprobar los permisos. No expongas jamás `SUPABASE_SECRET_KEY` al frontend.

### Endpoints existentes conservados

- `GET /health`, `GET /health/db` — salud
- `GET /catalogos/estados`, `GET /catalogos/municipios?estado_id=30` — catálogos
- `GET /auth/me` — perfil autenticado
- `GET /negocios` — negocios visibles según rol

### Endpoints nuevos

- `POST /auth/login` — nombre de usuario y contraseña → JWT; requiere cuenta previamente registrada.
- `POST /negocios` — crea negocio y ubicación, solo superadministrador.
- `POST /administradores` — crea administrador y lo vincula obligatoriamente a un negocio activo.
- `POST /usuarios` — crea usuario operativo en un negocio activo. Si llama un administrador, se usa **su** negocio.

Todos los endpoints de creación requieren `Authorization: Bearer <access_token>`. **No hay endpoint para registrar superadministradores.** La identidad de superadministrador se configura manualmente en Supabase Auth y `public.usuarios`, con el mismo UUID y el rol existente, sin negocio.

### Creación de usuarios y recuperación ante errores

FastAPI crea una identidad mediante `supabase.auth.admin.create_user` con correo técnico interno y luego llama a una función RPC que **inserta perfil + membresía + auditoría en una sola transacción**; el trigger diferido valida al confirmar. Si la función RPC falla, FastAPI intenta borrar únicamente la identidad Auth que acaba de crear. Si la limpieza falla, devuelve el UUID para resolverlo manualmente.

**El SDK no hace transaccionales las dos llamadas Auth / PostgreSQL**; la compensación es el mecanismo previsto. No cambies las migraciones 01–08.

### Limitaciones explícitas de esta entrega

- No incluye bootstrap automatizado de superadministrador, recuperación de contraseña, solicitudes de vinculación ni endpoints de edición/suspensión; no se inventaron estas reglas.
- Los endpoints de lectura de catálogos se conservan para la interfaz, aunque su contenido sea público; las consultas se realizan con la clave de backend. Verifica los controles antes de desplegar en internet.
- El login usa un lookup privilegiado de nombre de usuario → correo técnico Auth. **Antes de publicar es obligatorio agregar rate limiting y protección contra fuerza bruta**, además de CORS restringido y HTTPS.
- Si `GET /health/db` funciona pero las rutas nuevas fallan, revisa migración 09 y los recursos expuestos en Data API.

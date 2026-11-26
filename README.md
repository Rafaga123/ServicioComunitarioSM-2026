# Servicio Comunitario SM — Backend

API REST para la gestión académica y disciplinaria de una escuela y un liceo. Está construida con **FastAPI + SQLModel + PostgreSQL** y separa la información por nivel educativo (`ESCUELA` / `LICEO`).

> **Estado actual:** Fases 1–6 completadas en `backend-dev`. El backend expone **14 routers**, **47 rutas** y **84 operaciones** documentadas en OpenAPI. No se agregaron rutas: la revocación de JWT y el límite de login se implementaron dentro de `/auth/login`, `/auth/logout` y el CRUD de usuarios. El contrato detallado para el frontend está en [`docs/ENTREGA_FRONTEND.md`](docs/ENTREGA_FRONTEND.md).
>
> **Importante:** no hay migraciones (Alembic). `create_all()` **no altera** tablas existentes, pero en el arranque se ejecutan dos migraciones no destructivas: `ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS version_tokens INTEGER NOT NULL DEFAULT 0` y `ALTER TYPE tipodocumento ADD VALUE IF NOT EXISTS 'docentes'`. Para el resto de cambios de esquema se usa `python -m scripts.cargar_datos_prueba --recrear-tablas`, que hace `drop_all()` antes de cargar y por eso es destructivo. La tabla nueva `tokens_revocados` sí la crea `create_all()` automáticamente.

---

## Contenido

1. [Requisitos](#1-requisitos)
2. [Puesta en marcha](#2-puesta-en-marcha)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Convenciones de la API](#4-convenciones-de-la-api)
5. [Roles y segmentación por nivel](#5-roles-y-segmentación-por-nivel)
6. [Endpoints](#6-endpoints)
7. [Reglas de negocio](#7-reglas-de-negocio)
8. [Semilla y catálogos](#8-semilla-y-catálogos)
9. [Modelo de datos y orden de carga](#9-modelo-de-datos-y-orden-de-carga)
10. [Guía rápida para el frontend](#10-guía-rápida-para-el-frontend)
11. [Pendientes y limitaciones conocidas](#11-pendientes-y-limitaciones-conocidas)
12. [Solución de problemas](#12-solución-de-problemas)

---

## 1. Requisitos

| Requisito | Versión / nota |
| --- | --- |
| Python | 3.11 o superior (`datetime.UTC` y `zoneinfo`) |
| PostgreSQL | 14 o superior recomendado |
| Permisos de BD | El usuario debe poder ejecutar `CREATE EXTENSION` (o las extensiones deben estar instaladas por el administrador) |
| Extensiones | `unaccent` y `pg_trgm` (las crea la API al arrancar) |
| Node.js | Solo para el frontend: `^22.18.0` o `>=24.12.0` |

La API usa PostgreSQL de forma obligatoria: los índices únicos parciales (`WHERE fecha_eliminacion IS NULL`) y las extensiones de búsqueda no existen en SQLite.

---

## 2. Puesta en marcha

Todos los comandos de esta sección se ejecutan desde la carpeta `backend/`, salvo que se indique lo contrario.

### 2.1 Crear el entorno virtual e instalar dependencias

**Windows (PowerShell):**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux / macOS:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.2 Crear la base de datos

```sql
psql -U postgres
CREATE DATABASE database;
\q
```

Puedes usar otro nombre; solo debe coincidir con `POSTGRES_DB` en el `.env`.

### 2.3 Configurar variables de entorno

Copia `backend/.env.example` a `backend/.env` y completa los valores:

```powershell
Copy-Item .env.example .env
```

| Variable | Obligatoria | Descripción |
| --- | --- | --- |
| `POSTGRES_USER` | Sí | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | Sí | Clave de PostgreSQL |
| `POSTGRES_HOST` | No | Host de la BD. Por defecto `127.0.0.1` |
| `POSTGRES_PORT` | Sí | Puerto de PostgreSQL (normalmente `5432`) |
| `POSTGRES_DB` | Sí | Nombre de la base de datos |
| `DEBUG` | No | `True` muestra el SQL de SQLAlchemy en consola. Usar `False` en operación normal |
| `SECRET_KEY` | Sí | Clave para firmar los JWT. **Mínimo 32 bytes** o la API no arranca |
| `ALGORITHM` | No | Algoritmo del JWT. Por defecto `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Duración del token en minutos. Por defecto `360` |
| `LIMITE_LOGIN_INTENTOS` | No | Fallos permitidos por `(IP, usuario)` en la ventana. Por defecto `5` |
| `LIMITE_LOGIN_IP` | No | Intentos totales permitidos por IP en la ventana. Por defecto `20` |
| `LIMITE_LOGIN_VENTANA_SEGUNDOS` | No | Tamaño de la ventana deslizante. Por defecto `60` |
| `TOKENS_REVOCADOS_RETENCION_HORAS` | No | Horas que se conserva un `jti` revocado después de su `exp`. Por defecto `24` |

Genera una `SECRET_KEY` segura con:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> El `.env.example` trae valores de ejemplo. No uses esa clave ni esa contraseña en un servidor real.

### 2.4 Arrancar la API

Con el entorno virtual activo:

```powershell
fastapi dev app/main.py
```

o, equivalentemente:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Al arrancar, la API:

1. Crea las extensiones `unaccent` y `pg_trgm`.
2. Crea las 16 tablas si no existen.
3. Carga la semilla de grados y bloques horarios si falta.
4. Imprime la IP local y las URLs de Swagger.

Para cargar datos de prueba reales (nóminas 2026) y las cuentas de prueba, ver [§ 8.3](#83-datos-de-prueba-locales-nminas).

Direcciones útiles:

| URL | Contenido |
| --- | --- |
| `http://localhost:8000/` | Health-check básico (`{"status": "Ok"}`) |
| `http://localhost:8000/health` | Health-check con verificación de la BD |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/openapi.json` | Contrato OpenAPI en JSON |

### 2.5 Crear el administrador inicial

El administrador **no** se crea por la API: se crea con un script porque es la única cuenta con `nivel = NULL` y acceso global.

1. Arranca la API una vez para que existan las tablas (puedes detenerla después).
2. Ejecuta:

```powershell
python -m scripts.crear_admin --usuario admin
```

El script pide la clave dos veces y exige mínimo 8 caracteres. Se niega a crear otro administrador si ya existe uno activo. La transferencia del rol se hace desde `POST /api/usuarios/{usuario_id}/transferir-admin`.

---

## 3. Estructura del proyecto

```text
ServicioComunitarioSM-2026/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # Variables de entorno y validación del JWT
│   │   │   ├── paginacion.py      # Envelope {items, total, offset, size}
│   │   │   └── semilla.py         # 11 grados y 10 bloques institucionales
│   │   ├── models/
│   │   │   ├── db.py              # 16 tablas SQLModel
│   │   │   ├── enums.py           # Enums de la API
│   │   │   ├── schemas.py         # Contratos de entrada/salida
│   │   │   └── session.py         # Engine, sesión y creación del esquema
│   │   ├── routers/               # 14 routers (ver sección 6)
│   │   ├── services/
│   │   │   ├── cierre.py          # Cierre de año atómico
│   │   │   └── listados.py        # Generación de PDFs
│   │   ├── utils/
│   │   │   ├── auditoria.py       # Registro de auditorías
│   │   │   ├── fechas.py          # Zona America/Caracas
│   │   │   ├── nombres.py         # Nombre completo
│   │   │   ├── pdf.py             # Render de listados (carta)
│   │   │   ├── security.py        # JWT, roles y filtros por nivel
│   │   │   ├── soft_delete.py     # Borrado lógico
│   │   │   └── storage.py         # Adjuntos y PDFs (STORAGE_ROOT)
│   │   └── main.py                # Registro de routers, CORS y /health
│   ├── scripts/
│   │   ├── cargar_datos_prueba.py # Cargador único de nóminas + usuarios
│   │   ├── crear_admin.py         # Administrador inicial
│   │   ├── normalizar_textos_auditoria.py  # Backfill de textos legibles
│   │   ├── regenerar_horarios_pdf.py       # Reemplaza los PDF de horarios
│   │   ├── excel.py / generar_sql.py / sembrar_horarios.py  # Generadores
│   │   └── nominas/               # Export original (ignorado por Git)
│   ├── .env.example
│   └── requirements.txt
├── docs/
│   └── ENTREGA_FRONTEND.md        # Contrato detallado para el frontend
├── frontend/                      # Vue 3 + Vite (aún sin conectar a la API)
└── README.md
```

---

## 4. Convenciones de la API

### 4.1 Prefijo y formato

- Todas las rutas de negocio llevan el prefijo **`/api`**. Las únicas excepciones son `/`, `/health`, `/docs`, `/redoc` y `/openapi.json`.
- Los cuerpos de petición y respuesta son **JSON** (`application/json`), salvo el login, que usa **`application/x-www-form-urlencoded`**.
- Los identificadores de recursos son enteros (`id`).
- Los listados devuelven el envelope paginado descrito abajo.

### 4.2 Autenticación

El login sigue el flujo OAuth2 Password:

```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=tu_clave
```

Respuesta:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

Todas las rutas protegidas esperan:

```http
Authorization: Bearer <access_token>
```

El token incluye `sub` (id del usuario), `rol`, `nivel`, `jti` (UUID único por emisión), `ver` (versión de tokens del usuario) y `exp` (epoch seconds). En cada petición el servidor vuelve a leer el usuario desde la BD, así que una baja o un cambio de rol surten efecto sin esperar a que expire el token.

- `401`: token ausente, inválido, expirado, revocado u obsoleto. El `detail` distingue cuatro casos:
  - `La sesión ha expirado. Inicia sesión nuevamente.`
  - `No se pudieron validar las credenciales (token inválido)`
  - `La sesión fue cerrada. Inicia sesión nuevamente.`
  - `La clave o los permisos del usuario cambiaron. Inicia sesión nuevamente.`
  En todos ellos el frontend debe limpiar la sesión local.
- `403`: token válido, pero sin permisos o sin acceso al nivel solicitado.
- `429`: demasiados intentos de login. Incluye `Retry-After` en segundos.
- `POST /api/auth/logout` inserta el `jti` en `tokens_revocados` y registra `CIERRE DE SESIÓN` en la misma transacción. El token usado deja de servir de inmediato; otros tokens del mismo usuario siguen válidos. Es idempotente: un segundo logout con el mismo token devuelve `204`.
- Cambiar clave (propia o por admin), dar de baja un usuario o transferir el rol de administrador incrementa `usuarios.version_tokens` y revoca **todas** las sesiones anteriores de los usuarios afectados.
- La tabla `tokens_revocados` se limpia al arrancar y, de forma perezosa, máximo una vez por hora desde login/logout. Se borran las filas con `expira_en < ahora_caracas() - TOKENS_REVOCADOS_RETENCION_HORAS`.
- No hay refresh token. El límite de login es en memoria por proceso: con múltiples workers debe moverse a Redis o al proxy.

### 4.3 Paginación

Todos los listados aceptan:

| Parámetro | Tipo | Default | Límites |
| --- | --- | --- | --- |
| `offset` | entero | `0` | `>= 0` |
| `size` | entero | `15` | `1..100` |

Los buscadores usan `size=10` por defecto.

Respuesta estándar:

```json
{
  "items": [],
  "total": 0,
  "offset": 0,
  "size": 15
}
```

- `total` es la cantidad de registros que cumplen los filtros, sin paginar.
- Para la página `N` (empezando en 1): `offset = (N - 1) * size`.
- Un `offset` fuera de rango devuelve `items: []` y el `total` real.

### 4.4 Fechas y zona horaria

- La única zona horaria del sistema es **`America/Caracas`**.
- La BD guarda `TIMESTAMP WITHOUT TIME ZONE` con la hora local de Caracas.
- La API acepta fechas ISO 8601 **con** offset o `Z` (por ejemplo `2026-03-02T08:00:00-04:00`) y las normaliza a hora de Caracas.
- Si la fecha llega **sin** offset, se asume que ya está en hora de Caracas.
- Las respuestas devuelven `datetime` sin offset. El frontend no debe hacer conversiones manuales de zona horaria.
- `hora_inicio` y `hora_fin` de los bloques viajan como `HH:MM:SS`.

### 4.5 Enums

Los valores viajan en **MAYÚSCULA** por la API. En PostgreSQL se guardan con el nombre del miembro en **minúscula** (por ejemplo `'liceo'`, `'academico'`), lo cual importa solo si se escriben scripts SQL manuales.

| Enum | Valores |
| --- | --- |
| `RolesUsuario` | `ADMINISTRADOR`, `COORDINADOR`, `SECRETARIA` |
| `RolesAsignables` | `COORDINADOR`, `SECRETARIA` |
| `NivelEducativo` | `ESCUELA`, `LICEO` |
| `TipoBloqueHorario` | `ACADEMICO`, `RECESO` |
| `TipoPase` | `ENTRADA`, `SALIDA` |
| `NivelGravedad` | `LEVE`, `GRAVE` |
| `CategoriaReportes` | `CONDUCTUAL`, `ACADEMICO` |
| `Reglamentos` | `LOPNNA`, `LOE`, `CBV`, `NC` |
| `ModuloAuditoria` | `USUARIOS`, `ESTUDIANTES`, `GRADOS`, `SECCIONES`, `REPRESENTANTES`, `DOCENTES`, `ASIGNATURAS`, `BLOQUES HORARIOS`, `HORARIOS`, `PERIODOS LECTIVOS`, `PASES`, `REPORTES`, `AUDITORIAS`, `DOCUMENTOS`, `CIERRE AÑO` |

### 4.6 Errores

Formato general:

```json
{ "detail": "Mensaje en español" }
```

| Código | Uso |
| --- | --- |
| `400` | Regla de negocio incumplida (duplicado, dato incoherente, autorizador faltante, etc.) |
| `401` | No autenticado o token inválido/expirado |
| `403` | Sin permisos o acceso a otro nivel educativo |
| `404` | Recurso inexistente o dado de baja |
| `409` | Conflicto con datos existentes (choque de horario, sección con dependencias, etc.) |
| `422` | Error de validación del esquema (tipo, longitud, enum, rango) |

Los `422` usan el formato estándar de FastAPI:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "primer_nombre"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

### 4.7 Borrado lógico

- **Todas** las tablas tienen `fecha_eliminacion`.
- Ningún `DELETE` borra filas físicamente: solo marca `fecha_eliminacion`.
- Todos los listados y validaciones filtran `fecha_eliminacion IS NULL`.
- Algunos recursos con dependencias activas devuelven `409` en vez de marcarse:
  - Sección con estudiantes activos o horarios activos.
  - Representante con estudiantes activos.
  - Docente con asignaturas/horarios activos.
  - Asignatura con horarios activos.
- Una baja lógica no libera necesariamente una clave única: los índices únicos parciales solo consideran registros activos, pero varias validaciones de negocio revisan también los registros dados de baja para no duplicar identidades (por ejemplo, cédula de docente).

### 4.8 Filtro por nivel educativo

- El **administrador** no tiene nivel (`nivel = NULL`): ve ambos niveles y puede filtrar con `?nivel=ESCUELA` o `?nivel=LICEO`. Si omite el parámetro, ve todo.
- **Coordinador y secretaria** siempre tienen nivel (`ESCUELA` o `LICEO`) y quedan atados a él.
  - Si envían `?nivel=` con otro nivel: `403`.
  - Si su cuenta no tiene nivel: `403`.
- El filtro aplica a estudiantes, representantes, docentes, grados, secciones, asignaturas, horarios, pases, reportes y al resumen de gestión.
- **Usuarios** es la excepción: su listado es solo para el administrador.

---

## 5. Roles y segmentación por nivel

### 5.1 Matriz de permisos

| Módulo | Consultar | Crear / editar / dar de baja |
| --- | --- | --- |
| Salud (`/`, `/health`) | Público | — |
| Auth (`/api/auth`) | `login` público; `me` cualquier autenticado | — |
| Usuarios | Solo administrador | Solo administrador |
| Estudiantes | Cualquier autenticado (filtrado por nivel) | Solo administrador |
| Representantes | Cualquier autenticado (filtrado por nivel) | Solo administrador |
| Docentes | Cualquier autenticado (filtrado por nivel) | Solo administrador |
| Grados | Cualquier autenticado (filtrado por nivel) | **No tiene escritura** (catálogo fijo) |
| Secciones | Cualquier autenticado (filtrado por nivel) | Solo administrador |
| Asignaturas | Cualquier autenticado (filtrado por nivel) | Solo administrador |
| Bloques horarios | Cualquier autenticado | Solo administrador |
| Horarios (registros) | Cualquier autenticado (filtrado por nivel) | Solo administrador |
| Horarios (consulta de estudiante) | Cualquier autenticado (filtrado por nivel) | — |
| Pases | Administrador, coordinador y secretaria | Administrador, coordinador y secretaria |
| Reportes | Administrador, coordinador y secretaria | Administrador, coordinador y secretaria |
| Gestión (resumen) | Cualquier autenticado (filtrado por nivel) | — |
| Auditorías | Solo administrador | — |

> **Ojo con Horarios:** `GET /api/horarios/registros/` y `GET /api/horarios/registros/{id}` son de **lectura para cualquier autenticado**, filtrados por nivel; `POST`, `PUT` y `DELETE` siguen siendo **solo del administrador**. La ruta `GET /api/horarios/` es distinta: es la consulta de “qué clase tiene este estudiante en esta fecha” y también está disponible para cualquier usuario autenticado. Como los horarios solo existen para LICEO, una cuenta de ESCUELA recibe la lista vacía.

### 5.2 Resumen de reglas de nivel

- El administrador puede crear/consultar pases y reportes de ambos niveles.
- Coordinador y secretaria solo operan dentro de su nivel, incluso si intentan forzar otro por query string.
- Los representantes no tienen columna `nivel`: se consideran de un nivel si tienen al menos un estudiante activo en ese nivel.
- Un representante sin estudiantes activos en el nivel del operador devuelve `403` al consultar su detalle.
- Cambiar el `nivel` de un docente con dependencias activas devuelve `409`.

---

## 6. Endpoints

> Esta sección lista las **84 operaciones** de la API. Los schemas completos, ejemplos y códigos de respuesta están en `/docs` y `/openapi.json`; el contrato de integración está en `docs/ENTREGA_FRONTEND.md`.

### 6.1 Salud

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/` | Público | Devuelve `{"status": "Ok"}` |
| GET | `/health` | Público | Ejecuta `SELECT 1`. Devuelve `{"status": "ok", "database": "ok"}` o `503` |

### 6.2 Autenticación (`/api/auth`)

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | Público | Form-data `username` y `password`. Devuelve `access_token` y `token_type` |
| GET | `/api/auth/me` | Autenticado | Devuelve `id`, `nombre`, `rol` y `nivel` del usuario actual |
| POST | `/api/auth/logout` | Autenticado | `204`; revoca el `jti` del token usado y registra `CIERRE DE SESIÓN` |

Ejemplo de respuesta de `/api/auth/me`:

```json
{
  "id": 1,
  "nombre": "admin",
  "rol": "ADMINISTRADOR",
  "nivel": null
}
```

### 6.3 Usuarios (`/api/usuarios`)

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/api/usuarios/` | Admin | Lista usuarios activos. Filtros: `nivel`, `rol` |
| POST | `/api/usuarios/` | Admin | Crea coordinador o secretaria. `nivel` es obligatorio. Devuelve `201` |
| GET | `/api/usuarios/{usuario_id}` | Admin | Detalle de un usuario |
| PUT | `/api/usuarios/{usuario_id}` | Admin | Actualiza `nombre`, `rol` y/o `nivel` |
| DELETE | `/api/usuarios/{usuario_id}` | Admin | Baja lógica. No permite dar de baja al administrador. Devuelve `204` |
| PUT | `/api/usuarios/me/clave` | Autenticado | Cambia la clave propia. Body: `clave_actual`, `clave_nueva`. Devuelve `204` |
| POST | `/api/usuarios/{usuario_id}/transferir-admin` | Admin | Transfiere el rol de administrador y da de baja al administrador actual |

Crear usuario:

```json
{
  "nombre": "secretaria_escuela",
  "clave": "clave_segura_123",
  "rol": "SECRETARIA",
  "nivel": "ESCUELA"
}
```

Reglas:

- `rol` solo puede ser `COORDINADOR` o `SECRETARIA`; el administrador se crea por script.
- `nivel` es obligatorio para coordinador y secretaria.
- El nombre de usuario es único entre los activos.
- La clave debe tener entre 8 y 72 caracteres.
- No se puede dar de baja al administrador: primero hay que transferir el rol.

### 6.4 Estudiantes (`/api/estudiantes`)

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/api/estudiantes/` | Autenticado | Lista estudiantes activos. Filtros: `nivel`, `id_grado`, `id_seccion`, `periodo_lectivo` |
| GET | `/api/estudiantes/buscar/` | Autenticado | Busca por cédula, nombre o apellido con `termino`. Sin distinguir acentos. `size=10` por defecto |
| GET | `/api/estudiantes/{estudiante_id}` | Autenticado | Detalle. `403` si pertenece a otro nivel |
| POST | `/api/estudiantes/` | Admin | Crea estudiante. Devuelve `201` |
| PUT | `/api/estudiantes/{estudiante_id}` | Admin | Actualiza campos parciales |
| DELETE | `/api/estudiantes/{estudiante_id}` | Admin | Baja lógica. Devuelve `204` |

Crear estudiante:

```json
{
  "id_seccion": 1,
  "id_representante": 1,
  "cedula_estudiantil": "V-12345678",
  "primer_nombre": "Ana",
  "segundo_nombre": "María",
  "primer_apellido": "Pérez",
  "segundo_apellido": "Gómez",
  "fecha_nacimiento": "2012-05-10T00:00:00-04:00"
}
```

Reglas:

- `id_seccion` es obligatorio y debe estar activo.
- `id_representante` es opcional; si se envía, debe estar activo.
- La cédula es única entre estudiantes activos.
- `fecha_nacimiento` se normaliza a hora de Caracas.
- La respuesta incluye datos de apoyo: `nivel`, `id_grado`, `grado_numero`, `grado_nombre`, `seccion_letra`, `periodo_lectivo` y `representante`.
- El estudiante pertenece a un solo nivel a través de su sección.

### 6.5 Representantes (`/api/representantes`)

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/api/representantes/` | Autenticado | Lista representantes activos. Filtro: `nivel`. Un operador solo ve los que tienen estudiantes activos en su nivel |
| GET | `/api/representantes/{representante_id}` | Autenticado | Detalle. `403` si no tiene estudiantes activos en el nivel del operador |
| POST | `/api/representantes/` | Admin | Crea representante. Devuelve `201` |
| PUT | `/api/representantes/{representante_id}` | Admin | Actualiza campos parciales |
| DELETE | `/api/representantes/{representante_id}` | Admin | Baja lógica. `409` si tiene estudiantes activos. Devuelve `204` |
| POST | `/api/representantes/{representante_id}/vincular_estudiante/{estudiante_id}` | Admin | Vincula un estudiante al representante |
| DELETE | `/api/representantes/{representante_id}/vincular_estudiante/{estudiante_id}` | Admin | Desvincula al estudiante |

Crear representante:

```json
{
  "primer_nombre": "Carlos",
  "segundo_nombre": null,
  "primer_apellido": "Pérez",
  "segundo_apellido": null,
  "telefono": "0414-1234567"
}
```

Reglas:

- No se usa cédula para representantes.
- Segundo nombre y segundo apellido son opcionales.
- Un representante puede tener varios estudiantes; un estudiante tiene como máximo un representante.
- Vincular reemplaza el representante anterior del estudiante si ya tenía uno.

### 6.6 Docentes (`/api/docentes`)

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/api/docentes/` | Autenticado | Lista docentes activos. Filtro: `nivel` |
| GET | `/api/docentes/{docente_id}` | Autenticado | Detalle. `403` si es de otro nivel |
| POST | `/api/docentes/` | Admin | Crea docente. Devuelve `201` |
| PUT | `/api/docentes/{docente_id}` | Admin | Actualiza datos. Cambiar `nivel` con dependencias activas devuelve `409` |
| DELETE | `/api/docentes/{docente_id}` | Admin | Baja lógica. `409` si tiene dependencias activas. Devuelve `204` |

Crear docente:

```json
{
  "primer_nombre": "Luis",
  "segundo_nombre": null,
  "primer_apellido": "Rodríguez",
  "segundo_apellido": null,
  "cedula": "V-87654321",
  "nivel": "LICEO"
}
```

Reglas:

- La cédula es única entre todos los docentes, incluidos los dados de baja.
- `nivel` es obligatorio.
- Los docentes de escuela solo pueden ser titulares de secciones de escuela.
- Los docentes de liceo son los únicos que pueden vincularse a asignaturas y horarios.

### 6.7 Grados (`/api/grados`)

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/api/grados/` | Autenticado | Lista los 11 grados. Filtro: `nivel` |
| GET | `/api/grados/{grado_id}` | Autenticado | Detalle de un grado |

- Catálogo **fijo y de solo lectura**. No existen POST, PUT ni DELETE.
- `1` a `6` = `1er Grado` … `6to Grado` (`ESCUELA`).
- `7` a `11` = `1er Año` … `5to Año` (`LICEO`).
- No se pueden editar ni dar de baja.

### 6.8 Secciones (`/api/secciones`)

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/api/secciones/` | Autenticado | Lista secciones activas. Filtros: `nivel`, `id_grado`, `periodo_lectivo` |
| GET | `/api/secciones/{seccion_id}` | Autenticado | Detalle. `403` si es de otro nivel |
| POST | `/api/secciones/` | Admin | Crea sección. Devuelve `201` |
| PUT | `/api/secciones/{seccion_id}` | Admin | Actualiza letra, período y/o titular |
| DELETE | `/api/secciones/{seccion_id}` | Admin | Baja lógica. `409` si tiene estudiantes o horarios activos. Devuelve `204` |

Crear sección:

```json
{
  "id_grado": 7,
  "letra": "A",
  "periodo_lectivo": 2026,
  "id_docente_titular": null
}
```

Reglas:

- Letras permitidas: **`A`, `B`, `U`** (se normalizan a mayúscula).
- `periodo_lectivo` es un año entero, por ejemplo `2026`.
- Única sección activa por `(id_grado, letra, periodo_lectivo)`.
- `id_docente_titular` es opcional y **solo para secciones de escuela**; debe ser un docente de escuela del mismo nivel del operador.
- Un docente solo puede ser titular de **una sección activa por período lectivo**; si ya es titular de otra, `409`.
- Las secciones de liceo no llevan docente titular.
- Para dar de baja una sección primero hay que trasladar a sus estudiantes y dar de baja sus horarios; si no, `409`.

### 6.9 Asignaturas (`/api/asignaturas`)

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/api/asignaturas/` | Autenticado | Lista asignaturas activas. Filtros: `nivel`, `id_grado` |
| GET | `/api/asignaturas/{asignatura_id}` | Autenticado | Detalle con docentes vinculados |
| POST | `/api/asignaturas/` | Admin | Crea asignatura. Devuelve `201` |
| PUT | `/api/asignaturas/{asignatura_id}` | Admin | Actualiza grado y/o nombre |
| DELETE | `/api/asignaturas/{asignatura_id}` | Admin | Baja lógica. `409` si tiene horarios activos. Devuelve `204` |
| GET | `/api/asignaturas/{asignatura_id}/docentes` | Autenticado | Lista docentes vinculados |
| POST | `/api/asignaturas/{asignatura_id}/docentes/{docente_id}` | Admin | Vincula docente de liceo |
| DELETE | `/api/asignaturas/{asignatura_id}/docentes/{docente_id}` | Admin | Desvincula docente |

Crear asignatura:

```json
{
  "id_grado": 7,
  "nombre": "Matemática"
}
```

Reglas:

- Solo se permiten grados de **liceo** (`7` a `11`).
- Única asignatura activa por `(id_grado, nombre)`.
- Solo se vinculan docentes de **liceo**.
- El vínculo se guarda en `asignaturas_docentes` con borrado lógico.
- Un docente debe estar vinculado a la asignatura para poder asignarle un horario o un pase con esa asignatura.

### 6.10 Bloques horarios (`/api/bloques-horarios`)

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/api/bloques-horarios/` | Autenticado | Lista bloques activos. Filtro: `tipo` (`ACADEMICO` / `RECESO`) |
| GET | `/api/bloques-horarios/{bloque_id}` | Autenticado | Detalle |
| POST | `/api/bloques-horarios/` | Admin | Crea bloque. Devuelve `201` |
| PUT | `/api/bloques-horarios/{bloque_id}` | Admin | Actualiza un bloque |
| DELETE | `/api/bloques-horarios/{bloque_id}` | Admin | Baja lógica. `409` si tiene horarios activos. Devuelve `204` |

Crear bloque académico:

```json
{
  "orden": 1,
  "numero": 1,
  "nombre": "Bloque 1",
  "tipo": "ACADEMICO",
  "hora_inicio": "07:00:00",
  "hora_fin": "07:40:00"
}
```

Crear receso:

```json
{
  "orden": 3,
  "numero": null,
  "nombre": "Receso 1",
  "tipo": "RECESO",
  "hora_inicio": "08:20:00",
  "hora_fin": "08:40:00"
}
```

Reglas:

- `orden` va de `1` a `10` y es único entre los activos.
- Un bloque `ACADEMICO` debe tener `numero` entre `1` y `8`.
- Un `RECESO` debe tener `numero = null`.
- `hora_fin` debe ser posterior a `hora_inicio`.
- Solo los bloques académicos se pueden usar en horarios.

### 6.11 Horarios (`/api/horarios`)

#### Registros de horarios

Los `GET` de registros son de lectura para cualquier autenticado y filtran por nivel: el administrador ve ambos niveles y coordinador/secretaria solo el suyo. `POST`, `PUT` y `DELETE` son exclusivos del administrador. Como los horarios solo aplican a LICEO, una cuenta de ESCUELA recibe `200` con la lista vacía; si intenta pedir `?nivel=LICEO`, recibe `403`.

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/api/horarios/registros/` | Lista horarios activos. Filtros: `id_seccion`, `id_grado`, `id_asignatura`, `id_docente`, `id_bloque`, `periodo_lectivo`, `dia_semana`, `nivel` |
| GET | `/api/horarios/registros/{horario_id}` | Detalle |
| POST | `/api/horarios/registros/` | Crea horario. Devuelve `201` |
| PUT | `/api/horarios/registros/{horario_id}` | Actualiza |
| DELETE | `/api/horarios/registros/{horario_id}` | Baja lógica. Devuelve `204` |

Crear horario:

```json
{
  "id_seccion": 1,
  "id_bloque": 1,
  "id_asignatura": 1,
  "id_docente": 1,
  "periodo_lectivo": 2026,
  "dia_semana": 1
}
```

`dia_semana`: `1` = lunes, `2` = martes, `3` = miércoles, `4` = jueves, `5` = viernes.

Reglas:

- Solo secciones de **liceo**.
- El período del horario debe existir y no estar cerrado (`400` al crear o editar).
- El período del horario debe coincidir con el `periodo_lectivo` de la sección.
- Solo bloques `ACADEMICO`.
- La asignatura debe pertenecer al grado de la sección.
- El docente debe ser de liceo y estar vinculado a la asignatura.
- Choque de sección (`id_seccion + id_bloque + periodo_lectivo + dia_semana`) → `409`.
- Choque de docente (`id_docente + id_bloque + periodo_lectivo + dia_semana`) → `409`.
- Un docente titular de otra sección no puede programarse aquí (`409`): está ocupado con su sección y solo puede dar clases en ella.
- La respuesta incluye datos de apoyo: `seccion`, `grado`, `nivel`, `bloque`, `bloque_orden`, `hora_inicio`, `hora_fin`, `asignatura` y `docente`.

#### Consulta de clase por estudiante (cualquier autenticado)

```http
GET /api/horarios/?id_estudiante=1&fecha=2026-03-02&id_bloque=1
```

o por hora:

```http
GET /api/horarios/?id_estudiante=1&fecha=2026-03-02&hora=07:30:00
```

| Parámetro | Obligatorio | Descripción |
| --- | --- | --- |
| `id_estudiante` | Sí | Estudiante activo |
| `fecha` | Sí | Fecha (`YYYY-MM-DD`). Se usa para calcular el día de la semana |
| `id_bloque` | No | Bloque institucional exacto |
| `hora` | No | Hora dentro de un bloque académico |

- Se debe enviar `id_bloque` **o** `hora`, no ambos.
- Si no hay clase, devuelve `encontrado: false` con los demás campos en `null`.
- Si el estudiante es de otro nivel, `403`.

### 6.12 Pases (`/api/pases`)

Acceso: `ADMINISTRADOR`, `COORDINADOR` y `SECRETARIA`. Los operadores quedan limitados a su nivel.

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/api/pases/` | Lista pases activos. Filtros: `id_estudiante`, `id_seccion`, `tipo`, `anio`, `mes`, `nivel` |
| GET | `/api/pases/{pase_id}` | Detalle. `403` si es de otro nivel |
| POST | `/api/pases/` | Crea pase. Devuelve `201` |
| PUT | `/api/pases/{pase_id}` | Actualiza. Revalida la cuota y el autorizador |
| DELETE | `/api/pases/{pase_id}` | Baja lógica. Devuelve `204` |
| POST | `/api/pases/{pase_id}/archivo` | Sube una imagen (multipart `archivo`). Devuelve el pase con metadatos |
| GET | `/api/pases/{pase_id}/archivo` | Descarga el adjunto (`?inline=true` para mostrarlo) |
| DELETE | `/api/pases/{pase_id}/archivo` | Desvincula el adjunto; el archivo físico se conserva |

`archivo_url` **no se acepta** en POST/PUT: los adjuntos solo se gestionan con estos tres endpoints.

Crear pase:

```json
{
  "id_estudiante": 1,
  "id_docente": null,
  "id_asignatura": null,
  "tipo": "ENTRADA",
  "motivo": "Consulta médica",
  "fecha": "2026-03-02T08:00:00-04:00",
  "autorizador": null
}
```

Reglas:

- Solo `ENTRADA` y `SALIDA`.
- **3 pases sin autorizador por estudiante, por tipo y por mes calendario.**
  - Es decir: hasta 3 entradas y hasta 3 salidas al mes sin autorizador.
  - El cuarto pase del mismo tipo en el mismo mes exige `autorizador` no vacío.
  - El conteo excluye pases dados de baja y usa el mes de `fecha`.
- Si se envía `id_asignatura`, debe pertenecer al grado del estudiante.
- Si se envían `id_docente` e `id_asignatura`, el docente debe estar vinculado a la asignatura.
- El pase guarda el usuario que lo registró (`id_usuario`).
- La respuesta incluye `estudiante`, `cedula_estudiantil`, `nivel`, `usuario`, `docente` y `asignatura`.

### 6.13 Reportes (`/api/reportes`)

Acceso: `ADMINISTRADOR`, `COORDINADOR` y `SECRETARIA`. Los operadores quedan limitados a su nivel.

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/api/reportes/` | Lista reportes activos. Filtros: `id_estudiante`, `id_seccion`, `id_docente`, `anio`, `mes`, `categoria`, `nivel_gravedad`, `nivel` |
| GET | `/api/reportes/{reporte_id}` | Detalle. `403` si es de otro nivel |
| POST | `/api/reportes/` | Crea reporte. Devuelve `201` |
| PUT | `/api/reportes/{reporte_id}` | Actualiza |
| DELETE | `/api/reportes/{reporte_id}` | Baja lógica. Devuelve `204` |
| POST | `/api/reportes/{reporte_id}/archivo` | Sube una imagen (multipart `archivo`). Devuelve el reporte con metadatos |
| GET | `/api/reportes/{reporte_id}/archivo` | Descarga el adjunto (`?inline=true` para mostrarlo) |
| DELETE | `/api/reportes/{reporte_id}/archivo` | Desvincula el adjunto; el archivo físico se conserva |

Igual que en pases, `archivo_url` **no se acepta** en POST/PUT.

Crear reporte:

```json
{
  "id_estudiante": 1,
  "id_docente": null,
  "articulo": 1,
  "reglamento": "LOPNNA",
  "incidencia": "Interrupción reiterada de la clase",
  "defensa": "El estudiante explicó lo ocurrido",
  "nivel_gravedad": "LEVE",
  "categoria": "CONDUCTUAL",
  "fecha": "2026-03-02T09:00:00-04:00"
}
```

Reglas:

- **No hay cuota mensual** para reportes.
- `articulo` es un entero mayor o igual a 1.
- `reglamento`: `LOPNNA`, `LOE`, `CBV` o `NC`.
- `nivel_gravedad`: `LEVE` o `GRAVE`.
- `categoria`: `CONDUCTUAL` o `ACADEMICO`.
- `id_docente` es opcional; si se envía, debe estar activo.
- La respuesta incluye `estudiante`, `cedula_estudiantil`, `nivel`, `usuario` y `docente`.
- No existe un campo de estado (“borrador/enviado/atendido”): el contrato actual no lo contempla.

### 6.14 Gestión (`/api/gestion`)

#### Períodos lectivos

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/api/gestion/periodos` | Admin | Lista períodos (ordenados por año desc) |
| GET | `/api/gestion/periodos/activo` | Autenticado | Devuelve el período activo o `null` |
| POST | `/api/gestion/periodos` | Admin | Crea un período (`anio`, `activo`). Devuelve `201` |
| PATCH | `/api/gestion/periodos/{periodo_id}` | Admin | Activa/desactiva; no permite cerrar ni reactivar un período cerrado |

Crear período:

```json
{ "anio": 2026, "activo": true }
```

Reglas: `anio ≥ 2000` y único; activar uno desactiva los demás; `cerrado` solo lo escribe el cierre de año.

#### Resumen

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/api/gestion/resumen` | Autenticado | Conteos activos para la pantalla de Gestión Académica |

Filtros opcionales: `?nivel=ESCUELA|LICEO` (solo el administrador puede elegir; los operadores quedan atados a su nivel) y `?periodo_lectivo=2026` (por defecto, el activo).

Respuesta:

```json
{
  "nivel": null,
  "periodo_lectivo": 2026,
  "representantes": 341,
  "estudiantes": 359,
  "secciones": 17,
  "docentes": 27,
  "asignaturas": 51,
  "horarios": 283,
  "pases": 0,
  "reportes": 0
}
```

Reglas de conteo:

- Solo registros con `fecha_eliminacion IS NULL`.
- Con período activo, todos los contadores se filtran por ese año, excepto `docentes`, que se cuenta globalmente dentro del nivel.
- Sin periodo activo y sin parámetro, `periodo_lectivo` es `null` y los contadores vuelven `0` (`docentes` global).
- `docentes` usa su columna directa `nivel`; `secciones`, `estudiantes`, `horarios` y `asignaturas` se filtran por `sección → grado → nivel`.
- `pases` y `reportes` se filtran por `estudiante → sección → grado → nivel`.
- `representantes` se cuentan como distintos con al menos un estudiante activo en el nivel consultado (no tienen columna `nivel`).
- Una sola petición devuelve todos los números; el frontend no necesita consultar cada módulo al entrar a Gestión Académica.

#### Cierre de año

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| POST | `/api/gestion/cerrar-anio` | Admin | Cierra el período actual, traspasa estudiantes y crea la estructura del siguiente |

```json
{ "periodo_actual": 2026, "periodo_siguiente": 2027 }
```

Devuelve `200` con `{ periodo_cerrado, periodo_activado, documentos_generados, estudiantes_promovidos, egresados, secciones_creadas, asignaturas_creadas }`.

- El período actual debe estar activo y abierto; el siguiente debe ser mayor y no tener secciones creadas.
- Genera PDFs de nóminas y representantes para todas las secciones, de horarios solo para las de LICEO y un listado general de docentes por nivel. Se preparan en staging y se mueven solo si toda la operación tiene éxito; si falla, se revierten.
- Traspasa estudiantes al siguiente grado (6to Grado → 1er Año) y marca el egreso en 5to Año mediante `fecha_egreso` (solo lectura en la API normal).
- Replica las combinaciones grado+letra existentes sin docentes titulares y copia los nombres de asignaturas de liceo sin docentes.

### 6.15 Listados (`/api/listados`)

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| POST | `/api/listados/{tipo}` | Autenticado (según nivel) | Genera un PDF (`tipo`: `nominas`, `representantes`, `horarios` o `docentes`). Devuelve `201` |
| GET | `/api/listados/documentos` | Admin | Lista documentos generados. Filtros: `tipo`, `periodo_lectivo`, `nivel`, `id_grado`, `id_seccion` |
| GET | `/api/listados/documentos/{documento_id}/archivo` | Autenticado | Descarga el PDF |
| GET | `/api/listados/documentos/paquete` | Admin | Descarga un ZIP con todos los PDFs de un tipo y período |

Generar un listado:

```json
{ "id_seccion": 10 }
```

o, sin sección: `{ "nivel": "ESCUELA", "periodo_lectivo": 2026 }`.

- `periodo_lectivo` es opcional: por defecto se usa el activo (400 si no hay activo y no se indicó uno).
- `horarios` requiere `id_seccion` de **liceo** (400 si la sección es de ESCUELA); `docentes` es general por nivel (400 con `id_seccion` o `id_grado`); los demás listados generales requieren `nivel`.
- Los PDF usan hoja carta, margen izquierdo de 4 cm y 3 cm en los demás lados.
- La ruta incluye el periodo lectivo: `2026-2027/listados/nominas/ESCUELA/1er_grado/U/nomina_2026-2027_1er_grado_U.pdf` (si ya existe, se agrega `_v2`, `_v3`, …).
- Título: `UNIDAD EDUCATIVA PRIVADA SANTA MARTA — Listado de estudiantes 2026-2027/1er Grado "U"`. Metadatos: `ESCUELA • 1er Grado U • 2026-2027`.
- Los representantes de ESCUELA del export original solo tienen teléfono; en la columna `Representante` se muestra `-`. Los de LICEO conservan su nombre real.
- PDF de `horarios`: tabla de 12 filas (periodo/curso/sección, `Hora | LUNES | ... | VIERNES` y los bloques `7:00-7:40`, `7:40-8:20`, `8:20-8:40` (RECESO), `8:40-9:20`, `9:20-10:00`, `10:10-10:10` (RECESO), `10:10-10:50`, `10:10-11:30`, `11:30-12:10`, `12:10-12:40`), seguida de `Docentes:` con `Materia: Docente` de esa sección.
- PDF de `docentes`: columnas `Cédula | Docente | Asignaturas` en LICEO y `Cédula | Docente | Grado/Sección` en ESCUELA; una fila por docente activo del nivel. En LICEO se incluye el año de cada materia (`Matemática 1er Año`) y se deduplica por materia+año; en ESCUELA se listan los grados/secciones donde es titular (o `-` si no tiene).

### 6.16 Auditorías (`/api/auditorias`)

Acceso: **solo administrador**.

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/api/auditorias/` | Lista auditorías. Filtros: `usuario`, `modulo`, `accion`, `fecha` (`YYYY-MM-DD`) |
| GET | `/api/auditorias/{auditoria_id}` | Detalle |

Cada operación de escritura registra automáticamente una auditoría con:

- `usuario_id`
- `modulo` (`USUARIOS`, `ESTUDIANTES`, `SECCIONES`, `PASES`, `REPORTES`, etc.)
- `accion` (`CREAR`, `ACTUALIZAR`, `ELIMINAR`, `CAMBIAR CLAVE`, `TRANSFERIR ADMIN`, `SUBIR ARCHIVO`, `INICIO DE SESIÓN`, `CIERRE DE SESIÓN`, etc.)
- `descripcion`
- `fecha_creacion`

Los textos visibles se normalizan al guardar: `_` → espacio y `ano`/`anio` → `año` (`BLOQUES HORARIOS`, `CIERRE AÑO`, `1er año`). Para normalizar auditorías antiguas:

```powershell
python -m scripts.normalizar_textos_auditoria
```

---

## 7. Reglas de negocio

### 7.1 Pases

- Solo existen dos tipos: `ENTRADA` y `SALIDA`.
- Cuota mensual por estudiante y por tipo: **3 sin autorizador**.
- Desde el cuarto pase del mismo tipo en el mismo mes, `autorizador` es obligatorio.
- El conteo se hace por mes calendario de `fecha` y excluye pases dados de baja.
- Al actualizar un pase se recalcula la cuota excluyendo el propio pase.
- Un pase dado de baja deja de contar para la cuota.
- Los pases se conservan durante el año académico; su baja masiva queda a cargo del cierre de año.

### 7.2 Reportes

- No tienen cuota mensual.
- Se filtran por año, mes, categoría, gravedad y nivel.
- Se conservan durante el año académico; su baja masiva queda a cargo del cierre de año.
- No existe flujo de estados ni aprobación en el contrato actual.

### 7.3 Horarios

- Se programan sobre **sección + bloque institucional**, no sobre una hora suelta.
- Solo aplican al liceo.
- Solo bloques académicos (nunca recesos).
- La asignatura debe ser del grado de la sección.
- El docente debe ser de liceo y estar vinculado a la asignatura.
- No puede haber dos clases para la misma sección en el mismo bloque/día/período.
- No puede haber dos clases para el mismo docente en el mismo bloque/día/período.
- El titular de una sección es único por período y no puede programarse en otra sección.
- La consulta por estudiante resuelve la sección del estudiante y el bloque por `id_bloque` o por `hora`.

### 7.4 Secciones

- Letras `A`, `B`, `U`.
- Una sección pertenece a un grado y a un período lectivo.
- Única sección activa por `(id_grado, letra, periodo_lectivo)`.
- Titular opcional solo en escuela y debe ser docente de escuela.
- No se puede dar de baja una sección con estudiantes o horarios activos.

### 7.5 Asignaturas y docentes

- Asignaturas solo para grados `7` a `11`.
- Única asignatura activa por `(id_grado, nombre)`.
- Solo docentes de liceo pueden vincularse a asignaturas.
- El vínculo asignatura-docente es muchos a muchos y usa borrado lógico.
- Un docente con dependencias activas no puede cambiar de nivel ni darse de baja.

### 7.6 Estudiantes y representantes

- Un estudiante tiene exactamente una sección activa.
- Un estudiante puede tener cero o un representante.
- Un representante puede tener varios estudiantes.
- La cédula del estudiante es única entre los activos.
- Los representantes no tienen cédula.
- El segundo nombre y el segundo apellido son opcionales.

### 7.7 Auditoría

- Las operaciones de escritura registran auditoría en la misma transacción.
- `GET /api/auditorias/` es exclusivo del administrador.
- Los filtros de auditoría son por nombre de usuario, módulo, acción y fecha.

### 7.8 Períodos lectivos

- El período activo es compartido por listados, resumen y los DTOs de creación que no reciben un año explícito.
- No se puede cerrar un período con `PATCH`; solo `POST /api/gestion/cerrar-anio`.
- No se puede activar un período cerrado.

### 7.9 Listados y PDFs

- Los PDF se generan para el período activo salvo que se envíe `periodo_lectivo`.
- Las rutas de almacenamiento llevan el periodo como primera carpeta (`2026` → `2026-2027`).
- Si el archivo destino ya existe, se conserva y se genera un nombre único con sufijo.
- Los representantes sin nombre (placeholders de ESCUELA) se muestran como `-`, conservando su teléfono.

### 7.10 Adjuntos de pases y reportes

- Solo imágenes JPG/JPEG/PNG/WebP, máximo 5 MB.
- La subida es multipart con el campo `archivo`; `archivo_url` es solo de lectura.
- El nombre visible `archivo_nombre` se formatea (`_` → espacio, `ano`/`anio` → `año`); el archivo físico conserva su nombre UUID por seguridad.
- Al desvincular con `DELETE /{id}/archivo` se limpia la metadata, pero el archivo físico permanece en `STORAGE_ROOT`.

### 7.11 Estructura física

Todo se guarda bajo `STORAGE_ROOT` (`C:\sistema` por defecto):

```text
2026-2027/
├─ pases/{nivel}/{grado}/{letra}/estudiante-{id}/archivo.ext
├─ reportes/{nivel}/{grado}/{letra}/estudiante-{id}/archivo.ext
└─ listados/{nominas|representantes|horarios|docentes}/{nivel}/{grado|general}/{letra}/archivo.pdf
```

La BD sigue guardando el año como entero (`2026`); la etiqueta `2026-2027` se deriva para rutas, nombres de archivo, títulos y metadatos.

---

## 8. Semilla y catálogos

La semilla se ejecuta en cada arranque y es idempotente. No resucita registros dados de baja deliberadamente.

### 8.1 Grados (11)

| Número | Nombre | Nivel |
| --- | --- | --- |
| 1 | 1er Grado | ESCUELA |
| 2 | 2do Grado | ESCUELA |
| 3 | 3er Grado | ESCUELA |
| 4 | 4to Grado | ESCUELA |
| 5 | 5to Grado | ESCUELA |
| 6 | 6to Grado | ESCUELA |
| 7 | 1er Año | LICEO |
| 8 | 2do Año | LICEO |
| 9 | 3er Año | LICEO |
| 10 | 4to Año | LICEO |
| 11 | 5to Año | LICEO |

### 8.2 Bloques horarios (10)

| Orden | Número | Nombre | Tipo | Inicio | Fin |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 | Bloque 1 | ACADEMICO | 07:00 | 07:40 |
| 2 | 2 | Bloque 2 | ACADEMICO | 07:40 | 08:20 |
| 3 | — | Receso 1 | RECESO | 08:20 | 08:40 |
| 4 | 3 | Bloque 3 | ACADEMICO | 08:40 | 09:20 |
| 5 | 4 | Bloque 4 | ACADEMICO | 09:20 | 10:00 |
| 6 | — | Receso 2 | RECESO | 10:00 | 10:10 |
| 7 | 5 | Bloque 5 | ACADEMICO | 10:10 | 10:50 |
| 8 | 6 | Bloque 6 | ACADEMICO | 10:50 | 11:30 |
| 9 | 7 | Bloque 7 | ACADEMICO | 11:30 | 12:10 |
| 10 | 8 | Bloque 8 | ACADEMICO | 12:10 | 12:40 |

### 8.3 Datos de prueba locales (nóminas)

`backend/scripts/nominas/` contiene el export original, organizado en `PDFs/` y `Excels/`, con los SQL y JSON en la raíz. Es una carpeta **ignorada por Git** porque incluye nombres y cédulas reales: no debe subirse al repositorio. Un clone nuevo no la trae; hay que copiarla manualmente desde el export local antes de cargar datos de prueba. Los scripts generadores (`excel.py`, `generar_sql.py`) reciben como `--carpeta` la ruta a `nominas/Excels`.

Los SQL de esa carpeta están adaptados al esquema actual:

- cédulas sin el prefijo `V-` (coinciden con el CRUD de docentes y con `sembrar_horarios.py`);
- periodo lectivo `2026` activo y no cerrado;
- los grados los crea la semilla de la API, así que los SQL solo insertan secciones;
- dos estudiantes de 5to Año tienen `fecha_egreso` para probar el detalle de egresados;
- las 4 colisiones docente+bloque+día del JSON se insertan tal cual vienen en el export;
- los representantes de ESCUELA del PDF original no tienen nombre (solo teléfono): los 190 placeholders quedan con nombre y apellidos vacíos y los PDFs muestran `-` en la columna `Representante`;
- todos los `INSERT` son idempotentes y pueden re-ejecutarse.

Carga completa en un solo comando, desde `backend/` y con la configuración de `.env`:

```powershell
.\.venv\Scripts\python.exe -m scripts.cargar_datos_prueba
```

El cargador crea las tablas y la semilla base si faltan, y ejecuta en orden jerárquico: periodo → docentes → secciones → representantes → estudiantes → asignaturas → vínculos docentes → horarios → reclasificación de docentes sin materias → usuarios. Es idempotente: puede ejecutarse las veces que haga falta sin duplicar registros. Acepta `--sql`, `--json`, `--clave`, `--no-actualizar-horarios`, `--solo-reclasificar-docentes` y `--recrear-tablas`.

La reclasificación pasa a `ESCUELA` los docentes activos de `LICEO` que no tienen vínculos de asignatura ni horarios activos y no son titulares de una sección de liceo. Para aplicar solo ese ajuste sin recargar el resto:

```powershell
.\.venv\Scripts\python.exe -m scripts.cargar_datos_prueba --solo-reclasificar-docentes
```

Si la base viene de una versión anterior del esquema, `create_all()` no agrega columnas a tablas ya existentes (por ejemplo, falta `estudiantes.fecha_egreso`). Para esos casos, y **solo cuando la base pueda perderse**, usar:

```powershell
.\.venv\Scripts\python.exe -m scripts.cargar_datos_prueba --recrear-tablas
```

Ese flag hace `drop_all()` antes de crear las tablas y cargar; borra todos los datos de las 16 tablas.

Usuarios creados por el cargador (todos con la clave de prueba `Prueba123*`, sobreescribible con `--clave` o la variable `CLAVE_PRUEBA`):

| Usuario | Rol | Nivel |
| --- | --- | --- |
| `admin_prueba` | ADMINISTRADOR | — |
| `secretaria_liceo` | SECRETARIA | LICEO |
| `secretaria_escuela` | SECRETARIA | ESCUELA |

> Son cuentas de prueba: no usar estas claves en un entorno desplegado.

> Los commits antiguos del repositorio todavía contienen `backend/scripts/docentes.sql` y `backend/scripts/horarios_liceo_2026.json`. Su eliminación del historial quedó pendiente de una decisión explícita.

---

## 9. Modelo de datos y orden de carga

### 9.1 Tablas (15)

| Tabla | Propósito |
| --- | --- |
| `usuarios` | Administrador, coordinadores y secretarias |
| `periodos_lectivos` | Años lectivos, cuál está activo y cuál cerrado |
| `representantes` | Datos de contacto de los representantes |
| `grados` | Catálogo fijo de 1 a 11 |
| `asignaturas` | Asignaturas por grado de liceo |
| `asignaturas_docentes` | Vínculo muchos a muchos asignatura-docente |
| `docentes` | Docentes de escuela y liceo |
| `secciones` | Grado + letra + período lectivo |
| `estudiantes` | Estudiante con sección y representante opcional |
| `bloques_horarios` | Jornada institucional (académicos y recesos) |
| `horarios` | Clase de una sección en un bloque y día |
| `pases` | Entradas y salidas de estudiantes |
| `reportes` | Incidencias disciplinarias/académicas |
| `auditorias` | Bitácora de operaciones |
| `documentos_generados` | PDFs de listados generados |

Todas las tablas incluyen `fecha_creacion`, `fecha_actualizacion` y `fecha_eliminacion`. La excepción es `tokens_revocados`: hereda las tres columnas por convención, pero se limpia con `DELETE` físico porque es una tabla de control, no dato de negocio.

### 9.2 Orden recomendado para cargar datos

Por las claves foráneas, el orden seguro es:

1. Usuarios (administrador y operadores).
2. Docentes.
3. Asignaturas.
4. Vínculos `asignaturas_docentes`.
5. Secciones.
6. Representantes.
7. Estudiantes.
8. Horarios.
9. Pases y reportes.

Los PDF de listados se generan desde los endpoints o desde el cierre de año; no se cargan con este orden. Para datos de prueba reales, usar `scripts/cargar_datos_prueba.py` (§ 8.3), que respeta este orden jerárquico.

---

## 10. Guía rápida para el frontend

### 10.1 URL base

En desarrollo, el frontend puede apuntar a:

```text
http://localhost:8000/api
```

Con el futuro empaquetado (frontend servido por el mismo backend) debe usar rutas relativas:

```text
/api
```

No uses `http://localhost:8000` en el build que se ejecutará en otra computadora: `localhost` se resolvería en la máquina del usuario, no en el servidor central.

### 10.2 Flujo de login

```js
const respuesta = await fetch("http://localhost:8000/api/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({
    username: "admin",
    password: "tu_clave",
  }),
});

const { access_token } = await respuesta.json();
```

Guarda el token y envíalo en cada petición:

```js
headers: {
  Authorization: `Bearer ${access_token}`,
}
```

Para cerrar sesión (botón manual **o** temporizador de inactividad), llama `POST /api/auth/logout` con el Bearer token y después borra el token local. Si solo borras el token local, el backend no se entera y un token robado sigue válido hasta `exp`. Cualquier `401` (expirado, revocado, clave cambiada, baja) debe limpiar la sesión en el cliente. Las notas detalladas para `frontend-dev` están en [`docs/ENTREGA_FRONTEND.md`](docs/ENTREGA_FRONTEND.md), sección 11.

### 10.3 Ejemplo de listado paginado

```http
GET /api/estudiantes/?offset=0&size=15&nivel=ESCUELA
Authorization: Bearer <access_token>
```

```json
{
  "items": [
    {
      "id": 1,
      "id_seccion": 1,
      "id_representante": 1,
      "cedula_estudiantil": "V-12345678",
      "primer_nombre": "Ana",
      "segundo_nombre": "María",
      "primer_apellido": "Pérez",
      "segundo_apellido": "Gómez",
      "fecha_nacimiento": "2012-05-10T00:00:00",
      "nivel": "ESCUELA",
      "id_grado": 1,
      "grado_numero": 1,
      "grado_nombre": "1er Grado",
      "seccion_letra": "A",
      "periodo_lectivo": 2026,
      "representante": "Carlos Pérez"
    }
  ],
  "total": 1,
  "offset": 0,
  "size": 15
}
```

### 10.4 Resumen de gestión

El frontend debe llamar a `GET /api/gestion/resumen` al entrar a la sección de Gestión Académica y usar esos valores para los contadores iniciales. Los listados de cada módulo siguen siendo independientes.

### 10.5 CORS

Configuración actual en `backend/app/main.py`:

- `allow_origins=["*"]`
- `allow_credentials=False`
- `allow_methods=["*"]`
- `allow_headers=["*"]`

Con el frontend servido desde el mismo backend y el mismo puerto, las peticiones son del **mismo origen** y CORS no interviene. Para desarrollo con Vite en otro puerto, `*` permite la conexión. El auth usa Bearer, no cookies, por eso `allow_credentials=False` es correcto.

### 10.6 Errores que el frontend debe manejar

- `401`: limpiar sesión y redirigir al login (no hay refresh token).
- `403`: mostrar “sin permisos” o “fuera de tu nivel”.
- `429`: demasiados intentos de login; esperar los segundos indicados en `Retry-After`.
- `404`: recurso inexistente o dado de baja.
- `409`: conflicto de negocio (choque de horario, sección con alumnos, etc.).
- `422`: errores de formulario; `detail` es una lista de campos.

---

## 11. Pendientes y limitaciones conocidas

### 11.1 Entrega y mantenimiento (pendiente)

- Revisión final del frontend contra `docs/ENTREGA_FRONTEND.md`.
- Purgar del historial de Git los archivos antiguos con cédulas (`backend/scripts/docentes.sql`, `backend/scripts/horarios_liceo_2026.json`): requiere autorización explícita porque reescribe commits.
- Push de `backend-dev` a `origin/backend-dev`: solo con autorización explícita.
- Suite formal de `pytest` (hoy los smokes son temporales y se borran) y documentación de despliegue/empaquetado.

### 11.2 Limitaciones actuales

- **No hay Alembic.** `create_all()` no altera tablas existentes. Las migraciones automáticas del arranque son `ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS version_tokens ...` y `ALTER TYPE tipodocumento ADD VALUE IF NOT EXISTS 'docentes'`. Para otros cambios de columna se usa `--recrear-tablas` (destructivo).
- **Logout con revocación por `jti`** y revocación masiva por `version_tokens` (cambio de clave, baja, transferencia de admin).
- **No hay refresh token.** El token dura 360 minutos por defecto.
- **El límite de login es en memoria por proceso.** No sobrevive a reinicios ni es compartido entre workers; en despliegues con balanceador, moverlo a Redis o al gateway.
- **No hay endpoint de restauración** de registros dados de baja.
- **No hay Docker/compose** ni instalador `.exe` todavía.
- La subida de archivos admite solo imágenes; no hay vista previa ni borrado físico de adjuntos.
- El frontend aún no está conectado; este README describe solo el backend.
- La carpeta `backend/scripts/` contiene scripts auxiliares (`generar_sql.py`, `excel.py`, `sembrar_horarios.py`, `crear_admin.py`, `cargar_datos_prueba.py`, `normalizar_textos_auditoria.py`, `regenerar_horarios_pdf.py`) que no forman parte del contrato de la API. Los datos sensibles de nóminas están solo en `backend/scripts/nominas/`, ignorada por Git.

---

## 12. Solución de problemas

### La API no arranca: `SECRET_KEY no está definida`

Falta `SECRET_KEY` en `backend/.env`. Genera una con `secrets.token_urlsafe(48)` y cópiala.

### La API no arranca: `SECRET_KEY es demasiado corta`

Debe tener al menos 32 bytes. No uses el valor de ejemplo del `.env.example`.

### Error al crear extensiones (`unaccent`, `pg_trgm`)

El usuario de PostgreSQL necesita permisos para `CREATE EXTENSION`. Si no los tiene, pídele al administrador de la BD que ejecute:

```sql
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### `relation "..." does not exist`

La API crea las tablas al arrancar. Verifica que hayas iniciado la API al menos una vez con la BD correcta y que `POSTGRES_DB` apunte a la base esperada.

### `python -m scripts.crear_admin` falla porque no hay tablas

Arranca la API una vez (aunque sea para crear el esquema), detenla y vuelve a ejecutar el script.

### La carga de datos falla con `no existe la columna «fecha_egreso»`

La BD tiene un esquema anterior: `create_all()` no agrega columnas a tablas existentes. Si puedes perder los datos, ejecuta `python -m scripts.cargar_datos_prueba --recrear-tablas` (hace `drop_all()` y vuelve a cargar todo).

### El login devuelve `401`

- Verifica que el usuario exista y no esté dado de baja.
- La clave se envía como form-data, no como JSON.
- El script `crear_admin.py` es la única forma de crear el primer administrador.

### Un operador recibe `403` al listar

- Su cuenta debe tener `nivel` (`ESCUELA` o `LICEO`).
- No puede pedir `?nivel=` con el nivel contrario.
- Algunos recursos (usuarios, auditorías, escritura de horarios) son exclusivos del administrador. La lectura de horarios está disponible para cualquier autenticado, filtrada por nivel.

### Un `DELETE` devuelve `409`

El recurso tiene dependencias activas. Revisa el mensaje: por ejemplo, una sección con estudiantes u horarios, o un representante con estudiantes. Primero hay que trasladar/desvincular/dar de baja las dependencias.

---

## Licencia / uso

Proyecto de servicio comunitario. No se incluye una licencia formal en este repositorio.

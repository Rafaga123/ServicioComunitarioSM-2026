# Handoff: API completa del backend para el Frontend

> Actualizado el 27-11-2026 (`backend-dev`, Fases 1–6 completadas: 49 paths / 86 operaciones; ajustes locales sin push)
> Base: `backend/` (FastAPI). URL base: `import.meta.env.VITE_API_URL ?? "http://localhost:8000/api"`
> Auth: `Authorization: Bearer <JWT>` (Bearer en header, CORS: `allow_origins=["*"]`, `allow_credentials=False`, `expose_headers=["Retry-After"]`). Toda respuesta lleva `Cache-Control: private, no-store`: no guardar respuestas de la API en cachés compartidas ni reutilizar PDFs descargados sin volver a pedirlos al backend.
> Fechas de entrada: ISO **sin zona horaria**; el backend las normaliza a Caracas (America/Caracas) por su cuenta.

---

## 1. Convenciones globales

### 1.1 Autenticación

| Método | Ruta | Detalle |
|---|---|---|
| `POST /api/auth/login` | body `application/x-www-form-urlencoded`: `username` (nombre del Usuario), `password` | Devuelve `200 {access_token, token_type: "bearer"}`. `401` si credenciales incorrectas; `429` si se superó el límite de intentos, con header `Retry-After`. |
| `GET /api/auth/me` | — | Devuelve el `PeticionUsuario` del usuario del token. |
| `POST /api/auth/logout` | Bearer token | `204`. Revoca el `jti` del token usado y registra `CIERRE DE SESIÓN`. El token deja de servir de inmediato; el frontend **igual debe borrarlo de localStorage**. Llamarlo dos veces con el mismo token devuelve `204` solo si sigue vigente; si expiró o cambió la clave/rol, devuelve `401`. |

- El JWT es HS256, firmado con `SECRET_KEY`, expira en `ACCESS_TOKEN_EXPIRE_MINUTES` (defecto 360 min).
- Claims del token: `sub` (string con el id del usuario), `rol`, `nivel` (nulo si no hay), `jti` (UUID de la emisión), `ver` (versión de tokens del usuario), `exp` (epoch seconds).
- `401` posibles: `"La sesión ha expirado. Inicia sesión nuevamente."`, `"No se pudieron validar las credenciales (token inválido)"`, `"La sesión fue cerrada. Inicia sesión nuevamente."` y `"La clave o los permisos del usuario cambiaron. Inicia sesión nuevamente."`. En los cuatro casos: limpiar sesión y redirigir al login.
- Los JWT emitidos antes de la revocación no incluyen `jti` ni `ver`: dejan de valer al desplegar. Hay que forzar el login de todos los usuarios.
- Login con demasiados intentos → `429` con `detail` en español y header `Retry-After` (segundos). Mostrar ese tiempo al usuario. El límite por IP incluye los logins correctos (default `20` por minuto por equipo). La cabecera está expuesta en CORS, así que se puede leer también si el frontend apunta directo al backend; con el proxy de Vite funciona sin este ajuste.
- `Content-Type` de todos los POST: `application/json` (excepto login `x-www-form-urlencoded` y uploads multipart).
- Login correcto: auditoría `modulo: "USUARIOS"`, `accion: "INICIO DE SESIÓN"`.
- Cierre de sesión: auditoría `modulo: "USUARIOS"`, `accion: "CIERRE DE SESIÓN"`.
- Textos de auditoría (`modulo`, `accion`, `descripcion`) son legibles: `_` → espacio y `ano`/`anio` → `año`. Ejemplos: `SUBIR_ARCHIVO` → `SUBIR ARCHIVO`, `BLOQUES_HORARIOS` → `BLOQUES HORARIOS`, `1er_ano` → `1er año`. Las rutas y claves de la API no cambian.

### 1.2 Paginación (listados)

Todos los GET que devuelven lista tienen respuesta estándar:

```json
{ "items": [ ... ], "total": 47, "offset": 0, "size": 15 }
```

- `offset`: 0-based (defecto 0, mínimo 0).
- `size`: 1–100 (defecto 15; en buscadores `PaginacionBusqueda` defecto 10).
- **Siempre usar `total`** (conteo sin aplicar offset/size) para mostrar la paginación, no `items.length`.

### 1.3 Errores y códigos

| Status | Uso |
|---|---|
| `200` | GET exitoso, `PUT`/`PATCH` exitoso |
| `201` | POST creado |
| `204` | DELETE/PUT sin contenido de retorno |
| `400` | Validación de datos (campo, rango, duplicado) |
| `401` | Token inválido, expirado, revocado u obsoleto. El frontend debe limpiar la sesión local y redirigir al login; el `detail` distingue las cuatro causas. |
| `403` | Sin rol/nivel permitido |
| `429` | Demasiados intentos de login. Leer `Retry-After` y esperar ese tiempo antes de reintentar. |
| `404` | Registro no encontrado |
| `409` | Conflicto (dependencias, duplicado de nota) |
| `422` | Body inválido (Pydantic) |

### 1.4 Semántica de soft delete

Todos los registros con `fecha_eliminacion` son listados/obtenidos solo si `fecha_eliminacion IS NULL`. DELETE marca la fecha (eliminación lógica; los archivos adjuntos no se borran físicamente).

### 1.5 Fechas, horas y campos auxiliares

- Fechas se envían como ISO sin tzinfo: `YYYY-MM-DDTHH:MM:SS`. El backend las asume en hora de Caracas.
- `id` son enteros autogenerados (PK).
- Campos `fecha_creacion`, `fecha_actualizacion` — audit base, generados por el backend.
- Secciones con grado ESCUELA: 1–6 → `ESCUELA`; LICEO: 7–11 → `LICEO` (CheckConstraint).
- En pases/reportes, `periodo_lectivo` es derivado de la sección del estudiante (solo lectura).
- En `PeticionPase`, `PeticionReporte`, `PeticionEstudiante`, `PeticionSeccion`, `PeticionAsignatura`, `PeticionDocumentoGenerado`: los campos `estudiante`, `cedula_estudiantil`, `usuario`, `docente`, `asignatura`, `grado_numero`, `grado_nombre`, `nivel` (y `seccion_letra` donde aplique) son campos de **apoyo** (joins) para desplegables y listados; pueden ignorarse como dato crítico.
- `archivo_url` **no existe** en los DTOs de escritura de pases/reportes: solo se devuelve en lectura y se actualiza con los endpoints de subida. `fecha_egreso` tampoco se acepta en POST/PUT de estudiantes: solo aparece en lectura.

---

## 2. Roles y niveles (permisos globales)

| Rol | Permisos globales |
|---|---|
| `ADMINISTRADOR` | Todo (catálogos, CRUD, pases/reportes, listados, cierre de año, usuarios, permisos) |
| `COORDINADOR` / `SECRETARIA` | Están limitados a su `nivel`; requieren `nivel` asignado (400/403 si no lo tienen). Sólo pueden operar dentro de pases, reportes, estudiantes, secciones, docentes, asignaturas, horarios (solo lectura), resumen, listados (generar). |

- Roles asignables desde API: `COORDINADOR`, `SECRETARIA` (no se asignan `ADMINISTRADOR` por CRUD).
- Niveles: `ESCUELA`, `LICEO`. Grados: 1–6 → `ESCUELA`, 7–11 → `LICEO`.
- `GET /api/gestion/periodos`, `POST /api/gestion/periodos`, `PATCH /api/gestion/periodos/{id}` → **admin**. `GET /api/gestion/periodos/activo` → personal autenticado (devuelve `null` si no hay periodo activo).
- `POST /api/gestion/cerrar-anio` → **admin**.
- `GET /api/gestion/resumen` → personal autenticado (filtra por nivel).
- `GET /api/usuarios/`, POST/PUT/DELETE `/api/usuarios/{id}`, `POST /api/usuarios/{id}/transferir-admin` → **admin**. `PUT /api/usuarios/me/clave` → cualquier autenticado (solo cambia su propia clave).
- `GET /api/listados/documentos` → personal autenticado con filtro por nivel; `GET /api/listados/documentos/paquete` → **admin**; `POST /api/listados/{tipo}` → personal autenticado.

---

## 3. Entidades y endpoints

---

### 3.1 Usuarios (catálogo, admin)

**`GET /api/usuarios/`** → `RespuestaPaginada<PeticionUsuario>`
`PeticionUsuario = { id: int|null, nombre: str, rol: RolesUsuario, nivel: NivelEducativo|null }`
Filtros: `nivel`, `rol`, `offset`, `size`.

**`POST /api/usuarios/`** — body `CrearUsuario = { nombre: str(1-100), clave: str(8-72), rol: ADMINISTRADOR|COORDINADOR|SECRETARIA, nivel: NivelEducativo }`
→ `201 PeticionUsuario`. 400 si `nombre` duplicado; 400 si coordinador/secretaria sin nivel.

**`GET /api/usuarios/{id}`** → `PeticionUsuario`.

**`PUT /api/usuarios/{id}`** — body `ActualizarUsuario = { nombre?, rol?, nivel?, clave? }` (opcionales; `nombre` 1-100, `clave` 8-72). Si el admin envía `clave`, se hashea y **todas las sesiones de ese usuario quedan revocadas**: deberá iniciar sesión con la clave nueva. → `200 PeticionUsuario`. 400: nombre duplicado, cambio de rol sin nivel, intento de demote a admin. El reset no aplica a cuentas de administrador (se gestionan por transferencia de rol). La clave nunca aparece en la auditoría ni en la respuesta.

**`DELETE /api/usuarios/{id}`** → `204`. 400: no se puede dar de baja a admin (transfiere rol antes).

**`POST /api/usuarios/{id}/transferir-admin`** → `200 PeticionUsuario`.

**`PUT /api/usuarios/me/clave`** — body `CambiarClave = { clave_actual: str, clave_nueva: str(8-72) }` → `204`. 400 si la clave actual no es correcta. Tras el éxito, **todas** las sesiones del usuario quedan revocadas, incluida la que hizo el cambio: hay que volver a loguearse.

---

### 3.2 Grados (catálogo, solo lectura)

**`GET /api/grados/`** → `RespuestaPaginada<PeticionGrado>`; filtro `nivel`.
`PeticionGrado = { id: int, numero: int, nombre: str, nivel: NivelEducativo }`.

**`GET /api/grados/{id}`** → `PeticionGrado`.

Recomendación de campo: `nivel` → filtra secciones/horarios/asignaturas; `numero`+`nivel` suelen venir juntos como clave de UI.

---

### 3.3 Secciones

**`GET /api/secciones/`** → `RespuestaPaginada<PeticionSeccion>`; filtros `nivel`, `id_grado`, `periodo_lectivo`, `offset`, `size`.
**`GET /api/secciones/{id}`** → `PeticionSeccion`.
`PeticionSeccion = { id, id_grado, letra, periodo_lectivo, id_docente_titular?, grado_numero?, grado_nombre?, nivel?, docente_titular? }`

**`POST /api/secciones/`** — body `CrearSeccion = { id_grado: int, letra: "A"|"B"|"U", periodo_lectivo: int (≥2000), id_docente_titular?: int|null }` → `201 PeticionSeccion`.
- `letra` se normaliza a mayúsculas (A/B/U obligatorios).
- Titular debe ser de ESCUELA (solo se puede nombrar a titular a una sección de escuela con docente de escuela).
- 409 si el docente ya es titular de otra sección activa del mismo `periodo_lectivo`: `El docente ya es titular de otra sección en este período lectivo`.
- 400 si ya existe sección activa con ese (grado, letra, periodo_lectivo).

**`PUT /api/secciones/{id}`** — body `ActualizarSeccion = { letra?, periodo_lectivo?, id_docente_titular? }` → `200 PeticionSeccion`.

**`DELETE /api/secciones/{id}`** → `204`. 409 si la sección tiene estudiantes o horarios activos.

Recomendación: `periodo_lectivo` es año del período lectivo (int); `id_docente_titular` nullable; `docente_titular` es nombre completo (apoyo).

---

### 3.4 Representantes

**`POST /api/representantes/`** — body `CrearRepresentante = { primer_nombre, segundo_nombre?, primer_apellido, segundo_apellido?, telefono }` → `201 PeticionRepresentante`.
**`GET /api/representantes/`** → paginado; filtro `nivel` (solo los que tienen estudiante activo en ese nivel).
**`GET /api/representantes/{id}`** → `PeticionRepresentante`.
**`PUT /api/representantes/{id}`** — body opcionales `ActualizarRepresentante = { primer_nombre?, segundo_nombre?, primer_apellido?, segundo_apellido?, telefono? }` → `200`.
**`DELETE /api/representantes/{id}`** → `204`. 409 si tiene estudiantes asignados.
**`POST /api/representantes/{rep_id}/vincular_estudiante/{est_id}`** → `200 { mensaje: "Representante X vinculado exitosamente al estudiante Y" }`.
**`DELETE /api/representantes/{rep_id}/vincular_estudiante/{est_id}`** → `204`. 404 si no está vinculado.

---

### 3.5 Estudiantes

**`POST /api/estudiantes/`** — body `CrearEstudiante = { id_seccion: int, id_representante?: int|null, cedula_estudiantil: str, primer_nombre: str, segundo_nombre?: str|null, primer_apellido: str, segundo_apellido?: str|null, fecha_nacimiento: datetime }` → `201 PeticionEstudiante`.
- 400 si cédula duplicada (activos).
- `fecha_nacimiento`: normalizada a hora de Caracas.

**`GET /api/estudiantes/`** → paginado; filtros `nivel`, `id_grado`, `id_seccion`, `periodo_lectivo`, `offset`, `size`.
**`GET /api/estudiantes/buscar/?termino=...`** → paginado (búsqueda ilike en cedula, primer_nombre, primer_apellido); filtro `nivel`. (Tope por defecto: `size=10`.)
**`GET /api/estudiantes/{id}`** → `PeticionEstudiante`.
**`PUT /api/estudiantes/{id}`** — body `ActualizarEstudiante = { id_seccion?, id_representante?, cedula_estudiantil?, primer_nombre?, segundo_nombre?, primer_apellido?, segundo_apellido?, fecha_nacimiento? }` → `200`.
**`DELETE /api/estudiantes/{id}`** → `204`.

`PeticionEstudiante = { id, id_seccion, id_representante?, cedula_estudiantil, primer_nombre, segundo_nombre?, primer_apellido, segundo_apellido?, fecha_nacimiento, nivel, id_grado, grado_numero?, grado_nombre?, seccion_letra?, periodo_lectivo?, representante? }`

Recomendación de campos:
- `id_seccion`: FK a sección activa. UI: select tipo "1er Año A", construido con `grado_numero + seccion_letra`.
- `cedula_estudiantil`: única entre activos (validar en cliente antes de POST).
- `fecha_nacimiento`: display "Edad: N años".
- `periodo_lectivo`: **solo-lectura** (apoyo).
- `fecha_egreso`: aparece en la lectura (`PeticionEstudiante`); no se acepta en POST/PUT y solo lo escribe el backend durante el cierre de año. Un egresado sale de listados/búsquedas y de pases, reportes y horarios, pero su ficha sigue consultable por `id`.

---

### 3.6 Docentes (admin)

**`GET /api/docentes/`** → paginado; filtro `nivel`.
**`GET /api/docentes/{id}`** → `PeticionDocente`.
**`POST /api/docentes/`** — body `CrearDocente = { primer_nombre, segundo_nombre?, primer_apellido, segundo_apellido?, cedula: str, nivel }` → `201 PeticionDocente`. 400 si cédula duplicada.
**`PUT /api/docentes/{id}`** — body `ActualizarDocente = { ...opcionales }` → `200`.
**`DELETE /api/docentes/{id}`** → `204`. 409 si tiene secciones asignadas, horarios o asignaturas vinculadas.

Recomendación: mostrar `cedula` como identificador principal; `nivel` obligatorio.

---

### 3.7 Asignaturas

**`GET /api/asignaturas/`** → paginado; filtros `nivel`, `id_grado`, `periodo_lectivo`, `offset`, `size`.
**`GET /api/asignaturas/{id}`** → `PeticionAsignatura` (incluye `docentes: PeticionDocente[]` vinculados).
**`POST /api/asignaturas/`** — body `CrearAsignatura = { id_grado: int, nombre: str, periodo_lectivo?: int (≥2000) }` → `201 PeticionAsignatura`.
- Solo grados de LICEO. 400 si grado no es liceo.
- `periodo_lectivo` opcional: si se omite, el servidor usa el periodo activo; 400 si no hay activo ("No hay periodo lectivo activo; selecciona uno explícitamente.").
- 400 si ya existe asignatura activa en ese grado+nombre+periodo.
**`PUT /api/asignaturas/{id}`** — body `ActualizarAsignatura = { id_grado?, nombre? }` → `200`.
- `periodo_lectivo` no se puede cambiar → 400 ("El periodo lectivo de una asignatura no puede cambiar después del registro...").
- 409 si la asignatura tiene horarios activos (cambio de grado).
**`DELETE /api/asignaturas/{id}`** → `204`. 409 si tiene horarios/vinculaciones activas.
**`GET /api/asignaturas/{id}/docentes`** → `list[PeticionDocente]`.
**`POST /api/asignaturas/{id}/docentes/{docente_id}`** → `200 { mensaje }`. 400 si docente no es de liceo o ya vinculado.
**`DELETE /api/asignaturas/{id}/docentes/{docente_id}`** → `204`.

---

### 3.8 Bloques Horarios (jornada institucional del liceo, admin)

**`GET /api/bloques-horarios/`** → paginado; filtro `tipo` (ACADEMICO|RECESO).
**`GET /api/bloques-horarios/{id}`** → `PeticionBloqueHorario`.
**`POST /api/bloques-horarios/`** — body `CrearBloqueHorario = { orden: int(1-10), numero?: int(1-8), nombre: str, tipo: ACADEMICO|RECESO, hora_inicio: time, hora_fin: time }` → `201 PeticionBloqueHorario`.
**`PUT /api/bloques-horarios/{id}`** — body `ActualizarBloqueHorario = { orden?, numero?, nombre?, tipo?, hora_inicio?, hora_fin? }` → `200`.
**`DELETE /api/bloques-horarios/{id}`** → `204`.
Validaciones: `orden` único (activos), `hora_fin > hora_inicio`, académico ⇒ 1≤numero≤8, receso ⇒ numero null.

Recomendación: UI de grilla: lista `/api/bloques-horarios/` para definir los tramos de la jornada.

---

### 3.9 Horarios

**`GET /api/horarios/registros/`** → paginado `PeticionHorario`; filtros: `id_seccion`, `id_grado`, `id_asignatura`, `id_docente`, `id_bloque`, `periodo_lectivo`, `dia_semana` (1-5), `nivel`, `offset`, `size`.
Orden: `dia_semana`, luego `bloque.orden`.
**`GET /api/horarios/registros/{id}`** → `PeticionHorario`.
- Los dos `GET` de registros son de lectura para cualquier autenticado, filtrados por nivel; `POST/PUT/DELETE` siguen siendo solo administrador. Una cuenta de `ESCUELA` recibe `200` con lista vacía porque no hay horarios de ese nivel; si fuerza `?nivel=LICEO`, recibe `403`.
**`POST /api/horarios/registros/`** — body `CrearHorario = { id_seccion, id_bloque, id_asignatura, id_docente, periodo_lectivo (≥2000), dia_semana (1-5) }` → `201 PeticionHorario`.
**`PUT /api/horarios/registros/{id}`** — body `ActualizarHorario = { id_seccion?, id_bloque?, id_asignatura?, id_docente?, periodo_lectivo?, dia_semana? }` → `200`.
**`DELETE /api/horarios/registros/{id}`** → `204`.
**`GET /api/horarios/?id_estudiante=..&fecha=YYYY-MM-DD&id_bloque=?|hora=?`** → `PeticionConsultaHorario = { encontrado, id_horario?, id_bloque?, id_asignatura?, id_docente?, asignatura?, docente?, bloque?, hora_inicio?, hora_fin? }`.
- 400 si no se pasa `id_bloque` ni `hora`.
- Se aceptan los dos años del periodo: con `periodo_lectivo=2026`, una fecha de 2026 o 2027 es válida. Un estudiante egresado devuelve `encontrado=false`.

Validaciones de negocio (código):
- Solo secciones de LICEO.
- El periodo debe existir y no estar cerrado: `400 "El periodo lectivo no existe o está cerrado"` al crear o editar.
- `seccion.periodo_lectivo == periodo_lectivo`.
- Solo bloques académicos.
- `asignatura.id_grado == seccion.id_grado` y `asignatura.periodo_lectivo == periodo_lectivo`.
- Solo docentes de LICEO y vinculados a la asignatura.
- Colisión: no puede haber otra clase de la misma sección + bloque + periodo + día, ni de la misma clase del mismo docente + bloque + periodo + día. (409)
- 409 si el docente es titular de otra sección: `El docente es titular de otra sección y no puede impartir clases fuera de ella`. Puede dar clases en la sección que titula.
- Rango de bloques: `hora_inicio` ≥ 07:00 y `hora_fin` ≤ 12:40 (400 si fuera); 409 si `orden` duplicado o bloque solapado.
- Recomendación: desplegables: usar los campos de apoyo (`seccion`, `grado`, `nivel`, `bloque`, `asignatura`, `docente`) de `PeticionHorario`; la malla se construye con `hora_inicio`/`hora_fin` del bloque.

Recomendación de campos: `PeticionHorario` devuelve los nombres interpolados (`seccion`, `grado`, `bloque`, `asignatura`, `docente`) para desplegables directos; `hora_inicio`/`hora_fin` vienen del bloque.

---

### 3.10 Períodos lectivos (gestión)

- `GET /api/gestion/periodos` (admin) → `[PeticionPeriodoLectivo]` (`{ id, anio, activo, cerrado }`), orden desc por anio.
- `GET /api/gestion/periodos/activo` (personal autenticado) → `PeticionPeriodoLectivo | null` (null si no hay periodo activo).
- `POST /api/gestion/periodos` (admin) — body `CrearPeriodoLectivo = { anio (≥2000), activo: bool }` → `201 PeticionPeriodoLectivo`. 400 si ya existe año. Al activar, desactiva los otros periodos activos. `cerrado` siempre false al crear.
- `PATCH /api/gestion/periodos/{id}` (admin) — body `ActualizarPeriodoLectivo = { activo?: bool, cerrado?: bool }` → `200 PeticionPeriodoLectivo`.
  - Activar (`activo=true`): desactiva los otros activos y desactiva `cerrado`.
  - Rechaza `cerrado=true` (400: solo `POST /api/gestion/cerrar-anio` cierra periodos).
  - Rechaza activar un periodo cerrado (400).

PeticionPeriodoLectivo = `{ id: int|null, anio: int (≥2000), activo: bool, cerrado: bool }`



---

### 3.11 Resumen de gestión

`GET /api/gestion/resumen` → `PeticionResumenGestion = { nivel, periodo_lectivo, representantes, estudiantes, secciones, docentes, asignaturas, horarios, pases, reportes }`.
Parámetros: `nivel` (opcional; admin puede pedir ambos niveles, personal restringido a su nivel) y `periodo_lectivo` (opcional; por defecto el activo).

- Con periodo activo, todos los contadores se filtran por ese año, excepto `docentes`, que se cuenta globalmente dentro del nivel.
- Sin periodo activo y sin parámetro, `periodo_lectivo` vuelve `null` en los listados y el resumen devuelve contadores en `0` (docentes global).

---

### 3.12 Cierre de año (admin)

> **Estado para esta entrega: fuera de alcance.** El endpoint existe, está implementado y documentado, pero el frontend no expone ruta ni menú y **no debe ejecutarse sobre la BD institucional** en esta entrega. Si se habilita más adelante, ante `409` recargar `GET /api/gestion/periodos` sin reintentar el cierre.

**`POST /api/gestion/cerrar-anio`** — body `SolicitudCierreAnio = { periodo_actual: int (≥2000), periodo_siguiente: int (≥2000) }` → `200 PeticionCierreAnio`.

```json
PeticionCierreAnio = {
  "periodo_cerrado": int,
  "periodo_activado": int,
  "documentos_generados": int,
  "estudiantes_promovidos": int,
  "egresados": int,
  "secciones_creadas": int,
  "asignaturas_creadas": int
}
```

Errores (los códigos de negocio están declarados en OpenAPI; `422` es la validación automática del body):
- `400`: el periodo actual debe estar **activo** y no cerrado; `periodo_siguiente` debe ser > `periodo_actual`; si el periodo siguiente ya existe cerrado o con secciones se rechaza; si falta un grado destino en el catálogo se devuelve `No existe el grado destino X en el catálogo de grados`.
- `404`: `Periodo lectivo no encontrado` si no existe `periodo_actual`. Si no existe `periodo_siguiente`, se crea automáticamente (activo, sin secciones).
- `409`: si dos administradores cierran el mismo periodo a la vez, el segundo recibe `El periodo ya fue cerrado por otra solicitud`. No reintentar el cierre; recargar `GET /api/gestion/periodos`.
- `500`: `No se encontró la sección destino para promover un estudiante` si el catálogo de grados/secciones está inconsistente.

Efectos (orden):
1. Genera y guarda PDFs por **sección activa** del periodo actual: nóminas y representantes para todas las secciones; horarios solo para las de LICEO. También genera el listado general de docentes por nivel. Los PDFs se preparan en staging y se mueven al destino solo si toda la operación tiene éxito; si falla, se revierten. Se registran en `DocumentosGenerados` (`GET /api/listados/documentos`). `documentos_generados` cuenta solo los PDFs movidos: con `REUTILIZAR_DOCUMENTOS_IGUALES=True`, los documentos cuya firma ya existe se reutilizan y no se cuentan ni se registran de nuevo.
2. Traspaso de estudiantes activos: 6to Grado → 1er Año; grados intermedios → siguiente grado; 5to Año → egreso (`fecha_egreso`).
3. Crea en el periodo siguiente las combinaciones grado+letra que existían **y las de grado+1 hacia las que se promueve** (`secciones_creadas` incluye ambas), sin docentes titulares; copia los nombres de asignaturas de liceo del periodo actual, sin docentes.
4. Cierra el periodo actual (`cerrado=true`) y desactiva otro activo; activa el periodo siguiente.

Recomendación: mostrar un summary post-cierre con los 7 campos.

---

### 3.13 Pases

`PeticionPase = { id, id_estudiante, id_usuario, id_docente?, id_asignatura?, tipo: SALIDA|ENTRADA, motivo, fecha, periodo_lectivo?, autorizador?, archivo_url?, archivo_nombre?, archivo_mime?, archivo_tamano?, archivo_hash?, archivo_subido_por?, archivo_fecha?, estudiante?, cedula_estudiantil?, nivel?, usuario?, docente?, asignatura? }`

- `GET /api/pases/` → paginado; filtros `id_estudiante`, `id_seccion`, `tipo`, `anio`, `mes` (1-12), `periodo_lectivo`, `nivel`; orden `fecha desc`.
- `GET /api/pases/{id}` → `PeticionPase`.
- `GET /api/pases/{id}/pdf` → `application/pdf` con `Content-Disposition: attachment; filename="pase-{id}.pdf"`. Formato **básico provisional**: tabla campo/detalle con el membrete de los listados; se ajustará el diseño después, sin cambiar ruta ni MIME. `404` si el pase no existe; `403` si es de otro nivel. Registra auditoría `GENERAR` en `PASES`. Llámalo directamente (sin caché: ver nota global de `Cache-Control`). La exportación se mantiene; el **adjunto PDF opcional** ya está soportado en `POST /api/pases/{id}/archivo` (ver §4). Si la UI no expone el botón, el endpoint queda disponible sin uso.
- `POST /api/pases/` — body `CrearPase = { id_estudiante, id_docente?, id_asignatura?, tipo?: SALIDA|ENTRADA (defecto ENTRADA), motivo: str, fecha: datetime, autorizador?: str }` → `201 PeticionPase`. No acepta `archivo_url`.
  - Validaciones: nivel del estudiante; docente pertenece al nivel del estudiante; asignatura pertenece al grado del estudiante; docente vinculado a la asignatura; el **cuarto pase activo del mes del mismo tipo requiere autorizador** (400).
- `PUT /api/pases/{id}` — body `ActualizacionPase = { id_docente?, id_asignatura?, tipo?, motivo?, fecha?, autorizador? }` → `200 PeticionPase`. Tampoco acepta `archivo_url`.
- `DELETE /api/pases/{id}` → `204`.
- **Adjuntos (pases)**:
  - `POST /api/pases/{id}/archivo` — multipart field `archivo` → `200 PeticionPase` (metadatos actualizados).
  - `GET /api/pases/{id}/archivo?inline=false|true` → `FileResponse` (media_type de `archivo_mime`; disposition `attachment` / `inline`). 409 si el archivo físico no existe.
  - `DELETE /api/pases/{id}/archivo` → `204`. (Solo desvincula; el archivo físico queda en disco.)

Recomendación de campos: `archivo_tamano` en bytes; `archivo_url` solo legible via `GET /api/pases/{id}/archivo`; `autorizador` obligatorio al 4º pase activo del mes del mismo tipo (los 1-3 sin; mostrar advertencia si se sucede sin autorizador).

---

### 3.14 Reportes

`PeticionReporte = { id, id_estudiante, id_usuario, id_docente?, id_asignatura?, articulo, reglamento, incidencia, defensa, nivel_gravedad, categoria, fecha, periodo_lectivo?, archivo_url?, archivo_nombre?, archivo_mime?, archivo_tamano?, archivo_hash?, archivo_subido_por?, archivo_fecha?, estudiante?, cedula_estudiantil?, nivel?, usuario?, docente?, asignatura? }`

- `GET /api/reportes/` → paginado; filtros `id_estudiante`, `id_seccion`, `id_docente`, `anio`, `mes` (1-12), `periodo_lectivo`, `categoria: CONDUCTUAL|ACADEMICO`, `nivel_gravedad: LEVE|GRAVE`, `nivel`; orden `fecha desc`.
- `GET /api/reportes/{id}` → `PeticionReporte`.
- `GET /api/reportes/{id}/pdf` → `application/pdf` con `Content-Disposition: attachment; filename="reporte-{id}.pdf"`. Mismo formato básico provisional que el PDF de pases (campo/detalle + membrete); el diseño se ajustará después sin cambiar ruta ni MIME. `404` si el reporte no existe; `403` si es de otro nivel. Registra auditoría `GENERAR` en `REPORTES`. Es el endpoint que habilita el botón "Exportar PDF" de `ReporteFicha.vue`. La exportación se mantiene; el **adjunto PDF opcional** ya está soportado en `POST /api/reportes/{id}/archivo` (ver §4).
- `POST /api/reportes/` — body `CrearReporte = { id_estudiante, id_docente?, id_asignatura?, articulo: int (≥1), reglamento: LOPNNA|LOE|CBV|NC, incidencia: str, defensa: str, nivel_gravedad?: LEVE|GRAVE (defecto LEVE), categoria: CONDUCTUAL|ACADEMICO, fecha: datetime }` → `201 PeticionReporte`. No acepta `archivo_url`.
  - `id_asignatura` es opcional y registra la materia durante la incidencia: debe estar activa y ser del grado del estudiante. Si además se envía `id_docente`, debe estar vinculado a esa asignatura. El frontend actual puede seguir enviando solo `id_docente`; el campo nuevo es retrocompatible.
- `PUT /api/reportes/{id}` — body `ActualizarReporte = { id_docente?, id_asignatura?, articulo?, reglamento?, incidencia?, defensa?, nivel_gravedad?, categoria?, fecha? }` → `200 PeticionReporte`. Tampoco acepta `archivo_url`. Enviar `id_asignatura: null` lo desvincula.
- `DELETE /api/reportes/{id}` → `204`.
- **Adjuntos (reportes)**: idénticos a pases (`POST/GET/DELETE /api/reportes/{id}/archivo`).

---

### 3.15 Listados (PDFs de nóminas, representantes, horarios)

- `POST /api/listados/{tipo}` — `tipo ∈ {nominas, representantes, horarios, docentes}` (strings minúsculas de `TipoDocumento`). Body `SolicitudListado = { periodo_lectivo?: int, nivel?: NivelEducativo, id_grado?: int, id_seccion?: int }` → `201 PeticionDocumentoGenerado`.
  - Reglas:
    - `id_seccion`: el periodo del listado = `seccion.periodo_lectivo`; si el cliente pide otro, 400.
    - `id_grado` sin sección: genera nóminas o representantes de ese grado; 400 si el nivel no coincide.
    - `id_grado` e `id_seccion` juntos: 400 ("Indica una sección o un grado, no ambos").
    - `horarios` requieren `id_seccion` de **liceo** (400 sin sección o si la sección es de ESCUELA).
    - `docentes` es general por nivel: 400 si se envía `id_seccion` o `id_grado`.
    - `periodo_lectivo` opcional: si se omite se usa el activo; 400 si no hay activo y no se indicó uno. Si se envía, **debe existir** (`_validar_periodo_lectivo`: 404 "Periodo lectivo no encontrado").
    - Sin `id_seccion` ni `id_grado`, el nivel es obligatorio (400 "Necesita indicar nivel para listados generales").
    - Validación de acceso por nivel del usuario.
  - Matriz de body:
    - General por nivel: `{ "nivel": "LICEO" }`.
    - General por grado: `{ "id_grado": 5 }`.
    - Por sección: `{ "id_seccion": 10 }`.
    - Docentes: `{ "nivel": "LICEO" }`.
    - Horarios: `{ "id_seccion": 10 }` de LICEO.
  - `PeticionDocumentoGenerado = { id?, tipo, periodo_lectivo?, nivel?, id_grado?, id_seccion?, nombre_archivo, ruta_relativa, hash, tamano, mime, fecha_generacion, generado_por?, grado_numero?, grado_nombre? }`.
  - El frontend usa el `id` devuelto para descargar; no envía `nombre_archivo`, `ruta_relativa`, `hash` ni `tamano`, y no usa `ruta_relativa` como URL.
  - Duplicados: si el servidor tiene `REUTILIZAR_DOCUMENTOS_IGUALES=True`, una petición repetida con los mismos datos devuelve el `id` del PDF ya generado (sigue siendo `201`, sin crear archivo) y registra auditoría `REUTILIZAR`. Si los datos cambiaron, devuelve un `id` nuevo con sufijo `_v2`, `_v3`, …. Con el flag en `False` (default), siempre se crea un documento nuevo. El frontend debe usar siempre el `id` de la respuesta, sin asumir que será distinto.
- `GET /api/listados/documentos` (autenticado, según nivel) → paginado de `PeticionDocumentoGenerado`; filtros `tipo`, `periodo_lectivo`, `nivel`, `id_grado`, `id_seccion`. El operador solo ve su nivel; el admin ve ambos. Un operador que fuerce otro `?nivel=` recibe `403`.
- `GET /api/listados/documentos/paquete?tipo&periodo_lectivo` (admin) → `application/zip`, `Content-Disposition: attachment; filename="listados.zip"` con todos los PDFs de ese tipo+periodo.
- `GET /api/listados/documentos/{documento_id}/archivo` → `FileResponse` PDF (`attachment`). El frontend debe llamarlo con el `id`; `404` si no existe, está dado de baja, la ruta es inválida o el archivo no está en disco. El nivel se valida también para documentos antiguos con `nivel` nulo.

- Estructura física dentro de `STORAGE_ROOT` (`{etiqueta}/...`, donde la etiqueta de `2026` es `2026-2027`):

  ```text
  2026-2027/
  ├─ pases/{nivel}/{grado}/{letra}/estudiante-{id}/archivo.ext
  ├─ reportes/{nivel}/{grado}/{letra}/estudiante-{id}/archivo.ext
  ├─ listados/{tipo}/{nivel}/{grado}/{letra}/archivo.pdf
  └─ listados/{tipo}/{nivel}/generales/archivo.pdf
  ```

- Ejemplo por sección: `2026-2027/listados/nominas/LICEO/1er_ano/A/nomina_2026-2027_1er_ano_A.pdf`. General por nivel: `2026-2027/listados/nominas/LICEO/generales/nomina_2026-2027_LICEO_general.pdf`. General por grado: `.../generales/nomina_2026-2027_1er_ano.pdf`. Si el nombre ya existe se usa `_v2`, `_v3`, etc.
- Formato del encabezado de los PDFs (hoja carta, margen izquierdo 4 cm y 3 cm en los demás):
  - Título por sección: `UNIDAD EDUCATIVA PRIVADA SANTA MARTA — Listado de estudiantes 2026-2027/1er Grado "U"`.
  - Título general por nivel: `UNIDAD EDUCATIVA PRIVADA SANTA MARTA — Listado de estudiantes 2026-2027/ESCUELA general` (equivalente para `representantes` y `docentes`).
  - Título general por grado: `UNIDAD EDUCATIVA PRIVADA SANTA MARTA — Listado de estudiantes 2026-2027/1er Grado general`.
  - Línea de metadatos, sin comillas: `ESCUELA • 1er Grado U • 2026-2027`.
  - Las nóminas generales se ordenan por grado, sección y apellidos; los representantes generales por apellido del representante.
- Los representantes de ESCUELA cargados desde el PDF original solo tienen teléfono (no nombre): en la columna `Representante` del PDF se muestra `-`. Los representantes de LICEO conservan sus nombres reales.
- PDF de `horarios` (solo LICEO): encabezado `UNIDAD EDUCATIVA PRIVADA SANTA MARTA — HORARIO DE CLASES`; tabla de 12 filas (periodo/curso/sección, `Hora | LUNES | MARTES | MIERCOLES | JUEVES | VIERNES`, y los bloques `7:00-7:40`, `7:40-8:20`, `8:20-8:40` (RECESO), `8:40-9:20`, `9:20-10:00`, `10:10-10:10` (RECESO), `10:10-10:50`, `10:10-11:30`, `11:30-12:10`, `12:10-12:40`). Los recesos muestran `RECESO` en las columnas de los días; las celdas libres muestran `/`. Después se lista `Docentes:` con una línea `Materia: Docente` por cada asignatura de esa sección.
- PDF de `docentes`: columnas `Cédula | Docente | Asignaturas` en LICEO y `Cédula | Docente | Grado/Sección` en ESCUELA; una fila por docente activo del nivel. En LICEO cada materia lleva el año (`Matemática 1er Año`) y se deduplica por materia+año; en ESCUELA se listan los grados/secciones donde el docente es titular (o `-` cuando no tiene). El cargador de prueba reclasifica automáticamente a ESCUELA los docentes sin asignaturas ni horarios activos.

---

### 3.16 Auditorías

- `GET /api/auditorias/` (admin) → paginado `PeticionAuditoria = { id, usuario_id, usuario?, modulo, accion, descripcion, fecha_creacion }`. Filtros: `usuario` (ilike en nombre), `modulo` (ilike), `accion` (ilike), `fecha` (date). Orden: `fecha_creacion desc`.
- `GET /api/auditorias/{id}` → `PeticionAuditoria`.
- Los inicios de sesión correctos aparecen como `modulo: "USUARIOS"`, `accion: "INICIO DE SESIÓN"`; el `usuario_id` es el mismo valor del claim `sub` del token.
- El cierre de sesión registra `USUARIOS` / `CIERRE DE SESIÓN`. Los PDFs de pases y reportes registran `PASES` / `REPORTES` / `GENERAR`.
- `REUTILIZAR` solo se registra si el servidor corre con `REUTILIZAR_DOCUMENTOS_IGUALES=True` (en desarrollo local está `True`; el default de código/producción es `False`). Con el flag en `False` no habrá eventos `REUTILIZAR` para verificar.
- `CIERRE AÑO` existe en el backend pero no se verá en esta entrega porque el cierre está fuera de alcance.

---

## 4. Adjuntos: semántica completa

- **Subida** (`POST /api/pases/{id}/archivo`, `POST /api/reportes/{id}/archivo`):
  - Campo multipart: `archivo` (campo pela).
  - Validación (400): extensión ∉ {jpg, jpeg, png, webp, pdf}; firma binaria no reconocida o distinta de la extensión; tamaño > `ARCHIVOS_MAX_BYTES` (5 MB). El MIME se calcula desde los bytes, no desde el `Content-Type` enviado.
  - Nombre base sanitizado (sin nulos/dirs/`..`), ≤100 chars y legible: `_` → espacio y `ano`/`anio` → `año`. Ejemplo: `evidencia_anio_2026.png` → `evidencia año 2026.png`. Es el `archivo_nombre` que se devuelve y se usa al descargar.
  - Ruta relativa generada: `{etiqueta}/{pases|reportes}/{nivel_lower}/{slug_grado}/{letra_upper}/estudiante-{id}/{id_registro}_{uuid8}.{ext}` (slugs: 1→`1er_grado`, 7→`1er_ano`, ...). La etiqueta del periodo activo `2026` es `2026-2027`.
  - `archivo_url` en la respuesta = esa ruta relativa; también `archivo_mime`, `archivo_tamano` (bytes), `archivo_hash` (SHA-256 hex), `archivo_subido_por` (id del usuario), `archivo_fecha` (Caracas).
- **Descarga**: solo por `GET /api/{pases,reportes}/{id}/archivo`. `?inline=true` → `Content-Disposition: inline`; por defecto `attachment`. 409 si el archivo físico no existe.
- **Quitar adjunto** (`DELETE /api/{pases,reportes}/{id}/archivo`): solo desvincula (metadatos en null). El archivo físico queda en `STORAGE_ROOT` (no hay endpoint de borrado físico).

---

## 5. Archivos en disco (STORAGE_ROOT, default `C:\sistema`)

- `archivo_url` (pases/reportes) — ruta relativa segura dentro de `STORAGE_ROOT`; validada en ingreso (`422` si absoluta, con `..`, o vacía).
- `ruta_relativa` (listados) — de `GET /api/listados/documentos/{id}/archivo`.

---

## 6. Ejemplos (axios)

### 6.1 Login

```js
import axios from "axios";
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api",
});

const params = new URLSearchParams({ username: "admin", password: "password123" });
const { data } = await api.post("/auth/login", params, {
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
});
// { access_token, token_type }
api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;
```

### 6.2 Listados paginados (buscadores: default size 10)

```js
const { data } = await api.get("/estudiantes/", { params: { offset: 0, size: 15, termino: undefined } });
// data = { items: [...], total: 47, offset: 0, size: 15 }
```

### 6.3 Upload de adjunto + descarga (blob)

```js
// Subir
const form = new FormData();
form.append("archivo", fileInput.files[0]); // campo multipart
const r = await api.post(`/pases/${id}/archivo`, form);
// r.data = PeticionPase (metadatos actualizados)

// Descargar
const { data } = await api.get(`/pases/${id}/archivo`, { responseType: "blob" });
const url = URL.createObjectURL(data);
const a = document.createElement("a");
a.href = url;
a.download = r.data.archivo_nombre ?? `pase-${id}`;
a.click();
URL.revokeObjectURL(url);
```

### 6.4 Descargar ZIP de listados

```js
const res = await api.get(`/listados/documentos/paquete?tipo=nominas&periodo_lectivo=2027`, {
  responseType: "blob",
});
// media_type application/zip, filename listados.zip
```

---

## 7. Recomendaciones de campos (semántica de negocio)

Consulte las columnas `id_*`, `periodo_lectivo`, `fecha_*` y los campos `*_apoyo` para filtros y grids.

| Entidad | Campo | Recomendación |
|---|---|---|
| Estudiantes | `id_seccion` | Select dependiente: opciones de `/api/secciones/` (filtra por periodo activo) |
| Estudiantes | `cedula_estudiantil` | Única activa; validar duplicada cliente antes de POST (400) |
| Estudiantes | `fecha_egreso` | Entra en respuestas desde 6.6; informativo |
| Secciones | `letra` | `A|B|U`; UI: enums del backend |
| Secciones | `id_docente_titular` | Solo ESCUELA; desplegable de docentes de escuela |
| Asignaturas | `periodo_lectivo` | Aparece en PUT pero no se edita; default activo |
| Pases | `tipo` | Enum `ENTRADA|SALIDA` |
| Pases | `autorizador` | Mostrar aviso si se usa sin adjunto y no hay referencia externa |
| Pases/Reportes | `archivo_url` | solo lectura; se actualiza con `POST /{id}/archivo` y se desvincula con `DELETE /{id}/archivo` (no se acepta en POST/PUT) |
| Pases/Reportes | `archivo_hash` | De-dup posible |
| Listados | `ruta_relativa` | Rota dentro de STORAGE_ROOT; usar solo con `archivo_url` de documento |
| Periodos | `activo` | Radio button; en POST debe ir `activo: true` si quieres activo nuevo |
| Periodos | `cerrado` | No editable desde UI (solo por cierre) |
| Resumen | `nivel` | Filtro del perfil del usuario (admin puede elegir ambos) |
| Cierre | `periodo_siguiente` | Requiere ser > periodo_actual; validar duplicado con `GET /api/gestion/periodos` |

---

## 8. Semántica del liceo vs escuela

- Grados: `1-6` = `ESCUELA`, `7-11` = `LICEO` (`CheckConstraint`).
- Horarios y bloques académicos (1-8): **solo secciones de LICEO**.
- Nóminas, representantes y horarios en listados: se generan por sección activa; horarios solo de secciones de liceo. Docentes se genera de forma general por nivel.

---

## 9. Notas de integración

- `GET /` → `{ "status": "Ok" }`; `GET /health` → `{ status: "ok", database: "ok" }`.
- Validaciones 422 de Pydantic (errores en formato estándar FastAPI: `{ detail: [...] }`).
- Validaciones 422 de rutas relativas: `archivo_url` entrante se valida como relativa (path traversal/absoluta → 422).
- `FileResponse` importado de `fastapi.responses` (no de `fastapi`).
- Auditorías se registran automáticamente en los CRUD (no necesitan llamada por el frontend).

---

## 10. Curiosidad / semánticas extra

- `filtro_activos`: todos los GET listan/1-1 solo con `fecha_eliminacion IS NULL`.
- `Buscar estudiantes`: `filtro_texto` usa `unaccent` + `ilike` — no necesita acentos del usuario.
- `Consulta horario`: no usar hora suelta; requiere `id_bloque` o `hora` (400 si ambos null).
- `cedula` de docente y `cedula_estudiantil`: únicas activas por separado.
- El id del usuario de auditoría = token `sub` (cambia si se re-autentica).

---

## 11. Pendientes / notas para el compañero de frontend

> Esta rama (`backend-dev`) no modifica `frontend/src`. Son anotaciones para la rama `frontend-dev`.

### 11.1 Sesión, logout y expiración del JWT

- Botón **Cerrar sesión**: llamar `POST /api/auth/logout` con el Bearer token **antes** de borrar `localStorage.token`. El backend revoca el `jti` y audita el cierre; si solo se borra el token local no queda auditoría **ni revocación**.
- Un segundo logout con el mismo token devuelve `204` solo mientras siga vigente; si expiró o cambió la clave/rol, devuelve `401`. En ese caso limpia la sesión local sin reintentar.
- **Inactividad:** el temporizador (o `visibilitychange/focus`) debe ejecutar el **mismo** `POST /api/auth/logout` antes de limpiar `localStorage` y el estado de `auth.js`. El frontend decide **cuándo** cerrar; el backend decide que el token **ya no sirve**. Sin esa llamada, un token robado sigue válido hasta `exp`.
- El `exp` del token viaja en el claim `exp` (epoch seconds). Comparar `exp * 1000 <= Date.now()` para detectar expiración local. `sincronizarSesion()` de `auth.js` solo lo revisa al cargar el módulo, así que hace falta un temporizador.
- Cualquier `401` (expirado, inválido, cerrado, clave cambiada, usuario dado de baja o admin transferido) debe limpiar token y estado reactivo y redirigir al login. No hace falta distinguirlos en la UI: todos terminan en la misma pantalla.
- `429` en login: mostrar `Retry-After` y deshabilitar el botón ese tiempo. No reintentar automáticamente en bucle.
- Opcional: al iniciar la app llamar `GET /api/auth/me` para validar el token contra el backend. Es la forma de detectar revocaciones ocurridas mientras el usuario estaba fuera.

### 11.2 Listados y botones de exportar (aún sin UI)

El backend ya expone todo; falta conectar botones en frontend:

- `POST /api/listados/{tipo}` con `tipo ∈ nominas|representantes|horarios|docentes`. Body `SolicitudListado`: `nivel`, `periodo_lectivo`, `id_grado`, `id_seccion`. `horarios` exige `id_seccion` de LICEO; `docentes` es general por nivel.
- `GET /api/listados/documentos?tipo=&periodo_lectivo=&nivel=&id_grado=&id_seccion=&offset=&size=` → historial paginado; el operador queda limitado a su nivel y el admin ve ambos.
- `GET /api/listados/documentos/{documento_id}/archivo` → usar `apiDescargar` (attachment PDF).
- `GET /api/listados/documentos/paquete?tipo=&periodo_lectivo=` → ZIP (admin).
- Sugerencia: en la vista de gestión, un botón «Generar PDF» por sección para nóminas/representantes/horarios y uno por nivel para docentes; luego una tabla con «Descargar» y «Descargar paquete».

### 11.3 Auditorías visibles

- No hace falta enviar texto desde el frontend: el backend normaliza los textos al guardar (`SUBIR ARCHIVO`, `CIERRE AÑO`, `2026-2027`, `1er año`, etc.).
- Las auditorías históricas se normalizaron con `python -m scripts.normalizar_textos_auditoria` (ejecutado en esta rama).

### 11.4 Titular único por sección

- El backend ya rechaza con `409` asignar el mismo docente como titular de dos secciones del mismo período. En el desplegable de titulares conviene ocultar/inhabilitar los docentes que ya figuran como titulares de otra sección del período elegido (el `detail` del `409` es suficiente si no se quiere filtrar).
- La regla de negocio es: el titular está ocupado con su sección, por lo que **no puede dar clases en otra sección**. El backend también devuelve `409` al intentar programar un horario con un docente titular de sección distinta; sí puede programarse en la sección que titula.
- Hoy la API solo permite nombrar titulares en secciones de ESCUELA y los horarios son de LICEO, así que la exclusividad es una defensa para datos cargados directamente o para un futuro cambio de regla.

### 11.5 Otros pendientes menores

- El listado general de docentes de ESCUELA muestra `Grado/Sección = -` mientras no haya `id_docente_titular` cargado en las secciones. No bloquea el PDF.

### 11.6 Horarios para operadores (lectura)

- `GET /api/horarios/registros/` y `GET /api/horarios/registros/{id}` ya están disponibles para cualquier autenticado, filtrados por nivel. Los botones de crear/editar/eliminar deben seguir visibles solo para `ADMINISTRADOR`.
- Si `sesion.nivel === 'ESCUELA'`, mostrar un aviso: «Los horarios están disponibles solo para LICEO; la escuela no tiene horarios programados.» La API responde `200` con `items: []` y `total: 0`; no es un error.
- Para `LICEO`, si la lista llega vacía por filtros, mostrar «No hay horarios registrados para los filtros seleccionados.»
- No hace falta lógica nueva en `api.js`: una lista vacía es `200`; un `403` solo ocurre si un usuario de ESCUELA fuerza `?nivel=LICEO` o abre por ID un horario de otro nivel.

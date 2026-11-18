# ServicioComunitarioSM-

### Inicio de Servidor 
cd backend/

Creación del entorno virtual
python -m venv .venv

Activación del entorno virtual
./.venv/Scripts/Activate.ps1 

Instalación de dependencias
pip install -r requirements.txt

---
Conexión con PostgreSQL para la creación de la Base de Datos
psql -U postgres
create database database;
exit
---

Creación de archivo '.env' para las variables de entorno
.env.example > .env

Prueba del Servidor
fastapi dev

---

## Endpoints disponibles actualmente

Registrados en `app/main.py` (12 en total). Salvo `/`, `/auth/registro` y `/auth/login`, todos requieren token Bearer (`Authorization: Bearer <access_token>`).

### Paginación estándar

Todo endpoint GET que devuelva un listado debe usar el módulo `app/core/paginacion.py`:

- Query params: `offset` (desde 0) y `size` (entre 1 y 100, por defecto 15).
- Respuesta:

```json
{
  "items": [],
  "total": 0,
  "offset": 0,
  "size": 15
}
```

Componentes disponibles:

- `Paginacion`: dependencia con los parámetros validados (`Depends()`).
- `RespuestaPaginada[T]`: envelope genérico para usar como `response_model`.
- `paginar(session, consulta, paginacion)`: ejecuta el `count` y aplica `offset`/`size`; devuelve `(items, total)`.
- `construir_pagina(items, total, paginacion)`: arma el envelope final.

Ejemplo de uso:

```python
@router.get("/", response_model=RespuestaPaginada[PeticionEstudiante])
def listar_estudiantes(
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  consulta = select(Estudiantes).where(Estudiantes.fecha_eliminacion == None)
  items, total = paginar(session, consulta, paginacion)
  return construir_pagina(items, total, paginacion)
```

#### Contrato para el frontend

Un GET no lleva body: solo query params y el token en el header.

```http
GET /estudiantes/?offset=15&size=15
Authorization: Bearer <access_token>
```

- `offset`: índice del primer registro (base 0).
- `size`: registros por página (1 a 100; 15 por defecto, 10 en búsquedas).
- Para la página `N` (empezando en 1): `offset = (N - 1) * size`.
- La búsqueda usa los mismos parámetros: `GET /estudiantes/buscar/?termino=ana&offset=0&size=10`.

Respuesta:

```json
{
  "items": [
    {
      "id": 16,
      "grado_id": 2,
      "cedula_estudiantil": "V-12345678",
      "primer_nombre": "Ana",
      "segundo_nombre": "María",
      "primer_apellido": "Pérez",
      "segundo_apellido": "Gómez",
      "fecha_nacimiento": "2008-04-12T00:00:00Z"
    }
  ],
  "total": 42,
  "offset": 15,
  "size": 15
}
```

`total` es la cantidad de registros que cumplen los filtros (sin paginar), así que el frontend calcula las páginas con `ceil(total / size)`. Un `offset` fuera de rango devuelve `items: []` y el `total` real.

> Estado: todos los listados actuales (`estudiantes`, `buscar`, `auditorías`, `grados` y `representantes`) ya usan este estándar. Los listados de módulos futuros deben implementarlo igual.

### Generales

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/` | Health-check básico. Devuelve `{"status": "Ok"}`. Público. |

### Autenticación (`/auth`)

| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/auth/registro` | Crea un usuario (nombre, clave, rol). Público, devuelve 201. |
| POST | `/auth/login` | Login OAuth2 (form-data: `username` y `password`). Devuelve `access_token` y `token_type`. |
| GET | `/auth/me` | Devuelve el perfil del usuario autenticado. |

### Estudiantes (`/estudiantes`)

| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/estudiantes/` | Registra un estudiante. Valida cédula duplicada. Devuelve 201. |
| GET | `/estudiantes/` | Lista estudiantes activos con paginación `offset`/`size` y respuesta `{items, total, offset, size}` (ver Paginación estándar). |
| GET | `/estudiantes/buscar/` | Busca por cédula, nombre o apellido (`termino`), sin distinguir acentos. Paginado con `offset`/`size` (10 por defecto). |
| GET | `/estudiantes/{estudiante_id}` | Obtiene el detalle de un estudiante. 404 si no existe. |
| PUT | `/estudiantes/{estudiante_id}` | Actualiza datos del estudiante (campos parciales). |
| DELETE | `/estudiantes/{estudiante_id}` | Eliminación lógica (`fecha_eliminacion`). Devuelve 204. |

### Auditorías (`/auditorias`)

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/auditorias/` | Lista auditorías con filtros `usuario`, `modulo`, `accion`, `fecha` y paginación `offset`/`size` (ver Paginación estándar). |
| GET | `/auditorias/{auditoria_id}` | Obtiene el detalle de una auditoría. |

> Nota: el rol `secretaria` tiene acceso bloqueado (403) en ambos endpoints de auditoría.

### Endpoints ya escritos pero NO disponibles

Existen en `app/routers/grados.py` y `app/routers/representantes.py`, pero **no están registrados** en `app/main.py`, por lo que no aparecen en `/docs` ni responden. Solo falta agregar su `include_router`:

| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/grados/` | Registra un grado/sección. |
| GET | `/grados/` | Lista grados activos con paginación `offset`/`size`. |
| POST | `/representantes/` | Registra un representante. |
| GET | `/representantes/` | Lista representantes activos con paginación `offset`/`size` (ver Paginación estándar). |
| POST | `/representantes/{representante_id}/vincular_estudiante/{estudiante_id}` | Vincula un representante con un estudiante. |

---

## Endpoints faltantes por implementar

### Usuarios

| Método | Ruta sugerida | Observación |
| --- | --- | --- |
| GET | `/usuarios/` | Listado paginado para administración (existe la vista `UsuariosView.vue`). |
| GET | `/usuarios/{id}` | Detalle de un usuario (hoy solo existe `/auth/me`). |
| PUT / PATCH | `/usuarios/{id}` | Editar nombre, rol y estado. Falta el schema `ActualizarUsuario`. |
| DELETE | `/usuarios/{id}` | Eliminación lógica (el modelo ya tiene `fecha_eliminacion`). |
| POST | `/auth/cambiar-clave` | Cambio de contraseña. |
| POST | `/auth/logout` | Cierre de sesión / revocación del token (el JWT actual dura 360 min). |

### Grados (catálogo)

| Método | Ruta sugerida | Observación |
| --- | --- | --- |
| — | Registrar `grados.router` en `main.py` | Habilita los 2 endpoints ya escritos. |
| GET | `/grados/{id}` | Detalle de un grado. |
| PUT / PATCH | `/grados/{id}` | Editar grado/sección. |
| DELETE | `/grados/{id}` | Eliminación lógica (el listado ya filtra `fecha_eliminacion`). |

### Representantes

| Método | Ruta sugerida | Observación |
| --- | --- | --- |
| — | Registrar `representantes.router` en `main.py` | Habilita los 3 endpoints ya escritos. |
| GET | `/representantes/{id}` | Detalle de un representante. |
| PUT / PATCH | `/representantes/{id}` | El schema `ActualizarRepresentante` ya existe pero no se usa. |
| DELETE | `/representantes/{id}` | Eliminación lógica. |
| GET | `/representantes/{id}/estudiantes` | Listar estudiantes vinculados. |
| DELETE | `/representantes/{id}/vincular_estudiante/{estudiante_id}` | Desvincular representante de estudiante. |

### Estudiantes (complementos)

| Método | Ruta sugerida | Observación |
| --- | --- | --- |
| GET | `/estudiantes/{id}/representantes` | Listar representantes vinculados. |
| DELETE | `/estudiantes/{id}/representantes/{representante_id}` | Desvincular. |
| POST | `/estudiantes/{id}/restaurar` | Revertir la eliminación lógica. |
| GET | `/estudiantes/eliminados` | Consultar el historial de bajas lógicas. |

### Pases (sin router)

Existen el modelo y los schemas `CrearPase`, `PeticionPase` y `ActualizacionPase`, pero ningún endpoint.

| Método | Ruta sugerida | Observación |
| --- | --- | --- |
| POST | `/pases/` | Registrar entrada/salida, motivo y autorizador. |
| GET | `/pases/` | Listar con filtros `estudiante`, `docente`, `fecha`, `tipo`. |
| GET | `/pases/{id}` | Detalle de un pase. |
| PUT / PATCH | `/pases/{id}` | Actualizar (schema `ActualizacionPase` ya definido). |
| DELETE | `/pases/{id}` | Eliminación lógica. |

### Reportes (sin modelo de schemas ni router)

Solo existe la tabla `reportes` y los enums de reglamentos, gravedad y categoría.

| Método | Ruta sugerida | Observación |
| --- | --- | --- |
| POST | `/reportes/` | Crear reporte (borrador o enviado). |
| GET | `/reportes/` | Listar con filtros de estudiante, grado, tipo, gravedad y fecha. |
| GET | `/reportes/{id}` | Detalle del reporte. |
| PATCH | `/reportes/{id}` | Cambiar estado: borrador → enviado → atendido. |
| DELETE | `/reportes/{id}` | Eliminación lógica. |

### Docentes y Asignaturas (catálogos)

Solo existen los modelos en `db.py`; se necesitan como catálogos para los FKs de reportes y pases.

| Método | Ruta sugerida | Observación |
| --- | --- | --- |
| GET | `/docentes/`, `/docentes/{id}` | Catálogo de docentes. |
| POST / PUT / DELETE | `/docentes/...` | Alta, edición y baja de docentes. |
| GET | `/asignaturas/`, `/asignaturas/{id}` | Catálogo de asignaturas. |
| POST / PUT / DELETE | `/asignaturas/...` | Alta, edición y baja de asignaturas. |
| GET / POST / DELETE | `/asignaturas/{id}/docentes/{docente_id}` | Gestionar la relación asignatura-docente. |

### Auditorías (complementos)

| Método | Ruta sugerida | Observación |
| --- | --- | --- |
| — | Llamar a `registrar_auditoria()` desde los endpoints de escritura | La utilidad existe pero no se invoca (y no hace `commit`). |
| GET | `/auditorias/exportar` | Exportación CSV (hoy se hace en el frontend). |

### Operaciones

| Método | Ruta sugerida | Observación |
| --- | --- | --- |
| GET | `/health` | Health-check que verifique conexión con la BD (`/` solo devuelve `Ok`). |

### Observaciones a resolver

- `grados` y `representantes` están implementados pero aún no se registran en `main.py`.
- `/auth/registro` es público y permite elegir cualquier rol; conviene definir una matriz de permisos.
- El código usa PostgreSQL con extensiones `unaccent`/`pg_trgm`, pero el repo incluye un `database.db` de SQLite.

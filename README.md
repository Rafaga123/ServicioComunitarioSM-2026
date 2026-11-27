# Servicio Comunitario SM

Gestión académica y disciplinaria para una escuela y un liceo. El backend es una API REST con **FastAPI + SQLModel + PostgreSQL**; el frontend es **Vue 3 + Vite**.

## Estado de la entrega

- Backend estable: **14 routers, 47 paths y 84 operaciones** en `/docs` y `/openapi.json`.
- El contrato HTTP no cambió: rutas, métodos, códigos y envelope siguen iguales. Los docstrings solo modifican la `description` de OpenAPI.
- Sin Alembic. En el arranque se crean las tablas y se aplican dos migraciones no destructivas: `version_tokens` en `usuarios` y `ALTER TYPE tipodocumento ADD VALUE IF NOT EXISTS 'docentes'`.
- Commits locales en `backend-dev`; **sin push ni merge** sin autorización.
- Esta entrega no modifica `frontend/src`.

## Backend

Requisitos: Python 3.11+, PostgreSQL 14+ y permisos para crear las extensiones `unaccent` y `pg_trgm`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # completar SECRET_KEY y datos de la BD
fastapi dev app/main.py
```

Crear el administrador inicial (la API no lo crea por CRUD):

```powershell
python -m scripts.crear_admin --usuario admin
```

URLs útiles: `/` y `/health` (estado), `/docs` (Swagger), `/redoc` y `/openapi.json`.

El detalle completo —variables de entorno, estructura, convenciones, endpoints, reglas de negocio y modelo de datos— está en [`docs/BACKEND.md`](docs/BACKEND.md).

## Frontend

Ubicación: `frontend/`. En desarrollo apunta a `http://localhost:8000/api`; en el empaquetado debe usar la ruta relativa `/api`.

- Login: `POST /api/auth/login` con `application/x-www-form-urlencoded` (`username` y `password`).
- Autorización: `Authorization: Bearer <access_token>` en el resto de las rutas.
- Cualquier `401` debe limpiar la sesión local y redirigir al login; no hay refresh token.
- La guía corta de conexión y actualización de datos está en [`docs/FRONTEND.md`](docs/FRONTEND.md).
- El contrato detallado por entidad está en [`docs/ENTREGA_FRONTEND.md`](docs/ENTREGA_FRONTEND.md).

## Documentación

| Archivo | Contenido |
| --- | --- |
| [`docs/BACKEND.md`](docs/BACKEND.md) | Detalle de instalación, API, reglas de negocio y datos. |
| [`docs/FRONTEND.md`](docs/FRONTEND.md) | Guía corta de conexión, errores y refresco de pantallas. |
| [`docs/ENTREGA_FRONTEND.md`](docs/ENTREGA_FRONTEND.md) | Contrato completo para el equipo de frontend. |
| [`docs/PENDIENTES.md`](docs/PENDIENTES.md) | Tareas y limitaciones conocidas. |

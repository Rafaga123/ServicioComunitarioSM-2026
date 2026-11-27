# Frontend — guía corta

Esta guía resume cómo conectarse a la API. El contrato completo por entidad (bodies, filtros, códigos y campos de apoyo) está en [`ENTREGA_FRONTEND.md`](ENTREGA_FRONTEND.md). El detalle del backend está en [`BACKEND.md`](BACKEND.md).

## Conexión

- Base URL: `import.meta.env.VITE_API_URL ?? "/api"`. En desarrollo con Vite en otro puerto: `http://localhost:8000/api`.
- Login: `POST /auth/login` con `application/x-www-form-urlencoded`, campos `username` y `password`. Devuelve `{ access_token, token_type: "bearer" }`.
- Autorización: enviar `Authorization: Bearer <access_token>` en todas las demás rutas.
- Cierre de sesión: llamar `POST /auth/logout` con el Bearer y después borrar el token local. Borrar solo el localStorage deja el token válido hasta `exp`.
- CORS: `allow_origins=["*"]` y `allow_credentials=False`; la autenticación viaja en el header, no en cookies.

## Respuestas

- Los listados devuelven `{ items, total, offset, size }`. Usar siempre `total` para la paginación; `size` por defecto es 15 (10 en buscadores).
- `401`: token inválido, expirado, revocado u obsoleto. Limpiar sesión y redirigir al login; no hay refresh token.
- `403`: sin permisos o fuera del nivel asignado. `404`: registro inexistente o dado de baja.
- `409`: conflicto de negocio. `422`: error de validación del body. `429`: demasiados logins; esperar los segundos de `Retry-After`.
- Las fechas se envían ISO sin zona (`YYYY-MM-DDTHH:MM:SS`); el backend las interpreta en `America/Caracas` y responde sin offset.
- `fecha_egreso` solo aparece en lectura de estudiantes; el backend lo escribe en el cierre de año.

## Refresco de datos

No hay WebSocket ni SSE. Para mantener las pantallas alineadas con el backend:

1. **Refetch al enfocar la ventana**: al recibir `focus` o `visibilitychange` con la pestaña visible, recargar la vista activa.
2. **Poll ligero**: en pantallas operativas (pases, reportes, gestión, listados) consultar cada **15–30 s**. Usar el intervalo mayor para vistas de solo lectura.
3. **Perfil periódico**: `GET /auth/me` cada **~30 s** para detectar cambios de rol, nivel o baja. Un `401` debe cerrar la sesión de inmediato.
4. **Tras una mutación propia**: invalidar y volver a cargar la vista afectada; no hace falta esperar al poll.
5. Evitar el poll mientras haya un formulario sin guardar y deduplicar peticiones solapadas para no saturar la API.

## Reglas visibles que conviene respetar

- Roles asignables por CRUD: `COORDINADOR` y `SECRETARIA`. El administrador se crea por script o se transfiere con `POST /usuarios/{id}/transferir-admin`.
- Los operadores están limitados a su `nivel`; el administrador puede consultar ambos.
- Cambiar clave, rol o nivel, dar de baja un usuario o transferir el admin cierra todas sus sesiones. Cambiar solo el nombre no revoca tokens.
- Los listados de docentes son generales por nivel: `grado` se acepta pero se ignora; `id_grado` junto con `id_seccion` produce `400`.
- En los horarios, las celdas libres se muestran como `/`.

## Pendiente en el frontend

El cliente aún debe llamar a `POST /auth/logout` al cerrar sesión (manual o por inactividad) y aplicar las reglas de refresco anteriores. Esta entrega solo documenta la especificación; no modifica `frontend/src`.

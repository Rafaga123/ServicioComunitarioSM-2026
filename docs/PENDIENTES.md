# Pendientes

Estado al **2026-11-26**, rama `backend-dev`, Tareas 1, 2 y 3
(commits `f9060`, `b934b` y `612a4`, más el cierre de Tarea 3).

## 1. Listados (`/api/listados`)

- [x] **`id_grado` + `id_seccion` juntos devuelven `400`.**
      `_resolver_filtros()` rechaza la combinación antes de resolver la sección.

- [x] **Filtro por grado para nóminas y representantes en modo general.**
      Las filas generales reciben el grado y filtran por `Secciones.id_grado`;
      las nóminas se ordenan por grado, sección y apellidos.

- [x] **Carpeta `generales/` en plural.**
      `ruta_relativa_listado()` escribe `.../{nivel}/generales/`, con el grado
      en el nombre del archivo y sin subcarpeta `por_grado/`.

- [x] **Descarga segura y consulta por nivel.**
      `descargar_documento()` deriva el nivel cuando el registro lo tiene nulo,
      valida ruta/archivo y devuelve `404` si no está disponible. El historial
      `/documentos` es autenticado con filtro por nivel; el paquete ZIP sigue
      siendo solo para administrador.

- [x] **Política de duplicados (Tarea 3).** Firma canónica en `documentos_firmas`
      con bloqueo `pg_advisory_xact_lock(hashtext(firma))`. Aplica al endpoint,
      al script batch y al cierre de año. El reemplazo del nombre de archivo ya
      no es global (`ruta_con_nombre()`). Gobernada por
      `REUTILIZAR_DOCUMENTOS_IGUALES` (default `False`).

- [ ] **Activar `REUTILIZAR_DOCUMENTOS_IGUALES=True`** en el entorno cuando se
      apruebe el cambio de comportamiento (hoy queda desactivado).

- [ ] **Pruebas `TestClient`** de la matriz de validación y de las rutas relativas.

### Ya resuelto en listados

- [x] Docentes solo general por nivel; `id_grado` / `id_seccion` → `400`
      (`backend/app/routers/listados.py:170`).

## 2. Documentación

- [x] `README.md`, sección **6.15**: contrato de rutas, body mínimo, descarga
      por `id` y acceso autenticado al historial.
- [x] `docs/ENTREGA_FRONTEND.md`, sección **3.15**: matriz de body, carpeta
      `generales/`, descarga y permisos por nivel.

## 3. Operativo / frontend (secundario)

- [ ] Borrar manualmente la carpeta antigua `C:\sistema\...\general\`.
      No se migran PDFs viejos desde el código.
- [ ] `npm audit`: 3 vulnerabilidades moderadas en `eslint`/`minimatch` sin
      corregir. No se aplicó `audit fix` para no modificar el lockfile.
- [ ] Datos de prueba: no hay estudiantes ni representantes reales (no había
      export completo); solo catálogos, horarios y 3 usuarios.
- [ ] Frontend: reportes/dashboard con datos mock.
- [ ] Frontend: el logout del cliente aún no llama a `POST /api/auth/logout`
      (el backend revoca el `jti` y registra la auditoría; el cliente debe
      borrar el token local).

## 4. Ya completado y subido

- [x] Logo institucional en todas las páginas de listados y horarios.
- [x] Membrete `UNIDAD EDUCATIVA PRIVADA SANTA MARTA` en una sola línea, a la
      derecha del logo, con subtítulo de tipo + alcance.
- [x] Márgenes respetados: 4 cm a la izquierda y 3 cm arriba/derecha/abajo,
      sin superposición del cuerpo desde la segunda página.
- [x] Dependencias backend y frontend instaladas; base `database` creada;
      datos mínimos de prueba cargados de forma idempotente.
- [x] Recarga automática estabilizada con `fastapi dev app/main.py --host 0.0.0.0 --reload-dir app`.

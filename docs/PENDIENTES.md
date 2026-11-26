# Pendientes

Estado al **2026-11-26**, rama `backend-dev`, commit `2aaa8bc`
(«feat(pdf): membrete institucional con logo en todas las paginas»).

## 1. Listados (`/api/listados`)

- [ ] **`id_grado` + `id_seccion` juntos deben devolver `400`.**
      Hoy `_resolver_filtros()` usa `elif`, así que la sección gana silenciosamente
      y el grado se ignora.
      Archivo: `backend/app/routers/listados.py:99-116`.

- [ ] **Filtro por grado para nóminas y representantes en modo general.**
      `_filas_nominas_general()` y `_filas_representantes_general()` solo filtran
      por periodo + nivel, y `construir_documento()` descarta el grado cuando no
      hay sección (`descripcion = "general"`).
      Archivos: `backend/app/services/listados.py:250`, `:278`, `:465-472`.

- [ ] **Carpeta `generales/` en plural.**
      `ruta_relativa_listado()` todavía escribe `.../{nivel}/general/...`.
      Contrato deseado: `2026-2027/.../{nivel}/generales/`, con el grado en el
      nombre del archivo y sin subcarpeta `por_grado/`.
      Archivo: `backend/app/services/listados.py:498-520`.

- [ ] **Pruebas `TestClient`** de la matriz de validación y de las rutas relativas.

### Ya resuelto en listados

- [x] Docentes solo general por nivel; `id_grado` / `id_seccion` → `400`
      (`backend/app/routers/listados.py:170`).

## 2. Documentación

- [ ] `README.md`, sección **6.15** (`línea 875`): actualizar contrato de rutas
      y describir el membrete institucional.
- [ ] `docs/ENTREGA_FRONTEND.md`, sección **3.15** (`líneas 337` y `362`):
      todavía documenta la carpeta `general/` en singular.

## 3. Operativo / frontend (secundario)

- [ ] Borrar manualmente la carpeta antigua `C:\sistema\...\general\`.
      No se migran PDFs viejos desde el código.
- [ ] `npm audit`: 3 vulnerabilidades moderadas en `eslint`/`minimatch` sin
      corregir. No se aplicó `audit fix` para no modificar el lockfile.
- [ ] Datos de prueba: no hay estudiantes ni representantes reales (no había
      export completo); solo catálogos, horarios y 3 usuarios.
- [ ] Frontend: reportes/dashboard con datos mock.
- [ ] Frontend: el logout del cliente aún no llama a `POST /api/auth/logout`
      (el backend ya registra la auditoría; el cliente debe borrar el token local).

## 4. Ya completado y subido

- [x] Logo institucional en todas las páginas de listados y horarios.
- [x] Membrete `UNIDAD EDUCATIVA PRIVADA SANTA MARTA` en una sola línea, a la
      derecha del logo, con subtítulo de tipo + alcance.
- [x] Márgenes respetados: 4 cm a la izquierda y 3 cm arriba/derecha/abajo,
      sin superposición del cuerpo desde la segunda página.
- [x] Dependencias backend y frontend instaladas; base `database` creada;
      datos mínimos de prueba cargados de forma idempotente.
- [x] Recarga automática estabilizada con `fastapi dev app/main.py --host 0.0.0.0 --reload-dir app`.

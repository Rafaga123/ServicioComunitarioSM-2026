// Servicio de docentes.
//
// Endpoints del backend (todos bajo el prefijo /api):
//   GET    /docentes/?offset=0&size=10  -> { items, total, offset, size }
//   GET    /docentes/{id}               -> PeticionDocente
//   POST   /docentes/                   -> 201 PeticionDocente (solo ADMIN)
//   PUT    /docentes/{id}               -> PeticionDocente        (solo ADMIN)
//   DELETE /docentes/{id}               -> 204                    (solo ADMIN)
//
// El backend usa snake_case y el frontend camelCase; la conversión se hace aquí
// para que las vistas no dependan del nombre exacto de los campos de la API.
import { apiFetch } from './api'

const RECURSO = '/docentes/'

// Límite que impone el backend en el parámetro `size` (Paginacion: le=100).
export const MAXIMO_POR_PAGINA = 100

// PeticionDocente -> objeto de la vista
const aDocente = (docente) => ({
  id: docente.id,
  primerNombre: docente.primer_nombre ?? '',
  segundoNombre: docente.segundo_nombre ?? '',
  primerApellido: docente.primer_apellido ?? '',
  segundoApellido: docente.segundo_apellido ?? '',
  cedula: docente.cedula ?? '',
  nivel: docente.nivel ?? '',
  // Las asignaturas se gestionan desde /asignaturas/{id}/docentes/{docente_id}.
  // Se deja el arreglo para que las otras pestañas no fallen mientras siguen locales.
  asignaturaIds: [],
})

// objeto de la vista -> CrearDocente / ActualizarDocente
const aPayload = (docente) => ({
  primer_nombre: String(docente.primerNombre ?? '').trim(),
  segundo_nombre: String(docente.segundoNombre ?? '').trim(),
  primer_apellido: String(docente.primerApellido ?? '').trim(),
  segundo_apellido: String(docente.segundoApellido ?? '').trim(),
  cedula: String(docente.cedula ?? '').trim(),
  // CrearDocente exige nivel; en ActualizarDocente es opcional.
  nivel: docente.nivel || undefined,
})

/**
 * Lista docentes con la paginación del backend.
 * El backend recibe offset/size, no número de página.
 *
 * @param {object} [opciones]
 * @param {number} [opciones.page] Página 1-based.
 * @param {number} [opciones.size] Registros por página (máx. 100).
 * @param {string} [opciones.nivel] LICEO | ESCUELA (opcional).
 */
export async function listarDocentes({ page = 1, size = 10, nivel } = {}) {
  const pagina = Math.max(1, Math.trunc(page) || 1)
  const tamano = Math.min(MAXIMO_POR_PAGINA, Math.max(1, Math.trunc(size) || 10))
  const offset = (pagina - 1) * tamano

  const data = await apiFetch(RECURSO, {
    params: { offset, size: tamano, nivel: nivel || undefined },
  })

  return {
    items: (data?.items ?? []).map(aDocente),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

/**
 * Trae TODOS los docentes recorriendo las páginas del backend (size=100).
 * El endpoint no tiene búsqueda por texto ni orden, así que el filtrado y la
 * ordenación se resuelven en el cliente sobre esta lista completa.
 *
 * @param {object} [opciones]
 * @param {string} [opciones.nivel] LICEO | ESCUELA (opcional).
 */
export async function listarTodosDocentes({ nivel } = {}) {
  const items = []
  let offset = 0
  let total

  do {
    const data = await apiFetch(RECURSO, {
      params: { offset, size: MAXIMO_POR_PAGINA, nivel: nivel || undefined },
    })
    const pagina = (data?.items ?? []).map(aDocente)

    items.push(...pagina)
    total = data?.total ?? items.length
    offset += MAXIMO_POR_PAGINA

    // Sin items no tiene sentido seguir pidiendo páginas.
    if (!pagina.length) break
  } while (items.length < total)

  return { items, total }
}

export async function obtenerDocente(id) {
  return aDocente(await apiFetch(`${RECURSO}${id}`))
}

export async function crearDocente(docente) {
  return aDocente(
    await apiFetch(RECURSO, { method: 'POST', body: aPayload(docente) }),
  )
}

export async function actualizarDocente(id, docente) {
  return aDocente(
    await apiFetch(`${RECURSO}${id}`, { method: 'PUT', body: aPayload(docente) }),
  )
}

export async function eliminarDocente(id) {
  return apiFetch(`${RECURSO}${id}`, { method: 'DELETE' })
}

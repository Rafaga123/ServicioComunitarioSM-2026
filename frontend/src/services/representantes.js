// Servicio de representantes.
//
// Endpoints del backend (todos bajo el prefijo /api):
//   GET    /representantes/?offset=0&size=10&nivel=  -> { items, total, offset, size }
//   GET    /representantes/{id}                      -> PeticionRepresentante
//   POST   /representantes/                          -> 201 PeticionRepresentante (solo ADMIN)
//   PUT    /representantes/{id}                      -> PeticionRepresentante        (solo ADMIN)
//   DELETE /representantes/{id}                      -> 204                        (solo ADMIN)
//   POST   /representantes/{id}/vincular_estudiante/{estudiante_id}
//   DELETE /representantes/{id}/vincular_estudiante/{estudiante_id}
//
// El filtro `nivel` no es una columna del representante: el backend lo aplica
// a través de los estudiantes vinculados. Un representante sin estudiantes
// activos no aparece cuando se filtra por LICEO o ESCUELA.
//
// El backend usa snake_case y el frontend camelCase; la conversión se hace aquí
// para que las vistas no dependan del nombre exacto de los campos de la API.
import { apiFetch } from './api'

const RECURSO = '/representantes/'

// Límite que impone el backend en el parámetro `size` (Paginacion: le=100).
export const MAXIMO_POR_PAGINA = 100

// PeticionRepresentante -> objeto de la vista
const aRepresentante = (representante) => ({
  id: representante.id,
  primerNombre: representante.primer_nombre ?? '',
  segundoNombre: representante.segundo_nombre ?? '',
  primerApellido: representante.primer_apellido ?? '',
  segundoApellido: representante.segundo_apellido ?? '',
  telefono: representante.telefono ?? '',
})

// objeto de la vista -> CrearRepresentante / ActualizarRepresentante
const aPayload = (representante) => ({
  primer_nombre: String(representante.primerNombre ?? '').trim(),
  segundo_nombre: String(representante.segundoNombre ?? '').trim(),
  primer_apellido: String(representante.primerApellido ?? '').trim(),
  segundo_apellido: String(representante.segundoApellido ?? '').trim(),
  telefono: String(representante.telefono ?? '').trim(),
})

/**
 * Lista representantes con la paginación del backend.
 * El backend recibe offset/size, no número de página.
 *
 * @param {object} [opciones]
 * @param {number} [opciones.page] Página 1-based.
 * @param {number} [opciones.size] Registros por página (máx. 100).
 * @param {string} [opciones.nivel] LICEO | ESCUELA (opcional).
 */
export async function listarRepresentantes({ page = 1, size = 10, nivel } = {}) {
  const pagina = Math.max(1, Math.trunc(page) || 1)
  const tamano = Math.min(MAXIMO_POR_PAGINA, Math.max(1, Math.trunc(size) || 10))
  const offset = (pagina - 1) * tamano

  const data = await apiFetch(RECURSO, {
    params: { offset, size: tamano, nivel: nivel || undefined },
  })

  return {
    items: (data?.items ?? []).map(aRepresentante),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

/**
 * Trae TODOS los representantes recorriendo las páginas del backend (size=100).
 * El endpoint no tiene búsqueda por texto ni orden, así que el filtrado se
 * resuelve en el cliente sobre esta lista completa.
 *
 * @param {object} [opciones]
 * @param {string} [opciones.nivel] LICEO | ESCUELA (opcional).
 */
export async function listarTodosRepresentantes({ nivel } = {}) {
  const items = []
  let offset = 0
  let total

  do {
    const data = await apiFetch(RECURSO, {
      params: { offset, size: MAXIMO_POR_PAGINA, nivel: nivel || undefined },
    })
    const pagina = (data?.items ?? []).map(aRepresentante)

    items.push(...pagina)
    total = data?.total ?? items.length
    offset += MAXIMO_POR_PAGINA

    // Sin items no tiene sentido seguir pidiendo páginas.
    if (!pagina.length) break
  } while (items.length < total)

  return { items, total }
}

export async function obtenerRepresentante(id) {
  return aRepresentante(await apiFetch(`${RECURSO}${id}`))
}

export async function crearRepresentante(representante) {
  return aRepresentante(
    await apiFetch(RECURSO, { method: 'POST', body: aPayload(representante) }),
  )
}

export async function actualizarRepresentante(id, representante) {
  return aRepresentante(
    await apiFetch(`${RECURSO}${id}`, {
      method: 'PUT',
      body: aPayload(representante),
    }),
  )
}

export async function eliminarRepresentante(id) {
  return apiFetch(`${RECURSO}${id}`, { method: 'DELETE' })
}

// Vinculación directa (el formulario de estudiantes la usará cuando esa
// pestaña se conecte a la API).
export async function vincularEstudiante(representanteId, estudianteId) {
  return apiFetch(
    `${RECURSO}${representanteId}/vincular_estudiante/${estudianteId}`,
    { method: 'POST' },
  )
}

export async function desvincularEstudiante(representanteId, estudianteId) {
  return apiFetch(
    `${RECURSO}${representanteId}/vincular_estudiante/${estudianteId}`,
    { method: 'DELETE' },
  )
}

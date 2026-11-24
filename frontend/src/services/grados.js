// Servicio de grados (catálogo de solo lectura).
//
//   GET /grados/?offset=0&size=10&nivel=  -> { items, total, offset, size }
//   GET /grados/{id}
//
// El backend siembra el catálogo al arrancar: 1er a 6to Grado (ESCUELA) y
// 1er a 5to Año (LICEO). No hay endpoints de escritura.
import { apiFetch } from './api'

const RECURSO = '/grados/'

export const MAXIMO_POR_PAGINA = 100

const aGrado = (grado) => ({
  id: grado.id,
  numero: grado.numero,
  nombre: grado.nombre ?? '',
  nivel: grado.nivel ?? '',
})

export async function listarGrados({ page = 1, size = 10, nivel } = {}) {
  const pagina = Math.max(1, Math.trunc(page) || 1)
  const tamano = Math.min(MAXIMO_POR_PAGINA, Math.max(1, Math.trunc(size) || 10))
  const offset = (pagina - 1) * tamano

  const data = await apiFetch(RECURSO, {
    params: { offset, size: tamano, nivel: nivel || undefined },
  })

  return {
    items: (data?.items ?? []).map(aGrado),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

/**
 * Trae todos los grados del nivel indicado (o de ambos si no se envía).
 * Son pocos registros (11 en total), así que se piden de una vez.
 */
export async function listarTodosGrados({ nivel } = {}) {
  const items = []
  let offset = 0
  let total

  do {
    const data = await apiFetch(RECURSO, {
      params: { offset, size: MAXIMO_POR_PAGINA, nivel: nivel || undefined },
    })
    const pagina = (data?.items ?? []).map(aGrado)

    items.push(...pagina)
    total = data?.total ?? items.length
    offset += MAXIMO_POR_PAGINA

    if (!pagina.length) break
  } while (items.length < total)

  return { items, total }
}

export async function obtenerGrado(id) {
  return aGrado(await apiFetch(`${RECURSO}${id}`))
}

// Servicio de asignaturas.
//
// Endpoints del backend (todos bajo el prefijo /api):
//   GET    /asignaturas/?offset=0&size=10&nivel=&id_grado=&periodo_lectivo=
//          -> { items, total, offset, size }
//   GET    /asignaturas/{id}                          -> PeticionAsignatura
//   POST   /asignaturas/                              -> 201 (solo ADMIN)
//   PUT    /asignaturas/{id}                          -> PeticionAsignatura (solo ADMIN)
//   DELETE /asignaturas/{id}                          -> 204 (solo ADMIN)
//   GET    /asignaturas/{id}/docentes                 -> list[PeticionDocente]
//   POST   /asignaturas/{id}/docentes/{docente_id}    -> vincula (solo ADMIN)
//   DELETE /asignaturas/{id}/docentes/{docente_id}    -> desvincula (solo ADMIN)
//
// Reglas del backend que el frontend respeta:
// - Las asignaturas solo se pueden crear en grados de Liceo.
// - El período se elige al registrar: el PUT rechaza cualquier cambio de año.
// - El duplicado se mide por (id_grado, nombre, período lectivo).
// - No se puede dar de baja si tiene horarios o docentes vinculados.
import { apiFetch } from './api'
import { aDocente } from './docentes'

const RECURSO = '/asignaturas/'

// Límite que impone el backend en el parámetro `size` (Paginacion: le=100).
export const MAXIMO_POR_PAGINA = 100

// PeticionAsignatura -> objeto de la vista
const aAsignatura = (asignatura) => ({
  id: asignatura.id,
  idGrado: asignatura.id_grado,
  nombre: asignatura.nombre ?? '',
  periodoLectivo: asignatura.periodo_lectivo,
  gradoNumero: asignatura.grado_numero ?? null,
  gradoNombre: asignatura.grado_nombre ?? '',
  nivel: asignatura.nivel ?? '',
  docentes: (asignatura.docentes ?? []).map(aDocente),
})

// objeto de la vista -> CrearAsignatura / ActualizarAsignatura.
// `periodo_lectivo` solo se envía al crear: el backend lo rechaza en el PUT.
const aPayload = (asignatura, { crear = true } = {}) => ({
  id_grado:
    asignatura.idGrado === '' || asignatura.idGrado == null
      ? undefined
      : Number(asignatura.idGrado),
  nombre: String(asignatura.nombre ?? '').trim(),
  ...(crear
    ? {
        periodo_lectivo:
          asignatura.periodoLectivo === '' || asignatura.periodoLectivo == null
            ? undefined
            : Number(asignatura.periodoLectivo),
      }
    : {}),
})

/**
 * Lista asignaturas con la paginación del backend.
 *
 * @param {object} [opciones]
 * @param {number} [opciones.page] Página 1-based.
 * @param {number} [opciones.size] Registros por página (máx. 100).
 * @param {string} [opciones.nivel] LICEO | ESCUELA (opcional).
 * @param {number} [opciones.idGrado] Filtra por grado (opcional).
 * @param {number} [opciones.periodoLectivo] Filtra por año lectivo (opcional).
 */
export async function listarAsignaturas({
  page = 1,
  size = 10,
  nivel,
  idGrado,
  periodoLectivo,
} = {}) {
  const pagina = Math.max(1, Math.trunc(page) || 1)
  const tamano = Math.min(MAXIMO_POR_PAGINA, Math.max(1, Math.trunc(size) || 10))
  const offset = (pagina - 1) * tamano

  const data = await apiFetch(RECURSO, {
    params: {
      offset,
      size: tamano,
      nivel: nivel || undefined,
      id_grado: idGrado || undefined,
      periodo_lectivo: periodoLectivo || undefined,
    },
  })

  return {
    items: (data?.items ?? []).map(aAsignatura),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

/** Trae TODAS las asignaturas (recorriendo páginas) para filtrar en cliente. */
export async function listarTodasAsignaturas({
  nivel,
  idGrado,
  periodoLectivo,
} = {}) {
  const items = []
  let offset = 0
  let total

  do {
    const data = await apiFetch(RECURSO, {
      params: {
        offset,
        size: MAXIMO_POR_PAGINA,
        nivel: nivel || undefined,
        id_grado: idGrado || undefined,
        periodo_lectivo: periodoLectivo || undefined,
      },
    })
    const pagina = (data?.items ?? []).map(aAsignatura)

    items.push(...pagina)
    total = data?.total ?? items.length
    offset += MAXIMO_POR_PAGINA

    if (!pagina.length) break
  } while (items.length < total)

  return { items, total }
}

export async function obtenerAsignatura(id) {
  return aAsignatura(await apiFetch(`${RECURSO}${id}`))
}

export async function crearAsignatura(asignatura) {
  return aAsignatura(
    await apiFetch(RECURSO, { method: 'POST', body: aPayload(asignatura) }),
  )
}

export async function actualizarAsignatura(id, asignatura) {
  return aAsignatura(
    await apiFetch(`${RECURSO}${id}`, {
      method: 'PUT',
      body: aPayload(asignatura, { crear: false }),
    }),
  )
}

export async function eliminarAsignatura(id) {
  return apiFetch(`${RECURSO}${id}`, { method: 'DELETE' })
}

export async function listarDocentesDeAsignatura(id) {
  const docentes = await apiFetch(`${RECURSO}${id}/docentes`)
  return (docentes ?? []).map(aDocente)
}

/** Vincula un docente de Liceo a la asignatura. */
export async function vincularDocente(idAsignatura, idDocente) {
  return apiFetch(`${RECURSO}${idAsignatura}/docentes/${idDocente}`, {
    method: 'POST',
  })
}

/** Quita la vinculación (soft delete en el servidor). */
export async function desvincularDocente(idAsignatura, idDocente) {
  return apiFetch(`${RECURSO}${idAsignatura}/docentes/${idDocente}`, {
    method: 'DELETE',
  })
}

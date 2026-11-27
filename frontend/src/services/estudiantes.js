// Servicio de estudiantes.
//
// Endpoints del backend (todos bajo el prefijo /api):
//   GET    /estudiantes/?offset=0&size=10&nivel=&id_grado=&id_seccion=&periodo_lectivo=
//   GET    /estudiantes/buscar/?termino=&offset=0&size=10&nivel=
//   GET    /estudiantes/{id}
//   POST   /estudiantes/       -> 201 PeticionEstudiante (solo ADMIN)
//   PUT    /estudiantes/{id}   -> PeticionEstudiante     (solo ADMIN)
//   DELETE /estudiantes/{id}   -> 204                     (solo ADMIN)
//
// Un estudiante vive dentro de una sección (id_seccion): la sección ya fija
// grado, letra y período lectivo. Solo puede tener un representante.
//
// El backend usa snake_case y el frontend camelCase; la conversión se hace aquí
// para que las vistas no dependan del nombre exacto de los campos de la API.
import { apiFetch } from './api'

const RECURSO = '/estudiantes/'
const BUSCAR = '/estudiantes/buscar/'

// Límite que impone el backend en el parámetro `size` (Paginacion: le=100).
export const MAXIMO_POR_PAGINA = 100

// PeticionEstudiante -> objeto de la vista
const aEstudiante = (estudiante) => ({
  id: estudiante.id,
  idSeccion: estudiante.id_seccion,
  idRepresentante: estudiante.id_representante ?? null,
  cedula: estudiante.cedula_estudiantil ?? '',
  primerNombre: estudiante.primer_nombre ?? '',
  segundoNombre: estudiante.segundo_nombre ?? '',
  primerApellido: estudiante.primer_apellido ?? '',
  segundoApellido: estudiante.segundo_apellido ?? '',
  // El input type="date" solo entiende YYYY-MM-DD.
  fechaNacimiento: String(estudiante.fecha_nacimiento ?? '').slice(0, 10),
  // Datos de apoyo que ya resuelve el backend.
  nivel: estudiante.nivel ?? '',
  idGrado: estudiante.id_grado ?? null,
  gradoNumero: estudiante.grado_numero ?? null,
  gradoNombre: estudiante.grado_nombre ?? '',
  seccionLetra: estudiante.seccion_letra ?? '',
  periodoLectivo: estudiante.periodo_lectivo ?? null,
  representanteNombre: estudiante.representante ?? '',
})

// YYYY-MM-DD -> datetime que espera el backend (hora local de Caracas).
const aFechaBackend = (valor) => {
  const texto = String(valor ?? '').slice(0, 10)
  return /^\d{4}-\d{2}-\d{2}$/.test(texto) ? `${texto}T00:00:00` : texto || null
}

// objeto de la vista -> CrearEstudiante / ActualizarEstudiante
const aPayload = (estudiante) => ({
  id_seccion: Number(estudiante.idSeccion),
  id_representante: estudiante.idRepresentante || null,
  cedula_estudiantil: String(estudiante.cedula ?? '').trim(),
  primer_nombre: String(estudiante.primerNombre ?? '').trim(),
  segundo_nombre: String(estudiante.segundoNombre ?? '').trim(),
  primer_apellido: String(estudiante.primerApellido ?? '').trim(),
  segundo_apellido: String(estudiante.segundoApellido ?? '').trim(),
  fecha_nacimiento: aFechaBackend(estudiante.fechaNacimiento),
})

/**
 * Lista estudiantes con la paginación del backend.
 *
 * @param {object} [opciones]
 * @param {number} [opciones.page] Página 1-based.
 * @param {number} [opciones.size] Registros por página (máx. 100).
 * @param {string} [opciones.nivel] LICEO | ESCUELA (opcional).
 * @param {number} [opciones.idGrado] Filtro por grado.
 * @param {number} [opciones.idSeccion] Filtro por sección.
 * @param {number} [opciones.periodoLectivo] Filtro por período lectivo.
 */
export async function listarEstudiantes({
  page = 1,
  size = 10,
  nivel,
  idGrado,
  idSeccion,
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
      id_seccion: idSeccion || undefined,
      periodo_lectivo: periodoLectivo || undefined,
    },
  })

  return {
    items: (data?.items ?? []).map(aEstudiante),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

/**
 * Trae TODOS los estudiantes recorriendo las páginas del backend (size=100).
 * Se usa para filtrar en el cliente sobre la lista completa.
 *
 * @param {object} [opciones]
 * @param {string} [opciones.nivel] LICEO | ESCUELA (opcional).
 * @param {number} [opciones.idGrado] Filtro por año/grado.
 * @param {number} [opciones.idSeccion] Filtro por sección.
 * @param {number} [opciones.periodoLectivo] Filtro por período lectivo.
 */
export async function listarTodosEstudiantes({
  nivel,
  idGrado,
  idSeccion,
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
        id_seccion: idSeccion || undefined,
        periodo_lectivo: periodoLectivo || undefined,
      },
    })
    const pagina = (data?.items ?? []).map(aEstudiante)

    items.push(...pagina)
    total = data?.total ?? items.length
    offset += MAXIMO_POR_PAGINA

    if (!pagina.length) break
  } while (items.length < total)

  return { items, total }
}

/**
 * Búsqueda en el servidor (cédula, primer nombre o primer apellido).
 * La vista usa el filtrado en cliente para incluir también el segundo nombre;
 * esta función queda disponible para otros listados que quieran la búsqueda
 * oficial del backend.
 */
export async function buscarEstudiantes(termino, { page = 1, size = 10, nivel } = {}) {
  const pagina = Math.max(1, Math.trunc(page) || 1)
  const tamano = Math.min(MAXIMO_POR_PAGINA, Math.max(1, Math.trunc(size) || 10))
  const offset = (pagina - 1) * tamano

  const data = await apiFetch(BUSCAR, {
    params: { termino, offset, size: tamano, nivel: nivel || undefined },
  })

  return {
    items: (data?.items ?? []).map(aEstudiante),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

export async function obtenerEstudiante(id) {
  return aEstudiante(await apiFetch(`${RECURSO}${id}`))
}

export async function crearEstudiante(estudiante) {
  return aEstudiante(
    await apiFetch(RECURSO, { method: 'POST', body: aPayload(estudiante) }),
  )
}

export async function actualizarEstudiante(id, estudiante) {
  return aEstudiante(
    await apiFetch(`${RECURSO}${id}`, {
      method: 'PUT',
      body: aPayload(estudiante),
    }),
  )
}

export async function eliminarEstudiante(id) {
  return apiFetch(`${RECURSO}${id}`, { method: 'DELETE' })
}

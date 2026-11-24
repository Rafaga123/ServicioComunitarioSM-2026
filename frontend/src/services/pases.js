// Servicio de pases (entradas y salidas de estudiantes).
//
// Endpoints del backend (todos bajo el prefijo /api):
//   GET    /pases/?offset=&size=&id_estudiante=&id_seccion=&tipo=&anio=&mes=
//          &periodo_lectivo=&nivel=          -> { items, total, offset, size }
//   GET    /pases/{id}                      -> PeticionPase
//   POST   /pases/                          -> 201 PeticionPase
//   PUT    /pases/{id}                      -> PeticionPase
//   DELETE /pases/{id}                      -> 204
//
//   GET    /pases/?id_estudiante=...&size=100 para el historial del estudiante.
//
// El backend ordena por fecha descendente. `id_docente` e `id_asignatura` son
// opcionales: cuando no hay horario que los determine, el pase se guarda sin
// ellos. `periodo_lectivo` lo calcula el backend desde la sección del estudiante.
//
// El backend usa snake_case y el frontend camelCase; la conversión se hace aquí
// para que las vistas no dependan del nombre exacto de los campos de la API.
import { apiDescargar, apiFetch } from './api'

const RECURSO = '/pases/'

// Límite que impone el backend en el parámetro `size` (Paginacion: le=100).
export const MAXIMO_POR_PAGINA = 100

// Tipos del enum del backend.
export const TIPOS_PASE = Object.freeze({
  ENTRADA: 'ENTRADA',
  SALIDA: 'SALIDA',
})

// PeticionPase -> objeto de la vista. `fecha` llega como datetime ISO
// (YYYY-MM-DDTHH:mm:ss); se conserva completa y se exponen partes listas
// para los inputs y las tablas.
const aPase = (pase) => {
  const fecha = String(pase.fecha ?? '')

  return {
    id: pase.id,
    idEstudiante: pase.id_estudiante,
    idUsuario: pase.id_usuario,
    idDocente: pase.id_docente ?? null,
    idAsignatura: pase.id_asignatura ?? null,
    tipo: pase.tipo ?? '',
    motivo: pase.motivo ?? '',
    fecha,
    fechaISO: fecha.slice(0, 10),
    hora: fecha.slice(11, 16),
    mes: fecha.slice(0, 7),
    periodoLectivo: pase.periodo_lectivo ?? null,
    autorizador: pase.autorizador ?? '',
    archivoUrl: pase.archivo_url ?? '',
    archivoNombre: pase.archivo_nombre ?? '',
    archivoMime: pase.archivo_mime ?? '',
    archivoTamano: pase.archivo_tamano ?? null,
    // Datos de apoyo que ya resuelve el backend.
    estudiante: pase.estudiante ?? '',
    cedula: pase.cedula_estudiantil ?? '',
    nivel: pase.nivel ?? '',
    usuario: pase.usuario ?? '',
    docente: pase.docente ?? '',
    asignatura: pase.asignatura ?? '',
  }
}

// Combina los campos de la vista en el datetime local que espera el backend.
const aFechaBackend = (fecha, hora) => {
  const dia = String(fecha ?? '').slice(0, 10)
  const hhmm = String(hora ?? '').slice(0, 5)
  return dia && hhmm ? `${dia}T${hhmm}:00` : null
}

// objeto de la vista -> CrearPase. Los IDs opcionales se omiten cuando no hay
// horario/titular que los determine (el backend los acepta como null).
const aPayloadCrear = (pase) => {
  const payload = {
    id_estudiante: Number(pase.idEstudiante),
    tipo: pase.tipo,
    motivo: String(pase.motivo ?? '').trim(),
    fecha: aFechaBackend(pase.fecha, pase.hora),
  }

  if (pase.idDocente) payload.id_docente = Number(pase.idDocente)
  if (pase.idAsignatura) payload.id_asignatura = Number(pase.idAsignatura)

  const autorizador = String(pase.autorizador ?? '').trim()
  if (autorizador) payload.autorizador = autorizador

  return payload
}

// objeto de la vista -> ActualizacionPase. Se envían solo los campos
// editables; `null` limpia docente, asignatura o autorizador.
const aPayloadActualizar = (cambios) => {
  const payload = {}

  if (cambios.tipo !== undefined) payload.tipo = cambios.tipo
  if (cambios.motivo !== undefined) payload.motivo = String(cambios.motivo).trim()
  if (cambios.fecha !== undefined || cambios.hora !== undefined) {
    payload.fecha = aFechaBackend(cambios.fecha, cambios.hora)
  }
  if (cambios.idDocente !== undefined) payload.id_docente = cambios.idDocente || null
  if (cambios.idAsignatura !== undefined) {
    payload.id_asignatura = cambios.idAsignatura || null
  }
  if (cambios.autorizador !== undefined) {
    payload.autorizador = String(cambios.autorizador ?? '').trim() || null
  }

  return payload
}

/**
 * Lista pases con la paginación del backend.
 *
 * @param {object} [opciones]
 * @param {number} [opciones.page] Página 1-based.
 * @param {number} [opciones.size] Registros por página (máx. 100).
 * @param {number} [opciones.idEstudiante] Filtra por estudiante.
 * @param {number} [opciones.idSeccion] Filtra por sección.
 * @param {string} [opciones.tipo] ENTRADA | SALIDA.
 * @param {number} [opciones.anio] Año de la fecha.
 * @param {number} [opciones.mes] Mes 1..12.
 * @param {number} [opciones.periodoLectivo] Año lectivo del pase.
 * @param {string} [opciones.nivel] LICEO | ESCUELA.
 */
export async function listarPases({
  page = 1,
  size = 10,
  idEstudiante,
  idSeccion,
  tipo,
  anio,
  mes,
  periodoLectivo,
  nivel,
} = {}) {
  const pagina = Math.max(1, Math.trunc(page) || 1)
  const tamano = Math.min(MAXIMO_POR_PAGINA, Math.max(1, Math.trunc(size) || 10))
  const offset = (pagina - 1) * tamano

  const data = await apiFetch(RECURSO, {
    params: {
      offset,
      size: tamano,
      id_estudiante: idEstudiante || undefined,
      id_seccion: idSeccion || undefined,
      tipo: tipo || undefined,
      anio: anio || undefined,
      mes: mes || undefined,
      periodo_lectivo: periodoLectivo || undefined,
      nivel: nivel || undefined,
    },
  })

  return {
    items: (data?.items ?? []).map(aPase),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

/**
 * Trae TODOS los pases que cumplan los filtros recorriendo las páginas del
 * backend (size=100). Se usa para filtrar por texto en el cliente, porque el
 * endpoint no tiene búsqueda por nombre ni cédula.
 *
 * @param {object} [filtros] Mismos filtros que listarPases, sin page/size.
 */
export async function listarTodosPases(filtros = {}) {
  const items = []
  let offset = 0
  let total

  do {
    const data = await apiFetch(RECURSO, {
      params: {
        offset,
        size: MAXIMO_POR_PAGINA,
        id_estudiante: filtros.idEstudiante || undefined,
        id_seccion: filtros.idSeccion || undefined,
        tipo: filtros.tipo || undefined,
        anio: filtros.anio || undefined,
        mes: filtros.mes || undefined,
        periodo_lectivo: filtros.periodoLectivo || undefined,
        nivel: filtros.nivel || undefined,
      },
    })
    const pagina = (data?.items ?? []).map(aPase)

    items.push(...pagina)
    total = data?.total ?? items.length
    offset += MAXIMO_POR_PAGINA

    if (!pagina.length) break
  } while (items.length < total)

  return { items, total }
}

export async function obtenerPase(id) {
  return aPase(await apiFetch(`${RECURSO}${id}`))
}

/**
 * @param {object} pase
 * @param {number} pase.idEstudiante
 * @param {string} pase.tipo ENTRADA | SALIDA
 * @param {string} pase.motivo
 * @param {string} pase.fecha YYYY-MM-DD
 * @param {string} pase.hora HH:mm
 * @param {number|null} [pase.idDocente]
 * @param {number|null} [pase.idAsignatura]
 * @param {string} [pase.autorizador]
 */
export async function crearPase(pase) {
  return aPase(
    await apiFetch(RECURSO, { method: 'POST', body: aPayloadCrear(pase) }),
  )
}

/**
 * @param {number} id
 * @param {object} cambios Campos editables; solo se envían los presentes.
 */
export async function actualizarPase(id, cambios) {
  return aPase(
    await apiFetch(`${RECURSO}${id}`, {
      method: 'PUT',
      body: aPayloadActualizar(cambios),
    }),
  )
}

export async function eliminarPase(id) {
  return apiFetch(`${RECURSO}${id}`, { method: 'DELETE' })
}

/** Adjunta una imagen al pase (jpg, jpeg, png o webp; máx. 5 MB). */
export async function subirArchivoPase(id, archivo) {
  const formulario = new FormData()
  formulario.append('archivo', archivo)

  return aPase(
    await apiFetch(`${RECURSO}${id}/archivo`, {
      method: 'POST',
      body: formulario,
      timeout: 60000,
    }),
  )
}

/** Descarga el adjunto del pase como Blob, junto con su nombre original. */
export async function descargarArchivoPase(id) {
  return apiDescargar(`${RECURSO}${id}/archivo`)
}

/** Desvincula el adjunto del pase (no borra el archivo físico). */
export async function quitarArchivoPase(id) {
  return apiFetch(`${RECURSO}${id}/archivo`, { method: 'DELETE' })
}

// Servicio de reportes de incidencias (conductuales y académicas).
//
//   GET    /reportes/?offset=&size=&id_estudiante=&id_seccion=&id_docente=
//          &anio=&mes=&periodo_lectivo=&categoria=&nivel_gravedad=&nivel=
//                                          -> { items, total, offset, size }
//   GET    /reportes/{id}                  -> PeticionReporte
//   GET    /reportes/{id}/pdf              -> application/pdf (Content-Disposition)
//   POST   /reportes/                      -> 201 PeticionReporte
//   PUT    /reportes/{id}                  -> PeticionReporte
//   DELETE /reportes/{id}                  -> 204
//   POST   /reportes/{id}/archivo          -> PeticionReporte (imagen/PDF)
//   GET    /reportes/{id}/archivo          -> archivo adjunto
//
// El backend usa snake_case y el frontend camelCase; la conversión se hace
// aquí para que las vistas no dependan del nombre exacto de los campos.
import { apiDescargar, apiFetch } from './api'

const RECURSO = '/reportes/'

export const MAXIMO_POR_PAGINA = 100

export const CATEGORIAS_REPORTE = Object.freeze({
  CONDUCTUAL: 'CONDUCTUAL',
  ACADEMICO: 'ACADEMICO',
})

export const GRAVEDADES_REPORTE = Object.freeze({
  LEVE: 'LEVE',
  GRAVE: 'GRAVE',
})

export const REGLAMENTOS_REPORTE = Object.freeze(['LOPNNA', 'LOE', 'CBV', 'NC'])

export const etiquetaCategoria = (categoria) =>
  ({ CONDUCTUAL: 'Conductual', ACADEMICO: 'Académica' })[categoria] ?? categoria ?? '—'

export const etiquetaGravedad = (gravedad) =>
  ({ LEVE: 'Leve', GRAVE: 'Grave' })[gravedad] ?? gravedad ?? '—'

// PeticionReporte -> objeto de la vista
const aReporte = (reporte) => {
  const fecha = String(reporte.fecha ?? '')

  return {
    id: reporte.id,
    idEstudiante: reporte.id_estudiante,
    idUsuario: reporte.id_usuario,
    idDocente: reporte.id_docente ?? null,
    idAsignatura: reporte.id_asignatura ?? null,
    articulo: reporte.articulo ?? null,
    reglamento: reporte.reglamento ?? '',
    incidencia: reporte.incidencia ?? '',
    defensa: reporte.defensa ?? '',
    gravedad: reporte.nivel_gravedad ?? '',
    categoria: reporte.categoria ?? '',
    fecha,
    fechaISO: fecha.slice(0, 10),
    hora: fecha.slice(11, 16),
    periodoLectivo: reporte.periodo_lectivo ?? null,
    estudiante: reporte.estudiante ?? '',
    cedula: reporte.cedula_estudiantil ?? '',
    nivel: reporte.nivel ?? '',
    usuario: reporte.usuario ?? '',
    docente: reporte.docente ?? '',
    asignatura: reporte.asignatura ?? '',
    archivoNombre: reporte.archivo_nombre ?? '',
    archivoMime: reporte.archivo_mime ?? '',
    archivoTamano: reporte.archivo_tamano ?? null,
  }
}

/**
 * Lista reportes con la paginación del backend.
 *
 * @param {object} [opciones]
 * @param {number} [opciones.page] Página 1-based.
 * @param {number} [opciones.size] Registros por página (máx. 100).
 * @param {number} [opciones.idEstudiante] Filtro por estudiante.
 * @param {number} [opciones.idSeccion] Filtro por sección.
 * @param {number} [opciones.idDocente] Filtro por docente.
 * @param {number} [opciones.anio] Año de la fecha.
 * @param {number} [opciones.mes] Mes 1..12.
 * @param {string} [opciones.categoria] CONDUCTUAL | ACADEMICO.
 * @param {string} [opciones.gravedad] LEVE | GRAVE.
 * @param {string} [opciones.nivel] LICEO | ESCUELA.
 */
export async function listarReportes({
  page = 1,
  size = 10,
  idEstudiante,
  idSeccion,
  idDocente,
  anio,
  mes,
  periodoLectivo,
  categoria,
  gravedad,
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
      id_docente: idDocente || undefined,
      anio: anio || undefined,
      mes: mes || undefined,
      periodo_lectivo: periodoLectivo || undefined,
      categoria: categoria || undefined,
      nivel_gravedad: gravedad || undefined,
      nivel: nivel || undefined,
    },
  })

  return {
    items: (data?.items ?? []).map(aReporte),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

/** Trae TODOS los reportes que cumplan los filtros recorriendo las páginas. */
export async function listarTodosReportes(filtros = {}) {
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
        id_docente: filtros.idDocente || undefined,
        anio: filtros.anio || undefined,
        mes: filtros.mes || undefined,
        periodo_lectivo: filtros.periodoLectivo || undefined,
        categoria: filtros.categoria || undefined,
        nivel_gravedad: filtros.gravedad || undefined,
        nivel: filtros.nivel || undefined,
      },
    })
    const pagina = (data?.items ?? []).map(aReporte)

    items.push(...pagina)
    total = data?.total ?? items.length
    offset += MAXIMO_POR_PAGINA

    if (!pagina.length) break
  } while (items.length < total)

  return { items, total }
}

// objeto de la vista -> CrearReporte / ActualizarReporte
const aPayload = (datos) => {
  const payload = {}
  if (datos.idEstudiante != null) payload.id_estudiante = Number(datos.idEstudiante)
  // null explícito permite quitar el docente en una actualización.
  if (Object.prototype.hasOwnProperty.call(datos, 'idDocente')) {
    payload.id_docente = datos.idDocente ? Number(datos.idDocente) : null
  }
  // null explícito permite desvincular la asignatura en una actualización.
  if (Object.prototype.hasOwnProperty.call(datos, 'idAsignatura')) {
    payload.id_asignatura = datos.idAsignatura ? Number(datos.idAsignatura) : null
  }
  if (datos.articulo != null) payload.articulo = Number(datos.articulo)
  if (datos.reglamento) payload.reglamento = datos.reglamento
  if (datos.incidencia !== undefined) payload.incidencia = String(datos.incidencia).trim()
  if (datos.defensa !== undefined) payload.defensa = String(datos.defensa).trim()
  if (datos.gravedad) payload.nivel_gravedad = datos.gravedad
  if (datos.categoria) payload.categoria = datos.categoria
  if (datos.fecha) payload.fecha = datos.fecha
  return payload
}

export async function obtenerReporte(id) {
  return aReporte(await apiFetch(`${RECURSO}${id}`))
}

export async function crearReporte(datos) {
  return aReporte(
    await apiFetch(RECURSO, { method: 'POST', body: aPayload(datos) }),
  )
}

export async function actualizarReporte(id, datos) {
  const cambios = {}
  Object.entries(aPayload(datos)).forEach(([clave, valor]) => {
    // ActualizarReporte usa exclude_unset: no enviar campos vacíos.
    if (valor !== undefined && valor !== '') cambios[clave] = valor
  })

  return aReporte(
    await apiFetch(`${RECURSO}${id}`, { method: 'PUT', body: cambios }),
  )
}

export async function eliminarReporte(id) {
  return apiFetch(`${RECURSO}${id}`, { method: 'DELETE' })
}

/** Adjunta una imagen o PDF al reporte (el backend conserva un solo adjunto). */
export async function subirArchivoReporte(id, archivo) {
  const formulario = new FormData()
  formulario.append('archivo', archivo)

  return aReporte(
    await apiFetch(`${RECURSO}${id}/archivo`, {
      method: 'POST',
      body: formulario,
      timeout: 60000,
    }),
  )
}

/** Descarga el adjunto del reporte como Blob, junto con su nombre original. */
export async function descargarArchivoReporte(id, { inline = false } = {}) {
  return apiDescargar(`${RECURSO}${id}/archivo`, { params: { inline } })
}

/** Descarga el PDF del reporte generado por el backend. */
export async function descargarPdfReporte(id) {
  return apiDescargar(`${RECURSO}${id}/pdf`)
}

/** Desvincula el adjunto del reporte (no borra el archivo físico). */
export async function quitarArchivoReporte(id) {
  return apiFetch(`${RECURSO}${id}/archivo`, { method: 'DELETE' })
}

// El PDF del reporte se obtiene con descargarPdfReporte(); el backend registra
// la auditoría y devuelve el archivo con filename "reporte-{id}.pdf".

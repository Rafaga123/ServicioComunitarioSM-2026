// Servicio de reportes de incidencias (conductuales y académicas).
//
//   GET /reportes/?offset=&size=&anio=&mes=&periodo_lectivo=
//        &categoria=&nivel_gravedad=&nivel=  -> { items, total, offset, size }
//   GET /reportes/{id}                      -> PeticionReporte
//
// El backend usa snake_case y el frontend camelCase; la conversión se hace
// aquí para que las vistas no dependan del nombre exacto de los campos.
import { apiFetch } from './api'

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

// PeticionReporte -> objeto de la vista
const aReporte = (reporte) => {
  const fecha = String(reporte.fecha ?? '')

  return {
    id: reporte.id,
    idEstudiante: reporte.id_estudiante,
    idUsuario: reporte.id_usuario,
    idDocente: reporte.id_docente ?? null,
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
  }
}

/**
 * Lista reportes con la paginación del backend.
 *
 * @param {object} [opciones]
 * @param {number} [opciones.page] Página 1-based.
 * @param {number} [opciones.size] Registros por página (máx. 100).
 * @param {number} [opciones.anio] Año de la fecha.
 * @param {number} [opciones.mes] Mes 1..12.
 * @param {string} [opciones.categoria] CONDUCTUAL | ACADEMICO.
 * @param {string} [opciones.gravedad] LEVE | GRAVE.
 * @param {string} [opciones.nivel] LICEO | ESCUELA.
 */
export async function listarReportes({
  page = 1,
  size = 10,
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

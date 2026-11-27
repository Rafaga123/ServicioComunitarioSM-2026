// Servicio de horarios de Liceo (una clase por sección, bloque y día).
//
//   GET    /horarios/registros/?offset=0&size=10&nivel=&id_seccion=&id_grado=
//          &id_asignatura=&id_docente=&id_bloque=&periodo_lectivo=&dia_semana=
//          -> { items, total, offset, size } (lectura para cualquier usuario
//             autenticado; el backend limita el nivel según su rol)
//   GET    /horarios/registros/{id}       -> PeticionHorario (ídem)
//   POST   /horarios/registros/           -> 201 (solo ADMIN)
//   PUT    /horarios/registros/{id}       -> PeticionHorario (solo ADMIN)
//   DELETE /horarios/registros/{id}       -> 204 (solo ADMIN)
//
//   GET    /bloques-horarios/?offset=0&size=100&tipo=ACADEMICO
//          -> bloques institucionales disponibles para programar.
//
//   GET    /horarios/?id_estudiante=&fecha=&hora=  (o id_bloque)
//          -> PeticionConsultaHorario: la clase de la sección del estudiante
//             para ese día y bloque, con asignatura y docente ya resueltos.
//          Se usa al registrar un pase para saber a qué clase faltó.
//
// Reglas que impone el backend y que el formulario debe respetar:
// - Solo secciones de Liceo, del mismo período lectivo del horario.
// - Solo bloques académicos.
// - La asignatura debe ser del grado y período de la sección.
// - El docente debe ser de Liceo y estar vinculado a la asignatura.
// - No puede repetirse sección ni docente en el mismo bloque y día.
import { apiFetch } from './api'

const RECURSO = '/horarios/registros/'
const BLOQUES = '/bloques-horarios/'

export const MAXIMO_POR_PAGINA = 100

// PeticionHorario -> objeto de la vista. El backend ya entrega los nombres
// preparados para la tabla, además de los id's que necesita el formulario.
const aHorario = (horario) => ({
  id: horario.id,
  idSeccion: horario.id_seccion,
  idBloque: horario.id_bloque,
  idAsignatura: horario.id_asignatura,
  idDocente: horario.id_docente,
  periodoLectivo: horario.periodo_lectivo,
  diaSemana: horario.dia_semana,
  seccion: horario.seccion ?? '',
  grado: horario.grado ?? '',
  nivel: horario.nivel ?? '',
  bloque: horario.bloque ?? '',
  bloqueOrden: horario.bloque_orden ?? null,
  horaInicio: horario.hora_inicio ?? '',
  horaFin: horario.hora_fin ?? '',
  asignatura: horario.asignatura ?? '',
  docente: horario.docente ?? '',
})

const aBloque = (bloque) => ({
  id: bloque.id,
  orden: bloque.orden,
  numero: bloque.numero ?? null,
  nombre: bloque.nombre ?? '',
  tipo: bloque.tipo ?? '',
  horaInicio: bloque.hora_inicio ?? '',
  horaFin: bloque.hora_fin ?? '',
})

// El PUT acepta todos los campos; el backend valida el estado final completo.
const aPayload = (horario) => ({
  id_seccion: Number(horario.idSeccion),
  id_bloque: Number(horario.idBloque),
  id_asignatura: Number(horario.idAsignatura),
  id_docente: Number(horario.idDocente),
  periodo_lectivo: Number(horario.periodoLectivo),
  dia_semana: Number(horario.diaSemana),
})

/**
 * Lista horarios con la paginación del backend.
 *
 * @param {object} [opciones]
 * @param {number} [opciones.page] Página 1-based.
 * @param {number} [opciones.size] Registros por página (máx. 100).
 * @param {string} [opciones.nivel] LICEO | ESCUELA (opcional; los horarios son de Liceo).
 * @param {number} [opciones.idSeccion] Filtra por sección (opcional).
 * @param {number} [opciones.idGrado] Filtra por grado (opcional).
 * @param {number} [opciones.idAsignatura] Filtra por asignatura (opcional).
 * @param {number} [opciones.idDocente] Filtra por docente (opcional).
 * @param {number} [opciones.idBloque] Filtra por bloque (opcional).
 * @param {number} [opciones.periodoLectivo] Filtra por año lectivo (opcional).
 * @param {number} [opciones.diaSemana] Filtra por día 1..5 (opcional).
 */
export async function listarHorarios({
  page = 1,
  size = 10,
  nivel,
  idSeccion,
  idGrado,
  idAsignatura,
  idDocente,
  idBloque,
  periodoLectivo,
  diaSemana,
} = {}) {
  const pagina = Math.max(1, Math.trunc(page) || 1)
  const tamano = Math.min(MAXIMO_POR_PAGINA, Math.max(1, Math.trunc(size) || 10))
  const offset = (pagina - 1) * tamano

  const data = await apiFetch(RECURSO, {
    params: {
      offset,
      size: tamano,
      nivel: nivel || undefined,
      id_seccion: idSeccion || undefined,
      id_grado: idGrado || undefined,
      id_asignatura: idAsignatura || undefined,
      id_docente: idDocente || undefined,
      id_bloque: idBloque || undefined,
      periodo_lectivo: periodoLectivo || undefined,
      dia_semana: diaSemana || undefined,
    },
  })

  return {
    items: (data?.items ?? []).map(aHorario),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

/** Trae TODOS los horarios (recorriendo páginas) para filtrar en cliente. */
export async function listarTodosHorarios({
  nivel,
  idSeccion,
  idGrado,
  idAsignatura,
  idDocente,
  idBloque,
  periodoLectivo,
  diaSemana,
} = {}) {
  const params = {
    offset: 0,
    size: MAXIMO_POR_PAGINA,
    nivel: nivel || undefined,
    id_seccion: idSeccion || undefined,
    id_grado: idGrado || undefined,
    id_asignatura: idAsignatura || undefined,
    id_docente: idDocente || undefined,
    id_bloque: idBloque || undefined,
    periodo_lectivo: periodoLectivo || undefined,
    dia_semana: diaSemana || undefined,
  }
  const items = []
  let offset = 0
  let total

  do {
    const data = await apiFetch(RECURSO, {
      params: { ...params, offset },
    })
    const pagina = (data?.items ?? []).map(aHorario)

    items.push(...pagina)
    total = data?.total ?? items.length
    offset += MAXIMO_POR_PAGINA

    if (!pagina.length) break
  } while (items.length < total)

  return { items, total }
}

export async function obtenerHorario(id) {
  return aHorario(await apiFetch(`${RECURSO}${id}`))
}

export async function crearHorario(horario) {
  return aHorario(
    await apiFetch(RECURSO, { method: 'POST', body: aPayload(horario) }),
  )
}

export async function actualizarHorario(id, horario) {
  return aHorario(
    await apiFetch(`${RECURSO}${id}`, {
      method: 'PUT',
      body: aPayload(horario),
    }),
  )
}

export async function eliminarHorario(id) {
  return apiFetch(`${RECURSO}${id}`, { method: 'DELETE' })
}

/** Bloques académicos disponibles, en el orden de la jornada. */
export async function listarBloquesAcademicos() {
  const data = await apiFetch(BLOQUES, {
    params: { offset: 0, size: MAXIMO_POR_PAGINA, tipo: 'ACADEMICO' },
  })
  return (data?.items ?? [])
    .map(aBloque)
    .sort((a, b) => a.orden - b.orden)
}

/**
 * Todos los bloques de la jornada (académicos y recesos), en orden.
 * La grilla semanal los usa como filas para que se vean también los huecos.
 */
export async function listarBloquesHorarios() {
  const data = await apiFetch(BLOQUES, {
    params: { offset: 0, size: MAXIMO_POR_PAGINA },
  })
  return (data?.items ?? [])
    .map(aBloque)
    .sort((a, b) => a.orden - b.orden)
}

/**
 * Horario completo de una sección en un período: como máximo 5 días × 8
 * bloques, así que una sola página de 100 registros basta para la grilla.
 */
export async function listarHorarioSemana({ idSeccion, periodoLectivo, nivel } = {}) {
  if (!idSeccion) return { items: [], total: 0 }

  const data = await apiFetch(RECURSO, {
    params: {
      offset: 0,
      size: MAXIMO_POR_PAGINA,
      id_seccion: idSeccion,
      periodo_lectivo: periodoLectivo || undefined,
      nivel: nivel || undefined,
    },
  })

  return {
    items: (data?.items ?? []).map(aHorario),
    total: data?.total ?? 0,
  }
}

/**
 * Clase que cursa el estudiante en una fecha y hora concretas.
 *
 * El backend usa el día de la semana de `fecha`, busca el bloque académico que
 * contenga `hora` y devuelve el horario de la sección del estudiante con la
 * asignatura y el docente ya resueltos. Si no hay clase (fin de semana, fuera
 * de bloque o sección sin horario) devuelve `encontrado: false`.
 *
 * @param {object} opciones
 * @param {number} opciones.idEstudiante
 * @param {string} opciones.fecha YYYY-MM-DD
 * @param {string} opciones.hora HH:mm
 */
export async function consultarHorarioEstudiante({ idEstudiante, fecha, hora }) {
  const data = await apiFetch('/horarios/', {
    params: {
      id_estudiante: Number(idEstudiante),
      fecha,
      hora: String(hora ?? '').slice(0, 5),
    },
  })

  return {
    encontrado: Boolean(data?.encontrado),
    idHorario: data?.id_horario ?? null,
    idBloque: data?.id_bloque ?? null,
    idAsignatura: data?.id_asignatura ?? null,
    idDocente: data?.id_docente ?? null,
    asignatura: data?.asignatura ?? '',
    docente: data?.docente ?? '',
    bloque: data?.bloque ?? '',
    // El backend serializa `time` con segundos (07:00:00); el formulario
    // muestra solo HH:mm para mantener el mismo formato del input de hora.
    horaInicio: String(data?.hora_inicio ?? '').slice(0, 5),
    horaFin: String(data?.hora_fin ?? '').slice(0, 5),
  }
}

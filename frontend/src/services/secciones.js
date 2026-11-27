// Servicio de secciones (aulas activas de un grado).
//
//   GET    /secciones/?offset=0&size=10&nivel=&id_grado=&periodo_lectivo=
//   GET    /secciones/{id}
//   POST   /secciones/       -> 201 PeticionSeccion (solo ADMIN)
//   PUT    /secciones/{id}   -> PeticionSeccion     (solo ADMIN)
//   DELETE /secciones/{id}   -> 204                 (solo ADMIN)
//
// Una sección combina grado + letra (A, B o U) + período lectivo. Por grado y
// período solo se admiten dos formatos: la sección única U, o las secciones A
// y B juntas. El backend evita duplicados de grado+letra+período, pero no
// conoce esa regla: se aplica aquí, en el frontend, al crear y al dar de baja.
import { apiFetch } from './api'
import { seccionesConDependencias } from './dependencias'

const RECURSO = '/secciones/'

export const MAXIMO_POR_PAGINA = 100

const aSeccion = (seccion) => ({
  id: seccion.id,
  idGrado: seccion.id_grado,
  letra: seccion.letra ?? '',
  periodoLectivo: seccion.periodo_lectivo,
  idDocenteTitular: seccion.id_docente_titular ?? null,
  gradoNumero: seccion.grado_numero ?? null,
  gradoNombre: seccion.grado_nombre ?? '',
  nivel: seccion.nivel ?? '',
  docenteTitular: seccion.docente_titular ?? '',
})

const aPayload = (seccion) => ({
  id_grado: Number(seccion.idGrado),
  letra: String(seccion.letra ?? '').trim().toUpperCase(),
  periodo_lectivo: Number(seccion.periodoLectivo),
  id_docente_titular: seccion.idDocenteTitular || null,
})

export async function listarSecciones({
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
    items: (data?.items ?? []).map(aSeccion),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

/** Trae todas las secciones del nivel y período indicados. */
export async function listarTodasSecciones({ nivel, periodoLectivo } = {}) {
  const items = []
  let offset = 0
  let total

  do {
    const data = await apiFetch(RECURSO, {
      params: {
        offset,
        size: MAXIMO_POR_PAGINA,
        nivel: nivel || undefined,
        periodo_lectivo: periodoLectivo || undefined,
      },
    })
    const pagina = (data?.items ?? []).map(aSeccion)

    items.push(...pagina)
    total = data?.total ?? items.length
    offset += MAXIMO_POR_PAGINA

    if (!pagina.length) break
  } while (items.length < total)

  return { items, total }
}

export async function obtenerSeccion(id) {
  return aSeccion(await apiFetch(`${RECURSO}${id}`))
}

export async function crearSeccion(seccion) {
  return aSeccion(
    await apiFetch(RECURSO, { method: 'POST', body: aPayload(seccion) }),
  )
}

export async function actualizarSeccion(id, seccion) {
  return aSeccion(
    await apiFetch(`${RECURSO}${id}`, {
      method: 'PUT',
      body: aPayload(seccion),
    }),
  )
}

export async function eliminarSeccion(id) {
  return apiFetch(`${RECURSO}${id}`, { method: 'DELETE' })
}

// ───────────── Regla de formato: U sola / A y B juntas ─────────────

export const LETRAS_POR_FORMATO = Object.freeze({
  unica: ['U'],
  dividida: ['A', 'B'],
})

const ETIQUETAS_FORMATO = {
  unica: 'Sección única (U)',
  dividida: 'Secciones A y B',
  'sin-crear': 'Sin secciones',
  inconsistente: 'Secciones inconsistentes',
}

export const etiquetaFormato = (formato) => ETIQUETAS_FORMATO[formato] ?? formato

/**
 * Clasifica las secciones de un grado en un período:
 *   sin-crear | unica (U) | dividida (A+B) | inconsistente
 */
export function formatoSecciones(secciones, idGrado, periodoLectivo) {
  const letras = new Set(
    (secciones ?? [])
      .filter(
        (s) =>
          Number(s.idGrado) === Number(idGrado) &&
          Number(s.periodoLectivo) === Number(periodoLectivo),
      )
      .map((s) => String(s.letra ?? '').toUpperCase()),
  )

  if (!letras.size) return 'sin-crear'
  const claves = [...letras].sort().join('')
  if (claves === 'U') return 'unica'
  if (claves === 'AB') return 'dividida'
  return 'inconsistente'
}

/**
 * Crea el formato completo de un grado/período. "unica" hace un POST (U);
 * "dividida" hace dos POST (A y B). Si falla el segundo, se da de baja el
 * primero para no dejar una A huérfana.
 * `titulares` es un mapa por letra: { U, A, B }, con docentes distintos.
 */
export async function crearFormatoSecciones({
  idGrado,
  periodoLectivo,
  formato,
  titulares = {},
} = {}) {
  const letras = LETRAS_POR_FORMATO[formato]
  if (!letras) throw new Error('Selecciona un formato de sección válido.')

  // Doble control: el formulario ya valida sobre el catálogo, pero esto evita
  // un estado partido si el catálogo estaba desactualizado.
  const { items } = await listarSecciones({
    idGrado,
    periodoLectivo,
    size: MAXIMO_POR_PAGINA,
  })
  const actual = formatoSecciones(items, idGrado, periodoLectivo)
  if (actual !== 'sin-crear') {
    throw new Error(
      actual === 'unica'
        ? 'Este grado ya tiene la sección única U. Dala de baja para crear A y B.'
        : actual === 'dividida'
          ? 'Este grado ya tiene las secciones A y B. Dales de baja para crear la sección única U.'
          : 'Las secciones de este grado están inconsistentes. Corrígelas antes de crear otras.',
    )
  }

  const creadas = []
  try {
    for (const letra of letras) {
      creadas.push(
        await crearSeccion({
          idGrado,
          periodoLectivo,
          letra,
          idDocenteTitular: titulares[letra] ?? null,
        }),
      )
    }
    return creadas
  } catch (error) {
    if (creadas.length) {
      try {
        await Promise.all(creadas.map((s) => eliminarSeccion(s.id)))
      } catch {
        throw new Error(
          `${error.message} No se pudo revertir la sección creada; revisa la lista antes de reintentar.`,
          { cause: error },
        )
      }
    }
    throw error
  }
}

/** Da de baja U, o A y B juntas, con preflight de estudiantes y horarios. */
export async function eliminarFormatoSecciones(secciones) {
  const lista = secciones ?? []
  if (!lista.length) return

  const bloqueadas = await seccionesConDependencias(lista)
  if (bloqueadas.length) {
    const detalle = bloqueadas
      .map(({ seccion, estudiantes, horarios }) => {
        const motivos = []
        if (estudiantes) motivos.push(`${estudiantes} estudiante(s)`)
        if (horarios) motivos.push(`${horarios} horario(s)`)
        return `${seccion.letra}: ${motivos.join(' y ')}`
      })
      .join('; ')
    throw new Error(
      `No se pueden dar de baja esas secciones (${detalle}). Traslada a los estudiantes y revisa los horarios.`,
    )
  }

  const borradas = []
  try {
    for (const seccion of lista) {
      await eliminarSeccion(seccion.id)
      borradas.push(seccion)
    }
  } catch (error) {
    if (borradas.length) {
      const letras = borradas.map((s) => s.letra).sort().join(' y ')
      throw new Error(
        `${error.message} Se dio de baja ${letras} pero no se pudo completar la baja; revisa la lista antes de reintentar.`,
        { cause: error },
      )
    }
    throw error
  }
}

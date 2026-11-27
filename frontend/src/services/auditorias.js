// Servicio del historial de auditoría (solo administradores).
//
//   GET /auditorias/?offset=0&size=10&usuario=&modulo=&accion=&fecha=
//     -> { items, total, offset, size }
//   GET /auditorias/{id} -> PeticionAuditoria
//
// Los filtros de texto se resuelven en el backend (ilike), así que no hace
// falta traer la lista completa para filtrar. `listarTodasAuditorias` existe
// solo para exportar a CSV todas las coincidencias.
import { apiFetch } from './api'

const RECURSO = '/auditorias/'

// Límite que impone el backend en el parámetro `size` (Paginacion: le=100).
export const MAXIMO_POR_PAGINA = 100

// `texto_legible()` del backend guarda estos valores con espacios y tilde
// (por ejemplo `BLOQUES HORARIOS`, `CIERRE AÑO`), no con guiones bajos.
export const MODULOS_AUDITORIA = [
  'USUARIOS',
  'ESTUDIANTES',
  'GRADOS',
  'SECCIONES',
  'REPRESENTANTES',
  'DOCENTES',
  'ASIGNATURAS',
  'BLOQUES HORARIOS',
  'HORARIOS',
  'PASES',
  'REPORTES',
  'AUDITORIAS',
  'PERIODOS LECTIVOS',
  'DOCUMENTOS',
  'CIERRE AÑO',
]

// `accion` es texto libre en el backend, no un enum. Estas son las acciones
// que realmente registra; el filtro usa `ilike`, así que deben ir legibles.
export const ACCIONES_AUDITORIA = [
  'CREAR',
  'ACTUALIZAR',
  'ELIMINAR',
  'CAMBIAR CLAVE',
  'TRANSFERIR ADMIN',
  'VINCULAR DOCENTE',
  'DESVINCULAR DOCENTE',
  'VINCULAR ESTUDIANTE',
  'DESVINCULAR ESTUDIANTE',
  'GENERAR',
  'REUTILIZAR',
  'DESCARGAR ARCHIVO',
  'SUBIR ARCHIVO',
  'QUITAR ARCHIVO',
  'INICIO DE SESIÓN',
  'CIERRE DE SESIÓN',
]

// PeticionAuditoria -> objeto de la vista
export const aAuditoria = (registro) => ({
  id: registro.id,
  usuarioId: registro.usuario_id ?? null,
  usuario: registro.usuario ?? '',
  modulo: registro.modulo ?? '',
  accion: registro.accion ?? '',
  descripcion: registro.descripcion ?? '',
  fechaCreacion: registro.fecha_creacion ?? null,
})

const paramsDe = ({ usuario, modulo, accion, fecha } = {}) => ({
  usuario: usuario || undefined,
  modulo: modulo || undefined,
  accion: accion || undefined,
  fecha: fecha || undefined,
})

/**
 * Lista auditorías con la paginación y los filtros del backend.
 * El backend recibe offset/size, no número de página.
 */
export async function listarAuditorias({
  page = 1,
  size = 10,
  usuario,
  modulo,
  accion,
  fecha,
} = {}) {
  const pagina = Math.max(1, Math.trunc(page) || 1)
  const tamano = Math.min(MAXIMO_POR_PAGINA, Math.max(1, Math.trunc(size) || 10))
  const offset = (pagina - 1) * tamano

  const data = await apiFetch(RECURSO, {
    params: {
      offset,
      size: tamano,
      ...paramsDe({ usuario, modulo, accion, fecha }),
    },
  })

  return {
    items: (data?.items ?? []).map(aAuditoria),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

/** Todas las coincidencias de los filtros actuales, para exportar a CSV. */
export async function listarTodasAuditorias(filtros = {}) {
  const items = []
  let page = 1
  let total

  do {
    const respuesta = await listarAuditorias({
      ...filtros,
      page,
      size: MAXIMO_POR_PAGINA,
    })
    items.push(...respuesta.items)
    total = respuesta.total
    page += 1
    if (!respuesta.items.length) break
  } while (items.length < total)

  return { items, total }
}

export async function obtenerAuditoria(id) {
  return aAuditoria(await apiFetch(`${RECURSO}${id}`))
}

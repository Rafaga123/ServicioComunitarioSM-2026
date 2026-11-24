// Servicio de cuentas de usuario.
//
//   GET    /usuarios/?offset=0&size=10&rol=&nivel= -> { items, total, offset, size }
//   GET    /usuarios/{id}                         -> PeticionUsuario
//   POST   /usuarios/                             -> 201 PeticionUsuario (solo ADMIN)
//   PUT    /usuarios/{id}                         -> PeticionUsuario        (solo ADMIN)
//   DELETE /usuarios/{id}                         -> 204                    (solo ADMIN)
//   PUT    /usuarios/me/clave                     -> 204 (clave del propio usuario)
//
// La API no permite buscar por nombre de usuario, así que el listado completo
// se usa para filtrar en cliente. Tampoco permite cambiar la clave de otro
// usuario: `/me/clave` exige la clave actual de la sesión.
import { apiFetch } from './api'

const RECURSO = '/usuarios/'

// Límite que impone el backend en el parámetro `size` (Paginacion: le=100).
export const MAXIMO_POR_PAGINA = 100

export const ROLES_ASIGNABLES = [
  { valor: 'COORDINADOR', etiqueta: 'Coordinador' },
  { valor: 'SECRETARIA', etiqueta: 'Secretaría' },
]

export const ROLES_USUARIO = [
  { valor: 'ADMINISTRADOR', etiqueta: 'Administrador' },
  ...ROLES_ASIGNABLES,
]

export const NIVELES = [
  { valor: 'LICEO', etiqueta: 'Liceo' },
  { valor: 'ESCUELA', etiqueta: 'Escuela' },
]

export const etiquetaRol = (rol) =>
  ROLES_USUARIO.find((opcion) => opcion.valor === rol)?.etiqueta ?? rol ?? '—'

export const etiquetaNivel = (nivel) =>
  NIVELES.find((opcion) => opcion.valor === nivel)?.etiqueta ?? (nivel || 'Todos los niveles')

// PeticionUsuario -> objeto de la vista
export const aUsuario = (usuario) => ({
  id: usuario.id,
  nombre: usuario.nombre ?? '',
  rol: usuario.rol ?? '',
  nivel: usuario.nivel ?? null,
})

const aPayloadCrear = (usuario) => ({
  nombre: String(usuario.nombre ?? '').trim(),
  clave: usuario.clave ?? '',
  rol: usuario.rol || undefined,
  nivel: usuario.nivel || undefined,
})

// ActualizarUsuario usa exclude_unset: no hay que enviar campos vacíos.
const aPayloadActualizar = (usuario) => {
  const payload = {}
  if (usuario.nombre !== undefined) payload.nombre = String(usuario.nombre).trim()
  if (usuario.rol !== undefined) payload.rol = usuario.rol || undefined
  if (usuario.nivel !== undefined) payload.nivel = usuario.nivel || undefined
  return payload
}

/**
 * Lista usuarios con la paginación del backend.
 * El backend recibe offset/size, no número de página.
 */
export async function listarUsuarios({ page = 1, size = 10, nivel, rol } = {}) {
  const pagina = Math.max(1, Math.trunc(page) || 1)
  const tamano = Math.min(MAXIMO_POR_PAGINA, Math.max(1, Math.trunc(size) || 10))
  const offset = (pagina - 1) * tamano

  const data = await apiFetch(RECURSO, {
    params: {
      offset,
      size: tamano,
      nivel: nivel || undefined,
      rol: rol || undefined,
    },
  })

  return {
    items: (data?.items ?? []).map(aUsuario),
    total: data?.total ?? 0,
    offset: data?.offset ?? offset,
    size: data?.size ?? tamano,
    page: pagina,
  }
}

/** Trae TODOS los usuarios (recorriendo páginas) para filtrar por nombre en cliente. */
export async function listarTodosUsuarios({ nivel, rol } = {}) {
  const items = []
  let offset = 0
  let total

  do {
    const data = await apiFetch(RECURSO, {
      params: {
        offset,
        size: MAXIMO_POR_PAGINA,
        nivel: nivel || undefined,
        rol: rol || undefined,
      },
    })
    const pagina = (data?.items ?? []).map(aUsuario)

    items.push(...pagina)
    total = data?.total ?? items.length
    offset += MAXIMO_POR_PAGINA

    if (!pagina.length) break
  } while (items.length < total)

  return { items, total }
}

export async function obtenerUsuario(id) {
  return aUsuario(await apiFetch(`${RECURSO}${id}`))
}

export async function crearUsuario(usuario) {
  return aUsuario(
    await apiFetch(RECURSO, { method: 'POST', body: aPayloadCrear(usuario) }),
  )
}

export async function actualizarUsuario(id, usuario) {
  return aUsuario(
    await apiFetch(`${RECURSO}${id}`, {
      method: 'PUT',
      body: aPayloadActualizar(usuario),
    }),
  )
}

export async function eliminarUsuario(id) {
  return apiFetch(`${RECURSO}${id}`, { method: 'DELETE' })
}

/** Cambia la clave del usuario autenticado; requiere la clave actual. */
export async function cambiarMiClave({ claveActual, claveNueva }) {
  return apiFetch(`${RECURSO}me/clave`, {
    method: 'PUT',
    body: { clave_actual: claveActual, clave_nueva: claveNueva },
  })
}

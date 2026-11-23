// Sesión del frontend basada en el JWT que emite /api/auth/login.
//
// El backend firma el token con estos claims (app/routers/auth.py):
//   sub   -> id del usuario
//   rol   -> ADMINISTRADOR | COORDINADOR | SECRETARIA
//   nivel -> LICEO | ESCUELA | null (el administrador no tiene nivel)
//   exp   -> fecha de expiración
//
// Con esos datos el frontend decide qué menú mostrar y qué rutas permitir.
// El nombre del usuario no viaja en el token: se pide a /auth/me.
import { computed, reactive } from 'vue'
import { apiFetch } from './api'

export const ROLES = {
  ADMINISTRADOR: 'ADMINISTRADOR',
  COORDINADOR: 'COORDINADOR',
  SECRETARIA: 'SECRETARIA',
}

export const NIVELES = {
  LICEO: 'LICEO',
  ESCUELA: 'ESCUELA',
}

// Rutas habilitadas por rol. Es la única fuente de verdad: la usan el sidebar
// y el guard del router, así que ocultar un enlace y bloquear la URL coinciden.
const RUTAS_POR_ROL = {
  [ROLES.ADMINISTRADOR]: [
    'dashboard',
    'pases',
    'reportes',
    'gestion-academica',
    'usuarios',
    'auditorias',
  ],
  [ROLES.SECRETARIA]: ['dashboard', 'pases'],
  [ROLES.COORDINADOR]: ['dashboard', 'reportes'],
}

const ETIQUETAS_ROL = {
  [ROLES.ADMINISTRADOR]: 'Administrador',
  [ROLES.COORDINADOR]: 'Coordinador',
  [ROLES.SECRETARIA]: 'Secretaría',
}

const ETIQUETAS_NIVEL = {
  [NIVELES.LICEO]: 'Liceo',
  [NIVELES.ESCUELA]: 'Escuela',
}

// Decodifica el payload del JWT sin validar la firma (eso lo hace el backend).
// Devuelve null si el token no es legible o ya expiró.
const decodificarToken = (token) => {
  try {
    const parte = token.split('.')[1]
    if (!parte) return null

    const base64 = parte.replace(/-/g, '+').replace(/_/g, '/')
    const relleno = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    const payload = JSON.parse(atob(relleno))

    if (typeof payload.exp === 'number' && payload.exp * 1000 <= Date.now()) {
      return null
    }

    return {
      id: payload.sub != null && payload.sub !== '' ? Number(payload.sub) : null,
      rol: payload.rol ?? null,
      nivel: payload.nivel ?? null,
      exp: payload.exp ?? null,
    }
  } catch {
    // Token ilegible: se trata como sesión ausente.
    return null
  }
}

export const sesion = reactive({
  token: null,
  // { id, nombre?, rol, nivel, exp }
  usuario: null,
  cargando: false,
})

let tokenCargado = null

// Lee el token de localStorage y actualiza el estado reactivo.
// También limpia tokens vencidos para no arrastrar sesiones inválidas.
export const sincronizarSesion = () => {
  const token = localStorage.getItem('token')

  if (token === tokenCargado) return sesion.usuario

  tokenCargado = token
  sesion.token = token
  sesion.usuario = token ? decodificarToken(token) : null

  if (token && !sesion.usuario) {
    localStorage.removeItem('token')
    tokenCargado = null
    sesion.token = null
  }

  return sesion.usuario
}

// Guarda el token recién emitido por el login y sincroniza el estado.
export const iniciarSesion = (token) => {
  localStorage.setItem('token', token)
  tokenCargado = token
  sesion.token = token
  sesion.usuario = decodificarToken(token)
  return sesion.usuario
}

export const cerrarSesion = () => {
  localStorage.removeItem('token')
  tokenCargado = null
  sesion.token = null
  sesion.usuario = null
}

// /auth/me devuelve id, nombre, rol y nivel. El rol/nivel del servidor manda
// sobre el token (por si la cuenta cambió después de emitirlo).
export const cargarPerfil = async () => {
  if (!sesion.token) return null

  sesion.cargando = true
  try {
    const perfil = await apiFetch('/auth/me')
    if (!perfil) return null

    sesion.usuario = {
      ...sesion.usuario,
      id: perfil.id ?? sesion.usuario?.id ?? null,
      nombre: perfil.nombre ?? sesion.usuario?.nombre ?? '',
      rol: perfil.rol ?? sesion.usuario?.rol ?? null,
      nivel: perfil.nivel ?? null,
    }

    return sesion.usuario
  } catch {
    // Un 401 ya limpia el token y redirige desde api.js.
    return null
  } finally {
    sesion.cargando = false
  }
}

export const rolActual = computed(() => sesion.usuario?.rol ?? null)
export const nivelActual = computed(() => sesion.usuario?.nivel ?? null)
export const esAdministrador = computed(() => rolActual.value === ROLES.ADMINISTRADOR)

// Ruta de inicio: todos los roles tienen dashboard.
export const rutaInicio = () => 'dashboard'

export const puedeAccederRuta = (nombreRuta) => {
  if (!nombreRuta) return false

  const rol = sesion.usuario?.rol
  const permitidas = RUTAS_POR_ROL[rol] ?? []
  return permitidas.includes(nombreRuta)
}

export const etiquetaRol = (rol = sesion.usuario?.rol) =>
  ETIQUETAS_ROL[rol] ?? rol ?? 'Sin rol'

export const etiquetaNivel = (nivel = sesion.usuario?.nivel) =>
  ETIQUETAS_NIVEL[nivel] ?? (nivel || '')

// Arranque del módulo: deja la sesión lista antes de que el router navegue.
sincronizarSesion()

// Cliente HTTP central para hablar con la API (FastAPI).
// En desarrollo, /api se resuelve con el proxy de vite.config.js.
// Si necesitas apuntar a otro servidor, define VITE_API_URL en tu .env.
const API_URL = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(message, status = 0, data = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

// FastAPI devuelve los errores de validación como { detail: [...] }.
const extraerMensaje = (data, status) => {
  if (typeof data?.detail === 'string') return data.detail

  if (Array.isArray(data?.detail)) {
    const detalles = data.detail
      .map((item) => {
        if (typeof item === 'string') return item
        const campo = Array.isArray(item?.loc) ? item.loc.slice(1).join('.') : ''
        return [campo, item?.msg].filter(Boolean).join(': ')
      })
      .filter(Boolean)

    if (detalles.length) return detalles.join('. ')
  }

  if (status === 401) return 'Tu sesión expiró. Inicia sesión nuevamente.'
  if (status === 403) return 'No tienes permisos para realizar esta acción.'
  if (status === 404) return 'El registro solicitado no existe.'
  return `No se pudo completar la solicitud (error ${status}).`
}

const construirUrl = (path, params) => {
  const url = `${API_URL}${path}`
  if (!params) return url

  const query = new URLSearchParams()
  Object.entries(params).forEach(([clave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== '') {
      query.set(clave, String(valor))
    }
  })

  const qs = query.toString()
  return qs ? `${url}?${qs}` : url
}

// Token vencido o inválido: limpiamos la sesión y volvemos al login
// conservando la ruta actual para retomarla después de autenticarse.
const cerrarSesion = () => {
  localStorage.removeItem('token')

  if (window.location.pathname !== '/login') {
    const destino = `${window.location.pathname}${window.location.search}`
    window.location.assign(`/login?redirect=${encodeURIComponent(destino)}`)
  }
}

/**
 * Ejecuta una petición a la API.
 *
 * @param {string} path Ruta relativa al prefijo /api (ej. "/docentes/").
 * @param {object} [options]
 * @param {string} [options.method] GET por defecto.
 * @param {object|FormData} [options.body] Se serializa a JSON salvo FormData.
 * @param {object} [options.params] Query string (offset, size, etc.).
 * @param {boolean} [options.auth] Añade el Bearer token (true por defecto).
 * @param {number} [options.timeout] Milisegundos antes de abortar.
 * @returns {Promise<any>} JSON de la respuesta o null en 204.
 */
export async function apiFetch(
  path,
  { method = 'GET', body, params, auth = true, timeout = 15000 } = {},
) {
  const headers = { Accept: 'application/json' }
  const esFormData = typeof FormData !== 'undefined' && body instanceof FormData

  if (body !== undefined && !esFormData) {
    headers['Content-Type'] = 'application/json'
  }

  if (auth) {
    const token = localStorage.getItem('token')
    if (token) headers.Authorization = `Bearer ${token}`
  }

  let response
  const enviarCuerpo = body !== undefined && method !== 'GET'
  try {
    response = await fetch(construirUrl(path, params), {
      method,
      headers,
      ...(enviarCuerpo ? { body: esFormData ? body : JSON.stringify(body) } : {}),
      signal:
        typeof AbortSignal !== 'undefined' && AbortSignal.timeout
          ? AbortSignal.timeout(timeout)
          : undefined,
    })
  } catch (error) {
    if (error?.name === 'TimeoutError' || error?.name === 'AbortError') {
      throw new ApiError('El servidor tardó demasiado en responder. Intenta de nuevo.', 0)
    }
    throw new ApiError(
      'No se pudo conectar con el servidor. Verifica que la API esté encendida.',
      0,
    )
  }

  if (response.status === 204) return null

  const texto = await response.text()
  let data = null
  if (texto) {
    try {
      data = JSON.parse(texto)
    } catch {
      data = texto
    }
  }

  if (!response.ok) {
    if (response.status === 401) cerrarSesion()
    throw new ApiError(extraerMensaje(data, response.status), response.status, data)
  }

  return data
}

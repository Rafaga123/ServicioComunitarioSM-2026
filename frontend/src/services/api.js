// Cliente HTTP central para hablar con la API (FastAPI).
// En desarrollo, /api se resuelve con el proxy de vite.config.js.
// Si necesitas apuntar a otro servidor, define VITE_API_URL en tu .env.
const API_URL = (import.meta.env.VITE_API_URL ?? '/api').replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(message, status = 0, data = null, retryAfter = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
    // Segundos indicados por el backend en una respuesta 429 (login).
    this.retryAfter = retryAfter
  }
}

const retryAfterDe = (response) => {
  if (response?.status !== 429) return null
  const segundos = Number.parseInt(response.headers?.get?.('Retry-After') ?? '', 10)
  return Number.isFinite(segundos) && segundos > 0 ? segundos : null
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
  // 502/503/504 llegan del proxy de Vite cuando el backend está apagado o
  // inaccesible; conviene un mensaje accionable en vez del número de error.
  if (status === 502 || status === 503 || status === 504) {
    return 'No se pudo conectar con el servidor. Verifica que la API esté encendida.'
  }
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
    throw new ApiError(
      extraerMensaje(data, response.status),
      response.status,
      data,
      retryAfterDe(response),
    )
  }

  return data
}

// Nombre de archivo que envía el backend en Content-Disposition. FastAPI usa
// `filename*=utf-8''...` para nombres con acentos y `filename="..."` como
// respaldo; se intentan ambos.
const nombreDeCabecera = (cabecera) => {
  const extendido = /filename\*\s*=\s*utf-8''([^;]+)/i.exec(cabecera)
  if (extendido) {
    try {
      return decodeURIComponent(extendido[1].trim())
    } catch {
      return extendido[1].trim()
    }
  }

  const simple = /filename\s*=\s*"?([^";]+)"?/i.exec(cabecera)
  return simple ? simple[1].trim() : ''
}

/**
 * Descarga un archivo binario de la API (adjuntos de pases y reportes).
 *
 * @param {string} path Ruta relativa al prefijo /api.
 * @param {object} [options]
 * @param {object} [options.params] Query string (por ejemplo `inline`).
 * @param {number} [options.timeout] Milisegundos antes de abortar.
 * @returns {Promise<{blob: Blob, nombre: string, mime: string}>}
 */
export async function apiDescargar(path, { params, timeout = 60000 } = {}) {
  const headers = { Accept: '*/*' }
  const token = localStorage.getItem('token')
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(construirUrl(path, params), {
      headers,
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

  if (!response.ok) {
    const texto = await response.text()
    let data = null
    if (texto) {
      try {
        data = JSON.parse(texto)
      } catch {
        data = texto
      }
    }
    if (response.status === 401) cerrarSesion()
    throw new ApiError(
      extraerMensaje(data, response.status),
      response.status,
      data,
      retryAfterDe(response),
    )
  }

  const blob = await response.blob()
  return {
    blob,
    nombre: nombreDeCabecera(response.headers.get('Content-Disposition') || ''),
    mime: blob.type,
  }
}

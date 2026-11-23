// Catálogos y funciones de formato compartidas por la gestión académica.

export const anios = [1, 2, 3, 4, 5] // Grados.grado (integer)
export const secciones = ['A', 'B', 'C', 'D'] // Grados.seccion
export const dias = [
  { v: 1, l: 'Lunes' },
  { v: 2, l: 'Martes' },
  { v: 3, l: 'Miércoles' },
  { v: 4, l: 'Jueves' },
  { v: 5, l: 'Viernes' },
] // Horarios.dia_semana (integer)

export const norm = (s) =>
  String(s ?? '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')

export const ordinal = (n) => ['1er', '2do', '3er', '4to', '5to', '6to'][n - 1] ?? `${n}°`

// Acepta tanto la forma de la API (primerNombre...) como la local (nombre/apellido).
export const nomPersona = (x) => {
  const partes = [x?.primerNombre, x?.segundoNombre, x?.primerApellido, x?.segundoApellido]
    .filter(Boolean)
    .join(' ')
  return partes || [x?.nombre, x?.apellido].filter(Boolean).join(' ') || '—'
}

export const nomEst = (e) =>
  [e.primerNombre, e.segundoNombre, e.primerApellido, e.segundoApellido].filter(Boolean).join(' ')

export const nomDocente = (d) =>
  [d.primerNombre, d.segundoNombre, d.primerApellido, d.segundoApellido].filter(Boolean).join(' ') ||
  '—'

export const diaNombre = (v) => dias.find((d) => d.v === v)?.l ?? '—'

export const gradoTexto = (grados, id) => {
  const g = grados.find((x) => x.id === id)
  return g ? `${ordinal(g.grado)} Año · Sección ${g.seccion}` : '—'
}

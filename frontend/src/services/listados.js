// Servicio de listados institucionales generados por el backend.
//
//   POST /listados/{tipo}            -> DocumentoGenerado (con el id del PDF)
//   GET  /listados/documentos/{id}/archivo -> archivo PDF
//
// Tipos usados por Gestión Académica: nominas, representantes, docentes y
// horarios. El backend valida el nivel, el periodo y la sección cuando aplica.
import { apiDescargar, apiFetch } from './api'

const RECURSO = '/listados'
const TIPOS = new Set(['nominas', 'representantes', 'docentes', 'horarios'])

const validarTipo = (tipo) => {
  if (!TIPOS.has(tipo)) throw new Error('Tipo de listado no válido.')
  return tipo
}

/** Genera (o reutiliza) un PDF de listado en el backend. */
export async function generarListado({ tipo, filtros = {} } = {}) {
  return apiFetch(`${RECURSO}/${validarTipo(tipo)}`, {
    method: 'POST',
    timeout: 60000,
    body: filtros,
  })
}

/** Descarga el PDF ya generado por el backend. */
export async function descargarListado(documentoId) {
  if (!documentoId) throw new Error('El documento no está disponible.')

  return apiDescargar(`${RECURSO}/documentos/${documentoId}/archivo`)
}

/**
 * Genera un listado y devuelve el PDF listo para guardar.
 * @returns {Promise<{blob: Blob, nombre: string}>}
 */
export async function exportarListado({
  tipo,
  filtros = {},
  nombrePorDefecto = 'listado.pdf',
} = {}) {
  const documento = await generarListado({ tipo, filtros })
  if (!documento?.id) {
    throw new Error('El servidor no devolvió el documento generado.')
  }

  const archivo = await descargarListado(documento.id)
  return {
    blob: archivo.blob,
    nombre: archivo.nombre || documento.nombre_archivo || nombrePorDefecto,
  }
}

/** Horario de una sección de Liceo. */
export function exportarListadoHorarios({ idSeccion, periodoLectivo } = {}) {
  if (!idSeccion) throw new Error('Selecciona una sección para exportar.')

  return exportarListado({
    tipo: 'horarios',
    nombrePorDefecto: 'horario.pdf',
    filtros: {
      id_seccion: Number(idSeccion),
      ...(periodoLectivo ? { periodo_lectivo: Number(periodoLectivo) } : {}),
    },
  })
}

/**
 * Nómina, representantes o docentes del nivel y período indicados.
 * La nómina acepta además año/grado o sección; el backend no admite ambos a la
 * vez, así que la sección (más específica) gana si vienen los dos.
 */
export function exportarListadoGeneral(
  tipo,
  { nivel, periodoLectivo, idGrado, idSeccion } = {},
) {
  if (!nivel) throw new Error('Elige un nivel para exportar.')

  const filtros = {
    nivel,
    ...(periodoLectivo ? { periodo_lectivo: Number(periodoLectivo) } : {}),
  }
  if (idSeccion) filtros.id_seccion = Number(idSeccion)
  else if (idGrado) filtros.id_grado = Number(idGrado)

  return exportarListado({
    tipo,
    nombrePorDefecto: `${tipo}.pdf`,
    filtros,
  })
}

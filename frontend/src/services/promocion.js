/* global api */
//La parte de la API esta documentada para prueba nada mas
//import api from './api'

// Datos de prueba para visualiuzacion del proceso, ya despues cuando se conecte con backend
//  se quitan y ademas se coloca la variable de usar mock en false
const USAR_MOCK = true

const MOCK_GRADOS = [
  { id: 11, numero: 11, nombre: '5to Año', nivel: 'liceo', total_estudiantes: 4, procesado: false },
  { id: 10, numero: 10, nombre: '4to Año', nivel: 'liceo', total_estudiantes: 3, procesado: false },
  { id: 9, numero: 9, nombre: '3er Año', nivel: 'liceo', total_estudiantes: 0, procesado: true },
  { id: 8, numero: 8, nombre: '2do Año', nivel: 'liceo', total_estudiantes: 0, procesado: true },
  { id: 7, numero: 7, nombre: '1er Año', nivel: 'liceo', total_estudiantes: 0, procesado: true },
  { id: 6, numero: 6, nombre: '6to Grado', nivel: 'escuela', total_estudiantes: 3, procesado: false },
  { id: 5, numero: 5, nombre: '5to Grado', nivel: 'escuela', total_estudiantes: 0, procesado: true },
  { id: 4, numero: 4, nombre: '4to Grado', nivel: 'escuela', total_estudiantes: 0, procesado: true },
  { id: 3, numero: 3, nombre: '3er Grado', nivel: 'escuela', total_estudiantes: 0, procesado: true },
  { id: 2, numero: 2, nombre: '2do Grado', nivel: 'escuela', total_estudiantes: 0, procesado: true },
  { id: 1, numero: 1, nombre: '1er Grado', nivel: 'escuela', total_estudiantes: 0, procesado: true },
]

const MOCK_ESTUDIANTES_POR_GRADO = {
  11: [
    { id: 101, cedula_estudiantil: 'V-31200111', primer_nombre: 'Carlos', primer_apellido: 'Mendoza', seccion_actual: 'A' },
    { id: 102, cedula_estudiantil: 'V-31200222', primer_nombre: 'Valeria', primer_apellido: 'Rojas', seccion_actual: 'A' },
    { id: 103, cedula_estudiantil: 'V-31200333', primer_nombre: 'Luis', primer_apellido: 'Pérez', seccion_actual: 'B' },
    { id: 104, cedula_estudiantil: 'V-31200444', primer_nombre: 'Sofía', primer_apellido: 'Gómez', seccion_actual: 'B' },
  ],
  10: [
    { id: 201, cedula_estudiantil: 'V-32100111', primer_nombre: 'Andrés', primer_apellido: 'Silva', seccion_actual: 'A' },
    { id: 202, cedula_estudiantil: 'V-32100222', primer_nombre: 'Camila', primer_apellido: 'Torres', seccion_actual: 'A' },
    { id: 203, cedula_estudiantil: 'V-32100333', primer_nombre: 'Diego', primer_apellido: 'Navarro', seccion_actual: 'B' },
  ],
  6: [
    { id: 301, cedula_estudiantil: 'V-34500111', primer_nombre: 'Mateo', primer_apellido: 'Castillo', seccion_actual: 'A' },
    { id: 302, cedula_estudiantil: 'V-34500222', primer_nombre: 'Lucía', primer_apellido: 'Ramírez', seccion_actual: 'A' },
    { id: 303, cedula_estudiantil: 'V-34500333', primer_nombre: 'Sebastián', primer_apellido: 'Ortiz', seccion_actual: 'B' },
  ],
}

export async function obtenerEstadoCascada(periodoOrigen, periodoDestino) {
  if (USAR_MOCK) {
    return structuredClone(MOCK_GRADOS)
  }
  const { data } = await api.get('/gestion/promocion/estado-cascada', {
    params: { periodo_origen: periodoOrigen, periodo_destino: periodoDestino },
  })
  return data
}

export async function obtenerEstudiantesGrado(numeroGrado, periodoOrigen) {
  if (USAR_MOCK) {
    return structuredClone(MOCK_ESTUDIANTES_POR_GRADO[numeroGrado] || [])
  }
  const { data } = await api.get(`/gestion/promocion/grado/${numeroGrado}`, {
    params: { periodo_origen: periodoOrigen },
  })
  return data
}

export async function procesarPasoDeAnio(payload) {
  if (USAR_MOCK) {
    return { ok: true, procesados: payload.decisiones.length }
  }
  const { data } = await api.post('/gestion/promocion/procesar-grado', payload)
  return data
}

export async function guardarReasignacionSecciones(payload) {
  if (USAR_MOCK) {
    return { ok: true }
  }
  const { data } = await api.patch('/gestion/promocion/reasignar-secciones', payload)
  return data
}
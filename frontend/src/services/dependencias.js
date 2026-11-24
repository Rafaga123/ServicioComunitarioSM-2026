// Comprobaciones previas antes de dar de baja una sección.
//
// El backend ya valida dependencias al hacer DELETE, pero hacerlo antes desde
// el frontend evita bajas parciales: la baja es lógica (soft delete) y no hay
// endpoint para restaurar una sección. Endpoints existentes:
//   GET /estudiantes/?id_seccion=&size=1
//   GET /horarios/registros/?id_seccion=&size=1
import { apiFetch } from './api'

const totalDe = (respuesta) => respuesta?.total ?? 0

/** Devuelve cuántos estudiantes y horarios activos tiene una sección. */
export async function dependenciasDeSeccion(id) {
  const [estudiantes, horarios] = await Promise.all([
    apiFetch('/estudiantes/', { params: { id_seccion: id, size: 1 } }),
    apiFetch('/horarios/registros/', { params: { id_seccion: id, size: 1 } }),
  ])

  return {
    estudiantes: totalDe(estudiantes),
    horarios: totalDe(horarios),
  }
}

/** Solo devuelve las secciones que tienen algo que impida darlas de baja. */
export async function seccionesConDependencias(secciones) {
  const bloqueadas = []
  for (const seccion of secciones ?? []) {
    const dependencias = await dependenciasDeSeccion(seccion.id)
    if (dependencias.estudiantes || dependencias.horarios) {
      bloqueadas.push({ seccion, ...dependencias })
    }
  }
  return bloqueadas
}

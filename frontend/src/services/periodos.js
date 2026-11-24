// Servicio del período lectivo activo.
//
//   GET /gestion/periodos        -> PeticionPeriodoLectivo[]  (solo ADMIN)
//   GET /gestion/periodos/activo -> PeticionPeriodoLectivo | null (solo ADMIN)
//
// Los formularios necesitan el año activo para crear la sección de un
// estudiante cuando todavía no existe (grado + letra + período). La vista de
// secciones permite elegir entre todos los períodos.
import { apiFetch } from './api'

const aPeriodo = (periodo) => ({
  id: periodo.id ?? null,
  anio: periodo.anio,
  activo: Boolean(periodo.activo),
  cerrado: Boolean(periodo.cerrado),
})

/** Todos los períodos lectivos, ordenados por año (los devuelve el backend). */
export async function listarPeriodos() {
  const periodos = await apiFetch('/gestion/periodos')
  return (periodos ?? []).map(aPeriodo)
}

export async function obtenerPeriodoActivo() {
  const periodo = await apiFetch('/gestion/periodos/activo')
  return periodo ? aPeriodo(periodo) : null
}

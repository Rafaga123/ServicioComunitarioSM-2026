// Servicio del resumen de gestión académica.
//
//   GET /gestion/resumen?nivel=  -> PeticionResumenGestion
//
// Devuelve de una sola vez la cantidad de registros activos por módulo. El
// administrador puede pedir LICEO, ESCUELA o ningún nivel (ambos); los
// operadores quedan restringidos a su nivel por el backend.
import { apiFetch } from './api'

const aEntero = (valor) => (typeof valor === 'number' ? valor : Number(valor) || 0)

/** Conteos globales de la vista de gestión académica. */
export async function obtenerResumenGestion({ nivel } = {}) {
  const data = await apiFetch('/gestion/resumen', {
    params: { nivel: nivel || undefined },
  })

  return {
    nivel: data?.nivel ?? null,
    representantes: aEntero(data?.representantes),
    estudiantes: aEntero(data?.estudiantes),
    secciones: aEntero(data?.secciones),
    docentes: aEntero(data?.docentes),
    asignaturas: aEntero(data?.asignaturas),
    horarios: aEntero(data?.horarios),
    pases: aEntero(data?.pases),
    reportes: aEntero(data?.reportes),
  }
}

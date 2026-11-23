// Estado y paginación de un listado que vive en el backend.
//
// Docentes y representantes comparten el mismo contrato:
//   GET /recurso/?offset=0&size=10 -> { items, total, offset, size }
// El backend no admite búsqueda por texto, así que para filtrar se trae la
// lista completa una sola vez y el filtrado se hace en el cliente.
import { reactive } from 'vue'

/**
 * @param {object} opciones
 * @param {(args: object) => Promise<object>} opciones.listar Lista paginada.
 * @param {(args: object) => Promise<object>} opciones.listarTodos Lista completa.
 * @param {(items: Array) => void} opciones.asignar Guarda los items en la vista.
 * @param {() => string} [opciones.getNivel] Nivel educativo de la consulta.
 * @param {number} [opciones.porDefecto] Registros por página iniciales.
 */
export function useRecursoPaginado({
  listar,
  listarTodos,
  asignar,
  getNivel = () => '',
  porDefecto = 10,
}) {
  const estado = reactive({
    page: 1,
    size: porDefecto,
    total: 0,
    loading: false,
    error: '',
    cargado: false,
    todos: [], // caché completa para la búsqueda
    todosListo: false, // ¿ya se cargó la lista completa?
    cargandoTodos: false,
  })

  // Evitan que una respuesta vieja pise a una más reciente.
  let peticion = 0
  let peticionTodos = 0

  const mensaje = (error, defecto) => error?.message || defecto

  async function cargar(paginaSolicitada = estado.page) {
    const solicitud = ++peticion
    estado.loading = true
    estado.error = ''

    try {
      const respuesta = await listar({
        page: paginaSolicitada,
        size: estado.size,
        nivel: getNivel() || undefined,
      })
      if (solicitud !== peticion) return

      const ultimaPagina = Math.max(1, Math.ceil(respuesta.total / estado.size))

      // Si la página pedida quedó vacía (por ejemplo al borrar el último
      // registro), retrocedemos a la última página válida.
      if (respuesta.total > 0 && paginaSolicitada > ultimaPagina) {
        estado.page = ultimaPagina
        await cargar(ultimaPagina)
        return
      }

      asignar(respuesta.items)
      estado.total = respuesta.total
      estado.page = Math.min(Math.max(1, paginaSolicitada), ultimaPagina)
      estado.cargado = true
    } catch (error) {
      if (solicitud !== peticion) return
      estado.error = mensaje(error, 'No se pudieron cargar los datos.')
    } finally {
      if (solicitud === peticion) estado.loading = false
    }
  }

  async function cargarTodos() {
    const solicitud = ++peticionTodos
    estado.cargandoTodos = true
    estado.todosListo = false
    estado.error = ''

    try {
      const { items } = await listarTodos({ nivel: getNivel() || undefined })
      if (solicitud !== peticionTodos) return
      estado.todos = items
      estado.todosListo = true
    } catch (error) {
      if (solicitud !== peticionTodos) return
      estado.todos = []
      estado.error = mensaje(
        error,
        'No se pudo cargar la lista completa para filtrar.',
      )
    } finally {
      if (solicitud === peticionTodos) estado.cargandoTodos = false
    }
  }

  // Tras crear/editar/eliminar: refresca la página del servidor y, si hay una
  // búsqueda activa, también la caché completa para que el filtro siga al día.
  async function refrescar({ conTodos = false } = {}) {
    estado.todos = []
    estado.todosListo = false
    await cargar(estado.page)
    if (conTodos) await cargarTodos()
  }

  // Vuelve al estado inicial (por ejemplo al cambiar el filtro de nivel).
  function reiniciar() {
    estado.page = 1
    estado.total = 0
    estado.error = ''
    estado.cargado = false
    estado.todos = []
    estado.todosListo = false
    asignar([])
  }

  return { estado, cargar, cargarTodos, refrescar, reiniciar }
}

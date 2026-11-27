<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted } from 'vue'
import {
  listarDocentes,
  listarTodosDocentes,
  crearDocente,
  actualizarDocente,
  eliminarDocente,
} from '../services/docentes'
import {
  listarRepresentantes,
  listarTodosRepresentantes,
  crearRepresentante,
  actualizarRepresentante,
  eliminarRepresentante,
} from '../services/representantes'
import {
  listarEstudiantes,
  listarTodosEstudiantes,
  crearEstudiante,
  actualizarEstudiante,
  eliminarEstudiante,
} from '../services/estudiantes'
import { listarTodosGrados } from '../services/grados'
import {
  listarAsignaturas,
  listarTodasAsignaturas,
  crearAsignatura,
  actualizarAsignatura,
  eliminarAsignatura,
  vincularDocente,
  desvincularDocente,
} from '../services/asignaturas'
import {
  listarSecciones,
  listarTodasSecciones,
  actualizarSeccion,
  LETRAS_POR_FORMATO,
  formatoSecciones,
  crearFormatoSecciones,
  eliminarFormatoSecciones,
} from '../services/secciones'
import { listarPeriodos, obtenerPeriodoActivo } from '../services/periodos'
import { obtenerResumenGestion } from '../services/gestion'
import {
  listarHorarios,
  listarTodosHorarios,
  crearHorario,
  actualizarHorario,
  eliminarHorario,
  listarBloquesAcademicos,
  listarBloquesHorarios,
  listarHorarioSemana,
} from '../services/horarios'
import { useRecursoPaginado } from '@/composables/useRecursoPaginado'
import SeccionesTabla from '@/components/gestion-academica/SeccionesTabla.vue'
import RepresentantesTabla from '@/components/gestion-academica/RepresentantesTabla.vue'
import EstudiantesTabla from '@/components/gestion-academica/EstudiantesTabla.vue'
import AsignaturasTabla from '@/components/gestion-academica/AsignaturasTabla.vue'
import DocentesTabla from '@/components/gestion-academica/DocentesTabla.vue'
import HorarioGrilla from '@/components/gestion-academica/HorarioGrilla.vue'
import {
  exportarListadoGeneral,
  exportarListadoHorarios,
} from '@/services/listados'
import {
  dias,
  norm,
  nomPersona,
  nomEst,
  nomDocente,
  diaNombre,
} from '@/components/gestion-academica/helpers'
import {
  esAdministrador,
  nivelActual,
  etiquetaNivel,
  puedeEditarGestion,
  NIVELES,
} from '@/services/auth'
import {
  card,
  inp,
  lbl,
  btnP,
  btnS,
  tag,
  nada,
  aviso2,
  btnPag,
  sinRes,
} from '@/components/gestion-academica/estilos'

// Uso en el layout:  <GestionAcademicaView tab-inicial="estudiantes" />
// Valores de tab-inicial: secciones | representantes | estudiantes | asignaturas | docentes | horarios
const props = defineProps({
  tabInicial: { type: String, default: 'secciones' },
})

// Secretaría y Coordinador entran en modo consulta: ven los listados, pero no
// pueden crear, editar ni eliminar. Es el mismo criterio que aplica el backend.
const puedeGestionar = puedeEditarGestion
const soloLectura = computed(() => !puedeGestionar.value)

// ───────────── Catálogos ─────────────
// dias, norm, nomPersona, nomEst, nomDocente y diaNombre viven en helpers.js

// Registros por página (el backend acepta size de 1 a 100)
const POR_PAGINA = 10

// El orden respeta la jerarquía de datos: las secciones son la base de
// estudiantes y horarios; el resto se muestra por relevancia.
const tabs = [
  { id: 'secciones', label: 'Secciones', nuevo: 'Nueva sección', singular: 'sección', plural: 'secciones' },
  { id: 'estudiantes', label: 'Estudiantes', nuevo: 'Nuevo estudiante', singular: 'estudiante' },
  { id: 'representantes', label: 'Representantes', nuevo: 'Nuevo representante', singular: 'representante' },
  { id: 'asignaturas', label: 'Asignaturas', nuevo: 'Nueva asignatura', singular: 'asignatura' },
  { id: 'docentes', label: 'Docentes', nuevo: 'Nuevo docente', singular: 'docente' },
  { id: 'horarios', label: 'Horarios', nuevo: 'Nuevo horario', singular: 'horario' },
]
// Asignaturas y horarios son datos de Liceo. Un operador de Escuela (Secretaría
// o Coordinador) no debe ver esas pestañas; el administrador, sin nivel propio,
// sigue viéndolas todas.
const esOperadorEscuela = computed(
  () => soloLectura.value && nivelActual.value === NIVELES.ESCUELA,
)
const tabsVisibles = computed(() =>
  esOperadorEscuela.value
    ? tabs.filter((t) => t.id !== 'asignaturas' && t.id !== 'horarios')
    : tabs,
)
// Navegación con flechas/Home/End entre pestañas (patrón ARIA de tablist).
const moverTab = (evento, id) => {
  const teclas = ['ArrowLeft', 'ArrowRight', 'Home', 'End']
  if (!teclas.includes(evento.key)) return
  evento.preventDefault()
  const lista = tabsVisibles.value
  const indice = lista.findIndex((t) => t.id === id)
  if (indice < 0) return
  let destino = indice
  if (evento.key === 'ArrowLeft') destino = (indice - 1 + lista.length) % lista.length
  else if (evento.key === 'ArrowRight') destino = (indice + 1) % lista.length
  else if (evento.key === 'Home') destino = 0
  else if (evento.key === 'End') destino = lista.length - 1
  const nuevo = lista[destino]?.id
  if (!nuevo) return
  tab.value = nuevo
  nextTick(() => document.getElementById(`tab-${nuevo}`)?.focus())
}
const placeholders = {
  secciones: 'Buscar por grado, letra, nivel o docente titular',
  representantes: 'Buscar por nombre o apellido',
  estudiantes: 'Buscar por nombre, apellido o cédula',
  asignaturas: 'Buscar por nombre de la asignatura',
  docentes: 'Buscar por nombre o cédula',
  horarios: 'Buscar por sección, día, bloque o asignatura',
}
const vacios = {
  secciones: { titulo: 'Aún no hay secciones registradas', texto: 'Crea las secciones por grado/año y letra para poder registrar estudiantes y armar los horarios.', boton: 'Registrar sección' },
  representantes: { titulo: 'Aún no hay representantes registrados', texto: 'Registra a los representantes para poder vincularlos con sus estudiantes.', boton: 'Registrar representante' },
  estudiantes: { titulo: 'Aún no hay estudiantes registrados', texto: 'Cuando registres estudiantes aparecerán aquí con su grado, sección y representantes.', boton: 'Registrar estudiante' },
  asignaturas: { titulo: 'Aún no hay asignaturas registradas', texto: 'Crea las asignaturas para poder asignarlas a docentes y armar los horarios.', boton: 'Registrar asignatura' },
  docentes: { titulo: 'Aún no hay docentes registrados', texto: 'Registra a los docentes con su cédula para poder asignarles asignaturas y horarios.', boton: 'Registrar docente' },
  horarios: { titulo: 'Aún no hay horarios registrados', texto: 'Necesitas secciones de Liceo, asignaturas y bloques académicos para armar el horario por bloques.', boton: 'Registrar horario' },
}
const tab = ref(
  tabsVisibles.value.some((t) => t.id === props.tabInicial) ? props.tabInicial : 'secciones',
)
const tabActual = computed(() => tabsVisibles.value.find((t) => t.id === tab.value))

// ───────────── Datos (vacío: los listados conectados se llenan desde la API) ─────────────
// secciones:      { id, idGrado, letra, periodoLectivo, idDocenteTitular, gradoNombre,
//                   gradoNumero, nivel, docenteTitular }  (API /secciones)
// representantes: { id, primerNombre, segundoNombre, primerApellido, segundoApellido, telefono }  (API /representantes)
// estudiantes:    { id, cedula, primerNombre, ..., fechaNacimiento, nivel, idGrado, gradoNombre,
//                   seccionLetra, periodoLectivo, idRepresentante, representanteNombre }  (API /estudiantes)
// asignaturas:    { id, nombre, idGrado, periodoLectivo, docentes }  (API /asignaturas)
// docentes:       { id, primerNombre, segundoNombre, primerApellido, segundoApellido, cedula, nivel }  (API /docentes)
// horarios:       { id, idSeccion, idBloque, idAsignatura, idDocente, periodoLectivo, diaSemana,
//                    seccion, grado, bloque, horaInicio, horaFin, asignatura, docente }  (API /horarios)
const datos = reactive({ secciones: [], representantes: [], estudiantes: [], asignaturas: [], docentes: [], horarios: [] })

// ───────────── Listados conectados a la API ─────────────
// Docentes, representantes y estudiantes comparten el contrato paginado:
// { items, total, offset, size }. El backend no busca por texto, así que el
// filtrado se resuelve en el cliente sobre la lista completa.

// Nivel educativo de la consulta:
// - El administrador no tiene nivel propio y puede ver ambos; el filtro es suyo.
// - Los operadores quedan atados a su nivel (el backend también lo impone).
const nivelFiltro = ref(esAdministrador.value ? '' : (nivelActual.value ?? ''))
// Período con el que se trabajan Secciones, Asignaturas y Horarios. Se
// inicializa con el activo del backend.
const periodoSeleccionado = ref('')
// Filtros de Estudiantes: año/grado y sección. El backend ya los acepta en
// /estudiantes/ y en el listado de nóminas, así que la tabla y el PDF coinciden.
const filtroAnio = ref('')
const filtroSeccion = ref('')
// Evita recargar dos veces cuando nivel/período reinician los filtros a la vez.
let ajustandoFiltros = false
const reiniciarFiltrosEstudiantes = () => {
  ajustandoFiltros = true
  filtroAnio.value = ''
  filtroSeccion.value = ''
  nextTick(() => { ajustandoFiltros = false })
}
const nivelConsulta = computed(() =>
  esAdministrador.value ? nivelFiltro.value : (nivelActual.value ?? ''),
)
const alcanceNivel = computed(() =>
  nivelConsulta.value ? etiquetaNivel(nivelConsulta.value) : 'todos los niveles',
)

// Texto del estado vacío: cuando el filtro de nivel esconde todo, conviene
// explicar por qué en vez de decir que no hay registros.
const vacioTitulo = computed(() => {
  if (tab.value === 'secciones' && periodoSeleccionado.value) {
    return `No hay secciones en ${alcanceNivel.value} · ${periodoSeleccionado.value}`
  }
  if (tab.value === 'asignaturas' && periodoSeleccionado.value) {
    return `No hay asignaturas en ${alcanceNivel.value} · ${periodoSeleccionado.value}`
  }
  if (!nivelConsulta.value) return vacios[tab.value].titulo
  if (tab.value === 'representantes') return `No hay representantes en ${alcanceNivel.value}`
  if (tab.value === 'estudiantes') return `No hay estudiantes en ${alcanceNivel.value}`
  if (tab.value === 'secciones') return `No hay secciones en ${alcanceNivel.value}`
  return vacios[tab.value].titulo
})
const vacioTexto = computed(() => {
  if (soloLectura.value) {
    return `No hay ${tabActual.value.label.toLowerCase()} disponibles para tu nivel.`
  }
  if (tab.value === 'secciones' && periodoSeleccionado.value) {
    return `Registra una sección para el período ${periodoSeleccionado.value} en ese nivel o cambia los filtros.`
  }
  if (tab.value === 'asignaturas' && periodoSeleccionado.value) {
    return `Las asignaturas solo se registran en grados de Liceo para el período ${periodoSeleccionado.value}. Cambia el filtro de nivel o de período.`
  }
  if (!nivelConsulta.value) return vacios[tab.value].texto
  if (tab.value === 'representantes') {
    return 'Solo aparecen representantes con estudiantes activos en ese nivel.'
  }
  if (tab.value === 'estudiantes') {
    if (filtroAnio.value || filtroSeccion.value) {
      return 'No hay estudiantes para el año o sección seleccionados. Cambia los filtros.'
    }
    return 'Registra un estudiante en ese nivel o cambia el filtro de nivel.'
  }
  return vacios[tab.value].texto
})

// "sección"/"secciones" según la pestaña, para los textos de totales.
const sustantivo = computed(() => {
  const { singular, plural } = tabActual.value
  return { uno: singular, varios: plural ?? `${singular}s` }
})

const docentes = useRecursoPaginado({
  listar: listarDocentes,
  listarTodos: listarTodosDocentes,
  getNivel: () => nivelConsulta.value,
  asignar: (items) => { datos.docentes = items },
  porDefecto: POR_PAGINA,
})
// Secciones se muestra completa (son pocas) y agrupada por grado/letra, así
// que no usa el selector "Por página". El período se inyecta en ambas consultas.
const secciones = useRecursoPaginado({
  listar: (args) => listarSecciones({
    ...args,
    periodoLectivo: periodoSeleccionado.value || undefined,
  }),
  listarTodos: (args) => listarTodasSecciones({
    ...args,
    periodoLectivo: periodoSeleccionado.value || undefined,
  }),
  getNivel: () => nivelConsulta.value,
  asignar: (items) => { datos.secciones = items },
  porDefecto: 100,
})
const representantes = useRecursoPaginado({
  listar: listarRepresentantes,
  listarTodos: listarTodosRepresentantes,
  getNivel: () => nivelConsulta.value,
  asignar: (items) => { datos.representantes = items },
  porDefecto: POR_PAGINA,
})
const estudiantes = useRecursoPaginado({
  // El composable solo conoce el nivel: aquí se inyectan año, sección y
  // período para que la paginación y la búsqueda usen los mismos filtros.
  listar: (args) => listarEstudiantes({
    ...args,
    idGrado: filtroSeccion.value ? undefined : (filtroAnio.value || undefined),
    idSeccion: filtroSeccion.value || undefined,
    periodoLectivo: periodoSeleccionado.value || undefined,
  }),
  listarTodos: (args) => listarTodosEstudiantes({
    ...args,
    idGrado: filtroSeccion.value ? undefined : (filtroAnio.value || undefined),
    idSeccion: filtroSeccion.value || undefined,
    periodoLectivo: periodoSeleccionado.value || undefined,
  }),
  getNivel: () => nivelConsulta.value,
  asignar: (items) => { datos.estudiantes = items },
  porDefecto: POR_PAGINA,
})
// Las asignaturas pertenecen a un grado y a un año lectivo: se consultan con
// el mismo período elegido en Secciones para no mezclar períodos distintos.
const asignaturas = useRecursoPaginado({
  listar: (args) => listarAsignaturas({
    ...args,
    periodoLectivo: periodoSeleccionado.value || undefined,
  }),
  listarTodos: (args) => listarTodasAsignaturas({
    ...args,
    periodoLectivo: periodoSeleccionado.value || undefined,
  }),
  getNivel: () => nivelConsulta.value,
  asignar: (items) => { datos.asignaturas = items },
  porDefecto: POR_PAGINA,
})
// El listado plano de horarios ya no tiene vista propia: solo se mantiene
// conectado para los totales y los formularios. La grilla se carga aparte.
const horarios = useRecursoPaginado({
  listar: (args) => listarHorarios({
    ...args,
    periodoLectivo: periodoSeleccionado.value || undefined,
  }),
  listarTodos: (args) => listarTodosHorarios({
    ...args,
    periodoLectivo: periodoSeleccionado.value || undefined,
  }),
  getNivel: () => nivelConsulta.value,
  asignar: (items) => { datos.horarios = items },
  porDefecto: POR_PAGINA,
})

const docentesApi = docentes.estado
const seccionesApi = secciones.estado
const representantesApi = representantes.estado
const estudiantesApi = estudiantes.estado
const asignaturasApi = asignaturas.estado
const horariosApi = horarios.estado
const cargarDocentes = docentes.cargar
const cargarTodosDocentes = docentes.cargarTodos
const cargarSecciones = secciones.cargar
const cargarTodosSecciones = secciones.cargarTodos
const cargarRepresentantes = representantes.cargar
const cargarTodosRepresentantes = representantes.cargarTodos
const cargarEstudiantes = estudiantes.cargar
const cargarTodosEstudiantes = estudiantes.cargarTodos
const cargarAsignaturas = asignaturas.cargar
const cargarTodosAsignaturas = asignaturas.cargarTodos
const cargarHorarios = horarios.cargar
const cargarTodosHorariosApi = horarios.cargarTodos

// Conteos globales para las insignias de las pestañas. Se piden una sola vez
// al /gestion/resumen en vez de esperar a que se visite cada listado. El
// resumen se pide para el período seleccionado (no solo para el activo), para
// que las insignias coincidan con las tablas.
const resumen = reactive({ datos: null, liceo: null, cargando: false, error: '' })
let resumenSolicitud = 0
const cargarResumen = async () => {
  const solicitud = ++resumenSolicitud
  resumen.cargando = true
  resumen.error = ''
  const nivel = nivelConsulta.value || undefined
  const periodoLectivo = periodoSeleccionado.value || undefined
  try {
    // Horarios es siempre de Liceo: con el filtro en Escuela hace falta un
    // segundo conteo para que su insignia no muestre 0 mientras la grilla
    // sigue mostrando secciones de Liceo.
    const [datos, liceo] = await Promise.all([
      obtenerResumenGestion({ nivel, periodoLectivo }),
      esAdministrador.value && nivel === NIVELES.ESCUELA
        ? obtenerResumenGestion({ nivel: NIVELES.LICEO, periodoLectivo })
        : Promise.resolve(null),
    ])
    if (solicitud === resumenSolicitud) {
      resumen.datos = datos
      resumen.liceo = liceo
    }
  } catch (error) {
    if (solicitud !== resumenSolicitud) return
    resumen.datos = null
    resumen.liceo = null
    resumen.error = error?.message || 'No se pudo cargar el resumen de gestión.'
  } finally {
    if (solicitud === resumenSolicitud) resumen.cargando = false
  }
}
watch(nivelConsulta, () => {
  resumen.datos = null
  resumen.liceo = null
  cargarResumen()
})
// Los totales de los listados cambian al crear o eliminar registros: eso también
// debe reflejarse en las insignias de las demás pestañas.
watch(
  () => [
    seccionesApi.total,
    docentesApi.total,
    representantesApi.total,
    estudiantesApi.total,
    asignaturasApi.total,
    horariosApi.total,
  ],
  () => { cargarResumen() },
)

// Cambiar el período recarga la matriz de secciones, las asignaturas, los
// horarios y los catálogos de ese año. Estudiantes filtra por período; en
// Representantes se recalculan los estudiantes a cargo (el backend de ese
// listado aún no filtra por año).
watch(periodoSeleccionado, () => {
  // Las opciones de año/sección dependen del período; una selección anterior
  // podría ya no existir en el año elegido.
  reiniciarFiltrosEstudiantes()
  // Las insignias cuentan por período: se recalculan con el año elegido.
  cargarResumen()
  // El catálogo del formulario de horarios también es de un año concreto.
  invalidarCatalogoHorarios()
  // Grados, secciones y períodos del formulario (y la matriz de Secciones)
  // son del período elegido.
  if (catalogos.periodoCargado !== periodoSeleccionado.value) cargarCatalogos()
  if (tab.value === 'estudiantes' && estudiantesApi.cargado) {
    recargarEstudiantesPorFiltro()
  }
  if (tab.value === 'representantes') {
    cargarEstudiantesReps()
  }
  // La carga inicial ya se hace en onMounted; solo reaccionamos a cambios
  // posteriores del selector de período. Si hay búsqueda activa se recarga la
  // caché completa para que el filtro siga funcionando.
  if (tab.value === 'secciones' && seccionesApi.cargado) {
    pagina.secciones = 1
    secciones.reiniciar()
    recargarTab()
  }
  if (tab.value === 'asignaturas' && asignaturasApi.cargado) {
    pagina.asignaturas = 1
    asignaturas.reiniciar()
    recargarTab()
  }
  if (tab.value === 'horarios' && horariosApi.cargado) {
    pagina.horarios = 1
    horarios.reiniciar()
    recargarTab()
  }
})

// ───────────── Catálogos del formulario de estudiantes ─────────────
// grados y secciones se piden para el nivel de la consulta; el período activo
// define el año escolar con el que se crea una sección si todavía no existe.
const catalogos = reactive({
  grados: [],
  secciones: [],
  periodos: [],
  periodoActivo: null,
  // Año con el que se cargaron grados/secciones; evita recargar dos veces al
  // inicializar el período activo.
  periodoCargado: '',
  cargando: false,
  error: '',
})

const cargarCatalogos = async () => {
  catalogos.cargando = true
  catalogos.error = ''
  const periodoPedido = periodoSeleccionado.value || undefined
  try {
    const nivel = nivelConsulta.value || undefined
    // /gestion/periodos es solo ADMIN. En modo consulta se usa el período
    // activo, disponible para cualquier usuario autenticado.
    const [grados, secciones, periodos, periodo] = await Promise.all([
      listarTodosGrados({ nivel }),
      listarTodasSecciones({ nivel, periodoLectivo: periodoPedido }),
      puedeGestionar.value ? listarPeriodos() : Promise.resolve(null),
      obtenerPeriodoActivo(),
    ])
    catalogos.grados = grados.items
    catalogos.secciones = secciones.items
    catalogos.periodos = puedeGestionar.value
      ? periodos
      : periodo
        ? [periodo]
        : []
    catalogos.periodoActivo = periodo
    if (periodo && !periodoSeleccionado.value) periodoSeleccionado.value = periodo.anio
    // El backend usa el período activo si no se envía uno: al fijarlo arriba,
    // las secciones cargadas ya corresponden a ese año.
    catalogos.periodoCargado = periodoSeleccionado.value
  } catch (error) {
    catalogos.error = error?.message || 'No se pudieron cargar los grados, las secciones o los períodos.'
  } finally {
    catalogos.cargando = false
  }
}

// Opciones de los filtros de Estudiantes. Se derivan del catálogo ya cargado
// para no hacer peticiones extra y para que año y sección sean coherentes con
// el nivel y el período activos.
const seccionesDelPeriodo = computed(() => {
  const anio = Number(periodoSeleccionado.value)
  return catalogos.secciones.filter(
    (s) => !anio || Number(s.periodoLectivo) === anio,
  )
})
const gradosFiltro = computed(() => {
  const ids = new Set(seccionesDelPeriodo.value.map((s) => Number(s.idGrado)))
  return catalogos.grados.filter((g) => {
    const nivelOk = !nivelConsulta.value || g.nivel === nivelConsulta.value
    return nivelOk && ids.has(Number(g.id))
  })
})
const seccionesFiltro = computed(() => {
  const anio = Number(filtroAnio.value)
  return seccionesDelPeriodo.value.filter((s) => {
    const nivelOk = !nivelConsulta.value || s.nivel === nivelConsulta.value
    return nivelOk && (!anio || Number(s.idGrado) === anio)
  })
})
const resumenFiltrosEstudiantes = computed(() => {
  if (tab.value !== 'estudiantes') return alcanceNivel.value
  const partes = []
  const seccion = filtroSeccion.value
    ? seccionesFiltro.value.find((s) => s.id === Number(filtroSeccion.value))
    : null
  const grado = filtroAnio.value
    ? gradosFiltro.value.find((g) => g.id === Number(filtroAnio.value))
    : null
  // Con el filtro de nivel en «Todos», el año o la sección ya determinan el
  // nivel. Se muestra ese alcance para que coincida con lo que se exporta.
  const nivelInferido = seccion?.nivel || grado?.nivel || ''
  const alcance = nivelConsulta.value || !nivelInferido
    ? alcanceNivel.value
    : etiquetaNivel(nivelInferido)
  if (seccion) {
    // La etiqueta de la sección ya incluye el año/grado: no repetirlo.
    partes.push(etiquetaSeccionGrilla(seccion))
  } else if (grado) {
    partes.push(grado.nombre)
  }
  return partes.length ? `${alcance} · ${partes.join(' · ')}` : alcance
})

// El selector del formulario de estudiantes necesita TODOS los representantes,
// sin el filtro de nivel de la pestaña: un representante es global y puede no
// tener estudiantes en el nivel consultado. Se cachea aparte de la lista que
// usa la búsqueda de la pestaña Representantes.
const repsFormulario = reactive({ items: [], listo: false, cargando: false, error: '' })
const cargarRepsFormulario = async () => {
  if (repsFormulario.cargando) return
  repsFormulario.cargando = true
  repsFormulario.error = ''
  try {
    const { items } = await listarTodosRepresentantes()
    repsFormulario.items = items
    repsFormulario.listo = true
  } catch (error) {
    repsFormulario.error = error?.message || 'No se pudieron cargar los representantes.'
  } finally {
    repsFormulario.cargando = false
  }
}
const invalidarRepsFormulario = () => {
  repsFormulario.items = []
  repsFormulario.listo = false
}

// La pestaña Representantes necesita TODOS los estudiantes del nivel para
// mostrar «Estudiantes a cargo»; la tabla paginada solo trae una página. El
// listado de representantes no filtra por período (el backend aún no lo
// admite), así que los estudiantes tampoco se acotan por período aquí.
const estudiantesReps = reactive({ items: [], cargando: false, error: '' })
let solicitudEstudiantesReps = 0
const cargarEstudiantesReps = async () => {
  const solicitud = ++solicitudEstudiantesReps
  estudiantesReps.cargando = true
  estudiantesReps.error = ''
  try {
    const { items } = await listarTodosEstudiantes({
      nivel: nivelConsulta.value || undefined,
    })
    if (solicitud !== solicitudEstudiantesReps) return
    estudiantesReps.items = items
  } catch (error) {
    if (solicitud !== solicitudEstudiantesReps) return
    estudiantesReps.items = []
    estudiantesReps.error =
      error?.message || 'No se pudieron cargar los estudiantes de los representantes.'
  } finally {
    if (solicitud === solicitudEstudiantesReps) estudiantesReps.cargando = false
  }
}

// Titulares posibles para secciones de Escuela. Se cargan aparte porque el
// docente titular es opcional y no debe bloquear el formulario si no hay
// docentes registrados todavía.
const titulares = reactive({ items: [], listo: false, cargando: false, error: '' })
const cargarTitulares = async () => {
  if (titulares.cargando) return
  titulares.cargando = true
  titulares.error = ''
  try {
    const { items } = await listarTodosDocentes({ nivel: 'ESCUELA' })
    titulares.items = items
    titulares.listo = true
  } catch (error) {
    titulares.error = error?.message || 'No se pudieron cargar los docentes de Escuela.'
  } finally {
    titulares.cargando = false
  }
}
const invalidarTitulares = () => {
  titulares.items = []
  titulares.listo = false
}

// Catálogo del panel de asignaturas: docentes y grados de Liceo. Se pide aparte
// porque el filtro de nivel de la pestaña puede estar en Escuela y aun así hay
// que poder registrar asignaturas.
const catalogoAsignaturas = reactive({
  docentes: [],
  grados: [],
  listo: false,
  cargando: false,
  error: '',
})
const cargarCatalogoAsignaturas = async () => {
  if (catalogoAsignaturas.cargando) return
  catalogoAsignaturas.cargando = true
  catalogoAsignaturas.error = ''
  try {
    const [docentes, grados] = await Promise.all([
      listarTodosDocentes({ nivel: 'LICEO' }),
      listarTodosGrados({ nivel: 'LICEO' }),
    ])
    catalogoAsignaturas.docentes = docentes.items
    catalogoAsignaturas.grados = grados.items
    catalogoAsignaturas.listo = true
  } catch (error) {
    catalogoAsignaturas.error = error?.message || 'No se pudo cargar el catálogo de Liceo.'
  } finally {
    catalogoAsignaturas.cargando = false
  }
}
const invalidarCatalogoAsignaturas = () => {
  catalogoAsignaturas.docentes = []
  catalogoAsignaturas.grados = []
  catalogoAsignaturas.listo = false
}

// ───────────── Vista de Horarios: grilla semanal ─────────────
// Es la única vista de la pestaña: una sección por vez, filas = bloques de la
// jornada (con los recreos) y columnas = lunes a viernes. No hay filtro de
// nivel aquí: los horarios son siempre de Liceo.
const seccionGrilla = ref(null)
const bloquesGrilla = reactive({ items: [], listo: false, cargando: false, error: '' })
const semanaGrilla = reactive({ items: [], seccionId: null, cargando: false, error: '' })
let solicitudSemana = 0

// Las secciones de la grilla se piden aparte del catálogo general: así el
// filtro de nivel usado en otras pestañas no puede ocultar las de Liceo.
const seccionesLiceo = ref([])
const seccionesGrillaCargadas = ref(false)
const seccionesGrillaCargando = ref(false)
const seccionesGrillaError = ref('')
let solicitudSeccionesGrilla = 0
const seccionesGrilla = computed(() =>
  seccionesLiceo.value
    .filter(
      (s) =>
        !periodoSeleccionado.value ||
        Number(s.periodoLectivo) === Number(periodoSeleccionado.value),
    )
    .sort(
      (a, b) =>
        (Number(a.gradoNumero) || 0) - (Number(b.gradoNumero) || 0) ||
        String(a.letra ?? '').localeCompare(String(b.letra ?? '')),
    ),
)

const cargarSeccionesGrilla = async () => {
  const solicitud = ++solicitudSeccionesGrilla
  seccionesGrillaCargando.value = true
  seccionesGrillaError.value = ''
  try {
    const { items } = await listarTodasSecciones({
      nivel: 'LICEO',
      periodoLectivo: periodoSeleccionado.value || undefined,
    })
    if (solicitud !== solicitudSeccionesGrilla) return
    seccionesLiceo.value = items
    seccionesGrillaCargadas.value = true
  } catch (error) {
    if (solicitud !== solicitudSeccionesGrilla) return
    // Sin el catálogo no se puede distinguir «no hay secciones» de «falló la
    // carga»: se guarda el error para ofrecer reintento en la grilla.
    seccionesLiceo.value = []
    seccionesGrillaError.value =
      error?.message || 'No se pudieron cargar las secciones de Liceo.'
  } finally {
    if (solicitud === solicitudSeccionesGrilla) seccionesGrillaCargando.value = false
  }
}

const etiquetaSeccionGrilla = (s) =>
  `${s.gradoNombre || (s.gradoNumero ? `${s.gradoNumero}° Año` : 'Grado')} · Sección ${s.letra}`

const elegirSeccionGrilla = (valor) => {
  seccionGrilla.value =
    seccionesGrilla.value.find((s) => s.id === Number(valor)) ?? null
}

const cargarBloquesGrilla = async () => {
  if (bloquesGrilla.cargando) return
  bloquesGrilla.cargando = true
  bloquesGrilla.error = ''
  try {
    bloquesGrilla.items = await listarBloquesHorarios()
    bloquesGrilla.listo = true
  } catch (error) {
    bloquesGrilla.error = error?.message || 'No se pudieron cargar los bloques horarios.'
  } finally {
    bloquesGrilla.cargando = false
  }
}

const cargarSemanaGrilla = async () => {
  const seccion = seccionGrilla.value
  if (!seccion) {
    solicitudSemana += 1
    semanaGrilla.items = []
    semanaGrilla.seccionId = null
    semanaGrilla.cargando = false
    semanaGrilla.error = ''
    return
  }

  const solicitud = ++solicitudSemana
  semanaGrilla.cargando = true
  semanaGrilla.error = ''
  try {
    const { items } = await listarHorarioSemana({
      idSeccion: seccion.id,
      periodoLectivo: seccion.periodoLectivo || periodoSeleccionado.value || undefined,
    })
    if (solicitud !== solicitudSemana) return
    semanaGrilla.items = items
    semanaGrilla.seccionId = seccion.id
  } catch (error) {
    if (solicitud !== solicitudSemana) return
    semanaGrilla.items = []
    semanaGrilla.error = error?.message || 'No se pudo cargar el horario de la sección.'
  } finally {
    if (solicitud === solicitudSemana) semanaGrilla.cargando = false
  }
}

const recargarGrilla = () => {
  cargarSeccionesGrilla()
  cargarBloquesGrilla()
  if (seccionGrilla.value) cargarSemanaGrilla()
}

// Al cargar el catálogo de Liceo (o cambiar de período) la sección elegida
// puede dejar de existir; en ese caso la grilla vuelve a pedir una sección.
watch(seccionesGrilla, (lista) => {
  if (!seccionesGrillaCargadas.value) return
  if (seccionGrilla.value && !lista.some((s) => s.id === seccionGrilla.value.id)) {
    seccionGrilla.value = null
  }
})

// Cambiar de sección en el selector recarga su semana.
watch(seccionGrilla, () => {
  if (tab.value === 'horarios') cargarSemanaGrilla()
})

watch(periodoSeleccionado, () => {
  if (tab.value !== 'horarios') return
  // La sección elegida pertenece al período anterior: se limpia antes de
  // recargar el catálogo del nuevo año.
  if (
    seccionGrilla.value &&
    Number(seccionGrilla.value.periodoLectivo) !== Number(periodoSeleccionado.value)
  ) {
    seccionGrilla.value = null
  }
  cargarSeccionesGrilla()
  if (seccionGrilla.value) cargarSemanaGrilla()
})

// Catálogo del panel de horarios: secciones de Liceo (para elegir el grado),
// asignaturas con sus docentes vinculados, bloques académicos y un listado
// completo de horarios para detectar choques de sección/docente.
const catalogoHorarios = reactive({
  secciones: [],
  asignaturas: [],
  bloques: [],
  horarios: [],
  listo: false,
  cargando: false,
  error: '',
})
let promesaCatalogoHorarios = null
let versionCatalogoHorarios = 0
const cargarCatalogoHorarios = () => {
  // El catálogo solo se usa en el formulario de alta/edición: en modo consulta
  // el listado se sirve directamente desde el endpoint paginado.
  if (!puedeGestionar.value) return Promise.resolve()
  if (catalogoHorarios.listo) return Promise.resolve()
  if (promesaCatalogoHorarios) return promesaCatalogoHorarios

  const version = versionCatalogoHorarios
  catalogoHorarios.cargando = true
  catalogoHorarios.error = ''
  promesaCatalogoHorarios = (async () => {
    try {
      const [secciones, asignaturas, bloques, todos] = await Promise.all([
        listarTodasSecciones({
          nivel: 'LICEO',
          periodoLectivo: periodoSeleccionado.value || undefined,
        }),
        listarTodasAsignaturas({
          nivel: 'LICEO',
          periodoLectivo: periodoSeleccionado.value || undefined,
        }),
        listarBloquesAcademicos(),
        listarTodosHorarios({
          periodoLectivo: periodoSeleccionado.value || undefined,
        }),
      ])
      // Si algo invalidó el catálogo mientras cargaba, estos datos ya no sirven.
      if (version !== versionCatalogoHorarios) return
      catalogoHorarios.secciones = secciones.items
      catalogoHorarios.asignaturas = asignaturas.items
      catalogoHorarios.bloques = bloques
      catalogoHorarios.horarios = todos.items
      catalogoHorarios.listo = true
    } catch (error) {
      if (version === versionCatalogoHorarios) {
        catalogoHorarios.error = error?.message || 'No se pudo cargar el catálogo de horarios.'
      }
    } finally {
      catalogoHorarios.cargando = false
      promesaCatalogoHorarios = null
    }
  })()
  return promesaCatalogoHorarios
}
const invalidarCatalogoHorarios = () => {
  versionCatalogoHorarios += 1
  catalogoHorarios.secciones = []
  catalogoHorarios.asignaturas = []
  catalogoHorarios.bloques = []
  catalogoHorarios.horarios = []
  catalogoHorarios.listo = false
}

// Pestaña cuyo listado vive en el backend.
const apiTab = computed(() =>
  ({
    secciones: seccionesApi,
    docentes: docentesApi,
    representantes: representantesApi,
    estudiantes: estudiantesApi,
    asignaturas: asignaturasApi,
    horarios: horariosApi,
  }[tab.value] ?? null),
)

const cargarTab = (paginaSolicitada) => {
  if (tab.value === 'secciones') return cargarSecciones(paginaSolicitada)
  if (tab.value === 'docentes') return cargarDocentes(paginaSolicitada)
  if (tab.value === 'representantes') return cargarRepresentantes(paginaSolicitada)
  if (tab.value === 'estudiantes') return cargarEstudiantes(paginaSolicitada)
  if (tab.value === 'asignaturas') return cargarAsignaturas(paginaSolicitada)
  if (tab.value === 'horarios') return cargarHorarios(paginaSolicitada)
}
const cargarTodosTab = () => {
  if (tab.value === 'secciones') return cargarTodosSecciones()
  if (tab.value === 'docentes') return cargarTodosDocentes()
  if (tab.value === 'representantes') return cargarTodosRepresentantes()
  if (tab.value === 'estudiantes') return cargarTodosEstudiantes()
  if (tab.value === 'asignaturas') return cargarTodosAsignaturas()
  if (tab.value === 'horarios') return cargarTodosHorariosApi()
}
const recargarTab = () =>
  filtrando.value ? cargarTodosTab() : cargarTab(apiTab.value?.page ?? 1)

const refrescarAsignaturas = () => {
  invalidarCatalogoHorarios()
  return asignaturas.refrescar({ conTodos: filtrando.value })
}
const refrescarDocentes = () => {
  invalidarTitulares()
  invalidarCatalogoAsignaturas()
  invalidarCatalogoHorarios()
  return docentes.refrescar({ conTodos: filtrando.value })
}
const refrescarSecciones = async () => {
  // El catálogo decide el formato de cada fila, así que hay que esperarlo
  // junto con el listado antes de volver a pintar la matriz.
  invalidarCatalogoHorarios()
  await Promise.all([
    cargarCatalogos(),
    secciones.refrescar({ conTodos: filtrando.value }),
  ])
}
const refrescarRepresentantes = () => {
  invalidarRepsFormulario()
  return representantes.refrescar({ conTodos: filtrando.value })
}
const refrescarEstudiantes = () =>
  estudiantes.refrescar({ conTodos: filtrando.value })
const refrescarHorarios = () => {
  invalidarCatalogoHorarios()
  const tareas = [horarios.refrescar({ conTodos: filtrando.value })]
  if (tab.value === 'horarios' && seccionGrilla.value) {
    tareas.push(cargarSemanaGrilla())
  }
  return Promise.all(tareas)
}

onMounted(async () => {
  // Los conteos no dependen del período ni del catálogo: se piden en cuanto
  // monta la vista para que todas las pestañas tengan su insignia.
  cargarResumen()
  // Primero los catálogos: así el período activo ya está elegido cuando se
  // pide la primera página de secciones.
  await cargarCatalogos()
  const enHorarios = tab.value === 'horarios'
  // Horarios solo usa la grilla: la lista plana no se pide nunca.
  if (apiTab.value && !enHorarios) cargarTab(1)
  if (enHorarios) {
    cargarSeccionesGrilla()
    cargarBloquesGrilla()
    if (seccionGrilla.value) cargarSemanaGrilla()
  }
  if (puedeGestionar.value) {
    if (tab.value === 'estudiantes') cargarRepsFormulario()
    if (tab.value === 'secciones') cargarTitulares()
    if (tab.value === 'asignaturas') cargarCatalogoAsignaturas()
  }
  if (tab.value === 'representantes') cargarEstudiantesReps()
})

// ───────────── Helpers ─────────────
// norm, nomPersona, nomEst, nomDocente y diaNombre vienen de helpers.js
const etiqueta = (t, x) =>
  t === 'secciones'
    ? `${x.gradoNombre || 'Grado'} · Sección ${x.letra || '—'}`
    : t === 'estudiantes'
      ? `${nomEst(x)}${x.cedula ? ` (${x.cedula})` : ''}`
      : t === 'asignaturas'
      ? x.nombre
      : t === 'docentes'
        ? nomDocente(x)
        : t === 'horarios'
          ? `${x.seccion || x.grado || 'Horario'} · ${diaNombre(x.diaSemana)} ${x.bloque || ''}`
          : nomPersona(x)

// ───────────── Búsqueda (un solo campo por pestaña) ─────────────
const busq = reactive({ secciones: '', representantes: '', estudiantes: '', asignaturas: '', docentes: '', horarios: '' })

const listaAsignaturas = computed(() => {
  const q = norm(busq.asignaturas)
  return datos.asignaturas.filter((a) => !q || norm(a.nombre).includes(q))
})

// Texto sobre el que se busca en cada pestaña conectada a la API.
const textoBusqueda = (t, x) => {
  if (t === 'secciones') {
    return `${x.gradoNombre ?? ''} ${x.letra ?? ''} ${x.nivel ?? ''} ${x.periodoLectivo ?? ''} ${x.docenteTitular ?? ''}`
  }
  if (t === 'docentes') return `${nomDocente(x)} ${x.cedula ?? ''}`
  if (t === 'estudiantes') return `${nomEst(x)} ${x.cedula ?? ''}`
  if (t === 'asignaturas') {
    const docentes = (x.docentes ?? []).map(nomDocente).join(' ')
    return `${x.nombre ?? ''} ${x.gradoNombre ?? ''} ${x.periodoLectivo ?? ''} ${docentes}`
  }
  if (t === 'horarios') {
    return `${x.seccion ?? ''} ${x.grado ?? ''} ${x.nivel ?? ''} ${diaNombre(x.diaSemana)} ${x.bloque ?? ''} ${x.asignatura ?? ''} ${x.docente ?? ''} ${x.periodoLectivo ?? ''}`
  }
  return etiqueta(t, x)
}

// Búsqueda de las pestañas conectadas: el backend no filtra, así que se hace
// en el cliente sobre la lista completa (sin mayúsculas ni acentos).
const busqTab = computed(() => norm(busq[tab.value]).trim())
const filtrando = computed(() => Boolean(apiTab.value) && busqTab.value !== '')
const filtrados = computed(() => {
  if (!apiTab.value || !busqTab.value) return []
  return apiTab.value.todos.filter((x) =>
    norm(textoBusqueda(tab.value, x)).includes(busqTab.value),
  )
})
const buscandoTab = computed(() => filtrando.value && !apiTab.value?.todosListo)
const cargandoTab = computed(
  () => Boolean(apiTab.value && (apiTab.value.loading || apiTab.value.cargandoTodos)),
)

// ───────────── Paginación ─────────────
const pagina = reactive({ secciones: 1, representantes: 1, estudiantes: 1, asignaturas: 1, docentes: 1, horarios: 1 })
Object.keys(busq).forEach((k) => watch(() => busq[k], () => { pagina[k] = 1 })) // al buscar, vuelve a la página 1

// Al buscar en una pestaña conectada se necesita la lista completa para
// filtrar en el cliente.
watch(() => [tab.value, busq[tab.value]], () => {
  pagina[tab.value] = 1
  const api = apiTab.value
  if (!api) return
  if (busqTab.value && !api.todosListo && !api.cargandoTodos) cargarTodosTab()
})

const listaTab = computed(() => {
  if (apiTab.value) return filtrando.value ? filtrados.value : datos[tab.value]
  return listaAsignaturas.value
})

// Las pestañas conectadas usan el total y la página del servidor, salvo con
// búsqueda activa: entonces se pagina en cliente sobre la lista filtrada.
const tamanoPagina = computed(() => apiTab.value?.size ?? POR_PAGINA)
const totalFiltrado = computed(() => {
  const api = apiTab.value
  if (!api) return listaTab.value.length
  return filtrando.value ? filtrados.value.length : api.total
})
const totalPaginas = computed(() => Math.max(1, Math.ceil(totalFiltrado.value / tamanoPagina.value)))
const pg = computed(() => {
  const api = apiTab.value
  if (!api) return Math.min(pagina[tab.value], totalPaginas.value)
  return Math.min(
    filtrando.value ? pagina[tab.value] : api.page,
    totalPaginas.value,
  )
})
const filasPagina = computed(() => {
  const api = apiTab.value
  if (!api) {
    return listaTab.value.slice((pg.value - 1) * tamanoPagina.value, pg.value * tamanoPagina.value)
  }
  if (!filtrando.value) return datos[tab.value]
  const inicio = (pg.value - 1) * tamanoPagina.value
  return filtrados.value.slice(inicio, inicio + tamanoPagina.value)
})
const desde = computed(() => (totalFiltrado.value ? (pg.value - 1) * tamanoPagina.value + 1 : 0))
const hasta = computed(() => Math.min(pg.value * tamanoPagina.value, totalFiltrado.value))
const irPagina = (n) => {
  const destino = Math.min(Math.max(1, n), totalPaginas.value)
  const api = apiTab.value

  if (!api || filtrando.value) {
    pagina[tab.value] = destino
    return
  }
  if (destino === api.page) return
  api.page = destino
  cargarTab(destino)
}

// Se observa el tamaño en vez de usar @change en el <select>: así la recarga
// siempre ocurre después de que v-model actualizó el tamaño del recurso.
const vigilarTamano = (nombre, api, recargar) =>
  watch(() => api.size, () => {
    pagina[nombre] = 1
    if (tab.value !== nombre || filtrando.value) return // se repagina en cliente
    api.page = 1
    recargar(1)
  })
vigilarTamano('docentes', docentesApi, cargarDocentes)
vigilarTamano('representantes', representantesApi, cargarRepresentantes)
vigilarTamano('estudiantes', estudiantesApi, cargarEstudiantes)
vigilarTamano('asignaturas', asignaturasApi, cargarAsignaturas)
vigilarTamano('horarios', horariosApi, cargarHorarios)

// Un cambio de año/sección debe descartar la caché: el total y la búsqueda
// cliente vuelven a calcularse sobre el nuevo conjunto de estudiantes.
const recargarEstudiantesPorFiltro = () => {
  pagina.estudiantes = 1
  estudiantes.reiniciar()
  if (tab.value !== 'estudiantes') return
  if (filtrando.value) return cargarTodosEstudiantes()
  return cargarEstudiantes(1)
}
watch(filtroAnio, () => {
  if (ajustandoFiltros) return
  if (
    filtroSeccion.value &&
    !seccionesFiltro.value.some((s) => s.id === Number(filtroSeccion.value))
  ) {
    // El año ya no contiene la sección elegida: el watcher de sección recarga.
    filtroSeccion.value = ''
    return
  }
  recargarEstudiantesPorFiltro()
})
watch(filtroSeccion, () => {
  if (ajustandoFiltros) return
  recargarEstudiantesPorFiltro()
})

// Cambiar el nivel reinicia los listados del servidor y recarga los catálogos
// del formulario (grados y secciones del nivel).
watch(nivelFiltro, () => {
  if (!esAdministrador.value) return
  reiniciarFiltrosEstudiantes()
  pagina.secciones = 1
  pagina.docentes = 1
  pagina.representantes = 1
  pagina.estudiantes = 1
  pagina.asignaturas = 1
  pagina.horarios = 1
  secciones.reiniciar()
  docentes.reiniciar()
  representantes.reiniciar()
  estudiantes.reiniciar()
  asignaturas.reiniciar()
  horarios.reiniciar()
  // Con búsqueda activa hay que recargar la caché completa; sin ella, la
  // primera página del nuevo nivel.
  if (apiTab.value) recargarTab()
  cargarCatalogos()
  if (tab.value === 'representantes') cargarEstudiantesReps()
})

const totalTab = (id) => {
  // El resumen es la fuente de verdad: incluye pestañas que todavía no se
  // visitaron. Mientras carga se conserva el total local del listado activo.
  // Horarios es siempre de Liceo: con el filtro en Escuela se usa el conteo de
  // Liceo para no mostrar 0 mientras la grilla sigue mostrando secciones.
  const conteo = id === 'horarios' && resumen.liceo ? resumen.liceo : resumen.datos
  if (conteo && Object.prototype.hasOwnProperty.call(conteo, id)) return conteo[id]
  if (id === 'secciones') return seccionesApi.total
  if (id === 'docentes') return docentesApi.total
  if (id === 'representantes') return representantesApi.total
  if (id === 'estudiantes') return estudiantesApi.total
  if (id === 'asignaturas') return asignaturasApi.total
  if (id === 'horarios') return horariosApi.total
  return datos[id].length
}
const botonesPagina = computed(() => {
  const total = totalPaginas.value, p = pg.value
  const nums = [...new Set([1, total, p - 1, p, p + 1].filter((n) => n >= 1 && n <= total))].sort((a, b) => a - b)
  const out = []
  nums.forEach((n, i) => { if (i && n - nums[i - 1] > 1) out.push('…'); out.push(n) })
  return out
})

// ───────────── Panel lateral (crear / editar) ─────────────
const panel = reactive({ abierto: false, modo: 'crear' })
const form = ref({})
const errorForm = ref('')
const panelRef = ref(null)
// Devuelve el foco al control que abrió el panel al cerrarlo.
let focoAntesDelPanel = null
watch(
  () => panel.abierto,
  (abierto) => {
    if (abierto) {
      focoAntesDelPanel = document.activeElement
      return
    }
    const anterior = focoAntesDelPanel
    focoAntesDelPanel = null
    if (anterior instanceof HTMLElement && document.contains(anterior)) {
      nextTick(() => anterior.focus())
    }
  },
)
const repBusq = ref('')
// Al abrir el panel con valores precargados (por ejemplo desde una celda de la
// grilla) los watchers de dependencias no deben borrar lo ya elegido.
let prefijandoHorario = false

const formVacio = {
  secciones: () => ({
    idGrado: '',
    formato: '',
    periodoLectivo: periodoSeleccionado.value || '',
    // Un docente distinto por sección: A, B y U pueden tener titulares propios.
    titulares: { U: null, A: null, B: null },
    letra: '',
    idDocenteTitular: null,
  }),
  // El nivel no existe en el modelo del backend para representantes: se pide
  // para saber con qué nivel de estudiante se vinculará y se conserva solo en
  // el formulario (el servicio no lo envía en el payload).
  representantes: () => ({
    primerNombre: '', segundoNombre: '', primerApellido: '', segundoApellido: '', telefono: '',
    nivel: nivelFiltro.value || '',
  }),
  estudiantes: () => ({
    cedula: '',
    primerNombre: '',
    segundoNombre: '',
    primerApellido: '',
    segundoApellido: '',
    fechaNacimiento: '',
    idGrado: '',
    // El estudiante pertenece a una sección ya registrada; nunca se crea una
    // sección automáticamente al guardar.
    idSeccion: null,
    idRepresentante: null,
    representanteNombre: '',
  }),
  asignaturas: () => ({
    nombre: '',
    idGrado: '',
    periodoLectivo: periodoSeleccionado.value || '',
    docenteIds: [],
  }),
  docentes: () => ({ primerNombre: '', segundoNombre: '', primerApellido: '', segundoApellido: '', cedula: '', nivel: nivelFiltro.value || '' }),
  horarios: () => ({
    idSeccion: null,
    idBloque: null,
    idAsignatura: null,
    idDocente: null,
    periodoLectivo: periodoSeleccionado.value || '',
    diaSemana: '',
  }),
}

// Registro rápido de representante dentro del panel de estudiantes. Es un
// formulario independiente: abrirlo no cambia de pestaña ni toca `form`, así
// que los datos ya escritos del estudiante se conservan.
const repInline = reactive({
  abierto: false,
  guardando: false,
  error: '',
  form: formVacio.representantes(),
})
const reiniciarRepInline = () => {
  repInline.abierto = false
  repInline.guardando = false
  repInline.error = ''
  repInline.form = formVacio.representantes()
}
const tituloPanel = computed(() => (panel.modo === 'crear' ? tabActual.value.nuevo : `Editar ${tabActual.value.singular}`))

// El nivel del grado define si se ofrece docente titular (solo Escuela).
const gradoDelFormulario = computed(() =>
  catalogos.grados.find((g) => g.id === Number(form.value.idGrado)),
)
const esSeccionEscuela = computed(() => gradoDelFormulario.value?.nivel === 'ESCUELA')
const formatoDelFormulario = computed(
  () => form.value.formato || (form.value.letra === 'U' ? 'unica' : form.value.letra ? 'dividida' : ''),
)
const letrasDelFormulario = computed(() => LETRAS_POR_FORMATO[formatoDelFormulario.value] ?? [])
const fijarTitular = (letra, valor) => {
  form.value.titulares ??= { U: null, A: null, B: null }
  form.value.titulares[letra] = valor === '' || valor === null ? null : Number(valor)
}
const enfocarPrimerCampo = async () => {
  await nextTick()
  // Al editar una sección casi todos los campos están bloqueados; hay que
  // buscar el primero habilitado o, si no hay ninguno, enfocar el panel.
  const campo = panelRef.value?.querySelector(
    'input:not([disabled]), select:not([disabled]), textarea:not([disabled])',
  )
  ;(campo || panelRef.value)?.focus()
}
const abrirNuevo = () => {
  if (!puedeGestionar.value) return
  form.value = formVacio[tab.value]()
  panel.modo = 'crear'
  errorForm.value = ''
  repBusq.value = ''
  reiniciarRepInline()
  if (tab.value === 'estudiantes') cargarRepsFormulario()
  if (tab.value === 'secciones') cargarTitulares()
  if (tab.value === 'asignaturas') cargarCatalogoAsignaturas()
  if (tab.value === 'horarios') cargarCatalogoHorarios()
  panel.abierto = true
  enfocarPrimerCampo()
}
const abrirEditar = async (item) => {
  if (!puedeGestionar.value) return
  if (tab.value === 'horarios') await cargarCatalogoHorarios()
  const copia = JSON.parse(JSON.stringify(item))
  if (tab.value === 'secciones') {
    // El grado y la letra no se pueden cambiar: el backend solo acepta letra,
    // período y docente titular en el PUT, y A/B deben ir juntas.
    copia.idGrado = item.idGrado ?? ''
    copia.letra = item.letra ?? ''
    copia.formato = item.letra === 'U' ? 'unica' : 'dividida'
    copia.titulares = { ...formVacio.secciones().titulares }
  } else if (tab.value === 'estudiantes') {
    // La API ya devuelve el grado y la sección a la que pertenece.
    copia.idGrado = item.idGrado ?? ''
    copia.idSeccion = item.idSeccion ?? null
    // Se conservan aunque el filtro de nivel oculte alguno de ellos, para que
    // el selector no quede vacío al editar un estudiante existente.
    copia.gradoActual = {
      id: item.idGrado,
      nombre: item.gradoNombre,
      numero: item.gradoNumero,
      nivel: item.nivel,
    }
    copia.seccionActual = {
      id: item.idSeccion,
      idGrado: item.idGrado,
      letra: item.seccionLetra,
      periodoLectivo: item.periodoLectivo,
    }
  } else if (tab.value === 'asignaturas') {
    // El grado y el período son fijos en el PUT (el backend rechaza el año).
    copia.idGrado = item.idGrado ?? ''
    copia.periodoLectivo = item.periodoLectivo ?? ''
    copia.docentesAnteriores = (item.docentes ?? []).map((d) => d.id)
    copia.docenteIds = [...copia.docentesAnteriores]
  } else if (tab.value === 'horarios') {
    // El DTO trae los nombres y los id's; el catálogo aporta id_grado para
    // filtrar las asignaturas. Se conserva lo original por si cambió el filtro.
    const seccionCatalogo = catalogoHorarios.secciones.find(
      (s) => s.id === item.idSeccion,
    )
    const docenteActual = item.docente
      ? { id: item.idDocente, nombre: item.docente }
      : null
    copia.idSeccion = item.idSeccion ?? null
    copia.idBloque = item.idBloque ?? null
    copia.idAsignatura = item.idAsignatura ?? null
    copia.idDocente = item.idDocente ?? null
    copia.periodoLectivo = item.periodoLectivo ?? ''
    copia.diaSemana = item.diaSemana ?? ''
    copia.seccionActual = seccionCatalogo
      ? { ...seccionCatalogo }
      : {
          id: item.idSeccion,
          idGrado: null,
          letra: String(item.seccion ?? '').split(' ').pop() ?? '',
          gradoNombre: item.grado ?? '',
          periodoLectivo: item.periodoLectivo,
          nivel: 'LICEO',
        }
    copia.asignaturaActual = {
      id: item.idAsignatura,
      nombre: item.asignatura ?? '',
      idGrado: seccionCatalogo?.idGrado ?? null,
      periodoLectivo: item.periodoLectivo,
      nivel: 'LICEO',
      docentes: docenteActual ? [docenteActual] : [],
    }
    copia.docenteActual = docenteActual
  }
  form.value = copia
  panel.modo = 'editar'
  errorForm.value = ''
  repBusq.value = ''
  reiniciarRepInline()
  if (tab.value === 'estudiantes') cargarRepsFormulario()
  if (tab.value === 'secciones') cargarTitulares()
  if (tab.value === 'asignaturas') cargarCatalogoAsignaturas()
  if (tab.value === 'horarios') cargarCatalogoHorarios()
  panel.abierto = true
  enfocarPrimerCampo()
}
const cerrarPanel = () => {
  panel.abierto = false
  reiniciarRepInline()
}
const irA = (id) => { cerrarPanel(); tab.value = id }

// "Celda vacía" de la matriz de secciones: abre el panel con grado, formato y
// período ya puestos para no obligar a repetir lo que el usuario eligió.
const crearSeccionEn = ({ idGrado, formato, periodoLectivo }) => {
  if (!puedeGestionar.value) return
  form.value = {
    ...formVacio.secciones(),
    idGrado,
    formato,
    periodoLectivo: periodoLectivo || periodoSeleccionado.value,
  }
  panel.modo = 'crear'
  errorForm.value = ''
  cargarTitulares()
  panel.abierto = true
  enfocarPrimerCampo()
}

// Desde una sección de Liceo se salta a Horarios con la grilla de esa sección.
// Escuela no se enlaza: su horario es corrido, no por bloques.
const verHorario = (seccion) => {
  if (!tabsVisibles.value.some((t) => t.id === 'horarios')) return
  seccionGrilla.value = seccion
  tab.value = 'horarios'
}

// Alta de un horario desde una celda de la grilla: sección, bloque y día ya
// vienen elegidos; el usuario solo completa asignatura y docente.
const crearHorarioEn = async ({ idSeccion, idBloque, diaSemana } = {}) => {
  if (!puedeGestionar.value) return
  const seccion =
    seccionesGrilla.value.find((s) => s.id === Number(idSeccion)) ?? seccionGrilla.value
  prefijandoHorario = true
  form.value = {
    ...formVacio.horarios(),
    idSeccion: idSeccion ?? null,
    idBloque: idBloque ?? null,
    diaSemana: diaSemana ?? '',
    periodoLectivo: seccion?.periodoLectivo || periodoSeleccionado.value || '',
  }
  // La sección ya se conoce aunque el catálogo tarde en cargar: se conserva
  // como "actual" para que el selector la muestre de inmediato.
  if (seccion) form.value.seccionActual = { ...seccion }
  panel.modo = 'crear'
  errorForm.value = ''
  repBusq.value = ''
  reiniciarRepInline()
  cargarCatalogoHorarios()
  panel.abierto = true
  await nextTick()
  prefijandoHorario = false
  enfocarPrimerCampo()
}

// Exportación con el generador de PDF del backend: se crea el documento y se
// descarga el archivo devuelto por /listados.
const guardarArchivoDescargado = ({ blob, nombre }) => {
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre || 'listado.pdf'
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  // Revocar de inmediato puede cancelar la descarga en algunos navegadores.
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}

const exportandoHorario = ref(false)
const exportarHorario = async () => {
  const seccion = seccionGrilla.value
  if (!seccion || exportandoHorario.value) return

  exportandoHorario.value = true
  try {
    guardarArchivoDescargado(
      await exportarListadoHorarios({
        idSeccion: seccion.id,
        periodoLectivo: seccion.periodoLectivo || periodoSeleccionado.value,
      }),
    )
    avisar('El horario se descargó en PDF.')
  } catch (error) {
    avisar(error?.message || 'No se pudo exportar el horario.')
  } finally {
    exportandoHorario.value = false
  }
}

// Las exportaciones de Estudiantes, Representantes y Docentes se generan por
// nivel. El administrador elige el nivel, salvo que el filtro de año/sección ya
// lo determine; el PDF no mezcla Liceo y Escuela.
const EXPORTACIONES_TAB = {
  estudiantes: {
    tipo: 'nominas',
    etiqueta: 'Exportar estudiantes',
    ayuda: 'Nómina del año/sección seleccionados (o del nivel y período elegidos); la búsqueda por texto no se incluye.',
  },
  representantes: {
    tipo: 'representantes',
    etiqueta: 'Exportar representantes',
    ayuda: 'Representantes del nivel del usuario y del período seleccionado.',
  },
  docentes: {
    tipo: 'docentes',
    etiqueta: 'Exportar docentes',
    ayuda: 'Docentes del nivel del usuario y del período seleccionado.',
  },
}
const exportacionTab = computed(() => EXPORTACIONES_TAB[tab.value] ?? null)
const nivelExportacion = computed(() => {
  if (nivelConsulta.value) return nivelConsulta.value
  if (tab.value !== 'estudiantes') return ''
  const seccion = catalogos.secciones.find(
    (s) => s.id === Number(filtroSeccion.value),
  )
  const grado = catalogos.grados.find((g) => g.id === Number(filtroAnio.value))
  return seccion?.nivel || grado?.nivel || ''
})
const exportandoListado = ref(false)
const exportarListadoDeTab = async () => {
  const configuracion = exportacionTab.value
  if (!configuracion || exportandoListado.value) return
  const nivel = configuracion.tipo === 'nominas'
    ? nivelExportacion.value
    : nivelConsulta.value
  if (!nivel) {
    avisar('Elige Liceo o Escuela en el filtro de nivel para exportar.')
    return
  }

  exportandoListado.value = true
  try {
    guardarArchivoDescargado(
      await exportarListadoGeneral(configuracion.tipo, {
        nivel,
        periodoLectivo: periodoSeleccionado.value,
        ...(configuracion.tipo === 'nominas'
          ? {
              idGrado: filtroAnio.value || undefined,
              idSeccion: filtroSeccion.value || undefined,
            }
          : {}),
      }),
    )
    avisar('El listado se descargó en PDF.')
  } catch (error) {
    avisar(error?.message || 'No se pudo exportar el listado.')
  } finally {
    exportandoListado.value = false
  }
}

watch(tab, (valor) => {
  cerrarPanel()
  // La primera vez que se abre una pestaña conectada se pide la página 1.
  // Horarios no tiene lista: solo trabaja con la grilla.
  if (apiTab.value && !apiTab.value.cargado && !apiTab.value.loading && valor !== 'horarios') {
    cargarTab(1)
  }
  if (valor === 'horarios') {
    cargarSeccionesGrilla()
    cargarBloquesGrilla()
    if (seccionGrilla.value) cargarSemanaGrilla()
  }
  if (valor === 'representantes') cargarEstudiantesReps()
  if (!puedeGestionar.value) return
  if (valor === 'estudiantes') cargarRepsFormulario()
  if (valor === 'secciones') cargarTitulares()
  if (valor === 'asignaturas') cargarCatalogoAsignaturas()
})

// Selector de representantes del formulario de estudiantes.
const repOpciones = computed(() =>
  repsFormulario.listo ? repsFormulario.items : datos.representantes,
)
const repPorId = (id) =>
  repsFormulario.items.find((r) => r.id === id) ??
  datos.representantes.find((r) => r.id === id)
const representanteNombre = computed(() => {
  const rep = repPorId(form.value.idRepresentante)
  return rep ? nomPersona(rep) : form.value.representanteNombre || '—'
})
const repCoincidencias = computed(() => {
  const q = norm(repBusq.value.trim())
  if (!q) return []
  return repOpciones.value
    .filter((r) => r.id !== form.value.idRepresentante && norm(nomPersona(r)).includes(q))
    .slice(0, 6)
})
const agregarRep = (rep) => {
  form.value.idRepresentante = rep.id
  form.value.representanteNombre = nomPersona(rep)
  repBusq.value = ''
}
const quitarRep = () => {
  form.value.idRepresentante = null
  form.value.representanteNombre = ''
}

// Alta de representante sin abandonar el formulario del estudiante.
const abrirRepInline = () => {
  if (!puedeGestionar.value) return
  // Aquí el nivel se infiere del grado del estudiante que se está registrando,
  // igual que en la pestaña Estudiantes.
  repInline.form.nivel =
    catalogos.grados.find((g) => g.id === Number(form.value.idGrado))?.nivel ||
    nivelFiltro.value ||
    ''
  repInline.form.inline = true
  repInline.error = ''
  repInline.abierto = true
}
const cerrarRepInline = () => {
  repInline.abierto = false
  repInline.error = ''
  repInline.form = formVacio.representantes()
}
const guardarRepInline = async () => {
  if (!puedeGestionar.value) return
  for (const k in repInline.form) {
    if (typeof repInline.form[k] === 'string') repInline.form[k] = repInline.form[k].trim()
  }
  const err = validar('representantes', repInline.form)
  if (err) { repInline.error = err; return }

  repInline.guardando = true
  repInline.error = ''
  try {
    const creado = await crearRepresentante(repInline.form)
    if (!repsFormulario.listo) {
      repsFormulario.items = [creado]
      repsFormulario.listo = true
    } else if (!repsFormulario.items.some((r) => r.id === creado.id)) {
      repsFormulario.items.push(creado)
    }
    // Se selecciona automáticamente y se cierra solo el subformulario: el
    // estudiante sigue abierto con todos sus datos intactos.
    agregarRep(creado)
    cerrarRepInline()
    // La pestaña Representantes se actualiza sin invalidar la caché que usa
    // este formulario (refrescarRepresentantes sí la invalidaría).
    await representantes.refrescar()
    avisar('Representante registrado y vinculado al estudiante.')
  } catch (error) {
    repInline.error = error?.message || 'No se pudo registrar el representante.'
  } finally {
    repInline.guardando = false
  }
}

// Catálogos del formulario de estudiantes. Se toman del catálogo general (que
// ya está acotado al período elegido) y se añade lo que ya tenía el estudiante
// al editar para que el filtro de nivel nunca deje un selector vacío.
const gradosDelFormulario = computed(() => {
  // Solo se ofrecen grados que tengan al menos una sección en el período.
  const idsConSeccion = new Set(catalogos.secciones.map((s) => Number(s.idGrado)))
  const grados = catalogos.grados.filter((g) => idsConSeccion.has(Number(g.id)))
  const actual = form.value?.gradoActual
  if (actual && !grados.some((g) => g.id === actual.id)) grados.push(actual)
  return grados
})
const seccionesDelFormulario = computed(() => {
  const idGrado = Number(form.value?.idGrado)
  if (!idGrado) return []
  const periodo = Number(periodoSeleccionado.value) || null
  const seleccionada = Number(form.value?.idSeccion)
  const secciones = [...catalogos.secciones]
  const actual = form.value?.seccionActual
  if (actual && !secciones.some((s) => s.id === actual.id)) secciones.push(actual)
  return secciones.filter(
    (s) =>
      (Number(s.idGrado) === idGrado &&
        (!periodo || Number(s.periodoLectivo) === periodo)) ||
      s.id === seleccionada,
  )
})
// Si cambia el grado, la sección elegida deja de ser válida.
watch(() => form.value?.idGrado, (id, anterior) => {
  if (!panel.abierto || tab.value !== 'estudiantes' || anterior === id) return
  const seccion = seccionesDelFormulario.value.find(
    (s) => s.id === Number(form.value.idSeccion),
  )
  if (form.value.idSeccion && Number(seccion?.idGrado) !== Number(id)) {
    form.value.idSeccion = null
  }
})
// Al corregir la sección que faltaba, se retira el aviso anterior.
watch(() => form.value?.idSeccion, (valor, anterior) => {
  if (
    panel.abierto &&
    tab.value === 'estudiantes' &&
    valor &&
    valor !== anterior &&
    errorForm.value.includes('sección')
  ) {
    errorForm.value = ''
  }
})

// ───────────── Catálogos dependientes del formulario de horarios ─────────────
// Secciones de Liceo del período elegido. Al editar se conserva la original
// aunque ya no esté en el catálogo (por ejemplo, si cambió el filtro de nivel).
const seccionesDelHorario = computed(() => {
  const periodo = Number(form.value?.periodoLectivo)
  const seleccionada = Number(form.value?.idSeccion)
  const secciones = [...catalogoHorarios.secciones]
  const actual = form.value?.seccionActual
  if (actual && !secciones.some((s) => s.id === actual.id)) secciones.push(actual)
  return secciones.filter(
    (s) =>
      (s.nivel === 'LICEO' && Number(s.periodoLectivo) === periodo) ||
      s.id === seleccionada,
  )
})
const seccionDelHorario = computed(() =>
  seccionesDelHorario.value.find((s) => s.id === Number(form.value?.idSeccion)),
)
// Las asignaturas dependen del grado de la sección y del período.
const asignaturasDelHorario = computed(() => {
  const seccion = seccionDelHorario.value
  const actual = form.value?.asignaturaActual
  if (!seccion) return actual ? [actual] : []
  const asignaturas = [...catalogoHorarios.asignaturas]
  if (actual && !asignaturas.some((a) => a.id === actual.id)) asignaturas.push(actual)
  return asignaturas.filter(
    (a) =>
      a.nivel === 'LICEO' &&
      Number(a.periodoLectivo) === Number(form.value?.periodoLectivo) &&
      Number(a.idGrado) === Number(seccion.idGrado),
  )
})
// Un docente solo puede programarse si está vinculado a la asignatura elegida.
const docentesDelHorario = computed(() => {
  const asignatura = asignaturasDelHorario.value.find(
    (a) => a.id === Number(form.value?.idAsignatura),
  )
  const docentes = [...(asignatura?.docentes ?? [])]
  const actual = form.value?.docenteActual
  if (actual && !docentes.some((d) => d.id === actual.id)) docentes.push(actual)
  return docentes
})
// Al cambiar uno de los selectores dependientes, se descartan las opciones que
// ya no son válidas. Solo aplica al registrar: al editar se conserva lo que
// traía el horario aunque el catálogo haya cambiado.
watch(
  () => form.value?.periodoLectivo,
  (valor, anterior) => {
    if (prefijandoHorario) return
    if (!panel.abierto || panel.modo !== 'crear' || tab.value !== 'horarios' || valor === anterior) return
    form.value.idSeccion = null
    form.value.idAsignatura = null
    form.value.idDocente = null
  },
)
watch(
  () => form.value?.idSeccion,
  (valor, anterior) => {
    if (prefijandoHorario) return
    if (!panel.abierto || panel.modo !== 'crear' || tab.value !== 'horarios' || valor === anterior) return
    form.value.idAsignatura = null
    form.value.idDocente = null
  },
)
watch(
  () => form.value?.idAsignatura,
  (valor, anterior) => {
    if (prefijandoHorario) return
    if (!panel.abierto || panel.modo !== 'crear' || tab.value !== 'horarios' || valor === anterior) return
    form.value.idDocente = null
  },
)

const validar = (t, f) => {
  const otros = datos[t].filter((x) => x.id !== f.id)
  if (t === 'secciones') {
    if (!f.idGrado) return 'Selecciona el grado de la sección.'
    if (!f.periodoLectivo) return 'Selecciona el período lectivo.'
    if (panel.modo === 'crear') {
      if (!LETRAS_POR_FORMATO[f.formato]) {
        return 'Selecciona el formato: sección única (U) o secciones A y B.'
      }
      const actual = formatoSecciones(catalogos.secciones, f.idGrado, f.periodoLectivo)
      if (actual === 'unica') return 'Este grado ya tiene la sección única U. Dala de baja para crear A y B.'
      if (actual === 'dividida') return 'Este grado ya tiene las secciones A y B. Dales de baja para crear la sección única U.'
      if (actual === 'inconsistente') return 'Las secciones de este grado están inconsistentes. Dales de baja antes de crear otras.'
    } else if (!f.letra) {
      return 'Selecciona la sección que vas a editar.'
    }
  }
  if (t === 'representantes') {
    if (!f.primerNombre || !f.primerApellido) return 'El primer nombre y el primer apellido son obligatorios.'
    if (!f.telefono) return 'El número telefónico es obligatorio.'
    // Con «Todos» el administrador debe decir para qué nivel registra al
    // representante; con un nivel de filtro ya viene prefijado. Al editar no se
    // pide porque el backend no guarda este campo.
    // El alta rápida dentro del formulario de estudiantes no lo pide: el nivel
    // ya se deduce del grado que se está registrando.
    if (!f.inline && panel.modo === 'crear' && !nivelFiltro.value && !f.nivel) {
      return 'Selecciona el nivel del estudiante que representará.'
    }
  }
  if (t === 'estudiantes') {
    if (!f.cedula) return 'La cédula del estudiante es obligatoria.'
    if (!f.primerNombre || !f.primerApellido) return 'El primer nombre y el primer apellido son obligatorios.'
    if (!f.fechaNacimiento) return 'La fecha de nacimiento es obligatoria.'
    if (f.fechaNacimiento > new Date().toISOString().slice(0, 10)) return 'La fecha de nacimiento no puede ser futura.'
    if (!f.idGrado) return 'Selecciona el grado del estudiante.'
    if (!f.idSeccion) return 'Selecciona una sección registrada para el estudiante.'
    const seccion = seccionesDelFormulario.value.find(
      (s) => s.id === Number(f.idSeccion),
    )
    if (!seccion) return 'La sección elegida no está registrada.'
    if (Number(seccion.idGrado) !== Number(f.idGrado)) {
      return 'La sección elegida no corresponde al grado seleccionado.'
    }
    if (
      periodoSeleccionado.value &&
      Number(seccion.periodoLectivo) !== Number(periodoSeleccionado.value)
    ) {
      return 'La sección elegida pertenece a otro período lectivo.'
    }
  }
  if (t === 'docentes' && !f.nivel) return 'Selecciona el nivel educativo del docente.'
  if (t === 'asignaturas') {
    if (!String(f.nombre ?? '').trim()) return 'Escribe el nombre de la asignatura.'
    if (!f.idGrado) return 'Selecciona el grado de Liceo.'
    const grado = catalogoAsignaturas.grados.find((g) => g.id === Number(f.idGrado))
    if (!grado || grado.nivel !== 'LICEO') {
      return 'Las asignaturas solo se registran en grados de Liceo.'
    }
    if (panel.modo === 'crear' && !f.periodoLectivo) {
      return 'Selecciona el período lectivo.'
    }
    // El duplicado se mide por grado + nombre + período. Se revisa sobre la
    // caché completa (si ya se cargó) para no depender de la página visible.
    const todas = asignaturasApi.todos.length ? asignaturasApi.todos : datos.asignaturas
    const duplicada = todas.some(
      (x) =>
        x.id !== f.id &&
        Number(x.idGrado) === Number(f.idGrado) &&
        Number(x.periodoLectivo) === Number(f.periodoLectivo) &&
        norm(x.nombre) === norm(f.nombre),
    )
    if (duplicada) return 'Ya existe esa asignatura en ese grado y período.'
  }
  if (t === 'horarios') {
    if (!f.periodoLectivo) return 'Selecciona el período lectivo.'
    if (!f.idSeccion) return 'Selecciona la sección de Liceo.'
    const seccion = seccionesDelHorario.value.find((s) => s.id === Number(f.idSeccion))
    if (!seccion) return 'La sección elegida no está registrada para ese período.'
    if (Number(seccion.periodoLectivo) !== Number(f.periodoLectivo)) {
      return 'La sección pertenece a otro período lectivo.'
    }
    if (!f.idBloque) return 'Selecciona el bloque horario.'
    if (!f.diaSemana) return 'Selecciona el día de la semana.'
    if (!f.idAsignatura) return 'Selecciona la asignatura.'
    const asignatura = asignaturasDelHorario.value.find((a) => a.id === Number(f.idAsignatura))
    if (!asignatura) return 'La asignatura no corresponde al grado y período de la sección.'
    if (!f.idDocente) return 'Selecciona el docente.'
    const docente = docentesDelHorario.value.find((d) => d.id === Number(f.idDocente))
    if (!docente) return 'El docente no está vinculado a la asignatura.'

    const conocidos = catalogoHorarios.horarios.length
      ? catalogoHorarios.horarios
      : horariosApi.todos.length ? horariosApi.todos : otros
    const mismoBloqueDia = conocidos.filter(
      (h) =>
        h.id !== f.id &&
        Number(h.periodoLectivo) === Number(f.periodoLectivo) &&
        Number(h.idBloque) === Number(f.idBloque) &&
        Number(h.diaSemana) === Number(f.diaSemana),
    )
    if (mismoBloqueDia.some((h) => Number(h.idSeccion) === Number(f.idSeccion))) {
      return 'La sección ya tiene una clase en ese bloque y día.'
    }
    if (mismoBloqueDia.some((h) => Number(h.idDocente) === Number(f.idDocente))) {
      return 'El docente ya tiene una clase en ese bloque y día.'
    }
  }
  return ''
}
// Ajusta las vinculaciones docente↔asignatura con los endpoints dedicados del
// backend. Solo se toca lo que cambió para no alterar vinculaciones ajenas.
const sincronizarDocentesAsignatura = async (
  idAsignatura,
  seleccionados = [],
  anteriores = [],
) => {
  const antes = new Set((anteriores ?? []).map(Number))
  const ahora = new Set((seleccionados ?? []).map(Number))
  const quitar = [...antes].filter((id) => !ahora.has(id))
  const agregar = [...ahora].filter((id) => !antes.has(id))

  try {
    for (const id of quitar) await desvincularDocente(idAsignatura, id)
    for (const id of agregar) await vincularDocente(idAsignatura, id)
  } catch (error) {
    throw new Error(
      `${error.message} La asignatura se guardó, pero no se pudo completar la vinculación de docentes. Revisa los docentes desde Editar.`,
      { cause: error },
    )
  }
}

const guardando = ref(false)

const guardar = async () => {
  if (!puedeGestionar.value) return
  const t = tab.value, f = form.value
  for (const k in f) if (typeof f[k] === 'string') f[k] = f[k].trim()
  const err = validar(t, f)
  if (err) { errorForm.value = err; return }

  // Todas las pestañas están conectadas: crear/actualizar en el servidor y recargar.
  if (t === 'secciones' || t === 'docentes' || t === 'representantes' || t === 'estudiantes' || t === 'asignaturas' || t === 'horarios') {
    const creando = panel.modo === 'crear'
    const recurso =
      t === 'asignaturas'
        ? {
            crear: async () => {
              const creada = await crearAsignatura(f)
              await sincronizarDocentesAsignatura(creada.id, f.docenteIds ?? [], [])
              return creada
            },
            actualizar: async () => {
              const actualizada = await actualizarAsignatura(f.id, f)
              await sincronizarDocentesAsignatura(
                f.id,
                f.docenteIds ?? [],
                f.docentesAnteriores ?? [],
              )
              return actualizada
            },
            recargar: refrescarAsignaturas,
          }
        : t === 'secciones'
        ? {
            // Crear U, o A y B juntas, con titular distinto por sección.
            crear: () => crearFormatoSecciones({
              idGrado: f.idGrado,
              periodoLectivo: f.periodoLectivo,
              formato: f.formato,
              titulares: f.titulares ?? {},
            }),
            actualizar: actualizarSeccion,
            recargar: refrescarSecciones,
          }
        : t === 'horarios'
          ? { crear: crearHorario, actualizar: actualizarHorario, recargar: refrescarHorarios }
          : t === 'docentes'
            ? { crear: crearDocente, actualizar: actualizarDocente, recargar: refrescarDocentes }
            : t === 'representantes'
              ? { crear: crearRepresentante, actualizar: actualizarRepresentante, recargar: refrescarRepresentantes }
              : { crear: crearEstudiante, actualizar: actualizarEstudiante, recargar: refrescarEstudiantes }
    errorForm.value = ''
    guardando.value = true
    try {
      if (creando) await recurso.crear(f)
      else await recurso.actualizar(f.id, f)
      cerrarPanel()
      avisar(creando ? 'Registro creado correctamente.' : 'Cambios guardados.')
      await recurso.recargar()
    } catch (error) {
      errorForm.value = error?.message || `No se pudo guardar el ${tabActual.value.singular}.`
    } finally {
      guardando.value = false
    }
    return
  }
}

// ───────────── Eliminar, confirmaciones y avisos ─────────────
const confirmacion = ref(null)
const confirmRef = ref(null)
const pedirConfirmacion = (titulo, texto, boton, accion) => { confirmacion.value = { titulo, texto, boton, accion } }
// La confirmación se abre con el foco en «Cancelar», la opción segura.
watch(confirmacion, async (valor) => {
  if (!valor) return
  await nextTick()
  confirmRef.value?.querySelector('button')?.focus()
})
const confirmar = async () => {
  const accion = confirmacion.value?.accion
  confirmacion.value = null
  if (accion) await accion()
}

const aviso = ref('')
let temporizador = null
const avisar = (msg) => {
  aviso.value = msg
  clearTimeout(temporizador)
  temporizador = setTimeout(() => (aviso.value = ''), 4000)
}

const consecuencias = {
  secciones: ' El servidor no permitirá darla de baja si tiene estudiantes o horarios activos.',
  representantes: ' Solo se puede eliminar si no tiene estudiantes asignados.',
  asignaturas: ' El servidor no permitirá darla de baja si tiene horarios o docentes vinculados.',
  docentes: '',
  estudiantes: '',
  horarios: '',
}
// Si el grado está dividido, A y B se dan de baja juntas. El catálogo es la
// fuente del formato; si está desactualizado se cae a la sección pulsada.
const seccionesABorrar = (item) => {
  const delCatalogo = catalogos.secciones.filter(
    (s) => s.idGrado === item.idGrado && s.periodoLectivo === item.periodoLectivo,
  )
  const formato = formatoSecciones(catalogos.secciones, item.idGrado, item.periodoLectivo)
  return formato === 'dividida' && delCatalogo.length === 2 ? delCatalogo : [item]
}

const bajasSecciones = async (secciones, mensaje) => {
  guardando.value = true
  try {
    await eliminarFormatoSecciones(secciones)
    avisar(mensaje)
    await refrescarSecciones()
  } catch (error) {
    seccionesApi.error = error?.message || 'No se pudieron dar de baja las secciones.'
    avisar(seccionesApi.error)
  } finally {
    guardando.value = false
  }
}

// Reparación de estados inconsistentes (por ejemplo, A sin B).
const reiniciarSecciones = (secciones) => {
  if (!puedeGestionar.value) return
  const letras = secciones.map((s) => s.letra).sort().join(' y ')
  pedirConfirmacion(
    'Dar de baja secciones',
    `¿Dar de baja ${letras}? Quedarán sin secciones y podrás crear el formato correcto (U sola, o A y B juntas).`,
    'Dar de baja',
    () => bajasSecciones(secciones, 'Secciones dadas de baja.'),
  )
}

const eliminar = (item) => {
  if (!puedeGestionar.value) return
  const t = tab.value

  if (t === 'secciones') {
    const objetivo = seccionesABorrar(item)
    const letras = objetivo.map((s) => s.letra).sort().join(' y ')
    pedirConfirmacion(
      'Eliminar sección',
      `¿Dar de baja ${objetivo.length > 1 ? 'las secciones' : 'la sección'} ${letras} de ${item.gradoNombre || 'ese grado'}? Esta acción no se puede deshacer.${objetivo.length > 1 ? ' Se darán de baja A y B juntas.' : ''} Antes se comprobará si tienen estudiantes u horarios.`,
      'Eliminar',
      () => bajasSecciones(objetivo, 'Registro eliminado.'),
    )
    return
  }

  pedirConfirmacion(`Eliminar ${tabActual.value.singular}`, `¿Eliminar "${etiqueta(t, item)}"? Esta acción no se puede deshacer.${consecuencias[t]}`, 'Eliminar', async () => {
    // Borrado real (soft delete en el servidor).
    if (t === 'docentes' || t === 'representantes' || t === 'estudiantes' || t === 'asignaturas' || t === 'horarios') {
      const recurso =
        t === 'docentes'
          ? { eliminar: eliminarDocente, api: docentesApi, recargar: refrescarDocentes, nombre: 'docente' }
          : t === 'representantes'
            ? { eliminar: eliminarRepresentante, api: representantesApi, recargar: refrescarRepresentantes, nombre: 'representante' }
            : t === 'estudiantes'
              ? { eliminar: eliminarEstudiante, api: estudiantesApi, recargar: refrescarEstudiantes, nombre: 'estudiante' }
              : t === 'asignaturas'
                ? { eliminar: eliminarAsignatura, api: asignaturasApi, recargar: refrescarAsignaturas, nombre: 'asignatura' }
                : { eliminar: eliminarHorario, api: horariosApi, recargar: refrescarHorarios, nombre: 'horario' }
      try {
        await recurso.eliminar(item.id)
        avisar('Registro eliminado.')
        await recurso.recargar()
      } catch (error) {
        // Se conserva el mensaje para que el usuario pueda reintentar.
        recurso.api.error = error?.message || `No se pudo eliminar el ${recurso.nombre}.`
        avisar(recurso.api.error)
      }
      return
    }
  })
}

// ───────────── Clases reutilizables ─────────────
// card, inp, lbl, btnP, btnS, tag, nada, aviso2, btnPag y sinRes
// viven en components/gestion-academica/estilos.js
</script>

<template>
  <div class="mx-auto flex w-full max-w-[1320px] flex-col font-sans text-[#1b2a2f]">

    <div :class="[card, 'overflow-hidden']">
      <!-- Pestañas (arriba, pegadas al inicio del componente) -->
      <div role="tablist" aria-label="Secciones de gestión académica" class="flex gap-1 overflow-x-auto border-b border-[#d5dbe6] bg-[#f6f9fe] px-3 pt-2.5">
        <button v-for="t in tabsVisibles" :id="'tab-' + t.id" :key="t.id" role="tab" type="button"
                :aria-selected="tab === t.id" aria-controls="panel-gestion" :tabindex="tab === t.id ? 0 : -1"
                @click="tab = t.id" @keydown="moverTab($event, t.id)"
                :class="['flex min-h-11 items-center gap-2 whitespace-nowrap rounded-t-xl border-b-[3px] px-4 text-[15px] transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#233E47]',
                         tab === t.id ? 'border-[#233E47] bg-white font-bold text-[#233E47]' : 'border-transparent font-semibold text-[#4a5a63] hover:text-[#233E47]']">
          {{ t.label }}
          <span :class="['rounded-full px-2 py-0.5 text-xs font-bold', tab === t.id ? 'bg-[#ccd5ae] text-[#233E47]' : 'bg-[#e4e7ee] text-[#4a5a63]']">{{ resumen.cargando && !resumen.datos ? '…' : totalTab(t.id) }}</span>
        </button>
      </div>

      <p v-if="resumen.error" role="alert" class="border-b border-[#fbd5d2] bg-[#fff5f4] px-5 py-2 text-sm font-semibold text-[#8a1c14]">
        {{ resumen.error }}
        <button type="button" class="ml-2 font-bold underline" @click="cargarResumen">Reintentar</button>
      </p>

      <div id="panel-gestion" role="tabpanel" :aria-labelledby="'tab-' + tab" class="flex flex-col gap-5 p-5 md:p-6">

        <!-- Barra: buscador + nivel + período + sección + acción -->
        <div class="flex flex-wrap items-center gap-3">
          <div v-if="tab !== 'horarios'" class="relative min-w-[220px] flex-1">
            <label for="busq" class="sr-only">Buscar</label>
            <svg aria-hidden="true" class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#5b6a72]" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
            <input id="busq" v-model="busq[tab]" type="search" :placeholder="placeholders[tab]" :class="[inp, '!pl-10']">
          </div>
          <div v-if="apiTab && esAdministrador && tab !== 'horarios'" class="flex items-center gap-2">
            <label for="nivel-filtro" class="whitespace-nowrap text-sm font-semibold text-[#233E47]">Nivel</label>
            <select id="nivel-filtro" v-model="nivelFiltro" :class="[inp, '!h-10 !w-auto']">
              <option value="">Todos</option>
              <option value="LICEO">Liceo</option>
              <option value="ESCUELA">Escuela</option>
            </select>
          </div>
          <div v-if="tab === 'estudiantes'" class="flex items-center gap-2">
            <label for="filtro-anio" class="whitespace-nowrap text-sm font-semibold text-[#233E47]">Año</label>
            <select id="filtro-anio" v-model.number="filtroAnio" :class="[inp, '!h-10 !w-auto']">
              <option value="">Todos</option>
              <option v-for="g in gradosFiltro" :key="g.id" :value="g.id">{{ g.nombre }}</option>
            </select>
          </div>
          <div v-if="tab === 'estudiantes'" class="flex items-center gap-2">
            <label for="filtro-seccion" class="whitespace-nowrap text-sm font-semibold text-[#233E47]">Sección</label>
            <select id="filtro-seccion" v-model.number="filtroSeccion" :class="[inp, '!h-10 !w-auto']">
              <option value="">Todas</option>
              <option v-for="s in seccionesFiltro" :key="s.id" :value="s.id">{{ etiquetaSeccionGrilla(s) }}</option>
            </select>
          </div>
          <div v-if="tab === 'secciones' || tab === 'asignaturas' || tab === 'horarios' || tab === 'estudiantes'" class="flex items-center gap-2">
            <label for="periodo-filtro" class="whitespace-nowrap text-sm font-semibold text-[#233E47]">Período</label>
            <select id="periodo-filtro" v-model.number="periodoSeleccionado" :class="[inp, '!h-10 !w-auto']">
              <option v-for="p in catalogos.periodos" :key="p.id ?? p.anio" :value="p.anio">
                {{ p.anio }}{{ p.activo ? ' · activo' : '' }}{{ p.cerrado ? ' · cerrado' : '' }}
              </option>
            </select>
          </div>
          <div v-if="tab === 'horarios'" class="flex items-center gap-2">
            <label for="seccion-grilla" class="whitespace-nowrap text-sm font-semibold text-[#233E47]">Sección</label>
            <select id="seccion-grilla" :value="seccionGrilla?.id ?? ''" :class="[inp, '!h-10 !w-auto']" @change="elegirSeccionGrilla($event.target.value)">
              <option value="">Elige una sección…</option>
              <option v-for="s in seccionesGrilla" :key="s.id" :value="s.id">{{ etiquetaSeccionGrilla(s) }}</option>
            </select>
          </div>
          <div v-if="tab === 'docentes'" class="flex items-center gap-2">
            <label for="tam-doc" class="whitespace-nowrap text-sm font-semibold text-[#233E47]">Por página</label>
            <select id="tam-doc" v-model.number="docentesApi.size" :class="[inp, '!h-10 !w-auto']">
              <option :value="10">10</option>
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>
          <div v-else-if="tab === 'representantes'" class="flex items-center gap-2">
            <label for="tam-rep" class="whitespace-nowrap text-sm font-semibold text-[#233E47]">Por página</label>
            <select id="tam-rep" v-model.number="representantesApi.size" :class="[inp, '!h-10 !w-auto']">
              <option :value="10">10</option>
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>
          <div v-else-if="tab === 'estudiantes'" class="flex items-center gap-2">
            <label for="tam-est" class="whitespace-nowrap text-sm font-semibold text-[#233E47]">Por página</label>
            <select id="tam-est" v-model.number="estudiantesApi.size" :class="[inp, '!h-10 !w-auto']">
              <option :value="10">10</option>
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>
          <div v-else-if="tab === 'asignaturas'" class="flex items-center gap-2">
            <label for="tam-asig" class="whitespace-nowrap text-sm font-semibold text-[#233E47]">Por página</label>
            <select id="tam-asig" v-model.number="asignaturasApi.size" :class="[inp, '!h-10 !w-auto']">
              <option :value="10">10</option>
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>
          <button v-if="exportacionTab" type="button"
                  :title="!nivelExportacion ? 'Elige Liceo o Escuela en el filtro de nivel para exportar.' : exportacionTab.ayuda"
                  :class="[btnS, 'disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-white']"
                  :disabled="!nivelExportacion || exportandoListado" @click="exportarListadoDeTab">
            <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12m0 0 4-4m-4 4-4-4M4 17v3h16v-3"/></svg>
            {{ exportandoListado ? 'Exportando…' : exportacionTab.etiqueta }}
          </button>
          <button v-if="tab === 'horarios'" type="button"
                  :class="[btnS, 'disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-white']"
                  :disabled="!seccionGrilla || exportandoHorario" @click="exportarHorario">
            <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12m0 0 4-4m-4 4-4-4M4 17v3h16v-3"/></svg>
            {{ exportandoHorario ? 'Exportando…' : 'Exportar horario' }}
          </button>
          <button v-if="puedeGestionar && tab !== 'horarios'" type="button" :class="btnP" @click="abrirNuevo">
            <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
            {{ tabActual.nuevo }}
          </button>
        </div>

        <!-- Resumen del filtro y del total -->
        <p v-if="apiTab && tab !== 'horarios' && !(apiTab.error && !apiTab.cargado)" class="-mt-1 text-sm text-[#4a5a63]">
          <span v-if="buscandoTab">Buscando en la lista completa…</span>
          <span v-else-if="filtrando"><b class="text-[#233E47]">{{ totalFiltrado }}</b> coincidencia(s) de <b class="text-[#233E47]">{{ apiTab.total }}</b> {{ apiTab.total === 1 ? sustantivo.uno : sustantivo.varios }}</span>
          <span v-else><b class="text-[#233E47]">{{ apiTab.total }}</b> {{ apiTab.total === 1 ? sustantivo.uno : sustantivo.varios }} en {{ resumenFiltrosEstudiantes }}</span>
        </p>

        <!-- El nivel de un representante se deduce de sus estudiantes -->
        <p v-if="tab === 'representantes' && nivelConsulta" class="-mt-3 text-xs text-[#5b6a72]">
          Solo aparecen representantes con estudiantes activos en {{ alcanceNivel }}.
        </p>

        <!-- Error de carga -->
        <p v-if="apiTab && apiTab.error && tab !== 'horarios'" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
          {{ apiTab.error }}
          <button type="button" class="ml-2 font-bold underline" @click="recargarTab">Reintentar</button>
        </p>

        <!-- Cargando la primera página -->
        <p v-if="apiTab && apiTab.loading && !datos[tab].length && tab !== 'horarios'" :class="sinRes">Cargando {{ tabActual.label.toLowerCase() }}…</p>

        <!-- En Secciones se muestra la matriz aunque esté vacía: las celdas
             "+ Crear" son el punto de entrada para registrar la primera. -->
        <p v-if="tab === 'secciones' && !datos.secciones.length && !apiTab.loading && !apiTab.cargandoTodos && !apiTab.error && !filtrando" :class="aviso2">
          {{ puedeGestionar ? 'Aún no hay secciones. Usa las celdas «+ Crear» del grado que corresponda.' : 'Aún no hay secciones registradas para tu nivel.' }}
        </p>

        <!-- Estado vacío general (aún no hay ningún dato) -->
        <div v-if="tab !== 'secciones' && tab !== 'horarios' && !listaTab.length && !(apiTab && (apiTab.loading || apiTab.cargandoTodos || apiTab.error))" class="flex flex-col items-center gap-2 rounded-xl border border-dashed border-[#91a5c9] bg-[#f6f9fe] px-4 py-14 text-center">
          <svg aria-hidden="true" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#91a5c9" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M7 9.5V15c0 1.5 2.2 3 5 3s5-1.5 5-3V9.5"/></svg>
          <p class="text-lg font-bold text-[#233E47]">{{ vacioTitulo }}</p>
          <p class="max-w-md text-sm text-[#4a5a63]">{{ vacioTexto }}</p>
          <button v-if="puedeGestionar" type="button" :class="[btnS, 'mt-2']" @click="abrirNuevo">{{ vacios[tab].boton }}</button>
        </div>

        <!-- Vista principal y única de Horarios: grilla semanal por sección -->
        <HorarioGrilla
          v-if="tab === 'horarios'"
          :seccion="seccionGrilla"
          :hay-secciones="seccionesGrilla.length > 0"
          :bloques="bloquesGrilla.items"
          :horarios="semanaGrilla.items"
          :cargando="semanaGrilla.cargando"
          :cargando-bloques="bloquesGrilla.cargando"
          :cargando-secciones="seccionesGrillaCargando"
          :error="semanaGrilla.error"
          :error-bloques="bloquesGrilla.error"
          :error-secciones="seccionesGrillaError"
          :puede-gestionar="puedeGestionar"
          @crear="crearHorarioEn"
          @editar="abrirEditar"
          @eliminar="eliminar"
          @reintentar="recargarGrilla"
          @ir-secciones="tab = 'secciones'"
        />

        <template v-else-if="listaTab.length || tab === 'secciones'">

          <!-- Cada pestaña vive en su propio componente -->
          <SeccionesTabla
            v-if="tab === 'secciones'"
            :filas="filasPagina"
            :catalogo="catalogos.secciones"
            :grados="catalogos.grados"
            :periodo="periodoSeleccionado"
            :buscando="buscandoTab"
            :cargando="apiTab.cargandoTodos"
            :filtrando="filtrando"
            :puede-gestionar="puedeGestionar"
            @editar="abrirEditar"
            @eliminar="eliminar"
            @crear="crearSeccionEn"
            @ver-horario="verHorario"
            @reiniciar="reiniciarSecciones"
          />

          <RepresentantesTabla
            v-else-if="tab === 'representantes'"
            :filas="filasPagina"
            :estudiantes="estudiantesReps.items"
            :cargando-estudiantes="estudiantesReps.cargando"
            :buscando="buscandoTab"
            :cargando="apiTab.cargandoTodos"
            :filtrando="filtrando"
            :puede-gestionar="puedeGestionar"
            @editar="abrirEditar"
            @eliminar="eliminar"
          />

          <EstudiantesTabla
            v-else-if="tab === 'estudiantes'"
            :filas="filasPagina"
            :buscando="buscandoTab"
            :cargando="apiTab.cargandoTodos"
            :filtrando="filtrando"
            :puede-gestionar="puedeGestionar"
            @editar="abrirEditar"
            @eliminar="eliminar"
          />

          <AsignaturasTabla
            v-else-if="tab === 'asignaturas'"
            :filas="filasPagina"
            :buscando="buscandoTab"
            :cargando="apiTab.cargandoTodos"
            :filtrando="filtrando"
            :puede-gestionar="puedeGestionar"
            @editar="abrirEditar"
            @eliminar="eliminar"
          />

          <DocentesTabla
            v-else-if="tab === 'docentes'"
            :filas="filasPagina"
            :buscando="buscandoTab"
            :cargando="apiTab.cargandoTodos"
            :filtrando="filtrando"
            :puede-gestionar="puedeGestionar"
            @editar="abrirEditar"
            @eliminar="eliminar"
          />

          <!-- Paginación -->
          <nav v-if="totalFiltrado > 0" aria-label="Paginación" class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-sm text-[#4a5a63]">
              Mostrando <b class="text-[#233E47]">{{ desde }}–{{ hasta }}</b> de <b class="text-[#233E47]">{{ totalFiltrado }}</b>
              {{ filtrando ? 'coincidencias' : 'registros' }}
              <span v-if="cargandoTab" class="ml-2 italic text-[#5b6a72]">actualizando…</span>
            </p>
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="mr-1 whitespace-nowrap text-sm text-[#4a5a63]">Página <b class="text-[#233E47]">{{ pg }}</b> de <b class="text-[#233E47]">{{ totalPaginas }}</b></span>
              <button type="button" :class="btnPag" :disabled="pg === 1 || cargandoTab" aria-label="Primera página" @click="irPagina(1)">«</button>
              <button type="button" :class="btnPag" :disabled="pg === 1 || cargandoTab" aria-label="Página anterior" @click="irPagina(pg - 1)">← Anterior</button>
              <template v-for="(b, i) in botonesPagina" :key="i">
                <span v-if="b === '…'" class="px-1 text-[#5b6a72]" aria-hidden="true">…</span>
                <button v-else type="button" :aria-current="b === pg ? 'page' : null" :aria-label="'Página ' + b"
                        :class="[btnPag, b === pg ? '!border-[#233E47] !bg-[#233E47] !text-white' : '']" @click="irPagina(b)">{{ b }}</button>
              </template>
              <button type="button" :class="btnPag" :disabled="pg === totalPaginas || cargandoTab" aria-label="Página siguiente" @click="irPagina(pg + 1)">Siguiente →</button>
              <button type="button" :class="btnPag" :disabled="pg === totalPaginas || cargandoTab" aria-label="Última página" @click="irPagina(totalPaginas)">»</button>
            </div>
          </nav>
        </template>
      </div>
    </div>

    <!-- ═══════════ Panel lateral, confirmación y aviso ═══════════ -->
    <Teleport to="body">
      <Transition enter-active-class="transition-opacity duration-200" enter-from-class="opacity-0" leave-active-class="transition-opacity duration-150" leave-to-class="opacity-0">
        <div v-if="panel.abierto" class="fixed inset-0 z-40 bg-[#0f1f24]/50" aria-hidden="true" @click="cerrarPanel"></div>
      </Transition>
      <Transition enter-active-class="transition-transform duration-300 ease-out" enter-from-class="translate-x-full" leave-active-class="transition-transform duration-200 ease-in" leave-to-class="translate-x-full">
        <aside v-if="panel.abierto" ref="panelRef" role="dialog" aria-modal="true" tabindex="-1" :aria-label="tituloPanel" @keydown.esc="cerrarPanel"
               class="fixed inset-y-0 right-0 z-50 flex w-full flex-col bg-white font-sans text-[#1b2a2f] shadow-2xl sm:max-w-[480px]">
          <header class="flex items-center justify-between border-b border-[#d5dbe6] bg-[#f6f9fe] px-6 py-4">
            <h2 class="text-lg font-bold text-[#233E47]">{{ tituloPanel }}</h2>
            <button type="button" aria-label="Cerrar panel" class="grid h-10 w-10 place-items-center rounded-lg text-[#233E47] hover:bg-[#e4ecf8]" @click="cerrarPanel">
              <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
            </button>
          </header>

          <form class="flex min-h-0 flex-1 flex-col" @submit.prevent="guardar">
            <div class="flex-1 space-y-4 overflow-y-auto px-6 py-5">
              <p v-if="errorForm" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">{{ errorForm }}</p>

              <!-- Sección -->
              <template v-if="tab === 'secciones'">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label for="f-s-grado" :class="lbl">Grado / año</label>
                    <select id="f-s-grado" v-model="form.idGrado" required :disabled="panel.modo === 'editar'" :class="[inp, 'mt-1', panel.modo === 'editar' ? 'bg-[#f3f6f1] opacity-70' : '']">
                      <option value="" disabled>Selecciona</option>
                      <option v-for="g in catalogos.grados" :key="g.id" :value="g.id">{{ g.nombre }} ({{ etiquetaNivel(g.nivel) }})</option>
                    </select>
                  </div>
                  <div>
                    <label for="f-s-formato" :class="lbl">Formato</label>
                    <select id="f-s-formato" v-model="form.formato" required :disabled="panel.modo === 'editar'" :class="[inp, 'mt-1', panel.modo === 'editar' ? 'bg-[#f3f6f1] opacity-70' : '']">
                      <option value="" disabled>Selecciona</option>
                      <option value="unica">Sección única (U)</option>
                      <option value="dividida">Secciones A y B</option>
                    </select>
                  </div>
                  <div>
                    <label for="f-s-letra" :class="lbl">Sección</label>
                    <select v-if="panel.modo === 'editar'" id="f-s-letra" :value="form.letra" disabled :class="[inp, 'mt-1', 'bg-[#f3f6f1] opacity-70']">
                      <option :value="form.letra">{{ form.letra }}</option>
                    </select>
                    <p v-else :class="[nada, 'mt-2']">
                      {{ form.formato === 'unica' ? 'Se creará la sección U.' : form.formato === 'dividida' ? 'Se crearán las secciones A y B.' : 'Elige el formato para ver las secciones que se crearán.' }}
                    </p>
                  </div>
                  <div>
                    <label for="f-s-periodo" :class="lbl">Período lectivo</label>
                    <select id="f-s-periodo" v-model.number="form.periodoLectivo" required :disabled="panel.modo === 'editar'" :class="[inp, 'mt-1', panel.modo === 'editar' ? 'bg-[#f3f6f1] opacity-70' : '']">
                      <option value="" disabled>Selecciona</option>
                      <option v-for="p in catalogos.periodos" :key="p.id ?? p.anio" :value="p.anio">
                        {{ p.anio }}{{ p.activo ? ' · activo' : '' }}{{ p.cerrado ? ' · cerrado' : '' }}
                      </option>
                    </select>
                  </div>
                </div>

                <p v-if="catalogos.error" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
                  {{ catalogos.error }}
                  <button type="button" class="ml-2 font-bold underline" @click="cargarCatalogos">Reintentar</button>
                </p>
                <p v-else-if="catalogos.cargando" :class="aviso2">Cargando catálogos…</p>
                <p v-else-if="!catalogos.grados.length || !catalogos.periodos.length" :class="aviso2">
                  No hay grados o períodos disponibles. Revisa la configuración del backend.
                </p>

                <div v-if="esSeccionEscuela">
                  <template v-if="panel.modo === 'crear'">
                    <div v-for="letra in letrasDelFormulario" :key="letra" class="mt-3">
                      <label :for="`f-s-titular-${letra}`" :class="lbl">
                        Docente titular de la sección {{ letra }}
                        <span class="font-normal text-[#5b6a72]">(opcional)</span>
                      </label>
                      <select :id="`f-s-titular-${letra}`" :value="form.titulares?.[letra] ?? null" @change="fijarTitular(letra, $event.target.value)" :class="[inp, 'mt-1']">
                        <option :value="null">Sin titular</option>
                        <option v-for="d in titulares.items" :key="d.id" :value="d.id">{{ nomDocente(d) }}</option>
                      </select>
                    </div>
                  </template>
                  <div v-else>
                    <label for="f-s-titular" :class="lbl">
                      Docente titular de la sección {{ form.letra }}
                      <span class="font-normal text-[#5b6a72]">(opcional)</span>
                    </label>
                    <select id="f-s-titular" v-model.number="form.idDocenteTitular" :class="[inp, 'mt-1']">
                      <option :value="null">Sin titular</option>
                      <option v-for="d in titulares.items" :key="d.id" :value="d.id">{{ nomDocente(d) }}</option>
                    </select>
                  </div>
                  <p v-if="titulares.error" role="alert" class="mt-2 rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
                    {{ titulares.error }}
                    <button type="button" class="ml-2 font-bold underline" @click="cargarTitulares">Reintentar</button>
                  </p>
                  <p v-else-if="titulares.cargando && !titulares.listo" :class="[nada, 'mt-2']">Cargando docentes de Escuela…</p>
                  <p v-else-if="!titulares.items.length" :class="[nada, 'mt-2']">Todavía no hay docentes de Escuela; puedes dejar las secciones sin titular.</p>
                </div>
                <p v-else :class="aviso2">
                  El titular solo se asigna en secciones de Escuela. El horario de Liceo se organiza por bloques de materia.
                </p>

                <p v-if="panel.modo === 'editar'" class="text-sm text-[#4a5a63]">
                  El grado, la letra y el período no se pueden cambiar. Para pasar de sección única a A y B (o al revés) o de año lectivo, da de baja la actual y crea el otro formato.
                </p>
              </template>

              <!-- Representante -->
              <template v-else-if="tab === 'representantes'">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div><label for="f-r-pn" :class="lbl">Primer nombre</label><input id="f-r-pn" v-model="form.primerNombre" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-r-sn" :class="lbl">Segundo nombre</label><input id="f-r-sn" v-model="form.segundoNombre" maxlength="50" :class="[inp, 'mt-1']"></div>
                  <div><label for="f-r-pa" :class="lbl">Primer apellido</label><input id="f-r-pa" v-model="form.primerApellido" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-r-sa" :class="lbl">Segundo apellido</label><input id="f-r-sa" v-model="form.segundoApellido" maxlength="50" :class="[inp, 'mt-1']"></div>
                </div>
                <div><label for="f-tel" :class="lbl">Número telefónico</label><input id="f-tel" v-model="form.telefono" type="tel" maxlength="50" required :class="[inp, 'mt-1']"></div>
                <!-- Con el filtro en «Todos» hay que pedir el nivel también
                     aquí, igual que en el formulario de docentes. El backend no
                     almacena este campo: sirve para indicar con qué estudiantes
                     debe vincularse desde la pestaña Estudiantes. -->
                <template v-if="!nivelFiltro && panel.modo === 'crear'">
                  <div>
                    <label for="f-r-nivel" :class="lbl">Nivel del estudiante que representará</label>
                    <select id="f-r-nivel" v-model="form.nivel" required :class="[inp, 'mt-1']">
                      <option value="" disabled>Selecciona</option>
                      <option v-for="n in [NIVELES.LICEO, NIVELES.ESCUELA]" :key="n" :value="n">{{ etiquetaNivel(n) }}</option>
                    </select>
                  </div>
                  <p class="text-sm text-[#4a5a63] sm:col-span-2">
                    El nivel no se guarda en el representante: vincúlalo con un estudiante de {{ etiquetaNivel(form.nivel) || 'ese nivel' }} desde la pestaña Estudiantes.
                  </p>
                </template>
              </template>

              <!-- Estudiante -->
              <template v-else-if="tab === 'estudiantes'">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div><label for="f-e-ced" :class="lbl">Cédula estudiantil</label><input id="f-e-ced" v-model="form.cedula" maxlength="20" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-e-fn" :class="lbl">Fecha de nacimiento</label><input id="f-e-fn" v-model="form.fechaNacimiento" type="date" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-e-pn" :class="lbl">Primer nombre</label><input id="f-e-pn" v-model="form.primerNombre" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-e-sn" :class="lbl">Segundo nombre</label><input id="f-e-sn" v-model="form.segundoNombre" maxlength="50" :class="[inp, 'mt-1']"></div>
                  <div><label for="f-e-pa" :class="lbl">Primer apellido</label><input id="f-e-pa" v-model="form.primerApellido" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-e-sa" :class="lbl">Segundo apellido</label><input id="f-e-sa" v-model="form.segundoApellido" maxlength="50" :class="[inp, 'mt-1']"></div>
                  <div>
                    <label for="f-e-grado" :class="lbl">Grado</label>
                    <select id="f-e-grado" v-model="form.idGrado" required :class="[inp, 'mt-1']">
                      <option value="" disabled>Selecciona</option>
                      <option v-for="g in gradosDelFormulario" :key="g.id" :value="g.id">{{ g.nombre }}</option>
                    </select>
                  </div>
                  <div>
                    <label for="f-e-seccion" :class="lbl">Sección registrada</label>
                    <select id="f-e-seccion" v-model.number="form.idSeccion" required :class="[inp, 'mt-1']">
                      <option :value="null" disabled>Selecciona</option>
                      <option v-for="s in seccionesDelFormulario" :key="s.id" :value="s.id">
                        Sección {{ s.letra }} · {{ s.periodoLectivo }}
                      </option>
                    </select>
                  </div>
                </div>

                <p v-if="catalogos.error" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
                  {{ catalogos.error }}
                  <button type="button" class="ml-2 font-bold underline" @click="cargarCatalogos">Reintentar</button>
                </p>
                <p v-else-if="catalogos.cargando" :class="aviso2">Cargando grados y secciones…</p>
                <p v-else-if="!catalogos.secciones.length" :class="aviso2">
                  No hay secciones registradas. Créalas desde la pestaña Secciones antes de registrar estudiantes.
                </p>
                <p v-else class="text-sm text-[#4a5a63]">
                  El estudiante se registra en una sección existente. No se crean secciones automáticamente.
                </p>

                <div>
                  <label for="f-rep" :class="lbl">Representante</label>
                  <div v-if="form.idRepresentante" class="mt-2 flex flex-wrap gap-1.5">
                    <span :class="[tag, 'flex items-center gap-1.5 !py-1']">
                      {{ representanteNombre }}
                      <button type="button" class="font-bold" aria-label="Quitar representante" @click="quitarRep">✕</button>
                    </span>
                  </div>
                  <p v-else :class="[nada, 'mt-2']">Sin representante vinculado</p>
                  <input id="f-rep" v-model="repBusq" type="search" placeholder="Buscar representante por nombre o apellido" autocomplete="off" :class="[inp, 'mt-2']">
                  <p v-if="repsFormulario.error" role="alert" class="mt-2 rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
                    {{ repsFormulario.error }}
                    <button type="button" class="ml-2 font-bold underline" @click="cargarRepsFormulario">Reintentar</button>
                  </p>
                  <p v-else-if="repsFormulario.cargando && !repsFormulario.listo" :class="[nada, 'mt-2']">Cargando representantes…</p>
                  <p v-else-if="!repOpciones.length" :class="aviso2">
                    Aún no hay representantes registrados. Puedes registrar uno aquí mismo sin salir del formulario.
                  </p>
                  <ul v-else-if="repBusq.trim() && !repInline.abierto" class="mt-1 overflow-hidden rounded-xl border border-[#d5dbe6]">
                    <li v-for="r in repCoincidencias" :key="r.id">
                      <button type="button" class="flex min-h-11 w-full items-center justify-between gap-3 px-3 text-left text-sm hover:bg-[#eef3fb]" @click="agregarRep(r)">
                        <span class="font-semibold">{{ nomPersona(r) }}</span><span class="text-[#4a5a63]">{{ r.telefono }}</span>
                      </button>
                    </li>
                    <li v-if="!repCoincidencias.length" class="px-3 py-3 text-sm italic text-[#5b6a72]">Ningún representante coincide con la búsqueda.</li>
                  </ul>

                  <button v-if="!repInline.abierto" type="button" class="mt-2 text-sm font-semibold text-[#233E47] underline" @click="abrirRepInline">
                    {{ repOpciones.length ? 'Registrar un representante nuevo aquí' : 'Registrar uno aquí' }}
                  </button>

                  <div v-if="repInline.abierto" class="mt-3 space-y-3 rounded-xl border border-[#b4d0f8] bg-[#f6f9fe] p-3">
                    <p class="text-sm font-bold text-[#233E47]">Registro rápido de representante</p>
                    <p v-if="repInline.error" role="alert" class="rounded-xl bg-[#fbd5d2] px-3 py-2 text-sm font-semibold text-[#8a1c14]">{{ repInline.error }}</p>
                    <div class="grid gap-2 sm:grid-cols-2">
                      <div><label for="f-er-pn" :class="lbl">Primer nombre</label><input id="f-er-pn" v-model="repInline.form.primerNombre" maxlength="50" required :class="[inp, 'mt-1']"></div>
                      <div><label for="f-er-sn" :class="lbl">Segundo nombre</label><input id="f-er-sn" v-model="repInline.form.segundoNombre" maxlength="50" :class="[inp, 'mt-1']"></div>
                      <div><label for="f-er-pa" :class="lbl">Primer apellido</label><input id="f-er-pa" v-model="repInline.form.primerApellido" maxlength="50" required :class="[inp, 'mt-1']"></div>
                      <div><label for="f-er-sa" :class="lbl">Segundo apellido</label><input id="f-er-sa" v-model="repInline.form.segundoApellido" maxlength="50" :class="[inp, 'mt-1']"></div>
                    </div>
                    <div><label for="f-er-tel" :class="lbl">Número telefónico</label><input id="f-er-tel" v-model="repInline.form.telefono" type="tel" maxlength="50" required :class="[inp, 'mt-1']"></div>
                    <div class="flex gap-2">
                      <button type="button" :class="[btnS, 'flex-1']" @click="cerrarRepInline">Cancelar</button>
                      <button type="button" :class="[btnP, 'flex-1']" :disabled="repInline.guardando" @click="guardarRepInline">{{ repInline.guardando ? 'Guardando…' : 'Guardar representante' }}</button>
                    </div>
                    <p class="text-xs text-[#5b6a72]">Los datos del estudiante se conservan y el representante quedará seleccionado automáticamente.</p>
                  </div>
                </div>
              </template>

              <!-- Asignatura -->
              <template v-else-if="tab === 'asignaturas'">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label for="f-a-nom" :class="lbl">Nombre de la asignatura</label>
                    <input id="f-a-nom" v-model="form.nombre" maxlength="100" required :class="[inp, 'mt-1']">
                  </div>
                  <div>
                    <label for="f-a-grado" :class="lbl">Grado / año (Liceo)</label>
                    <select id="f-a-grado" v-model="form.idGrado" required :disabled="panel.modo === 'editar'" :class="[inp, 'mt-1', panel.modo === 'editar' ? 'bg-[#f3f6f1] opacity-70' : '']">
                      <option value="" disabled>Selecciona</option>
                      <option v-for="g in catalogoAsignaturas.grados" :key="g.id" :value="g.id">{{ g.nombre }}</option>
                    </select>
                  </div>
                  <div>
                    <label for="f-a-periodo" :class="lbl">Período lectivo</label>
                    <select id="f-a-periodo" v-model.number="form.periodoLectivo" required :disabled="panel.modo === 'editar'" :class="[inp, 'mt-1', panel.modo === 'editar' ? 'bg-[#f3f6f1] opacity-70' : '']">
                      <option value="" disabled>Selecciona</option>
                      <option v-for="p in catalogos.periodos" :key="p.id ?? p.anio" :value="p.anio">
                        {{ p.anio }}{{ p.activo ? ' · activo' : '' }}{{ p.cerrado ? ' · cerrado' : '' }}
                      </option>
                    </select>
                  </div>
                </div>

                <p v-if="catalogoAsignaturas.error" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
                  {{ catalogoAsignaturas.error }}
                  <button type="button" class="ml-2 font-bold underline" @click="cargarCatalogoAsignaturas">Reintentar</button>
                </p>
                <p v-else-if="catalogoAsignaturas.cargando && !catalogoAsignaturas.listo" :class="aviso2">Cargando grados y docentes de Liceo…</p>
                <p v-else-if="!catalogoAsignaturas.grados.length" :class="aviso2">
                  No hay grados de Liceo disponibles. Revisa la configuración del backend.
                </p>

                <div>
                  <span :class="lbl">Docentes que dictan la asignatura</span>
                  <p :class="[nada, 'mt-1']">Solo docentes de Liceo. Puedes dejarla sin docentes y vincularlos después desde Editar.</p>
                  <div v-if="catalogoAsignaturas.docentes.length" class="mt-2 max-h-48 space-y-1 overflow-y-auto rounded-xl border border-[#d5dbe6] p-2">
                    <label v-for="d in catalogoAsignaturas.docentes" :key="d.id" class="flex min-h-10 cursor-pointer items-center gap-2 rounded-lg px-2 text-sm hover:bg-[#eef3fb]">
                      <input v-model="form.docenteIds" type="checkbox" :value="d.id" class="h-4 w-4 accent-[#233E47]">
                      <span>{{ nomDocente(d) }}</span>
                    </label>
                  </div>
                  <p v-else-if="catalogoAsignaturas.listo" :class="[nada, 'mt-2']">Todavía no hay docentes de Liceo registrados.</p>
                </div>

                <p v-if="panel.modo === 'editar'" class="text-sm text-[#4a5a63]">
                  El grado y el período se definen al registrar. Para cambiarlos, da de baja la asignatura y créala de nuevo.
                </p>
              </template>

              <!-- Docente -->
              <template v-else-if="tab === 'docentes'">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div><label for="f-d-pn" :class="lbl">Primer nombre</label><input id="f-d-pn" v-model="form.primerNombre" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-d-sn" :class="lbl">Segundo nombre</label><input id="f-d-sn" v-model="form.segundoNombre" maxlength="50" :class="[inp, 'mt-1']"></div>
                  <div><label for="f-d-pa" :class="lbl">Primer apellido</label><input id="f-d-pa" v-model="form.primerApellido" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-d-sa" :class="lbl">Segundo apellido</label><input id="f-d-sa" v-model="form.segundoApellido" maxlength="50" :class="[inp, 'mt-1']"></div>
                </div>
                <div>
                  <label for="f-d-ced" :class="lbl">Cédula</label>
                  <input id="f-d-ced" v-model="form.cedula" maxlength="20" required inputmode="numeric" :class="[inp, 'mt-1']">
                </div>
                <div>
                  <label for="f-d-nivel" :class="lbl">Nivel educativo</label>
                  <select id="f-d-nivel" v-model="form.nivel" required :class="[inp, 'mt-1']">
                    <option value="" disabled>Selecciona</option>
                    <option value="LICEO">Liceo</option>
                    <option value="ESCUELA">Escuela</option>
                  </select>
                </div>
                <p class="text-sm text-[#4a5a63]">Las asignaturas que dicta se gestionan aparte, desde la pestaña Asignaturas.</p>
              </template>

              <!-- Horario -->
              <template v-else-if="tab === 'horarios'">
                <p v-if="catalogoHorarios.error" role="alert" class="rounded-xl bg-[#fbd5d2] px-3 py-2 text-sm font-semibold text-[#8a1c14]">{{ catalogoHorarios.error }}</p>
                <div class="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label for="f-h-periodo" :class="lbl">Período lectivo</label>
                    <select id="f-h-periodo" v-model.number="form.periodoLectivo" required :disabled="panel.modo === 'editar'" :class="[inp, 'mt-1']">
                      <option value="" disabled>Selecciona</option>
                      <option v-for="p in catalogos.periodos" :key="p.id ?? p.anio" :value="p.anio">
                        {{ p.anio }}{{ p.activo ? ' · activo' : '' }}
                      </option>
                    </select>
                  </div>
                  <div>
                    <label for="f-h-seccion" :class="lbl">Sección de Liceo</label>
                    <select id="f-h-seccion" v-model="form.idSeccion" required :disabled="panel.modo === 'editar'" :class="[inp, 'mt-1']">
                      <option value="" disabled>Selecciona</option>
                      <option v-for="s in seccionesDelHorario" :key="s.id" :value="s.id">
                        {{ s.gradoNombre || `Grado ${s.gradoNumero}` }} · {{ s.letra }} · {{ s.periodoLectivo }}
                      </option>
                    </select>
                  </div>
                  <div>
                    <label for="f-h-dia" :class="lbl">Día de la semana</label>
                    <select id="f-h-dia" v-model="form.diaSemana" required :class="[inp, 'mt-1']">
                      <option value="" disabled>Selecciona</option>
                      <option v-for="d in dias" :key="d.v" :value="d.v">{{ d.l }}</option>
                    </select>
                  </div>
                  <div>
                    <label for="f-h-bloque" :class="lbl">Bloque</label>
                    <select id="f-h-bloque" v-model="form.idBloque" required :class="[inp, 'mt-1']">
                      <option value="" disabled>Selecciona</option>
                      <option v-for="b in catalogoHorarios.bloques" :key="b.id" :value="b.id">
                        {{ b.nombre || `Bloque ${b.numero ?? b.orden}` }} · {{ b.horaInicio.slice(0, 5) }}–{{ b.horaFin.slice(0, 5) }}
                      </option>
                    </select>
                  </div>
                  <div>
                    <label for="f-h-asig" :class="lbl">Asignatura</label>
                    <select id="f-h-asig" v-model="form.idAsignatura" required :disabled="!seccionDelHorario" :class="[inp, 'mt-1']">
                      <option value="" disabled>{{ seccionDelHorario ? 'Selecciona' : 'Primero elige la sección' }}</option>
                      <option v-for="a in asignaturasDelHorario" :key="a.id" :value="a.id">{{ a.nombre }}</option>
                    </select>
                    <p v-if="seccionDelHorario && !asignaturasDelHorario.length" :class="aviso2">
                      No hay asignaturas para esa sección y período.
                      <button type="button" class="font-bold underline" @click="irA('asignaturas')">Ir a Asignaturas</button>
                    </p>
                  </div>
                  <div>
                    <label for="f-h-doc" :class="lbl">Docente</label>
                    <select id="f-h-doc" v-model="form.idDocente" required :disabled="!form.idAsignatura" :class="[inp, 'mt-1']">
                      <option value="" disabled>{{ form.idAsignatura ? 'Selecciona' : 'Primero elige la asignatura' }}</option>
                      <option v-for="d in docentesDelHorario" :key="d.id" :value="d.id">{{ nomDocente(d) }}</option>
                    </select>
                    <p v-if="form.idAsignatura && !docentesDelHorario.length" class="mt-1 text-xs font-semibold text-[#8a1c14]">Esa asignatura aún no tiene docentes vinculados.</p>
                  </div>
                </div>
                <p class="text-xs text-[#5b6a72]">Los horarios son por bloques académicos de Liceo; no se programan en Escuela.</p>
              </template>
            </div>

            <footer class="flex gap-3 border-t border-[#d5dbe6] px-6 py-4">
              <button type="button" :class="[btnS, 'flex-1']" @click="cerrarPanel">Cancelar</button>
              <button type="submit" :class="[btnP, 'flex-1']" :disabled="guardando">{{ guardando ? 'Guardando…' : 'Guardar' }}</button>
            </footer>
          </form>
        </aside>
      </Transition>

      <!-- Confirmación -->
      <div v-if="confirmacion" class="fixed inset-0 z-[70] grid place-items-center bg-[#0f1f24]/60 p-4 font-sans" @keydown.esc="confirmacion = null">
        <div ref="confirmRef" role="alertdialog" aria-modal="true" tabindex="-1" :aria-label="confirmacion.titulo" class="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl" @keydown.esc="confirmacion = null">
          <h2 class="text-lg font-bold text-[#233E47]">{{ confirmacion.titulo }}</h2>
          <p class="mt-2 text-sm text-[#4a5a63]">{{ confirmacion.texto }}</p>
          <div class="mt-5 flex justify-end gap-3">
            <button type="button" :class="btnS" @click="confirmacion = null">Cancelar</button>
            <button type="button" :class="btnP" class="!bg-[#b42318] hover:!bg-[#8f1c12]" @click="confirmar">{{ confirmacion.boton }}</button>
          </div>
        </div>
      </div>

      <!-- Aviso -->
      <p v-if="aviso" role="status" class="fixed bottom-6 right-6 z-[80] rounded-xl bg-[#233E47] px-5 py-3 font-sans text-sm font-semibold text-white shadow-xl">{{ aviso }}</p>
    </Teleport>
  </div>
</template>
<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRecursoPaginado } from '@/composables/useRecursoPaginado'
import { norm, nomEst, nomPersona } from '@/components/gestion-academica/helpers'
import { sesion } from '@/services/auth'
import { buscarEstudiantes, obtenerEstudiante } from '@/services/estudiantes'
import { obtenerSeccion } from '@/services/secciones'
import { obtenerRepresentante } from '@/services/representantes'
import { consultarHorarioEstudiante } from '@/services/horarios'
import {
  listarPases,
  listarTodosPases,
  crearPase,
  actualizarPase,
  eliminarPase,
  subirArchivoPase,
  descargarArchivoPase,
  quitarArchivoPase,
} from '@/services/pases'

// ───────────── Helpers de fecha / formato ─────────────
const pad = (n) => String(n).padStart(2, '0')
const hoyISO = () => {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
const horaActual = () => {
  const d = new Date()
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}
const fmtFecha = (iso) => {
  const [anio, mes, dia] = String(iso ?? '').slice(0, 10).split('-')
  return anio && mes && dia ? `${dia}/${mes}/${anio}` : '—'
}
const fmtCedula = (cedula) => {
  const limpio = String(cedula ?? '').replace(/\D/g, '')
  return limpio ? `V-${limpio.replace(/\B(?=(\d{3})+(?!\d))/g, '.')}` : '—'
}
const fmtTamano = (bytes) => {
  const n = Number(bytes)
  if (!n) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}
const gradoSeccion = (est) =>
  est ? `${est.gradoNombre ?? ''} ${est.seccionLetra ?? ''}`.trim() || '—' : '—'
const etiquetaNivel = (nivel) =>
  nivel === 'LICEO' ? 'Liceo' : nivel === 'ESCUELA' ? 'Escuela' : '—'
const iniciales = (nombre) =>
  String(nombre ?? '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0])
    .join('')
    .toUpperCase() || '—'

// ───────────── Catálogos ─────────────
const TIPOS = ['ENTRADA', 'SALIDA']
const tipoLabel = (tipo) => (tipo === 'ENTRADA' ? 'Entrada' : tipo === 'SALIDA' ? 'Salida' : tipo)
// La entrada solo puede ser por retardo; la salida tiene dos motivos válidos.
const motivosPorTipo = {
  ENTRADA: ['Retardo'],
  SALIDA: ['Retirado por representante', 'Malestar de salud'],
}
const motivosTodos = [...new Set(Object.values(motivosPorTipo).flat())]
const LIMITE_PASES = 3

// Nivel del usuario: el administrador no tiene nivel y ve ambos.
const nivelSesion = computed(() => sesion.usuario?.nivel || '')

// ═════════════ SECCIÓN 1: Búsqueda y formulario ═════════════
const termino = ref('')
const resultados = ref([])
const buscando = ref(false)
const errorBusqueda = ref('')
const estudiante = ref(null)
let solicitudBusqueda = 0
let temporizadorBusqueda = null

const error = ref('')
const exito = ref('')
const guardando = ref(false)
let temporizadorExito = null

const form = reactive({
  tipo: 'ENTRADA',
  motivo: 'Retardo',
  autorizador: '',
  fecha: hoyISO(),
  hora: horaActual(),
})

const motivosDelTipo = computed(() => motivosPorTipo[form.tipo] ?? [])

watch(
  () => form.tipo,
  (tipo) => {
    form.motivo = motivosPorTipo[tipo]?.[0] ?? ''
    form.autorizador = ''
  },
)

const ahora = () => {
  form.fecha = hoyISO()
  form.hora = horaActual()
}

// ───────────── Pases del estudiante seleccionado ─────────────
const pasesEstudiante = ref([])
const cargandoPasesEst = ref(false)
const errorPasesEst = ref('')

const cargarPasesEstudiante = async (idEstudiante) => {
  if (!idEstudiante) {
    pasesEstudiante.value = []
    return
  }
  cargandoPasesEst.value = true
  errorPasesEst.value = ''
  try {
    const { items } = await listarTodosPases({ idEstudiante })
    pasesEstudiante.value = items
  } catch (e) {
    pasesEstudiante.value = []
    errorPasesEst.value = e?.message || 'No se pudieron cargar los pases del estudiante.'
  } finally {
    cargandoPasesEst.value = false
  }
}

// ───────────── Representante ─────────────
const representante = reactive({ cargando: false, error: '', datos: null })

const cargarRepresentante = async (idRepresentante) => {
  if (!idRepresentante) {
    representante.datos = null
    representante.error = ''
    return
  }
  representante.cargando = true
  representante.error = ''
  try {
    representante.datos = await obtenerRepresentante(idRepresentante)
  } catch (e) {
    representante.datos = null
    representante.error = e?.message || 'No se pudo cargar el representante.'
  } finally {
    representante.cargando = false
  }
}

// ───────────── Asignatura y docente derivados ─────────────
// Liceo: se buscan en el horario de la sección según fecha y hora.
// Escuela: se toma el docente titular de la sección.
//
// El mismo derivador se usa en el alta y en la edición, cada uno con su propio
// temporizador y token para descartar respuestas viejas.
const derivadoVacio = () => ({
  cargando: false,
  error: '',
  encontrado: false,
  origen: '',
  idAsignatura: null,
  idDocente: null,
  asignatura: '',
  docente: '',
  bloque: '',
  horaInicio: '',
  horaFin: '',
})

const crearDerivador = ({ getEstudiante, getFecha, getHora }) => {
  const estado = reactive(derivadoVacio())
  let temporizador = null
  let solicitud = 0

  const cancelar = () => {
    clearTimeout(temporizador)
    solicitud += 1
  }

  const limpiar = () => {
    cancelar()
    Object.assign(estado, derivadoVacio())
  }

  const resolverTitular = async (est, actual) => {
    if (!est.idSeccion) return
    try {
      const seccion = await obtenerSeccion(est.idSeccion)
      if (actual !== solicitud) return
      if (seccion.idDocenteTitular) {
        Object.assign(estado, {
          encontrado: true,
          origen: 'TITULAR',
          idAsignatura: null,
          idDocente: seccion.idDocenteTitular,
          asignatura: '',
          docente: seccion.docenteTitular,
        })
      }
    } catch (e) {
      if (actual !== solicitud) return
      estado.error = e?.message || 'No se pudo cargar la sección del estudiante.'
    } finally {
      if (actual === solicitud) estado.cargando = false
    }
  }

  const resolver = () => {
    limpiar()

    const est = getEstudiante()
    const fecha = getFecha()
    const hora = getHora()
    if (!est || !fecha || !hora) return

    const actual = solicitud
    estado.cargando = true

    if (est.nivel === 'ESCUELA') {
      resolverTitular(est, actual)
      return
    }

    if (est.nivel !== 'LICEO') {
      estado.cargando = false
      return
    }

    // Pequeña espera: mientras se escribe la hora no se consulta en cada tecla.
    temporizador = setTimeout(async () => {
      try {
        const clase = await consultarHorarioEstudiante({
          idEstudiante: est.id,
          fecha,
          hora,
        })
        if (actual !== solicitud) return
        if (clase.encontrado) {
          Object.assign(estado, {
            encontrado: true,
            origen: 'HORARIO',
            idAsignatura: clase.idAsignatura,
            idDocente: clase.idDocente,
            asignatura: clase.asignatura,
            docente: clase.docente,
            bloque: clase.bloque,
            horaInicio: clase.horaInicio,
            horaFin: clase.horaFin,
          })
        }
      } catch (e) {
        if (actual !== solicitud) return
        estado.error = e?.message || 'No se pudo consultar el horario.'
      } finally {
        if (actual === solicitud) estado.cargando = false
      }
    }, 300)
  }

  return { estado, resolver, limpiar, cancelar }
}

const derivadorAlta = crearDerivador({
  getEstudiante: () => estudiante.value,
  getFecha: () => form.fecha,
  getHora: () => form.hora,
})
const derivado = derivadorAlta.estado
const resolverAsignacion = derivadorAlta.resolver

watch([() => form.fecha, () => form.hora], () => {
  if (estudiante.value) resolverAsignacion()
})

// ───────────── Búsqueda de estudiante ─────────────
const buscar = async () => {
  clearTimeout(temporizadorBusqueda)
  const texto = termino.value.trim()
  if (!texto) {
    errorBusqueda.value = 'Escribe la cédula, el nombre o el apellido del estudiante.'
    return
  }

  const solicitud = ++solicitudBusqueda
  buscando.value = true
  errorBusqueda.value = ''
  resultados.value = []

  try {
    const { items } = await buscarEstudiantes(texto, {
      size: 10,
      nivel: nivelSesion.value || undefined,
    })
    if (solicitud !== solicitudBusqueda) return

    if (!items.length) {
      errorBusqueda.value = 'No se encontró ningún estudiante con ese dato.'
      return
    }
    if (items.length === 1) {
      seleccionarEstudiante(items[0])
      return
    }
    resultados.value = items
  } catch (e) {
    if (solicitud !== solicitudBusqueda) return
    errorBusqueda.value = e?.message || 'No se pudo buscar al estudiante.'
  } finally {
    if (solicitud === solicitudBusqueda) buscando.value = false
  }
}

// Búsqueda reactiva: se dispara sola 350 ms después de dejar de escribir.
// La asignación de la cédula al seleccionar un estudiante no cuenta como
// búsqueda nueva; si el usuario edita el texto, se descarta la selección previa.
watch(termino, () => {
  clearTimeout(temporizadorBusqueda)
  const texto = termino.value.trim()
  if (estudiante.value) {
    if (texto === estudiante.value.cedula) return
    estudiante.value = null
    pasesEstudiante.value = []
    errorPasesEst.value = ''
    representante.datos = null
    representante.error = ''
  }
  if (texto.length < 2) return
  temporizadorBusqueda = setTimeout(() => {
    temporizadorBusqueda = null
    buscar()
  }, 350)
})

const seleccionarEstudiante = (est) => {
  estudiante.value = est
  termino.value = est.cedula
  resultados.value = []
  errorBusqueda.value = ''
  error.value = ''
  exito.value = ''
  ahora()
  resolverAsignacion()
  cargarPasesEstudiante(est.id)
  cargarRepresentante(est.idRepresentante)
}

const nuevaBusqueda = () => {
  derivadorAlta.cancelar()
  solicitudBusqueda += 1
  termino.value = ''
  resultados.value = []
  estudiante.value = null
  pasesEstudiante.value = []
  errorPasesEst.value = ''
  representante.datos = null
  representante.error = ''
  errorBusqueda.value = ''
  error.value = ''
  exito.value = ''
  derivadorAlta.limpiar()
  reiniciarFormulario()
}

const reiniciarFormulario = () => {
  form.tipo = 'ENTRADA'
  form.motivo = motivosPorTipo.ENTRADA[0]
  form.autorizador = ''
  ahora()
  if (estudiante.value) resolverAsignacion()
}

// ───────────── Límites y alertas ─────────────
const pasesDelTipoMes = computed(() => {
  if (!estudiante.value) return 0
  const mes = String(form.fecha || hoyISO()).slice(0, 7)
  return pasesEstudiante.value.filter(
    (pase) => pase.tipo === form.tipo && pase.mes === mes,
  ).length
})
const requiereAutorizacion = computed(() => pasesDelTipoMes.value >= LIMITE_PASES)
const nivelAlerta = computed(() =>
  pasesDelTipoMes.value >= LIMITE_PASES
    ? 'bad'
    : pasesDelTipoMes.value === LIMITE_PASES - 1
      ? 'warn'
      : 'ok',
)
const nivelCls = {
  ok: 'bg-[#ccd5ae] text-[#233E47]',
  warn: 'bg-[#fdebc0] text-[#6b4200]',
  bad: 'bg-[#fbd5d2] text-[#8a1c14]',
}

// El bloqueo se muestra como toast flotante para no alterar el alto de la tarjeta.
const toastBloqueoDescartado = ref(false)
const mostrarToastBloqueo = computed(
  () =>
    Boolean(estudiante.value) &&
    nivelAlerta.value === 'bad' &&
    !toastBloqueoDescartado.value,
)
let temporizadorToast
watch(
  [estudiante, () => form.tipo, () => form.fecha, pasesDelTipoMes],
  () => {
    toastBloqueoDescartado.value = false
  },
)
watch(mostrarToastBloqueo, (visible) => {
  clearTimeout(temporizadorToast)
  if (visible) {
    temporizadorToast = setTimeout(() => {
      toastBloqueoDescartado.value = true
    }, 10000)
  }
})

// ───────────── Registro ─────────────
const registrar = async () => {
  if (!estudiante.value) return
  error.value = ''

  if (!form.motivo) {
    error.value = 'Selecciona el motivo del pase.'
    return
  }
  if (requiereAutorizacion.value && !form.autorizador.trim()) {
    error.value =
      'El cuarto pase del mes requiere el nombre del directivo que lo autoriza.'
    return
  }

  guardando.value = true
  try {
    await crearPase({
      idEstudiante: estudiante.value.id,
      idDocente: derivado.idDocente,
      idAsignatura: derivado.idAsignatura,
      tipo: form.tipo,
      motivo: form.motivo,
      fecha: form.fecha,
      hora: form.hora,
      autorizador: requiereAutorizacion.value ? form.autorizador.trim() : '',
    })

    exito.value = `Pase registrado para ${nomEst(estudiante.value)}.`
    clearTimeout(temporizadorExito)
    temporizadorExito = setTimeout(() => (exito.value = ''), 5000)

    await Promise.all([
      cargarPasesEstudiante(estudiante.value.id),
      refrescarHistorial(),
    ])
    reiniciarFormulario()
  } catch (e) {
    error.value = e?.message || 'No se pudo registrar el pase.'
  } finally {
    guardando.value = false
  }
}

// ═════════════ SECCIÓN 2: Historial ═════════════
const datos = reactive({ pases: [] })
const filtroTexto = ref('')
const filtroTipo = ref('')
const filtroMotivo = ref('')
const paginaCliente = ref(1)

const pasesApi = useRecursoPaginado({
  listar: (args) =>
    listarPases({ ...args, tipo: filtroTipo.value || undefined }),
  listarTodos: (args) =>
    listarTodosPases({ ...args, tipo: filtroTipo.value || undefined }),
  getNivel: () => nivelSesion.value || '',
  asignar: (items) => {
    datos.pases = items
  },
  porDefecto: 10,
})
const api = pasesApi.estado

const busqueda = computed(() => norm(filtroTexto.value).trim())
const filtrando = computed(() => busqueda.value !== '' || filtroMotivo.value !== '')
const cargando = computed(() => api.loading || api.cargandoTodos)

const coincideTexto = (pase) => {
  const texto = norm(`${pase.estudiante} ${pase.cedula}`)
  return texto.includes(busqueda.value)
}

const filtrados = computed(() =>
  filtrando.value
    ? api.todos.filter(
        (pase) =>
          coincideTexto(pase) &&
          (!filtroMotivo.value || pase.motivo === filtroMotivo.value),
      )
    : [],
)
const buscandoTodos = computed(() => filtrando.value && !api.todosListo)

// Paginación del servidor salvo cuando hay filtros de cliente.
const totalFiltrado = computed(() =>
  filtrando.value ? filtrados.value.length : api.total,
)
const totalPaginas = computed(() =>
  Math.max(1, Math.ceil(totalFiltrado.value / api.size)),
)
const pg = computed(() =>
  Math.min(filtrando.value ? paginaCliente.value : api.page, totalPaginas.value),
)
const filasPagina = computed(() => {
  if (!filtrando.value) return datos.pases
  const inicio = (pg.value - 1) * api.size
  return filtrados.value.slice(inicio, inicio + api.size)
})
const desde = computed(() =>
  totalFiltrado.value ? (pg.value - 1) * api.size + 1 : 0,
)
const hasta = computed(() => Math.min(pg.value * api.size, totalFiltrado.value))

const irPagina = (n) => {
  const destino = Math.min(Math.max(1, n), totalPaginas.value)
  if (filtrando.value) {
    paginaCliente.value = destino
    return
  }
  if (destino !== api.page) pasesApi.cargar(destino)
}

async function refrescarHistorial() {
  await pasesApi.refrescar({ conTodos: filtrando.value })
}

watch(filtroTexto, () => {
  paginaCliente.value = 1
  if (filtrando.value && !api.todosListo && !api.cargandoTodos) {
    pasesApi.cargarTodos()
  }
})
watch(filtroMotivo, () => {
  paginaCliente.value = 1
  if (filtrando.value && !api.todosListo && !api.cargandoTodos) {
    pasesApi.cargarTodos()
  }
})
watch(filtroTipo, () => {
  paginaCliente.value = 1
  pasesApi.reiniciar()
  pasesApi.cargar(1)
  if (filtrando.value) pasesApi.cargarTodos()
})
watch(
  () => api.size,
  () => {
    paginaCliente.value = 1
    pasesApi.cargar(1)
  },
)

// ═════════════ SECCIÓN 3: Detalle del pase ═════════════
const detalle = reactive({
  abierto: false,
  pase: null,
  cargando: false,
  error: '',
  estudiante: null,
  representante: null,
})
const estudiantesCache = new Map()
const representantesCache = new Map()

const obtenerEstudianteDetalle = async (id) => {
  if (!estudiantesCache.has(id)) estudiantesCache.set(id, await obtenerEstudiante(id))
  return estudiantesCache.get(id)
}

const obtenerRepresentanteDetalle = async (id) => {
  if (!representantesCache.has(id)) {
    representantesCache.set(id, await obtenerRepresentante(id))
  }
  return representantesCache.get(id)
}

const verPase = async (pase) => {
  Object.assign(detalle, {
    abierto: true,
    pase,
    cargando: true,
    error: '',
    estudiante: null,
    representante: null,
  })

  try {
    const est = await obtenerEstudianteDetalle(pase.idEstudiante)
    detalle.estudiante = est
    if (est.idRepresentante) {
      detalle.representante = await obtenerRepresentanteDetalle(est.idRepresentante)
    }
  } catch (e) {
    detalle.error = e?.message || 'No se pudieron cargar los datos del estudiante.'
  } finally {
    detalle.cargando = false
  }
}

const cerrarDetalle = () => {
  detalle.abierto = false
  detalle.pase = null
  archivo.error = ''
}

// ═════════════ SECCIÓN 4: Edición ═════════════
const edicion = reactive({
  abierto: false,
  cargando: false,
  guardando: false,
  error: '',
  pase: null,
  estudiante: null,
  pasesMes: [],
  form: { tipo: 'ENTRADA', motivo: 'Retardo', fecha: '', hora: '', autorizador: '' },
})

const derivadorEdicion = crearDerivador({
  getEstudiante: () => edicion.estudiante,
  getFecha: () => edicion.form.fecha,
  getHora: () => edicion.form.hora,
})
const derivadoEdicion = derivadorEdicion.estado

const motivosEdicion = computed(() => motivosPorTipo[edicion.form.tipo] ?? [])

watch(
  () => edicion.form.tipo,
  (tipo) => {
    edicion.form.motivo = motivosPorTipo[tipo]?.[0] ?? ''
    edicion.form.autorizador = ''
  },
)

watch([() => edicion.form.fecha, () => edicion.form.hora], () => {
  if (edicion.abierto && edicion.estudiante) derivadorEdicion.resolver()
})

// Conteo del mes excluyendo el propio pase: el backend usa el mismo criterio
// al validar la edición.
const pasesEdicionTipoMes = computed(() => {
  if (!edicion.pase) return 0
  const mes = String(edicion.form.fecha || '').slice(0, 7)
  return edicion.pasesMes.filter(
    (item) => item.id !== edicion.pase.id && item.tipo === edicion.form.tipo && item.mes === mes,
  ).length
})
const requiereAutorizacionEdicion = computed(
  () => pasesEdicionTipoMes.value >= LIMITE_PASES,
)

const avisarExito = (mensaje) => {
  exito.value = mensaje
  clearTimeout(temporizadorExito)
  temporizadorExito = setTimeout(() => (exito.value = ''), 5000)
}

const refrescarTrasCambio = async () => {
  const tareas = [refrescarHistorial()]
  if (estudiante.value) tareas.push(cargarPasesEstudiante(estudiante.value.id))
  await Promise.all(tareas)
}

const abrirEdicion = async (pase) => {
  if (detalle.abierto) cerrarDetalle()

  Object.assign(edicion, {
    abierto: true,
    cargando: true,
    guardando: false,
    error: '',
    pase,
    estudiante: null,
    pasesMes: [],
  })
  Object.assign(edicion.form, {
    tipo: pase.tipo,
    motivo: pase.motivo || motivosPorTipo[pase.tipo]?.[0] || '',
    fecha: pase.fechaISO,
    hora: pase.hora || horaActual(),
    autorizador: pase.autorizador || '',
  })
  derivadorEdicion.limpiar()

  try {
    const [est, { items }] = await Promise.all([
      obtenerEstudianteDetalle(pase.idEstudiante),
      listarTodosPases({ idEstudiante: pase.idEstudiante }),
    ])
    if (!edicion.abierto) return
    edicion.estudiante = est
    edicion.pasesMes = items
    derivadorEdicion.resolver()
  } catch (e) {
    edicion.error = e?.message || 'No se pudieron cargar los datos del pase.'
  } finally {
    edicion.cargando = false
  }
}

const cerrarEdicion = () => {
  derivadorEdicion.cancelar()
  Object.assign(edicion, {
    abierto: false,
    cargando: false,
    guardando: false,
    error: '',
    pase: null,
    estudiante: null,
    pasesMes: [],
  })
}

const guardarEdicion = async () => {
  if (!edicion.pase) return
  edicion.error = ''

  if (!edicion.form.motivo) {
    edicion.error = 'Selecciona el motivo del pase.'
    return
  }
  if (requiereAutorizacionEdicion.value && !edicion.form.autorizador.trim()) {
    edicion.error = 'El cuarto pase del mes requiere el nombre del directivo que lo autoriza.'
    return
  }

  edicion.guardando = true
  try {
    const actualizado = await actualizarPase(edicion.pase.id, {
      tipo: edicion.form.tipo,
      motivo: edicion.form.motivo,
      fecha: edicion.form.fecha,
      hora: edicion.form.hora,
      idDocente: derivadoEdicion.idDocente,
      idAsignatura: derivadoEdicion.idAsignatura,
      autorizador: requiereAutorizacionEdicion.value ? edicion.form.autorizador.trim() : '',
    })

    if (detalle.abierto && detalle.pase?.id === actualizado.id) {
      detalle.pase = actualizado
    }

    cerrarEdicion()
    await refrescarTrasCambio()
    avisarExito('Pase actualizado correctamente.')
  } catch (e) {
    edicion.error = e?.message || 'No se pudo actualizar el pase.'
  } finally {
    edicion.guardando = false
  }
}

// ═════════════ SECCIÓN 5: Baja ═════════════
const baja = reactive({ abierta: false, pase: null, error: '', eliminando: false })

const pedirBaja = (pase) => {
  Object.assign(baja, { abierta: true, pase, error: '', eliminando: false })
}

const cerrarBaja = () => {
  Object.assign(baja, { abierta: false, pase: null, error: '', eliminando: false })
}

const confirmarBaja = async () => {
  if (!baja.pase) return
  baja.error = ''
  baja.eliminando = true

  try {
    const id = baja.pase.id
    await eliminarPase(id)
    if (detalle.abierto && detalle.pase?.id === id) cerrarDetalle()
    cerrarBaja()
    await refrescarTrasCambio()
    avisarExito('Pase dado de baja correctamente.')
  } catch (e) {
    baja.error = e?.message || 'No se pudo dar de baja el pase.'
  } finally {
    baja.eliminando = false
  }
}

// ═════════════ SECCIÓN 6: Adjunto del pase ═════════════
const archivo = reactive({ subiendo: false, quitando: false, error: '' })
const MIME_PERMITIDOS = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
const TAMANO_MAXIMO = 5 * 1024 * 1024

const seleccionarArchivo = async (event) => {
  const entrada = event.target
  const file = entrada.files?.[0]
  entrada.value = ''
  if (!file || !detalle.pase) return

  archivo.error = ''
  if (!MIME_PERMITIDOS.includes(file.type)) {
    archivo.error = 'Solo se permiten imágenes JPG, PNG o WEBP.'
    return
  }
  if (file.size > TAMANO_MAXIMO) {
    archivo.error = 'La imagen supera el tamaño máximo de 5 MB.'
    return
  }

  archivo.subiendo = true
  try {
    const actualizado = await subirArchivoPase(detalle.pase.id, file)
    if (detalle.pase?.id === actualizado.id) detalle.pase = actualizado
    await refrescarTrasCambio()
    avisarExito('Adjunto actualizado correctamente.')
  } catch (e) {
    archivo.error = e?.message || 'No se pudo subir el adjunto.'
  } finally {
    archivo.subiendo = false
  }
}

const descargarAdjunto = async () => {
  if (!detalle.pase) return
  archivo.error = ''
  try {
    const { blob, nombre } = await descargarArchivoPase(detalle.pase.id)
    const url = URL.createObjectURL(blob)
    const enlace = document.createElement('a')
    enlace.href = url
    enlace.download = nombre || detalle.pase.archivoNombre || `pase-${detalle.pase.id}`
    document.body.appendChild(enlace)
    enlace.click()
    enlace.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    archivo.error = e?.message || 'No se pudo descargar el adjunto.'
  }
}

const quitarAdjunto = async () => {
  if (!detalle.pase) return
  archivo.error = ''
  archivo.quitando = true
  try {
    await quitarArchivoPase(detalle.pase.id)
    detalle.pase = {
      ...detalle.pase,
      archivoUrl: '',
      archivoNombre: '',
      archivoMime: '',
      archivoTamano: null,
    }
    await refrescarTrasCambio()
    avisarExito('Adjunto quitado correctamente.')
  } catch (e) {
    archivo.error = e?.message || 'No se pudo quitar el adjunto.'
  } finally {
    archivo.quitando = false
  }
}

const alPresionarTecla = (event) => {
  if (event.key !== 'Escape') return
  if (baja.abierta) cerrarBaja()
  else if (edicion.abierto) cerrarEdicion()
  else if (detalle.abierto) cerrarDetalle()
}

// ───────────── Clases reutilizables ─────────────
const inp =
  'clay-field h-11 w-full rounded-xl border border-[#b8c2d3] bg-white px-3 text-[15px] text-[#1b2a2f] placeholder:text-[#41515b] transition focus:border-[#233E47] focus:outline-none focus:ring-4 focus:ring-[#b4d0f8]/70 disabled:cursor-not-allowed disabled:bg-[#f1f4f0]'
const ro =
  'clay-field h-11 w-full rounded-xl border border-[#dbe2d0] bg-[#f1f4f0] px-3 text-[15px] font-semibold text-[#233E47]'
const lbl = 'text-sm font-semibold text-[#233E47]'
const card =
  'clay-card flex w-full flex-col p-5 md:p-6'
const btnP =
  'clay-btn inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[#233E47] px-5 text-[15px] font-bold text-white transition hover:bg-[#1a2f36] focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[#91a5c9] disabled:cursor-not-allowed disabled:opacity-50'
const btnS =
  'clay-btn clay-btn-soft inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-[#233E47] bg-white px-5 text-[15px] font-bold text-[#233E47] transition hover:bg-[#eef3fb] focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[#91a5c9] disabled:cursor-not-allowed disabled:opacity-50'
const th =
  'whitespace-nowrap bg-[#eef2f6] px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-[#34434b]'
const td =
  'whitespace-nowrap border-t border-[#e3e8ee] px-3 py-2.5 text-sm text-[#1b2a2f]'
// Tabla compacta de pases del estudiante: cabe sin scroll horizontal en columnas estrechas.
const thPases =
  'bg-[#eef2f6] px-2 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-[#34434b]'
const tdPases =
  'border-t border-[#e3e8ee] px-2 py-2 text-xs text-[#1b2a2f] align-top'
const tipoCls = (tipo) =>
  tipo === 'ENTRADA'
    ? 'bg-[#ccd5ae] text-[#233E47]'
    : 'bg-[#b4d0f8] text-[#233E47]'

onMounted(() => {
  pasesApi.cargar(1)
  window.addEventListener('keydown', alPresionarTecla)
})

onBeforeUnmount(() => {
  derivadorAlta.cancelar()
  derivadorEdicion.cancelar()
  clearTimeout(temporizadorExito)
  clearTimeout(temporizadorToast)
  clearTimeout(temporizadorBusqueda)
  window.removeEventListener('keydown', alPresionarTecla)
})
</script>

<template>
  <div class="pases-page -m-6 min-h-[calc(100vh-4rem)] p-6 md:-m-8 md:p-8">
    <div class="pases-mesh" aria-hidden="true"></div>
    <div class="relative z-10 mx-auto flex w-full max-w-[1600px] flex-col gap-6 font-sans text-[#1b2a2f]">
      <!-- Bento grid: el formulario ocupa dos filas, las tarjetas laterales una y el historial todo el ancho -->
      <div class="grid grid-cols-1 items-stretch gap-6 md:grid-cols-12">
        <!-- ═══════════ SECCIÓN 1: Buscar estudiante y registrar pase ═══════════ -->
        <section :class="[card, 'relative z-20 md:col-span-7 md:row-span-2']" aria-labelledby="t1">
          <header class="mb-5">
            <h2 id="t1" class="text-xl font-bold text-[#233E47]">Registrar pase</h2>
            <p class="text-sm text-[#34434b]">Busca al estudiante y completa los datos del pase.</p>
          </header>

        <form @submit.prevent="buscar" class="flex flex-wrap items-end gap-3">
          <div class="min-w-[12rem] flex-1">
            <label for="cedula" :class="lbl">Cédula, nombre o apellido</label>
            <div class="relative mt-1.5">
              <svg aria-hidden="true" class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#41515b]" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" />
              </svg>
              <input v-model="termino" id="cedula" type="search" autocomplete="off" autofocus placeholder="Buscar estudiante" class="clay-field h-12 w-full rounded-xl border-2 border-[#233E47] bg-white pl-11 pr-4 text-lg font-medium placeholder:text-[#41515b] focus:outline-none focus:ring-4 focus:ring-[#b4d0f8]/70"/>
              <!-- Desplegable: flota sobre el formulario sin aumentar su altura. -->
              <ul v-if="resultados.length" class="absolute left-0 right-0 top-full z-30 mt-2 max-h-[19rem] divide-y divide-[#e3e8ee] overflow-y-auto rounded-xl border border-[#e3e8ee] bg-white shadow-xl">
                <li v-for="r in resultados" :key="r.id">
                  <button type="button" class="flex w-full items-center justify-between gap-2 px-3 py-2 text-left transition hover:bg-[#eef3fb]" @click="seleccionarEstudiante(r)">
                    <span class="min-w-0">
                      <span class="line-clamp-2 text-sm font-semibold text-[#1b2a2f]">{{ nomEst(r) }}</span>
                      <span class="block truncate text-xs text-[#34434b]">{{ fmtCedula(r.cedula) }} · {{ gradoSeccion(r) }} · {{ etiquetaNivel(r.nivel) }}</span>
                    </span>
                    <span class="shrink-0 text-xs font-semibold text-[#3454c5]">Seleccionar</span>
                  </button>
                </li>
              </ul>
            </div>
          </div>
          <div class="flex shrink-0 gap-2">
            <button type="submit" :class="btnP" class="!h-12" :disabled="buscando">
              {{ buscando ? 'Buscando…' : 'Buscar' }}
            </button>
            <button v-if="estudiante || termino" type="button" @click="nuevaBusqueda" :class="btnS" class="!h-12">Limpiar</button>
          </div>
        </form>

        <p v-if="errorBusqueda" role="alert" class="mt-3 rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">{{ errorBusqueda }}</p>
        <p v-if="error" role="alert" class="mt-3 rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">{{ error }}</p>
        <p v-if="exito" role="status" class="mt-3 rounded-xl bg-[#ccd5ae] px-4 py-3 text-sm font-semibold text-[#233E47]">✔ {{ exito }}</p>

        <div v-if="estudiante && nivelAlerta === 'warn'" class="mt-3 rounded-xl bg-[#fdebc0] px-4 py-3 text-sm font-semibold text-[#6b4200]">
          Advertencia: lleva {{ pasesDelTipoMes }} pases de {{ tipoLabel(form.tipo).toLowerCase() }} este mes. El próximo necesitará autorización de un directivo.
        </div>
        <div v-else-if="estudiante && pasesDelTipoMes === 1" class="mt-3 rounded-xl bg-[#eef3fb] px-4 py-3 text-sm font-semibold text-[#233E47]">
          Este será el segundo pase de {{ tipoLabel(form.tipo).toLowerCase() }} del mes. Después le quedará solo 1 de los {{ LIMITE_PASES }} permitidos.
        </div>

        <form @submit.prevent="registrar" class="mt-6">
          <fieldset :disabled="!estudiante || guardando" class="flex flex-col gap-5 disabled:opacity-60">
            <legend class="sr-only">Datos del pase</legend>
            <div class="grid gap-4 md:grid-cols-2">
              <div class="md:col-span-2">
                <label for="nombre" :class="lbl">Nombre y apellido del estudiante</label>
                <input id="nombre" :value="estudiante ? nomEst(estudiante) : ''" placeholder="Se completa al buscar" readonly :class="[ro, 'mt-1.5']"/>
              </div>
              <div>
                <label for="grado" :class="lbl">Grado y sección</label>
                <input id="grado" :value="estudiante ? gradoSeccion(estudiante) : ''" placeholder="—" readonly :class="[ro, 'mt-1.5']"/>
              </div>
              <div>
                <label for="nivel" :class="lbl">Nivel</label>
                <input id="nivel" :value="estudiante ? etiquetaNivel(estudiante.nivel) : ''" placeholder="—" readonly :class="[ro, 'mt-1.5']"/>
              </div>
            </div>

            <fieldset>
              <legend :class="lbl">Tipo y motivo</legend>
              <div class="mt-1.5 flex flex-wrap items-center gap-x-6 gap-y-3">
                <div class="flex flex-wrap items-center gap-2" role="group" aria-label="Tipo de pase">
                  <button
                    v-for="t in TIPOS"
                    :key="t"
                    type="button"
                    class="clay-tipo-btn"
                    :class="{ 'is-active': form.tipo === t }"
                    :aria-pressed="form.tipo === t"
                    @click="form.tipo = t"
                  >
                    {{ tipoLabel(t) }}
                  </button>
                </div>
                <div class="flex flex-wrap items-center gap-x-4 gap-y-2 border-l border-[#d5dbe6] pl-6 max-sm:border-0 max-sm:pl-0">
                  <label v-for="mo in motivosDelTipo" :key="mo" class="inline-flex cursor-pointer items-center gap-2 text-sm font-semibold text-[#34434b]">
                    <input type="radio" name="motivo" :value="mo" v-model="form.motivo" class="clay-radio" required/>
                    <span>{{ mo }}</span>
                  </label>
                </div>
              </div>
            </fieldset>

            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label for="fecha" :class="lbl">Fecha</label>
                <input v-model="form.fecha" id="fecha" type="date" required :class="[inp, 'mt-1.5']"/>
              </div>
              <div>
                <label for="hora" :class="lbl">Hora</label>
                <input v-model="form.hora" id="hora" type="time" required :class="[inp, 'mt-1.5']"/>
              </div>
            </div>

            <!-- Asignatura y docente se derivan del horario o del titular de
                 la sección; no se editan a mano. -->
            <div>
              <span :class="lbl">
                Asignatura y docente
                <span class="font-normal text-[#41515b]">(automático)</span>
              </span>
              <div class="mt-1.5 grid min-h-[3.5rem] gap-x-6 gap-y-1 rounded-xl border border-[#dbe2d0] bg-[#f1f4f0] px-3 py-2.5 text-[15px] lg:grid-cols-2" aria-live="polite">
                <p v-if="!estudiante" class="text-sm text-[#41515b] lg:col-span-2">Se completa al buscar al estudiante.</p>
                <p v-else-if="derivado.cargando" class="text-sm text-[#34434b] lg:col-span-2">Consultando el horario…</p>
                <template v-else-if="derivado.encontrado && derivado.origen === 'HORARIO'">
                  <p class="font-semibold text-[#233E47]">{{ derivado.asignatura || 'Asignatura sin nombre' }}</p>
                  <p class="text-sm text-[#34434b]">
                    {{ derivado.docente || 'Docente sin nombre' }}
                    <span v-if="derivado.bloque"> · {{ derivado.bloque }}</span>
                    <span v-if="derivado.horaInicio && derivado.horaFin"> ({{ derivado.horaInicio }}–{{ derivado.horaFin }})</span>
                  </p>
                </template>
                <template v-else-if="derivado.encontrado && derivado.origen === 'TITULAR'">
                  <p class="font-semibold text-[#233E47]">{{ derivado.docente || 'Docente sin nombre' }}</p>
                  <p class="text-sm text-[#34434b]">Docente titular de la sección · Escuela</p>
                </template>
                <template v-else-if="derivado.error">
                  <p class="text-sm font-semibold text-[#8a1c14]">{{ derivado.error }}</p>
                  <p class="text-sm text-[#34434b]">El pase se puede registrar sin asignatura ni docente.</p>
                  <button type="button" class="mt-1 text-sm font-semibold text-[#3454c5] hover:underline lg:col-span-2" @click="resolverAsignacion">Reintentar</button>
                </template>
                <p v-else-if="estudiante.nivel === 'ESCUELA'" class="text-sm text-[#34434b] lg:col-span-2">
                  La sección no tiene docente titular; el pase se registrará sin docente.
                </p>
                <p v-else class="text-sm text-[#34434b] lg:col-span-2">
                  Sin clase registrada para ese día y hora; el pase se registrará sin asignatura ni docente.
                </p>
              </div>
            </div>

            <!-- Solo se pide cuando el estudiante ya completó los 3 pases del mes. -->
            <div v-if="requiereAutorizacion" class="grid gap-4 sm:grid-cols-2">
              <div class="sm:col-span-2">
                <label for="autoriza" :class="lbl">Autorizado por el directivo</label>
                <input v-model="form.autorizador" id="autoriza" list="autoridades" placeholder="Nombre del directivo" required :class="[inp, 'mt-1.5']"/>
              </div>
            </div>

            <button type="submit" :class="btnP" class="self-center" :disabled="guardando">
              <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M5 12l5 5L20 7" />
              </svg>
              {{ guardando ? 'Registrando…' : 'Registrar pase' }}
            </button>
          </fieldset>
        </form>
      </section>

        <!-- ═══════════ SECCIÓN 2: Pases del estudiante ═══════════ -->
        <section :class="[card, 'md:col-span-5']" aria-labelledby="t2">
            <header class="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 id="t2" class="text-xl font-bold text-[#233E47]">Pases del estudiante</h2>
                <p v-if="estudiante" class="text-sm text-[#34434b]">
                  {{ nomEst(estudiante) }} · {{ fmtCedula(estudiante.cedula) }} · {{ gradoSeccion(estudiante) }} · {{ etiquetaNivel(estudiante.nivel) }}
                </p>
              </div>
              <span v-if="estudiante" :class="['rounded-full px-3 py-1 text-sm font-bold', nivelCls[nivelAlerta]]">
                Pases de {{ tipoLabel(form.tipo).toLowerCase() }} este mes: {{ pasesDelTipoMes }} de {{ LIMITE_PASES }}
              </span>
            </header>

            <div v-if="!estudiante" class="clay-inset flex min-h-[10rem] flex-1 flex-col items-center justify-center gap-2 rounded-xl bg-[#f3f6f1] px-4 py-8 text-center text-[#34434b]">
              <svg aria-hidden="true" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#34434b" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <rect x="5" y="3" width="14" height="18" rx="2" /><path d="M9 8h6M9 12h6M9 16h3" />
              </svg>
              <p class="font-semibold text-[#233E47]">Aún no hay un estudiante seleccionado</p>
              <p class="text-sm">Busca por cédula, nombre o apellido para ver sus pases.</p>
            </div>

            <div v-else class="flex min-h-0 flex-1 flex-col gap-3">
          <!-- Pases del estudiante -->
          <div class="flex min-h-0 min-w-0 flex-col">
            <h3 class="mb-2 text-base font-bold text-[#233E47]">Pases registrados ({{ pasesEstudiante.length }})</h3>

            <p v-if="cargandoPasesEst" class="clay-inset flex flex-1 items-center justify-center rounded-xl bg-[#f3f6f1] px-4 py-8 text-center text-sm text-[#34434b]">Cargando pases…</p>
            <p v-else-if="errorPasesEst" class="rounded-xl bg-[#fbd5d2] px-4 py-4 text-center text-sm font-semibold text-[#8a1c14]">{{ errorPasesEst }}</p>
            <div v-else-if="pasesEstudiante.length" class="clay-inset min-h-0 flex-1 overflow-auto rounded-xl border border-[#e3e8ee]">
              <table class="w-full table-fixed border-collapse">
                <colgroup>
                  <col class="w-[20%]" /><col class="w-[14%]" /><col class="w-[24%]" /><col class="w-[14%]" /><col class="w-[28%]" />
                </colgroup>
                <thead class="sticky top-0 z-10">
                  <tr>
                    <th :class="thPases">Fecha</th><th :class="thPases">Hora</th><th :class="thPases">Motivo</th><th :class="thPases">Tipo</th><th :class="[thPases, 'text-right']">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="p in pasesEstudiante" :key="p.id">
                    <td :class="tdPases">{{ fmtFecha(p.fechaISO) }}</td>
                    <td :class="tdPases">{{ p.hora || '—' }}</td>
                    <td :class="tdPases">{{ p.motivo || '—' }}</td>
                    <td :class="tdPases"><span :class="['inline-block rounded-full px-2 py-0.5 text-[11px] font-bold', tipoCls(p.tipo)]">{{ tipoLabel(p.tipo) }}</span></td>
                    <td :class="[tdPases, 'text-right']">
                      <div class="flex flex-wrap justify-end gap-x-2 gap-y-0.5 text-[11px] font-semibold">
                        <button type="button" class="text-[#3454c5] hover:underline" @click="verPase(p)">Ver</button>
                        <button type="button" class="text-[#233E47] hover:underline" @click="abrirEdicion(p)">Editar</button>
                        <button type="button" class="text-[#8a1c14] hover:underline" @click="pedirBaja(p)">Eliminar</button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else class="clay-inset flex min-h-[8rem] flex-1 items-center justify-center rounded-xl bg-[#f3f6f1] px-4 py-8 text-center text-sm text-[#34434b]">Este estudiante aún no tiene pases registrados.</p>
          </div>
            </div>
          </section>

        <!-- ═══════════ SECCIÓN 3: Datos del representante ═══════════ -->
        <section :class="[card, 'md:col-span-5']" aria-labelledby="rep-titulo">
            <header class="mb-5">
              <h2 id="rep-titulo" class="text-xl font-bold text-[#233E47]">Datos del representante</h2>
              <p v-if="estudiante" class="text-sm text-[#34434b]">{{ nomEst(estudiante) }}</p>
            </header>

            <div v-if="!estudiante" class="clay-inset flex min-h-[8rem] flex-1 flex-col items-center justify-center gap-2 rounded-xl bg-[#f3f6f1] px-4 py-8 text-center text-[#34434b]">
              <svg aria-hidden="true" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#34434b" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
              </svg>
              <p class="font-semibold text-[#233E47]">Aún no hay un estudiante seleccionado</p>
              <p class="text-sm">Busca por cédula, nombre o apellido para ver los datos de su representante.</p>
            </div>

            <template v-else>
              <p v-if="representante.cargando" class="clay-inset flex min-h-[8rem] flex-1 items-center justify-center rounded-xl bg-[#f3f6f1] px-4 py-6 text-center text-sm text-[#34434b]">Cargando representante…</p>
              <p v-else-if="representante.error" class="rounded-xl bg-[#fbd5d2] px-4 py-4 text-center text-sm font-semibold text-[#8a1c14]">{{ representante.error }}</p>
              <template v-else-if="representante.datos">
              <div class="flex items-center gap-3">
                <span class="grid h-14 w-14 flex-none place-items-center rounded-full bg-[#b4d0f8] text-lg font-bold text-[#233E47]">
                  {{ iniciales(nomPersona(representante.datos)) }}
                </span>
                <div>
                  <p class="font-bold text-[#1b2a2f]">{{ nomPersona(representante.datos) }}</p>
                  <span class="mt-0.5 inline-block rounded-full bg-[#ccd5ae] px-2.5 py-0.5 text-xs font-bold text-[#233E47]">Representante</span>
                </div>
              </div>
              <dl class="mt-4 grid grid-cols-1 gap-4 text-sm">
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Teléfono</dt>
                  <dd class="mt-1">{{ representante.datos.telefono || '—' }}</dd>
                </div>
              </dl>
            </template>
            <p v-else class="clay-inset flex min-h-[8rem] flex-1 items-center justify-center rounded-xl bg-[#f3f6f1] px-4 py-6 text-center text-sm text-[#34434b]">
              {{ estudiante.idRepresentante ? 'No se pudo cargar el representante.' : 'El estudiante no tiene un representante registrado.' }}
            </p>
            </template>
        </section>

        <!-- ═══════════ SECCIÓN 4: Historial completo ═══════════ -->
        <section :class="[card, 'md:col-span-12']" aria-labelledby="t3">
        <header class="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="t3" class="text-xl font-bold text-[#233E47]">Historial de pases</h2>
            <p class="text-sm text-[#34434b]">
              {{ totalFiltrado }} {{ totalFiltrado === 1 ? 'pase' : 'pases' }} registrados
              <span v-if="cargando"> · actualizando…</span>
            </p>
          </div>
        </header>

      <div class="mb-4 grid gap-3 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1.3fr)]">
        <input v-model="filtroTexto" type="search" aria-label="Buscar por estudiante o cédula" placeholder="Buscar por estudiante o cédula" :class="inp" />
        <select v-model="filtroTipo" aria-label="Filtrar por tipo" :class="inp">
          <option value="">Todos los tipos</option>
          <option v-for="t in TIPOS" :key="t" :value="t">{{ tipoLabel(t) }}</option>
        </select>
        <select v-model="filtroMotivo" aria-label="Filtrar por motivo" :class="inp">
          <option value="">Todos los motivos</option>
          <option v-for="mo in motivosTodos" :key="mo" :value="mo">{{ mo }}</option>
        </select>
      </div>

      <div class="clay-inset overflow-x-auto rounded-xl border border-[#e3e8ee]">
        <table class="w-full border-collapse">
          <thead>
            <tr>
              <th :class="th">Fecha</th><th :class="th">Hora</th><th :class="th">Estudiante</th><th :class="th">Motivo</th><th :class="th">Docente</th><th :class="th">Tipo</th><th :class="[th, 'text-right']">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in filasPagina" :key="p.id" class="hover:bg-[#f6f9fe]">
              <td :class="td">{{ fmtFecha(p.fechaISO) }}</td>
              <td :class="td">{{ p.hora || '—' }}</td>
              <td :class="[td, 'font-semibold']">{{ p.estudiante || '—' }}</td>
              <td :class="td">{{ p.motivo }}</td>
              <td :class="td">{{ p.docente || '—' }}</td>
              <td :class="td"><span :class="['rounded-full px-2.5 py-0.5 text-xs font-bold', tipoCls(p.tipo)]">{{ tipoLabel(p.tipo) }}</span></td>
              <td :class="[td, 'text-right']">
                <div class="flex justify-end gap-3">
                  <button type="button" class="font-semibold text-[#3454c5] hover:underline" @click="verPase(p)">Ver</button>
                  <button type="button" class="font-semibold text-[#233E47] hover:underline" @click="abrirEdicion(p)">Editar</button>
                  <button type="button" class="font-semibold text-[#8a1c14] hover:underline" @click="pedirBaja(p)">Eliminar</button>
                </div>
              </td>
            </tr>
            <tr v-if="!filasPagina.length">
              <td colspan="7" class="px-4 py-10 text-center text-sm text-[#34434b]">
                <span v-if="buscandoTodos">Cargando la lista para filtrar…</span>
                <span v-else-if="api.error" class="font-semibold text-[#8a1c14]">{{ api.error }}</span>
                <span v-else-if="filtrando">No hay pases que coincidan con los filtros.</span>
                <span v-else>Todavía no hay pases registrados.</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <footer class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-[#34434b]">
        <div class="flex flex-wrap items-center gap-3">
          <span>Mostrando {{ desde }}–{{ hasta }} de {{ totalFiltrado }}</span>
          <label class="flex items-center gap-2">
            Por página
            <select v-model.number="api.size" :class="[inp, '!h-10 !w-auto']" aria-label="Registros por página">
              <option v-for="n in [10, 25, 50, 100]" :key="n" :value="n">{{ n }}</option>
            </select>
          </label>
        </div>
        <div class="flex items-center gap-2">
          <span>Página {{ pg }} de {{ totalPaginas }}</span>
          <button type="button" :class="btnS" class="!h-10 !px-4" :disabled="pg === 1" @click="irPagina(pg - 1)">Anterior</button>
          <button type="button" :class="btnS" class="!h-10 !px-4" :disabled="pg === totalPaginas" @click="irPagina(pg + 1)">Siguiente</button>
        </div>
      </footer>
      </section>
      </div>

    <!-- ═══════════ MODAL: Detalle completo del pase ═══════════ -->
    <div
      v-if="detalle.abierto && detalle.pase"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="cerrarDetalle"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="detalle-pase-titulo"
        class="clay-card w-full max-w-2xl overflow-hidden"
      >
        <header class="flex items-start justify-between gap-4 border-b border-[#e3e8ee] bg-[#f6f9fe] px-6 py-5">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Detalle del pase</p>
            <h2 id="detalle-pase-titulo" class="mt-1 text-xl font-bold text-[#233E47]">
              Pase #{{ detalle.pase.id }}
            </h2>
            <div class="mt-2 flex flex-wrap items-center gap-2">
              <span :class="['rounded-full px-2.5 py-0.5 text-xs font-bold', tipoCls(detalle.pase.tipo)]">
                {{ tipoLabel(detalle.pase.tipo) }}
              </span>
              <span class="text-sm text-[#34434b]">{{ fmtFecha(detalle.pase.fechaISO) }} · {{ detalle.pase.hora || '—' }}</span>
            </div>
          </div>
          <button
            type="button"
            class="grid h-9 w-9 flex-none place-items-center rounded-full text-lg text-[#34434b] transition hover:bg-[#e3e8ee] hover:text-[#233E47]"
            aria-label="Cerrar detalle del pase"
            @click="cerrarDetalle"
          >
            ✕
          </button>
        </header>

        <div class="max-h-[70vh] overflow-y-auto px-6 py-5">
          <p v-if="detalle.cargando" class="mb-4 rounded-xl bg-[#eef3fb] px-4 py-2 text-sm text-[#233E47]">Cargando datos del estudiante…</p>
          <p v-if="detalle.error" role="alert" class="mb-4 rounded-xl bg-[#fbd5d2] px-4 py-2 text-sm font-semibold text-[#8a1c14]">{{ detalle.error }}</p>

          <section aria-labelledby="detalle-estudiante">
            <h3 id="detalle-estudiante" class="text-sm font-bold uppercase tracking-wide text-[#34434b]">Estudiante</h3>
            <dl class="mt-3 grid gap-4 text-sm sm:grid-cols-3">
              <div class="sm:col-span-2">
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Nombre y apellido</dt>
                <dd class="mt-1 font-semibold text-[#1b2a2f]">
                  {{ detalle.estudiante ? nomEst(detalle.estudiante) : detalle.pase.estudiante || '—' }}
                </dd>
              </div>
              <div>
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Cédula</dt>
                <dd class="mt-1 font-semibold text-[#1b2a2f]">
                  {{ fmtCedula(detalle.estudiante?.cedula || detalle.pase.cedula) }}
                </dd>
              </div>
              <div>
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Nivel</dt>
                <dd class="mt-1">{{ etiquetaNivel(detalle.estudiante?.nivel || detalle.pase.nivel) }}</dd>
              </div>
              <div>
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Grado y sección</dt>
                <dd class="mt-1">{{ detalle.estudiante ? gradoSeccion(detalle.estudiante) : '—' }}</dd>
              </div>
              <div>
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Período lectivo</dt>
                <dd class="mt-1">{{ detalle.estudiante?.periodoLectivo || detalle.pase.periodoLectivo || '—' }}</dd>
              </div>
            </dl>
          </section>

          <section class="mt-5 border-t border-[#e3e8ee] pt-5" aria-labelledby="detalle-datos">
            <h3 id="detalle-datos" class="text-sm font-bold uppercase tracking-wide text-[#34434b]">Datos del pase</h3>
            <dl class="mt-3 grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Motivo</dt>
                <dd class="mt-1 font-semibold text-[#1b2a2f]">{{ detalle.pase.motivo }}</dd>
              </div>
              <div>
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Docente</dt>
                <dd class="mt-1">{{ detalle.pase.docente || '—' }}</dd>
              </div>
              <div>
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Asignatura</dt>
                <dd class="mt-1">{{ detalle.pase.asignatura || 'No aplica' }}</dd>
              </div>
              <div>
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Autorizado por</dt>
                <dd class="mt-1">{{ detalle.pase.autorizador || 'No aplica' }}</dd>
              </div>
              <div>
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Registrado por</dt>
                <dd class="mt-1">{{ detalle.pase.usuario || '—' }}</dd>
              </div>
              <div class="sm:col-span-2">
                <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Adjunto</dt>
                <dd class="mt-1 flex flex-col gap-2">
                  <span v-if="detalle.pase.archivoNombre">
                    {{ detalle.pase.archivoNombre }} · {{ fmtTamano(detalle.pase.archivoTamano) }}
                  </span>
                  <span v-else class="text-[#34434b]">Sin adjunto</span>

                  <p v-if="archivo.error" role="alert" class="rounded-lg bg-[#fbd5d2] px-3 py-2 text-xs font-semibold text-[#8a1c14]">
                    {{ archivo.error }}
                  </p>

                  <div class="flex flex-wrap gap-2">
                    <button
                      v-if="detalle.pase.archivoNombre"
                      type="button"
                      :class="btnS"
                      class="!h-9 !px-3 !text-sm"
                      @click="descargarAdjunto"
                    >
                      Descargar
                    </button>
                    <label
                      v-else
                      :class="[btnS, '!h-9 cursor-pointer !px-3 !text-sm']"
                      :aria-disabled="archivo.subiendo"
                    >
                      <input
                        type="file"
                        class="sr-only"
                        accept="image/jpeg,image/png,image/webp"
                        :disabled="archivo.subiendo"
                        @change="seleccionarArchivo"
                      />
                      {{ archivo.subiendo ? 'Subiendo…' : 'Adjuntar imagen' }}
                    </label>
                    <button
                      v-if="detalle.pase.archivoNombre"
                      type="button"
                      :class="btnS"
                      class="!h-9 !px-3 !text-sm !text-[#8a1c14] !border-[#8a1c14]"
                      :disabled="archivo.quitando"
                      @click="quitarAdjunto"
                    >
                      {{ archivo.quitando ? 'Quitando…' : 'Quitar' }}
                    </button>
                  </div>
                </dd>
              </div>
            </dl>
          </section>

          <section class="mt-5 border-t border-[#e3e8ee] pt-5" aria-labelledby="detalle-representante">
            <h3 id="detalle-representante" class="text-sm font-bold uppercase tracking-wide text-[#34434b]">Representante</h3>
            <template v-if="detalle.representante">
              <dl class="mt-3 grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Nombre</dt>
                  <dd class="mt-1 font-semibold text-[#1b2a2f]">{{ nomPersona(detalle.representante) }}</dd>
                </div>
                <div>
                  <dt class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Teléfono</dt>
                  <dd class="mt-1">{{ detalle.representante.telefono || '—' }}</dd>
                </div>
              </dl>
            </template>
            <p v-else class="mt-3 rounded-xl bg-[#f3f6f1] px-4 py-3 text-sm text-[#34434b]">
              {{ detalle.cargando ? 'Cargando representante…' : 'El estudiante no tiene un representante registrado.' }}
            </p>
          </section>
        </div>

        <footer class="flex justify-end border-t border-[#e3e8ee] bg-[#f6f9fe] px-6 py-4">
          <button type="button" :class="btnP" @click="cerrarDetalle">Cerrar</button>
        </footer>
      </div>
    </div>

    <!-- ═══════════ MODAL: Editar pase ═══════════ -->
    <div
      v-if="edicion.abierto && edicion.pase"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="cerrarEdicion"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="editar-pase-titulo"
        class="clay-card w-full max-w-2xl overflow-hidden"
      >
        <header class="flex items-start justify-between gap-4 border-b border-[#e3e8ee] bg-[#f6f9fe] px-6 py-5">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-[#34434b]">Editar pase</p>
            <h2 id="editar-pase-titulo" class="mt-1 text-xl font-bold text-[#233E47]">
              Pase #{{ edicion.pase.id }}
            </h2>
            <p v-if="edicion.estudiante" class="mt-1 text-sm text-[#34434b]">
              {{ nomEst(edicion.estudiante) }} · {{ fmtCedula(edicion.estudiante.cedula) }} · {{ gradoSeccion(edicion.estudiante) }}
            </p>
          </div>
          <button
            type="button"
            class="grid h-9 w-9 flex-none place-items-center rounded-full text-lg text-[#34434b] transition hover:bg-[#e3e8ee] hover:text-[#233E47]"
            aria-label="Cerrar edición del pase"
            @click="cerrarEdicion"
          >
            ✕
          </button>
        </header>

        <form class="max-h-[70vh] overflow-y-auto px-6 py-5" @submit.prevent="guardarEdicion">
          <p v-if="edicion.cargando" class="mb-4 rounded-xl bg-[#eef3fb] px-4 py-2 text-sm text-[#233E47]">
            Cargando datos del pase…
          </p>
          <p v-if="edicion.error" role="alert" class="mb-4 rounded-xl bg-[#fbd5d2] px-4 py-2 text-sm font-semibold text-[#8a1c14]">
            {{ edicion.error }}
          </p>

          <fieldset :disabled="edicion.cargando || edicion.guardando" class="flex flex-col gap-5 disabled:opacity-60">
            <legend class="sr-only">Datos del pase</legend>

            <fieldset>
              <legend :class="lbl">Tipo y motivo</legend>
              <div class="mt-1.5 flex flex-wrap items-center gap-x-6 gap-y-3">
                <div class="flex flex-wrap items-center gap-2" role="group" aria-label="Tipo de pase">
                  <button
                    v-for="t in TIPOS"
                    :key="`ed-tipo-${t}`"
                    type="button"
                    class="clay-tipo-btn"
                    :class="{ 'is-active': edicion.form.tipo === t }"
                    :aria-pressed="edicion.form.tipo === t"
                    @click="edicion.form.tipo = t"
                  >
                    {{ tipoLabel(t) }}
                  </button>
                </div>
                <div class="flex flex-wrap items-center gap-x-4 gap-y-2 border-l border-[#d5dbe6] pl-6 max-sm:border-0 max-sm:pl-0">
                  <label v-for="mo in motivosEdicion" :key="`ed-${mo}`" class="inline-flex cursor-pointer items-center gap-2 text-sm font-semibold text-[#34434b]">
                    <input type="radio" name="motivo-edicion" :value="mo" v-model="edicion.form.motivo" class="clay-radio" required />
                    <span>{{ mo }}</span>
                  </label>
                </div>
              </div>
            </fieldset>

            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label for="ed-fecha" :class="lbl">Fecha</label>
                <input v-model="edicion.form.fecha" id="ed-fecha" type="date" required :class="[inp, 'mt-1.5']" />
              </div>
              <div>
                <label for="ed-hora" :class="lbl">Hora</label>
                <input v-model="edicion.form.hora" id="ed-hora" type="time" required :class="[inp, 'mt-1.5']" />
              </div>
            </div>

            <div>
              <span :class="lbl">
                Asignatura y docente
                <span class="font-normal text-[#41515b]">(automático)</span>
              </span>
              <div class="mt-1.5 min-h-[3.25rem] rounded-xl border border-[#dbe2d0] bg-[#f1f4f0] px-3 py-2.5 text-[15px]" aria-live="polite">
                <p v-if="derivadoEdicion.cargando" class="text-sm text-[#34434b]">Consultando el horario…</p>
                <template v-else-if="derivadoEdicion.encontrado && derivadoEdicion.origen === 'HORARIO'">
                  <p class="font-semibold text-[#233E47]">{{ derivadoEdicion.asignatura || 'Asignatura sin nombre' }}</p>
                  <p class="text-sm text-[#34434b]">
                    {{ derivadoEdicion.docente || 'Docente sin nombre' }}
                    <span v-if="derivadoEdicion.bloque"> · {{ derivadoEdicion.bloque }}</span>
                    <span v-if="derivadoEdicion.horaInicio && derivadoEdicion.horaFin"> ({{ derivadoEdicion.horaInicio }}–{{ derivadoEdicion.horaFin }})</span>
                  </p>
                </template>
                <template v-else-if="derivadoEdicion.encontrado && derivadoEdicion.origen === 'TITULAR'">
                  <p class="font-semibold text-[#233E47]">{{ derivadoEdicion.docente || 'Docente sin nombre' }}</p>
                  <p class="text-sm text-[#34434b]">Docente titular de la sección · Escuela</p>
                </template>
                <template v-else-if="derivadoEdicion.error">
                  <p class="text-sm font-semibold text-[#8a1c14]">{{ derivadoEdicion.error }}</p>
                  <p class="text-sm text-[#34434b]">El pase se puede guardar sin asignatura ni docente.</p>
                  <button type="button" class="mt-2 text-sm font-semibold text-[#3454c5] hover:underline" @click="derivadorEdicion.resolver">Reintentar</button>
                </template>
                <p v-else-if="edicion.estudiante?.nivel === 'ESCUELA'" class="text-sm text-[#34434b]">
                  La sección no tiene docente titular; el pase se guardará sin docente.
                </p>
                <p v-else class="text-sm text-[#34434b]">
                  Sin clase registrada para ese día y hora; el pase se guardará sin asignatura ni docente.
                </p>
              </div>
            </div>

            <div v-if="requiereAutorizacionEdicion" class="grid gap-4 sm:grid-cols-2">
              <div class="sm:col-span-2">
                <label for="ed-autoriza" :class="lbl">Autorizado por el directivo</label>
                <input v-model="edicion.form.autorizador" id="ed-autoriza" list="autoridades-edicion" placeholder="Nombre del directivo" required :class="[inp, 'mt-1.5']" />
                <datalist id="autoridades-edicion"><option value="Coordinación" /><option value="Dirección" /><option value="Control de estudios" /></datalist>
              </div>
            </div>
          </fieldset>

          <div class="mt-5 flex flex-wrap justify-end gap-3 border-t border-[#e3e8ee] pt-4">
            <button type="button" :class="btnS" :disabled="edicion.guardando" @click="cerrarEdicion">Cancelar</button>
            <button type="submit" :class="btnP" :disabled="edicion.cargando || edicion.guardando">
              {{ edicion.guardando ? 'Guardando…' : 'Guardar cambios' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ═══════════ MODAL: Confirmar baja del pase ═══════════ -->
    <div
      v-if="baja.abierta && baja.pase"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="cerrarBaja"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="baja-pase-titulo"
        class="clay-card w-full max-w-md p-6"
      >
        <h3 id="baja-pase-titulo" class="text-lg font-bold text-[#233E47]">Confirmar baja</h3>
        <p class="mt-3 text-sm text-[#34434b]">
          ¿Dar de baja el pase #{{ baja.pase.id }} de
          <b class="text-[#1b2a2f]">{{ baja.pase.estudiante || 'este estudiante' }}</b>
          del {{ fmtFecha(baja.pase.fechaISO) }}? Esta acción no se puede deshacer.
        </p>
        <p v-if="baja.error" role="alert" class="mt-3 rounded-xl bg-[#fbd5d2] px-3 py-2 text-sm font-semibold text-[#8a1c14]">
          {{ baja.error }}
        </p>
        <div class="mt-5 flex gap-3">
          <button type="button" :class="[btnS, 'flex-1']" :disabled="baja.eliminando" @click="cerrarBaja">Cancelar</button>
          <button
            type="button"
            :class="[btnP, 'flex-1 !bg-[#b42318] hover:!bg-[#8f1c12]']"
            :disabled="baja.eliminando"
            @click="confirmarBaja"
          >
            {{ baja.eliminando ? 'Eliminando…' : 'Eliminar' }}
          </button>
        </div>
      </div>
    </div>
    </div>

    <Teleport to="body">
      <Transition name="toast">
        <div
          v-if="mostrarToastBloqueo"
          role="alert"
          aria-live="assertive"
          class="pases-toast"
        >
          <span class="pases-toast-icon" aria-hidden="true">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="9" /><path d="M5.6 5.6l12.8 12.8" />
            </svg>
          </span>
          <div class="min-w-0 flex-1">
            <b class="block text-base font-bold">
              {{ form.tipo === 'ENTRADA' ? 'NO PUEDE INGRESAR' : 'LÍMITE ALCANZADO' }}
            </b>
            <p class="mt-1 text-sm leading-snug">
              Acumula {{ pasesDelTipoMes }} pases de {{ tipoLabel(form.tipo).toLowerCase() }} este mes. Para registrar otro se requiere autorización de un directivo.
            </p>
          </div>
          <button
            type="button"
            class="pases-toast-close"
            aria-label="Cerrar aviso"
            @click="toastBloqueoDescartado = true"
          >
            ✕
          </button>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.pases-page {
  position: relative;
  isolation: isolate;
  background: #dbeafe;
}

.pases-mesh {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: var(--app-mesh-bg);
  background-size: 180% 180%;
  animation: mesh-drift 28s ease-in-out infinite alternate;
}

@keyframes mesh-drift {
  0% { background-position: 0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%; }
  50% { background-position: 35% 25%, 65% 30%, 55% 65%, 35% 70%, 100% 100%; }
  100% { background-position: 100% 100%, 0% 100%, 0% 0%, 100% 0%, 100% 100%; }
}

.clay-card {
  border-radius: 2.25rem;
  border: 1px solid rgba(255, 255, 255, 0.85);
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.98), rgba(233, 242, 255, 0.92));
  box-shadow:
    0 30px 55px -28px rgba(30, 64, 175, 0.45),
    0 16px 30px -20px rgba(30, 64, 175, 0.28),
    inset 0 3px 3px rgba(255, 255, 255, 0.98),
    inset 0 -7px 14px rgba(148, 163, 184, 0.2);
  backdrop-filter: blur(14px);
}

.clay-inset {
  box-shadow:
    inset 0 3px 8px rgba(148, 163, 184, 0.24),
    inset 0 -3px 6px rgba(255, 255, 255, 0.85);
}

.clay-field {
  box-shadow:
    inset 0 3px 7px rgba(148, 163, 184, 0.24),
    inset 0 -2px 3px rgba(255, 255, 255, 0.9),
    0 2px 0 rgba(255, 255, 255, 0.75);
}

.clay-radio {
  appearance: none;
  display: grid;
  place-items: center;
  flex: none;
  width: 1.1rem;
  height: 1.1rem;
  border: 2px solid #8fa3b8;
  border-radius: 9999px;
  background-color: #ffffff;
  box-shadow: inset 0 1px 3px rgba(30, 64, 175, 0.22);
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.clay-radio:checked {
  border-color: #233e47;
  background-color: #233e47;
  box-shadow:
    inset 0 0 0 3px #ffffff,
    0 2px 5px -2px rgba(35, 62, 71, 0.55);
}

.clay-radio:hover {
  border-color: #233e47;
}

.clay-radio:focus-visible {
  outline: 3px solid #3454c5;
  outline-offset: 2px;
}

/* Botones de tipo: mismo acabado clay, sin input radio. */
.clay-tipo-btn {
  display: inline-flex;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  min-height: 2.5rem;
  border-radius: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.85);
  background: linear-gradient(145deg, #f9fcff, #e2edf9);
  padding: 0.45rem 1rem;
  font-size: 0.875rem;
  font-weight: 700;
  color: #34434b;
  box-shadow:
    0 8px 14px -12px rgba(30, 64, 175, 0.55),
    inset 0 2px 2px rgba(255, 255, 255, 0.98),
    inset 0 -3px 6px rgba(148, 163, 184, 0.22);
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease,
    background 0.15s ease,
    color 0.15s ease;
}

.clay-tipo-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow:
    0 12px 18px -12px rgba(30, 64, 175, 0.6),
    inset 0 2px 2px rgba(255, 255, 255, 0.98),
    inset 0 -3px 6px rgba(148, 163, 184, 0.22);
}

.clay-tipo-btn.is-active {
  border-color: rgba(35, 62, 71, 0.9);
  background: linear-gradient(145deg, #355a68, #233e47);
  color: #ffffff;
  box-shadow:
    0 12px 20px -12px rgba(35, 62, 71, 0.75),
    inset 0 2px 0 rgba(255, 255, 255, 0.24),
    inset 0 -4px 8px rgba(0, 0, 0, 0.28);
}

.clay-tipo-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
}

.clay-tipo-btn:focus-visible {
  outline: 3px solid #3454c5;
  outline-offset: 3px;
}

/* Aviso de bloqueo flotante: no empuja el contenido de la tarjeta. */
.pases-toast {
  position: fixed;
  top: 4.75rem;
  right: 1.5rem;
  z-index: 40;
  display: flex;
  align-items: flex-start;
  gap: 0.85rem;
  width: min(26rem, calc(100vw - 2rem));
  padding: 1rem 1.15rem;
  border-radius: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: linear-gradient(145deg, #c22a1d, #8a1c14);
  color: #ffffff;
  box-shadow:
    0 22px 40px -18px rgba(138, 28, 20, 0.65),
    inset 0 2px 0 rgba(255, 255, 255, 0.28),
    inset 0 -4px 8px rgba(0, 0, 0, 0.22);
}

.pases-toast-icon {
  display: grid;
  place-items: center;
  flex: none;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.18);
}

.pases-toast-close {
  display: grid;
  place-items: center;
  flex: none;
  width: 2rem;
  height: 2rem;
  border-radius: 9999px;
  color: #ffffff;
  transition: background-color 0.15s ease;
}

.pases-toast-close:hover {
  background: rgba(255, 255, 255, 0.2);
}

.pases-toast-close:focus-visible {
  outline: 3px solid #ffffff;
  outline-offset: 2px;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.97);
}

@media (max-width: 639px) {
  .pases-toast {
    top: auto;
    right: 1rem;
    bottom: 1rem;
    left: 1rem;
    width: auto;
  }
}

.clay-btn {
  box-shadow:
    0 12px 20px -14px rgba(30, 64, 175, 0.65),
    inset 0 2px 0 rgba(255, 255, 255, 0.28),
    inset 0 -3px 6px rgba(0, 0, 0, 0.16);
}

.clay-btn-soft {
  box-shadow:
    0 12px 20px -16px rgba(30, 64, 175, 0.45),
    inset 0 2px 0 rgba(255, 255, 255, 0.95),
    inset 0 -3px 6px rgba(148, 163, 184, 0.18);
}

@media (prefers-reduced-motion: reduce) {
  .pases-mesh {
    animation: none;
  }
}
</style>

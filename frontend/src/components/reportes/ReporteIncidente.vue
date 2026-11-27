<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { nomEst } from '@/components/gestion-academica/helpers'
import { sesion } from '@/services/auth'
import { buscarEstudiantes, obtenerEstudiante } from '@/services/estudiantes'
import { consultarHorarioEstudiante } from '@/services/horarios'
import { obtenerSeccion } from '@/services/secciones'
import { REGLAMENTOS_REPORTE } from '@/services/reportes'
import { ACEPTAR_ARCHIVOS, validarArchivoAdjunto } from '@/utils/archivos'

const props = defineProps({
  guardando: { type: Boolean, default: false },
  reporte: { type: Object, default: null },
  errorCarga: { type: String, default: '' },
})

const emit = defineEmits(['cancel', 'submit'])

const esAdmin = computed(() => sesion.usuario?.rol === 'ADMINISTRADOR')
const nivelSesion = computed(() => sesion.usuario?.nivel || '')

const pad = (numero) => String(numero).padStart(2, '0')
const hoyISO = () => {
  const fecha = new Date()
  return `${fecha.getFullYear()}-${pad(fecha.getMonth() + 1)}-${pad(fecha.getDate())}`
}
const horaActual = () => {
  const fecha = new Date()
  return `${pad(fecha.getHours())}:${pad(fecha.getMinutes())}`
}

const formulario = reactive({
  fecha: hoyISO(),
  hora: horaActual(),
  categoria: '',
  articulo: '',
  reglamento: '',
  incidencia: '',
  defensa: '',
  gravedad: 'LEVE',
  archivo: null,
  quitarAdjunto: false,
})

const nivelFiltro = ref('')
const cargandoDatos = ref(false)
const errorDatos = ref('')
const errorFormulario = ref('')
const errorBusqueda = ref('')

const estudiante = ref(null)
const termino = ref('')
const resultados = ref([])
const buscando = ref(false)

// Docente derivado del horario del estudiante, igual que en el formulario de pases.
const docenteDerivado = reactive({
  cargando: false,
  idDocente: null,
  idAsignatura: null,
  docente: '',
  origen: '',
  asignatura: '',
  bloque: '',
  horaInicio: '',
  horaFin: '',
  aviso: '',
})

const entradaArchivos = ref(null)
const arrastrando = ref(false)

let solicitudBusqueda = 0
let solicitudInicial = 0
let solicitudDocente = 0
let temporizadorBusqueda = null
let temporizadorDocente = null

const modoEdicion = computed(() => Boolean(props.reporte))

const claseCampo =
  'w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]'
const claseCampoCorto = `${claseCampo} min-h-10`
// Los campos automáticos van disabled: así no reciben foco ni evidencian edición.
const claseCampoAuto = `${claseCampoCorto} cursor-not-allowed disabled:border-[#dbe2d0] disabled:bg-[#f1f4f0] disabled:text-[#5b6a72]`

const etiquetaNivel = (nivel) =>
  ({ LICEO: 'Liceo', ESCUELA: 'Escuela' })[nivel] ?? nivel ?? '—'

const fmtCedula = (cedula) => (cedula ? `V-${cedula}` : '—')
const cursoDe = (est) =>
  `${est?.gradoNombre ?? ''} ${est?.seccionLetra ?? ''}`.trim() || '—'

const nivelActivo = computed(() =>
  esAdmin.value ? nivelFiltro.value : nivelSesion.value,
)

const cursoEstudiante = computed(() => cursoDe(estudiante.value))
const periodoEstudiante = computed(() => estudiante.value?.periodoLectivo || '—')
// ───────────── Docente derivado (automático, no editable) ─────────────
// Liceo: se consulta el horario de la sección con la fecha y hora del reporte.
// Escuela: se toma el docente titular de la sección. Igual que en Pases.
const docenteVacio = () => ({
  cargando: false,
  idDocente: null,
  idAsignatura: null,
  docente: '',
  origen: '',
  asignatura: '',
  bloque: '',
  horaInicio: '',
  horaFin: '',
  aviso: '',
})

function limpiarDocente() {
  clearTimeout(temporizadorDocente)
  Object.assign(docenteDerivado, docenteVacio())
}

function conservarDocenteDelReporte(mensaje) {
  const reporte = props.reporte
  if (reporte?.idDocente) {
    Object.assign(docenteDerivado, {
      origen: 'REPORTE',
      idDocente: reporte.idDocente,
      idAsignatura: reporte.idAsignatura ?? null,
      docente: reporte.docente || '',
      asignatura: reporte.asignatura || '',
      aviso: mensaje,
    })
  } else {
    docenteDerivado.aviso = mensaje
  }
}

async function resolverTitular(est, actual) {
  if (!est.idSeccion) {
    conservarDocenteDelReporte(
      'La sección no tiene docente titular; el reporte se guardará sin docente.',
    )
    return
  }

  try {
    const seccion = await obtenerSeccion(est.idSeccion)
    if (actual !== solicitudDocente) return
    if (seccion.idDocenteTitular) {
      Object.assign(docenteDerivado, {
        origen: 'TITULAR',
        idDocente: seccion.idDocenteTitular,
        docente: seccion.docenteTitular || '',
        aviso: '',
      })
    } else {
      conservarDocenteDelReporte(
        'La sección no tiene docente titular; el reporte se guardará sin docente.',
      )
    }
  } catch (e) {
    if (actual !== solicitudDocente) return
    conservarDocenteDelReporte(e?.message || 'No se pudo cargar la sección del estudiante.')
  } finally {
    if (actual === solicitudDocente) docenteDerivado.cargando = false
  }
}

function resolverDocente() {
  limpiarDocente()
  const est = estudiante.value
  if (!est) return

  const actual = ++solicitudDocente
  docenteDerivado.cargando = true

  if (est.nivel === 'ESCUELA') {
    resolverTitular(est, actual)
    return
  }
  if (est.nivel !== 'LICEO') {
    docenteDerivado.cargando = false
    conservarDocenteDelReporte(
      'El estudiante no tiene nivel de liceo; no hay horario para derivar el docente.',
    )
    return
  }

  // Pequeña espera: al cambiar la hora no se consulta en cada tecla.
  temporizadorDocente = setTimeout(async () => {
    try {
      const clase = await consultarHorarioEstudiante({
        idEstudiante: est.id,
        fecha: formulario.fecha,
        hora: formulario.hora,
      })
      if (actual !== solicitudDocente) return

      if (clase.encontrado) {
        Object.assign(docenteDerivado, {
          origen: 'HORARIO',
          idDocente: clase.idDocente,
          idAsignatura: clase.idAsignatura ?? null,
          docente: clase.docente || '',
          asignatura: clase.asignatura || '',
          bloque: clase.bloque || '',
          horaInicio: clase.horaInicio || '',
          horaFin: clase.horaFin || '',
          aviso: '',
        })
      } else {
        conservarDocenteDelReporte(
          'Sin clase registrada para ese día y hora; el reporte se guardará sin docente.',
        )
      }
    } catch (e) {
      if (actual !== solicitudDocente) return
      conservarDocenteDelReporte(e?.message || 'No se pudo consultar el horario.')
    } finally {
      if (actual === solicitudDocente) docenteDerivado.cargando = false
    }
  }, 300)
}

watch([estudiante, () => formulario.fecha, () => formulario.hora], resolverDocente)

function limpiarSeleccionEstudiante() {
  estudiante.value = null
  resultados.value = []
  errorBusqueda.value = ''
}

// Búsqueda contra /estudiantes/buscar: nunca se carga el catálogo completo.
async function buscar() {
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
      nivel: nivelActivo.value || undefined,
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

// Búsqueda reactiva: 350 ms después de dejar de escribir, igual que en Pases.
watch(termino, () => {
  clearTimeout(temporizadorBusqueda)
  const texto = termino.value.trim()

  if (estudiante.value) {
    // En edición el buscador se precarga con la cédula; eso no es una búsqueda nueva.
    if (texto === estudiante.value.cedula) return
    limpiarSeleccionEstudiante()
  } else {
    resultados.value = []
    errorBusqueda.value = ''
  }

  if (texto.length < 2) return
  temporizadorBusqueda = setTimeout(() => {
    temporizadorBusqueda = null
    buscar()
  }, 350)
})

function seleccionarEstudiante(est) {
  estudiante.value = est
  // Se conserva lo que el usuario escribió; la cédula va en su propio campo.
  resultados.value = []
  errorBusqueda.value = ''
  errorFormulario.value = ''
}

function nuevaBusqueda() {
  solicitudBusqueda += 1
  clearTimeout(temporizadorBusqueda)
  termino.value = ''
  limpiarSeleccionEstudiante()
}

watch(nivelFiltro, nuevaBusqueda)

function aplicarCamposReporte() {
  const reporte = props.reporte
  if (!reporte) return

  formulario.fecha = String(reporte.fecha || '').slice(0, 10) || hoyISO()
  formulario.hora = String(reporte.fecha || '').slice(11, 16) || horaActual()
  formulario.categoria = reporte.categoria || ''
  formulario.articulo = reporte.articulo ?? ''
  formulario.reglamento = reporte.reglamento || ''
  formulario.incidencia = reporte.incidencia || ''
  formulario.defensa = reporte.defensa || ''
  formulario.gravedad = reporte.gravedad || 'LEVE'
  formulario.archivo = null
  formulario.quitarAdjunto = false
}

async function cargarInicial() {
  const solicitud = ++solicitudInicial
  cargandoDatos.value = true
  errorDatos.value = ''

  if (!props.reporte) {
    cargandoDatos.value = false
    return
  }

  try {
    if (props.reporte.idEstudiante) {
      try {
        const est = await obtenerEstudiante(props.reporte.idEstudiante)
        if (solicitud !== solicitudInicial) return
        estudiante.value = est
        termino.value = est.cedula || props.reporte.cedula || ''
      } catch {
        if (solicitud !== solicitudInicial) return
        estudiante.value = null
        termino.value = props.reporte.estudiante || props.reporte.cedula || ''
        errorDatos.value =
          'No se pudo cargar el estudiante del reporte; búsquelo para continuar.'
      }

      aplicarCamposReporte()
    }
  } catch (error) {
    if (solicitud !== solicitudInicial) return
    errorDatos.value = error?.message || 'No se pudo cargar el reporte.'
  } finally {
    if (solicitud === solicitudInicial) cargandoDatos.value = false
  }
}

// El reporte puede llegar después del primer render (edición), por eso se vigila.
watch(() => props.reporte?.id ?? null, cargarInicial, { immediate: true })

onBeforeUnmount(() => {
  clearTimeout(temporizadorBusqueda)
  clearTimeout(temporizadorDocente)
  solicitudBusqueda += 1
  solicitudInicial += 1
  solicitudDocente += 1
})

// Píldoras de gravedad: rellenas cuando están inactivas y con borde al seleccionarse
function claseSeveridad(valor) {
  const seleccionado = formulario.gravedad === valor
  if (valor === 'GRAVE') {
    return seleccionado
      ? 'border-[#b7791f] bg-white text-[#72520b]'
      : 'border-transparent bg-[#faedc8] text-[#72520b]'
  }
  return seleccionado
    ? 'border-[#2f7d4f] bg-white text-[#285d3b]'
    : 'border-transparent bg-[#d9f1e2] text-[#285d3b]'
}

function seleccionarArchivo(archivo) {
  errorFormulario.value = validarArchivoAdjunto(archivo)
  if (errorFormulario.value) return

  formulario.archivo = archivo
  formulario.quitarAdjunto = false
}

function alSeleccionarArchivo(evento) {
  seleccionarArchivo(evento.target.files?.[0])
  evento.target.value = ''
}

function alSoltarArchivo(evento) {
  arrastrando.value = false
  seleccionarArchivo(evento.dataTransfer?.files?.[0])
}

function quitarArchivo() {
  formulario.archivo = null
  if (modoEdicion.value && props.reporte?.archivoNombre) {
    formulario.quitarAdjunto = true
  }
}

function enviarFormulario() {
  if (props.guardando) return
  errorFormulario.value = ''

  const articulo = Number(formulario.articulo)
  if (!estudiante.value) {
    errorFormulario.value = 'Busca y selecciona un estudiante.'
    return
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(formulario.fecha)) {
    errorFormulario.value = 'Indica la fecha del incidente.'
    return
  }
  if (!formulario.categoria) {
    errorFormulario.value = 'Selecciona el tipo de reporte.'
    return
  }
  if (!Number.isInteger(articulo) || articulo < 1) {
    errorFormulario.value = 'El artículo debe ser un número entero mayor que cero.'
    return
  }
  if (!formulario.reglamento) {
    errorFormulario.value = 'Selecciona el reglamento aplicable.'
    return
  }
  if (!formulario.incidencia.trim()) {
    errorFormulario.value = 'Describe la incidencia.'
    return
  }
  if (!formulario.defensa.trim()) {
    errorFormulario.value = 'Registra el derecho a la defensa.'
    return
  }
  if (docenteDerivado.cargando) {
    errorFormulario.value = 'Esperando al docente asignado según el horario…'
    return
  }

  emit('submit', {
    idEstudiante: estudiante.value.id,
    idDocente: docenteDerivado.idDocente ?? null,
    idAsignatura: docenteDerivado.idAsignatura ?? null,
    fecha: `${formulario.fecha}T${formulario.hora || '00:00'}:00`,
    categoria: formulario.categoria,
    articulo,
    reglamento: formulario.reglamento,
    incidencia: formulario.incidencia.trim(),
    defensa: formulario.defensa.trim(),
    gravedad: formulario.gravedad,
    archivo: formulario.archivo,
    quitarAdjunto: formulario.quitarAdjunto,
  })
}
</script>

<template>
  <form
    class="relative mx-auto grid w-full max-w-[1000px] gap-3.5 p-4 text-[#242a35] max-[520px]:p-2.5"
    @submit.prevent="enviarFormulario"
  >
    <div
      v-if="errorCarga || errorDatos || errorFormulario"
      role="alert"
      class="rounded-lg bg-[#fbd5d2] px-3 py-2 text-[13px] font-semibold text-[#8a1c14]"
    >
      {{ errorFormulario || errorCarga || errorDatos }}
    </div>

    <section class="rounded-[9px] border border-[#c8cbd1] bg-white px-4 pt-3.5 pb-4 shadow-sm">
      <div class="mb-2.5 flex flex-wrap items-center justify-between gap-2">
        <h2 class="m-0 text-[17px] font-bold">1 · Datos del estudiante</h2>
        <label v-if="esAdmin" class="flex items-center gap-2 text-xs font-semibold text-[#414752]">
          <span>Nivel</span>
          <select v-model="nivelFiltro" :class="[claseCampoCorto, 'w-auto min-w-[130px]']">
            <option value="">Todos</option>
            <option value="LICEO">Liceo</option>
            <option value="ESCUELA">Escuela</option>
          </select>
        </label>
      </div>

      <div class="flex flex-wrap items-end gap-2">
        <label class="min-w-[14rem] flex-1 text-xs text-[#414752]">
          <span>Cédula, nombre o apellido</span>
          <div class="relative mt-1">
            <svg
              aria-hidden="true"
              class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-[#777d87]"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3.5-3.5" />
            </svg>
            <input
              v-model="termino"
              type="search"
              autocomplete="off"
              placeholder="Buscar estudiante"
              :disabled="cargandoDatos"
              :class="[claseCampoCorto, 'pl-9']"
            />
            <ul
              v-if="resultados.length"
              class="absolute top-full right-0 left-0 z-30 mt-2 max-h-[19rem] divide-y divide-[#e3e8ee] overflow-y-auto rounded-xl border border-[#e3e8ee] bg-white shadow-xl"
            >
              <li v-for="r in resultados" :key="r.id">
                <button
                  type="button"
                  class="flex w-full items-center justify-between gap-2 px-3 py-2 text-left transition hover:bg-[#eef3fb]"
                  @click="seleccionarEstudiante(r)"
                >
                  <span class="min-w-0">
                    <span class="block truncate text-sm font-semibold text-[#1b2a2f]">
                      {{ nomEst(r) }}
                    </span>
                    <span class="block truncate text-xs text-[#59606c]">
                      {{ fmtCedula(r.cedula) }} · {{ cursoDe(r) }} · {{ etiquetaNivel(r.nivel) }}
                    </span>
                  </span>
                  <span class="shrink-0 text-xs font-bold text-[#304bbc]">Seleccionar</span>
                </button>
              </li>
            </ul>
          </div>
        </label>

        <button
          v-if="estudiante || termino"
          type="button"
          class="min-h-10 cursor-pointer rounded-md border border-[#c8cbd1] bg-white px-3 text-xs font-bold text-[#414752] hover:bg-[#f4f5f7]"
          @click="nuevaBusqueda"
        >
          Limpiar
        </button>
      </div>

      <p v-if="errorBusqueda" role="alert" class="mt-2 text-xs font-semibold text-[#8a1c14]">
        {{ errorBusqueda }}
      </p>

      <div class="mt-3 grid grid-cols-1 gap-x-3.5 gap-y-3 min-[521px]:grid-cols-2">
        <label class="grid min-w-0 gap-1 text-xs text-[#414752] min-[521px]:col-span-2">
          <span>Nombre y apellido</span>
          <input
            :value="estudiante ? nomEst(estudiante) : ''"
            placeholder="Se completa al buscar"
            type="text"
            name="nombreEstudiante"
            :class="claseCampoAuto"
            disabled
          />
        </label>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Cédula</span>
          <input
            :value="estudiante ? fmtCedula(estudiante.cedula) : ''"
            placeholder="Se completa al buscar"
            type="text"
            name="cedulaEstudiante"
            :class="claseCampoAuto"
            disabled
          />
        </label>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Nivel</span>
          <input
            :value="estudiante ? etiquetaNivel(estudiante.nivel) : ''"
            placeholder="—"
            type="text"
            name="nivelEstudiante"
            :class="claseCampoAuto"
            disabled
          />
        </label>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Curso</span>
          <input :value="cursoEstudiante" type="text" name="curso" :class="claseCampoAuto" disabled />
        </label>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Período lectivo</span>
          <input
            :value="periodoEstudiante"
            type="text"
            name="periodo"
            :class="claseCampoAuto"
            disabled
          />
        </label>
      </div>
    </section>

    <fieldset :disabled="!estudiante || guardando" class="grid w-full gap-3.5 disabled:opacity-60">
      <legend class="sr-only">Datos del reporte</legend>

      <section class="rounded-[9px] border border-[#c8cbd1] bg-white px-4 pt-3.5 pb-4 shadow-sm">
        <h2 class="m-0 mb-2.5 text-[17px] font-bold">2 · Datos del incidente</h2>

        <div class="grid grid-cols-1 gap-x-3.5 gap-y-3 min-[521px]:grid-cols-2 min-[761px]:grid-cols-4">
          <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
            <span>Fecha</span>
            <input v-model="formulario.fecha" type="date" name="fecha" :class="claseCampoCorto" />
          </label>

          <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
            <span>Hora</span>
            <input v-model="formulario.hora" type="time" name="hora" :class="claseCampoCorto" />
          </label>

          <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
            <span>Docente</span>
            <input
              :value="docenteDerivado.docente || (docenteDerivado.cargando ? 'Consultando horario…' : '')"
              type="text"
              name="docente"
              placeholder="Se completa según el horario"
              :class="claseCampoAuto"
              disabled
            />
          </label>

          <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
            <span>Asignatura</span>
            <input
              :value="estudiante ? docenteDerivado.asignatura || '—' : ''"
              type="text"
              name="asignatura"
              placeholder="Se completa según el horario"
              :class="claseCampoAuto"
              disabled
            />
          </label>

          <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
            <span>Tipo de reporte</span>
            <select v-model="formulario.categoria" name="categoria" :class="claseCampoCorto">
              <option value="" disabled>Seleccionar</option>
              <option value="CONDUCTUAL">Conductual</option>
              <option value="ACADEMICO">Académico</option>
            </select>
          </label>

          <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
            <span>Artículo (número)</span>
            <input
              v-model="formulario.articulo"
              type="number"
              min="1"
              step="1"
              name="articulo"
              :class="claseCampoCorto"
            />
          </label>
        </div>

        <p
          v-if="estudiante && docenteDerivado.aviso && !docenteDerivado.cargando"
          role="status"
          class="mt-2.5 flex flex-wrap items-center gap-2 text-xs font-semibold text-[#8a1c14]"
        >
          {{ docenteDerivado.aviso }}
          <button
            type="button"
            class="cursor-pointer border-0 bg-transparent text-[#3454c5] underline"
            @click="resolverDocente"
          >
            Reintentar
          </button>
        </p>

        <fieldset class="mt-3 border-0 p-0">
          <legend class="mb-2 text-xs font-bold text-[#414752]">
            Gravedad del incidente
          </legend>
          <div class="flex flex-wrap gap-2.5">
            <label
              v-for="nivel in [
                { valor: 'LEVE', texto: 'Leve', detalle: 'Falta menor' },
                { valor: 'GRAVE', texto: 'Grave', detalle: 'Falta mayor' },
              ]"
              :key="nivel.valor"
              :class="[
                'inline-flex min-h-[46px] min-w-[132px] cursor-pointer flex-col justify-center gap-0.5 rounded-lg border-2 px-3.5 py-2 leading-tight transition focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-[#3454c5]',
                claseSeveridad(nivel.valor),
              ]"
            >
              <input
                v-model="formulario.gravedad"
                class="absolute h-px w-px opacity-0"
                type="radio"
                name="gravedad"
                :value="nivel.valor"
              />
              <span class="text-sm font-bold">{{ nivel.texto }}</span>
              <span class="text-[11px] font-normal opacity-80">{{ nivel.detalle }}</span>
            </label>
          </div>
        </fieldset>
      </section>

      <section class="rounded-[9px] border border-[#c8cbd1] bg-white px-4 pt-3.5 pb-4 shadow-sm">
        <h2 class="m-0 mb-2.5 text-[17px] font-bold">3 · Descripción y acciones</h2>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Incidencia</span>
          <textarea
            v-model="formulario.incidencia"
            :class="[claseCampo, 'min-h-[100px] resize-y']"
            name="incidencia"
            rows="4"
          ></textarea>
        </label>

        <fieldset class="mt-3 flex flex-wrap gap-2 border-0 p-0">
          <legend class="mb-2 text-xs font-bold text-[#414752]">Reglamento</legend>
          <label
            v-for="reglamento in REGLAMENTOS_REPORTE"
            :key="reglamento"
            :class="[
              'inline-flex min-h-[38px] cursor-pointer items-center gap-2 rounded-lg border bg-white px-3 text-[13px] transition focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-[#3454c5]',
              formulario.reglamento === reglamento
                ? 'border-[#304bbc] bg-[#eef1fa] font-bold text-[#253d9f] shadow-[0_0_0_1px_#304bbc] hover:bg-[#eef1fa]'
                : 'border-[#c8cbd1] text-[#414752] hover:border-[#7d8ac2] hover:bg-[#f7f8fc]',
            ]"
          >
            <input
              v-model="formulario.reglamento"
              class="m-0 h-[18px] w-[18px] accent-[#304bbc]"
              type="radio"
              name="reglamento"
              :value="reglamento"
            />
            <span>{{ reglamento }}</span>
          </label>
        </fieldset>

        <label class="mt-2.5 grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Art.88, LOPNNA: Derecho a la Defensa</span>
          <textarea
            v-model="formulario.defensa"
            :class="[claseCampo, 'min-h-[76px] resize-y']"
            name="defensa"
            rows="3"
          ></textarea>
        </label>

        <div
          v-if="modoEdicion && reporte?.archivoNombre"
          class="mt-2.5 rounded-lg bg-[#eef3fb] px-3 py-2 text-xs text-[#233E47]"
        >
          <p class="m-0 font-semibold">Adjunto actual: {{ reporte.archivoNombre }}</p>
          <label class="mt-1 inline-flex cursor-pointer items-center gap-2">
            <input v-model="formulario.quitarAdjunto" type="checkbox" class="accent-[#304bbc]" />
            <span>Quitar este adjunto al guardar</span>
          </label>
        </div>

        <div
          :class="[
            'mt-2.5 grid min-h-14 cursor-pointer place-items-center rounded-md p-2 text-center text-[13px] text-[#414752] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[#3454c5]',
            arrastrando
              ? 'bg-[#eef1fa] outline outline-2 outline-dashed outline-[#3454c5]'
              : 'bg-[#e0e4ec]',
          ]"
          @dragover.prevent="arrastrando = true"
          @dragleave.prevent="arrastrando = false"
          @drop.prevent="alSoltarArchivo"
          @click="entradaArchivos?.click()"
          @keydown.enter.prevent="entradaArchivos?.click()"
          @keydown.space.prevent="entradaArchivos?.click()"
          role="button"
          tabindex="0"
          aria-label="Adjuntar una imagen o archivo PDF"
        >
          <input
            ref="entradaArchivos"
            class="sr-only"
            type="file"
            :accept="ACEPTAR_ARCHIVOS"
            @change="alSeleccionarArchivo"
          />
          <span class="flex flex-wrap items-center justify-center gap-2 [overflow-wrap:anywhere]">
            <span>
              {{
                formulario.archivo
                  ? formulario.archivo.name
                  : modoEdicion
                    ? 'Arrastra otra imagen o PDF para reemplazar el adjunto (opcional)'
                    : 'Arrastra una imagen o PDF (opcional) o haz clic para seleccionarlo'
              }}
            </span>
            <button
              v-if="formulario.archivo"
              type="button"
              class="cursor-pointer border-0 bg-transparent text-[#3454c5] underline"
              @click.stop="quitarArchivo"
            >
              Quitar
            </button>
          </span>
        </div>
      </section>

      <div class="flex flex-wrap justify-end gap-2.5 pt-px">
        <button
          type="submit"
          class="min-h-[42px] cursor-pointer rounded-md border border-[#304bbc] bg-[#304bbc] px-4 text-[13px] font-bold text-white hover:bg-[#253d9f] disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="guardando || cargandoDatos || docenteDerivado.cargando"
        >
          {{ guardando ? 'Guardando…' : modoEdicion ? 'Guardar cambios' : 'Registrar reporte' }}
        </button>
      </div>
    </fieldset>
  </form>
</template>

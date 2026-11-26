<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { nomDocente, nomEst, norm } from '@/components/gestion-academica/helpers'
import { sesion } from '@/services/auth'
import { listarTodosEstudiantes } from '@/services/estudiantes'
import { listarTodosDocentes } from '@/services/docentes'
import { REGLAMENTOS_REPORTE } from '@/services/reportes'

const props = defineProps({
  guardando: { type: Boolean, default: false },
})

const emit = defineEmits(['cancel', 'submit'])

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
  estudianteTexto: '',
  fecha: hoyISO(),
  hora: horaActual(),
  docenteTexto: '',
  categoria: '',
  articulo: '',
  reglamento: '',
  incidencia: '',
  defensa: '',
  gravedad: 'LEVE',
  archivo: null,
})

const estudiantes = ref([])
const docentes = ref([])
const cargandoCatalogos = ref(false)
const errorCatalogos = ref('')
const errorFormulario = ref('')
const estudiante = ref(null)
const docente = ref(null)
const entradaArchivos = ref(null)
const arrastrando = ref(false)

// Clases compartidas por los campos del formulario
const claseCampo =
  'w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]'
const claseCampoCorto = `${claseCampo} min-h-10`

const etiquetaNivel = (nivel) =>
  ({ LICEO: 'Liceo', ESCUELA: 'Escuela' })[nivel] ?? nivel ?? '—'

const etiquetaEstudiante = (est) =>
  `${nomEst(est)} · ${est.cedula ? `V-${est.cedula}` : `#${est.id}`}`
const etiquetaDocente = (doc) =>
  `${nomDocente(doc)} · ${doc.cedula ? `V-${doc.cedula}` : `#${doc.id}`}`

const opcionesEstudiante = computed(() => estudiantes.value.map(etiquetaEstudiante))

// El backend valida que el docente pertenezca al nivel del estudiante.
const docentesDisponibles = computed(() => {
  const nivel = estudiante.value?.nivel
  return nivel ? docentes.value.filter((doc) => doc.nivel === nivel) : docentes.value
})
const opcionesDocente = computed(() => docentesDisponibles.value.map(etiquetaDocente))

const cursoEstudiante = computed(() => {
  if (!estudiante.value) return '—'
  return `${estudiante.value.gradoNombre ?? ''} ${estudiante.value.seccionLetra ?? ''}`.trim() || '—'
})
const inicialEstudiante = computed(() =>
  estudiante.value ? nomEst(estudiante.value).charAt(0).toUpperCase() : '',
)

const mismoTexto = (valor, texto) => norm(valor) === norm(texto)

const resolverEstudiante = (texto) => {
  const busqueda = String(texto ?? '').trim()
  if (!busqueda) return null
  return (
    estudiantes.value.find(
      (est) =>
        mismoTexto(etiquetaEstudiante(est), busqueda) ||
        mismoTexto(est.cedula, busqueda) ||
        mismoTexto(nomEst(est), busqueda),
    ) ?? null
  )
}

const resolverDocente = (texto) => {
  const busqueda = String(texto ?? '').trim()
  if (!busqueda) return null
  return (
    docentesDisponibles.value.find(
      (doc) =>
        mismoTexto(etiquetaDocente(doc), busqueda) ||
        mismoTexto(doc.cedula, busqueda) ||
        mismoTexto(nomDocente(doc), busqueda),
    ) ?? null
  )
}

watch(
  () => formulario.estudianteTexto,
  (texto) => {
    estudiante.value = resolverEstudiante(texto)
    errorFormulario.value = ''
    if (!estudiante.value) {
      docente.value = null
      formulario.docenteTexto = ''
    }
  },
)

watch(
  () => formulario.docenteTexto,
  (texto) => {
    docente.value = resolverDocente(texto)
  },
)

onMounted(async () => {
  cargandoCatalogos.value = true
  errorCatalogos.value = ''
  try {
    const [listaEstudiantes, listaDocentes] = await Promise.all([
      listarTodosEstudiantes({ nivel: sesion.usuario?.nivel || undefined }),
      listarTodosDocentes(),
    ])
    estudiantes.value = listaEstudiantes.items
    docentes.value = listaDocentes.items
  } catch (error) {
    errorCatalogos.value = error?.message || 'No se pudieron cargar estudiantes y docentes.'
  } finally {
    cargandoCatalogos.value = false
  }
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
  errorFormulario.value = ''
  if (!archivo) return

  const permitido =
    archivo.type === 'application/pdf' || archivo.type.startsWith('image/')
  if (!permitido) {
    errorFormulario.value = 'Solo se permiten imágenes o archivos PDF.'
    return
  }
  formulario.archivo = archivo
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
}

function enviarFormulario() {
  if (props.guardando) return
  errorFormulario.value = ''

  const articulo = Number(formulario.articulo)
  if (!estudiante.value) {
    errorFormulario.value = 'Selecciona un estudiante válido de la lista.'
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
  if (formulario.docenteTexto && !docente.value) {
    errorFormulario.value = 'Selecciona un docente válido del nivel del estudiante.'
    return
  }

  emit('submit', {
    idEstudiante: estudiante.value.id,
    idDocente: docente.value?.id ?? null,
    fecha: `${formulario.fecha}T${formulario.hora || '00:00'}:00`,
    categoria: formulario.categoria,
    articulo,
    reglamento: formulario.reglamento,
    incidencia: formulario.incidencia.trim(),
    defensa: formulario.defensa.trim(),
    gravedad: formulario.gravedad,
    archivo: formulario.archivo,
  })
}
</script>

<template>
  <form
    class="relative mx-auto grid w-full max-w-[1000px] gap-3.5 p-4 text-[#242a35] max-[520px]:p-2.5"
    @submit.prevent="enviarFormulario"
  >
    <div
      v-if="errorCatalogos || errorFormulario"
      role="alert"
      class="rounded-lg bg-[#fbd5d2] px-3 py-2 text-[13px] font-semibold text-[#8a1c14]"
    >
      {{ errorFormulario || errorCatalogos }}
    </div>

    <section class="rounded-[9px] border border-[#c8cbd1] bg-white px-4 pt-3.5 pb-4 shadow-sm">
      <h2 class="m-0 mb-2.5 text-[17px] font-bold">1 · Datos del estudiante</h2>

      <div class="grid grid-cols-1 gap-x-3.5 gap-y-3 min-[521px]:grid-cols-2">
        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Curso</span>
          <input :value="cursoEstudiante" type="text" name="curso" :class="claseCampoCorto" readonly />
        </label>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Estudiante (con búsqueda)</span>
          <input
            v-model="formulario.estudianteTexto"
            type="search"
            name="estudiante"
            list="estudiantes-disponibles"
            autocomplete="off"
            placeholder="Nombre o cédula"
            :disabled="cargandoCatalogos"
            :class="claseCampoCorto"
          />
          <datalist id="estudiantes-disponibles">
            <option v-for="opcion in opcionesEstudiante" :key="opcion" :value="opcion" />
          </datalist>
        </label>
      </div>

      <div class="mt-[11px] flex items-center gap-3" aria-live="polite">
        <div
          class="grid h-[46px] w-[46px] shrink-0 place-items-center rounded-full bg-[#e0e4ec] text-lg font-bold text-[#46516a]"
          aria-hidden="true"
        >
          {{ inicialEstudiante }}
        </div>
        <div>
          <p class="m-0 text-xs">
            {{ estudiante ? nomEst(estudiante) : 'Tarjeta del estudiante' }}
          </p>
          <p class="m-0 text-xs text-[#777d87]">
            <template v-if="estudiante">
              {{ etiquetaNivel(estudiante.nivel) }} · {{ cursoEstudiante }}
            </template>
            <template v-else-if="cargandoCatalogos">Cargando estudiantes…</template>
            <template v-else>Selecciona un estudiante de la lista</template>
          </p>
        </div>
      </div>
    </section>

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
          <span>Docente (opcional)</span>
          <input
            v-model="formulario.docenteTexto"
            type="search"
            name="docente"
            list="docentes-disponibles"
            autocomplete="off"
            placeholder="Nombre o cédula"
            :disabled="!estudiante || cargandoCatalogos"
            :class="claseCampoCorto"
          />
          <datalist id="docentes-disponibles">
            <option v-for="opcion in opcionesDocente" :key="opcion" :value="opcion" />
          </datalist>
          <span v-if="!estudiante" class="text-[11px] text-[#777d87]">
            Selecciona un estudiante para ver docentes de su nivel.
          </span>
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
          <span>Artículo</span>
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

      <fieldset class="mt-2.5 flex flex-nowrap gap-3 border-0 p-0">
        <legend class="sr-only">Gravedad del incidente</legend>
        <label
          v-for="nivel in [
            { valor: 'LEVE', texto: 'Leve' },
            { valor: 'GRAVE', texto: 'Grave' },
          ]"
          :key="nivel.valor"
          :class="[
            'inline-flex cursor-pointer items-center gap-2 rounded-full border-2 px-2.5 py-1 text-xs leading-none transition',
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
          <span>{{ nivel.texto }}</span>
        </label>
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
        <input v-model="formulario.defensa" type="text" name="defensa" :class="claseCampoCorto" />
      </label>

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
          accept="image/*,.pdf,application/pdf"
          @change="alSeleccionarArchivo"
        />
        <span class="flex flex-wrap items-center justify-center gap-2 [overflow-wrap:anywhere]">
          <span>
            {{
              formulario.archivo
                ? formulario.archivo.name
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

    <div class="flex flex-wrap justify-end gap-2.5 pt-px max-[520px]:grid max-[520px]:grid-cols-1">
      <button
        type="button"
        class="min-h-[42px] cursor-pointer rounded-md border border-[#777d87] bg-white px-4 text-[13px] font-bold text-[#242a35] hover:bg-[#f4f5f7]"
        :disabled="guardando"
        @click="emit('cancel')"
      >
        Cancelar
      </button>
      <button
        type="submit"
        class="min-h-[42px] cursor-pointer rounded-md border border-[#304bbc] bg-[#304bbc] px-4 text-[13px] font-bold text-white hover:bg-[#253d9f] disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="guardando"
      >
        {{ guardando ? 'Registrando…' : 'Registrar reporte' }}
      </button>
    </div>
  </form>
</template>

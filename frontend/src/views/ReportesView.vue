<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import ReporteIncidente from '@/components/reportes/ReporteIncidente.vue'
import { norm } from '@/components/gestion-academica/helpers'
import { etiquetaNivel } from '@/services/auth'
import {
  crearReporte,
  descargarArchivoReporte,
  etiquetaCategoria,
  etiquetaGravedad,
  listarTodosReportes,
  subirArchivoReporte,
} from '@/services/reportes'

const reportes = ref([])
const cargando = ref(true)
const guardando = ref(false)
const error = ref('')
const exito = ref('')
const mostrarFormulario = ref(false)
const detalleAbierto = ref(null)
const paginaActual = ref(1)
const reportesPorPagina = 10

const filtros = ref({
  estudiante: '',
  docente: '',
  nivel: '',
  gravedad: '',
  categoria: '',
  fecha: '',
})

// Clases compartidas por encabezados y celdas de la tabla
const claseCelda = 'whitespace-nowrap border-b border-[#e1e3e7] px-[10px] py-[11px]'
const claseEncabezado = `${claseCelda} font-bold`

let solicitudCarga = 0
let temporizadorFiltros = null

async function cargarReportes() {
  const solicitud = ++solicitudCarga
  cargando.value = true
  error.value = ''

  try {
    // El backend filtra por año/mes, nivel, categoría y gravedad. El texto de
    // estudiante/docente y el día exacto se refinan en cliente porque la API
    // no expone esos filtros.
    const [anio, mes] = filtros.value.fecha
      ? [Number(filtros.value.fecha.slice(0, 4)), Number(filtros.value.fecha.slice(5, 7))]
      : []

    const { items } = await listarTodosReportes({
      anio,
      mes,
      nivel: filtros.value.nivel || undefined,
      gravedad: filtros.value.gravedad || undefined,
      categoria: filtros.value.categoria || undefined,
    })
    if (solicitud !== solicitudCarga) return
    reportes.value = items
  } catch (e) {
    if (solicitud !== solicitudCarga) return
    reportes.value = []
    error.value = e?.message || 'No se pudieron cargar los reportes.'
  } finally {
    if (solicitud === solicitudCarga) cargando.value = false
  }
}

const reportesFiltrados = computed(() => {
  const estudiante = norm(filtros.value.estudiante.trim())
  const docente = norm(filtros.value.docente.trim())

  return reportes.value.filter(
    (reporte) =>
      (!estudiante || norm(reporte.estudiante).includes(estudiante)) &&
      (!docente || norm(reporte.docente).includes(docente)) &&
      (!filtros.value.fecha || reporte.fechaISO === filtros.value.fecha),
  )
})

const totalPaginas = computed(() =>
  Math.max(1, Math.ceil(reportesFiltrados.value.length / reportesPorPagina)),
)

const reportesPaginados = computed(() => {
  const inicio = (paginaActual.value - 1) * reportesPorPagina
  return reportesFiltrados.value.slice(inicio, inicio + reportesPorPagina)
})

watch(
  filtros,
  () => {
    paginaActual.value = 1
    clearTimeout(temporizadorFiltros)
    temporizadorFiltros = setTimeout(() => {
      temporizadorFiltros = null
      cargarReportes()
    }, 300)
  },
  { deep: true },
)

onMounted(cargarReportes)
onBeforeUnmount(() => {
  clearTimeout(temporizadorFiltros)
  solicitudCarga += 1
})

function formatearFecha(fecha) {
  const dia = String(fecha ?? '').slice(0, 10)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dia)) return '—'
  return new Intl.DateTimeFormat('es', {
    day: 'numeric',
    month: 'short',
  }).format(new Date(`${dia}T12:00:00`))
}

function claseGravedad(gravedad) {
  return gravedad === 'GRAVE'
    ? 'bg-[#faedc8] text-[#72520b]'
    : 'bg-[#d9f1e2] text-[#285d3b]'
}

function exportarReportes() {
  const encabezados = [
    'N.º',
    'Fecha',
    'Hora',
    'Estudiante',
    'Cédula',
    'Nivel',
    'Tipo',
    'Gravedad',
    'Artículo',
    'Reglamento',
    'Docente',
    'Registrado por',
  ]
  const filas = reportesFiltrados.value.map((reporte) => [
    reporte.id,
    reporte.fechaISO,
    reporte.hora || '',
    reporte.estudiante,
    reporte.cedula,
    etiquetaNivel(reporte.nivel),
    etiquetaCategoria(reporte.categoria),
    etiquetaGravedad(reporte.gravedad),
    reporte.articulo,
    reporte.reglamento,
    reporte.docente,
    reporte.usuario,
  ])
  const csv = [encabezados, ...filas]
    .map((fila) => fila.map((valor) => `"${String(valor ?? '').replaceAll('"', '""')}"`).join(','))
    .join('\r\n')
  const archivo = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' })
  const enlace = document.createElement('a')
  const url = URL.createObjectURL(archivo)

  enlace.href = url
  enlace.download = 'reportes.csv'
  enlace.click()
  URL.revokeObjectURL(url)
}

async function descargarAdjunto(reporte) {
  try {
    const { blob, nombre } = await descargarArchivoReporte(reporte.id)
    const url = URL.createObjectURL(blob)
    const enlace = document.createElement('a')

    enlace.href = url
    enlace.download = nombre || `reporte-${reporte.id}`
    enlace.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = e?.message || 'No se pudo descargar el adjunto.'
  }
}

async function guardarReporte(datos) {
  guardando.value = true
  error.value = ''
  exito.value = ''

  try {
    const creado = await crearReporte(datos)
    let avisoAdjunto = ''

    if (datos.archivo) {
      try {
        await subirArchivoReporte(creado.id, datos.archivo)
      } catch (e) {
        avisoAdjunto = ` El reporte se creó, pero no se pudo adjuntar el archivo: ${
          e?.message || 'inténtalo de nuevo desde el detalle.'
        }`
      }
    }

    mostrarFormulario.value = false
    await cargarReportes()
    exito.value = `Reporte #${creado.id} registrado.${avisoAdjunto}`
  } catch (e) {
    error.value = e?.message || 'No se pudo registrar el reporte.'
  } finally {
    guardando.value = false
  }
}

function nuevoReporte() {
  error.value = ''
  exito.value = ''
  detalleAbierto.value = null
  mostrarFormulario.value = true
}
</script>

<template>
  <main class="w-full text-[#242a35]">
    <div v-if="error" role="alert" class="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
      <span>{{ error }}</span>
      <button type="button" class="rounded-lg border border-[#8a1c14] px-3 py-1 hover:bg-white/60" @click="cargarReportes">
        Reintentar
      </button>
    </div>
    <p v-if="exito && !mostrarFormulario" role="status" class="mb-4 rounded-xl bg-[#d9f1e2] px-4 py-3 text-sm font-semibold text-[#285d3b]">
      {{ exito }}
    </p>

    <div v-if="!mostrarFormulario" class="flex flex-col gap-4">
      <header
        class="grid grid-cols-2 items-end gap-3 md:grid-cols-3 xl:grid-cols-7"
        aria-label="Filtros de reportes"
      >
        <label class="grid min-w-0 gap-1.5 text-xs font-semibold text-[#414752]">
          <span>Buscar estudiante</span>
          <input
            v-model="filtros.estudiante"
            type="search"
            placeholder="Nombre del estudiante"
            class="min-h-[42px] w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]"
          />
        </label>

        <label class="grid min-w-0 gap-1.5 text-xs font-semibold text-[#414752]">
          <span>Buscar docente</span>
          <input
            v-model="filtros.docente"
            type="search"
            placeholder="Nombre del docente"
            class="min-h-[42px] w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]"
          />
        </label>

        <label class="grid min-w-0 gap-1.5 text-xs font-semibold text-[#414752]">
          <span>Nivel</span>
          <select
            v-model="filtros.nivel"
            class="min-h-[42px] w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]"
          >
            <option value="">Todos</option>
            <option value="LICEO">Liceo</option>
            <option value="ESCUELA">Escuela</option>
          </select>
        </label>

        <label class="grid min-w-0 gap-1.5 text-xs font-semibold text-[#414752]">
          <span>Gravedad</span>
          <select
            v-model="filtros.gravedad"
            class="min-h-[42px] w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]"
          >
            <option value="">Todas</option>
            <option value="LEVE">Leve</option>
            <option value="GRAVE">Grave</option>
          </select>
        </label>

        <label class="grid min-w-0 gap-1.5 text-xs font-semibold text-[#414752]">
          <span>Tipo</span>
          <select
            v-model="filtros.categoria"
            class="min-h-[42px] w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]"
          >
            <option value="">Todos</option>
            <option value="CONDUCTUAL">Conductual</option>
            <option value="ACADEMICO">Académico</option>
          </select>
        </label>

        <label class="grid min-w-0 gap-1.5 text-xs font-semibold text-[#414752]">
          <span>Fecha</span>
          <input
            v-model="filtros.fecha"
            type="date"
            class="min-h-[42px] w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]"
          />
        </label>

        <button
          class="col-span-2 min-h-[42px] cursor-pointer whitespace-nowrap rounded-md border border-[#304bbc] bg-[#304bbc] px-4 text-sm font-bold text-white hover:bg-[#253d9f] md:col-span-3 xl:col-span-1"
          type="button"
          @click="nuevoReporte"
        >
          + Nuevo reporte
        </button>
      </header>

      <section class="rounded-[9px] border border-[#c8cbd1] bg-white p-4 shadow-sm" aria-label="Lista de reportes">
        <div class="overflow-x-auto">
          <table
            class="w-full border-collapse text-left text-[13px] [&_tbody_tr:last-child>td]:border-b-0"
          >
            <thead class="bg-[#f1f2f5] text-[#59606c]">
              <tr>
                <th scope="col" :class="claseEncabezado">N.º</th>
                <th scope="col" :class="claseEncabezado">Fecha / hora</th>
                <th scope="col" :class="claseEncabezado">Estudiante</th>
                <th scope="col" :class="claseEncabezado">Nivel</th>
                <th scope="col" :class="claseEncabezado">Tipo</th>
                <th scope="col" :class="claseEncabezado">Gravedad</th>
                <th scope="col" :class="claseEncabezado">Docente</th>
                <th scope="col" :class="claseEncabezado">Registrado por</th>
                <th scope="col" :class="claseEncabezado"><span class="sr-only">Detalle</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="cargando">
                <td colspan="9" class="border-b border-[#e1e3e7] px-6 py-6 text-center whitespace-normal text-[#777d87]">
                  Cargando reportes…
                </td>
              </tr>
              <template v-else>
                <template v-for="reporte in reportesPaginados" :key="reporte.id">
                  <tr>
                    <td
                      :class="[
                        claseCelda,
                        reporte.gravedad === 'GRAVE' ? 'border-l-4 border-l-[#d59a13]' : '',
                      ]"
                    >
                      #{{ reporte.id }}
                    </td>
                    <td :class="claseCelda">
                      {{ formatearFecha(reporte.fecha) }}
                      <span v-if="reporte.hora"> · {{ reporte.hora }}</span>
                    </td>
                    <td :class="claseCelda">{{ reporte.estudiante || '—' }}</td>
                    <td :class="claseCelda">{{ etiquetaNivel(reporte.nivel) }}</td>
                    <td :class="claseCelda">{{ etiquetaCategoria(reporte.categoria) }}</td>
                    <td :class="claseCelda">
                      <span
                        :class="[
                          'inline-block rounded-full px-[9px] py-1 text-xs font-bold',
                          claseGravedad(reporte.gravedad),
                        ]"
                      >
                        {{ etiquetaGravedad(reporte.gravedad) }}
                      </span>
                    </td>
                    <td :class="claseCelda">{{ reporte.docente || '—' }}</td>
                    <td :class="claseCelda">{{ reporte.usuario || '—' }}</td>
                    <td :class="claseCelda">
                      <button
                        class="cursor-pointer border-0 bg-transparent text-[#304bbc] underline"
                        type="button"
                        :aria-expanded="detalleAbierto === reporte.id"
                        @click="detalleAbierto = detalleAbierto === reporte.id ? null : reporte.id"
                      >
                        {{ detalleAbierto === reporte.id ? 'Ocultar' : 'Ver' }}
                      </button>
                    </td>
                  </tr>
                  <tr v-if="detalleAbierto === reporte.id">
                    <td
                      colspan="9"
                      class="whitespace-normal border-b border-[#e1e3e7] bg-[#f8f9fb] px-[10px] py-[11px] text-[#59606c]"
                    >
                      <div class="grid gap-2 text-[13px] sm:grid-cols-2">
                        <p class="m-0"><strong>Incidencia:</strong> {{ reporte.incidencia || '—' }}</p>
                        <p class="m-0"><strong>Defensa:</strong> {{ reporte.defensa || '—' }}</p>
                        <p class="m-0">
                          <strong>Artículo:</strong> {{ reporte.articulo || '—' }}
                          <span class="mx-1 text-[#aeb2b8]">·</span>
                          <strong>Reglamento:</strong> {{ reporte.reglamento || '—' }}
                        </p>
                        <p v-if="reporte.archivoNombre" class="m-0">
                          <strong>Adjunto:</strong>
                          <button
                            type="button"
                            class="cursor-pointer border-0 bg-transparent text-[#304bbc] underline"
                            @click="descargarAdjunto(reporte)"
                          >
                            {{ reporte.archivoNombre }}
                          </button>
                        </p>
                      </div>
                    </td>
                  </tr>
                </template>
                <tr v-if="!reportesFiltrados.length">
                  <td
                    class="border-b border-[#e1e3e7] px-6 py-6 text-center whitespace-normal text-[#777d87]"
                    colspan="9"
                  >
                    No hay reportes que coincidan con los filtros.
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>

        <footer class="mt-3 flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
          <p class="m-0 text-xs text-[#777d87]">
            Mostrando {{ reportesFiltrados.length }}
            {{ reportesFiltrados.length === 1 ? 'reporte' : 'reportes' }}
          </p>
          <div class="flex flex-wrap items-center gap-3">
            <button
              type="button"
              class="min-h-8 cursor-pointer rounded-[5px] border border-[#aeb2b8] bg-white px-2.5 text-xs text-[#414752] disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="cargando || !reportesFiltrados.length"
              @click="exportarReportes"
            >
              Exportar CSV
            </button>
            <nav class="flex items-center gap-3 text-xs text-[#59606c]" aria-label="Paginación de reportes">
              <button
                type="button"
                class="min-h-8 cursor-pointer rounded-[5px] border border-[#aeb2b8] bg-white px-2.5 text-xs text-[#414752] disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="paginaActual === 1"
                @click="paginaActual -= 1"
              >
                Anterior
              </button>
              <span>Página {{ paginaActual }} de {{ totalPaginas }}</span>
              <button
                type="button"
                class="min-h-8 cursor-pointer rounded-[5px] border border-[#aeb2b8] bg-white px-2.5 text-xs text-[#414752] disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="paginaActual === totalPaginas"
                @click="paginaActual += 1"
              >
                Siguiente
              </button>
            </nav>
          </div>
        </footer>
      </section>
    </div>

    <section v-else class="mx-auto w-full max-w-[1032px]">
      <header class="mx-4">
        <h1 class="m-0 text-[22px] font-bold">Nuevo reporte</h1>
      </header>
      <ReporteIncidente
        :guardando="guardando"
        @cancel="mostrarFormulario = false"
        @submit="guardarReporte"
      />
    </section>
  </main>
</template>

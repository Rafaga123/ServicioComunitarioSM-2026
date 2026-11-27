<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ReporteFicha from '@/components/reportes/ReporteFicha.vue'
import ReporteIncidente from '@/components/reportes/ReporteIncidente.vue'
import { norm } from '@/components/gestion-academica/helpers'
import { etiquetaNivel } from '@/services/auth'
import { obtenerEstudiante } from '@/services/estudiantes'
import {
  actualizarReporte,
  crearReporte,
  descargarArchivoReporte,
  descargarPdfReporte,
  eliminarReporte,
  etiquetaCategoria,
  etiquetaGravedad,
  listarTodosReportes,
  obtenerReporte,
  quitarArchivoReporte,
  subirArchivoReporte,
} from '@/services/reportes'

const route = useRoute()
const router = useRouter()

const reportes = ref([])
const cargando = ref(true)
const guardando = ref(false)
const error = ref('')
const exito = ref('')
const paginaActual = ref(1)
const reportesPorPagina = 10

const filtros = ref({
  estudiante: '',
  gravedad: '',
  categoria: '',
})

// La vista se controla por query para no crear rutas nuevas: el guard de
// permisos y el menú siguen usando únicamente el nombre `reportes`.
const vista = computed(() =>
  ['nuevo', 'editar'].includes(route.query.vista) ? 'formulario' : 'listado',
)
const idEdicion = computed(() =>
  route.query.vista === 'editar' && route.query.id ? Number(route.query.id) : null,
)
const verId = computed(() => (route.query.ver ? Number(route.query.ver) : null))

const reporteFicha = ref(null)
const estudianteFicha = ref(null)
const cargandoFicha = ref(false)
const errorFicha = ref('')
const exportandoPdf = ref(false)

const reporteEdicion = ref(null)
const cargandoEdicion = ref(false)
const errorEdicion = ref('')
const idEliminando = ref(null)

const claseCelda = 'whitespace-nowrap border-b border-[#e1e3e7] px-[10px] py-[11px]'
const claseEncabezado = `${claseCelda} font-bold`

let solicitudCarga = 0
let temporizadorFiltros = null

async function cargarReportes() {
  const solicitud = ++solicitudCarga
  cargando.value = true
  error.value = ''

  try {
    // El backend filtra por categoría y gravedad; el texto del estudiante
    // se refina en cliente.
    const { items } = await listarTodosReportes({
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

  return reportes.value.filter(
    (reporte) => !estudiante || norm(reporte.estudiante).includes(estudiante),
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

async function cargarFicha(id) {
  reporteFicha.value = null
  estudianteFicha.value = null
  errorFicha.value = ''
  if (!id) return

  cargandoFicha.value = true
  try {
    const reporte = await obtenerReporte(id)
    reporteFicha.value = reporte
    try {
      estudianteFicha.value = await obtenerEstudiante(reporte.idEstudiante)
    } catch {
      // El DTO ya trae nombre, cédula y nivel; grado/sección quedan como "—".
      estudianteFicha.value = null
    }
  } catch (e) {
    errorFicha.value = e?.message || 'No se pudo cargar la ficha del reporte.'
  } finally {
    cargandoFicha.value = false
  }
}

watch(verId, cargarFicha, { immediate: true })

watch(
  [vista, idEdicion],
  async ([modo, id]) => {
    reporteEdicion.value = null
    errorEdicion.value = ''
    if (modo !== 'formulario' || !id) return

    cargandoEdicion.value = true
    try {
      reporteEdicion.value = await obtenerReporte(id)
    } catch (e) {
      errorEdicion.value = e?.message || 'No se pudo cargar el reporte a editar.'
    } finally {
      cargandoEdicion.value = false
    }
  },
  { immediate: true },
)

onMounted(cargarReportes)
onBeforeUnmount(() => {
  clearTimeout(temporizadorFiltros)
  solicitudCarga += 1
})

function irNuevo() {
  error.value = ''
  exito.value = ''
  router.push({ name: 'reportes', query: { vista: 'nuevo' } })
}

function irEditar(id) {
  error.value = ''
  exito.value = ''
  router.push({ name: 'reportes', query: { vista: 'editar', id: String(id) } })
}

function volverListado() {
  router.push({ name: 'reportes' })
}

function abrirFicha(id) {
  router.push({ name: 'reportes', query: { ...route.query, ver: String(id) } })
}

function cerrarFicha() {
  const consulta = { ...route.query }
  delete consulta.ver
  router.push({ name: 'reportes', query: consulta })
}

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

function guardarDescarga({ blob, nombre }, nombrePorDefecto) {
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')

  enlace.href = url
  enlace.download = nombre || nombrePorDefecto
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  // Revocar de inmediato puede cancelar la descarga en algunos navegadores.
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}

async function descargarAdjunto(reporte) {
  try {
    guardarDescarga(
      await descargarArchivoReporte(reporte.id),
      `reporte-${reporte.id}`,
    )
  } catch (e) {
    error.value = e?.message || 'No se pudo descargar el adjunto.'
  }
}

async function descargarPdf(reporte) {
  if (exportandoPdf.value) return
  exportandoPdf.value = true
  errorFicha.value = ''
  try {
    guardarDescarga(
      await descargarPdfReporte(reporte.id),
      `reporte-${reporte.id}.pdf`,
    )
  } catch (e) {
    errorFicha.value = e?.message || 'No se pudo generar el PDF del reporte.'
  } finally {
    exportandoPdf.value = false
  }
}

async function guardarReporte(datos) {
  guardando.value = true
  error.value = ''
  exito.value = ''

  try {
    const id = idEdicion.value
    const guardado = id
      ? await actualizarReporte(id, datos)
      : await crearReporte(datos)

    let avisoAdjunto = ''
    try {
      if (datos.quitarAdjunto && guardado.archivoNombre) {
        await quitarArchivoReporte(guardado.id)
      }
      if (datos.archivo) {
        await subirArchivoReporte(guardado.id, datos.archivo)
      }
    } catch (e) {
      avisoAdjunto = ` El reporte se guardó, pero el adjunto no pudo actualizarse: ${
        e?.message || 'inténtalo de nuevo desde la ficha.'
      }`
    }

    await cargarReportes()
    exito.value = `Reporte #${guardado.id} ${id ? 'actualizado' : 'registrado'}.${avisoAdjunto}`
    router.push({ name: 'reportes', query: { ver: String(guardado.id) } })
  } catch (e) {
    error.value = e?.message || 'No se pudo guardar el reporte.'
  } finally {
    guardando.value = false
  }
}

async function eliminarReporteConfirmado() {
  const id = idEliminando.value
  if (!id) return

  idEliminando.value = null
  error.value = ''
  try {
    await eliminarReporte(id)
    await cargarReportes()
    router.push({ name: 'reportes' })
    exito.value = `Reporte #${id} eliminado.`
  } catch (e) {
    error.value = e?.message || 'No se pudo eliminar el reporte.'
  }
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

    <p
      v-if="exito && vista === 'listado' && !verId"
      role="status"
      class="mb-4 rounded-xl bg-[#d9f1e2] px-4 py-3 text-sm font-semibold text-[#285d3b]"
    >
      {{ exito }}
    </p>

    <div v-if="vista === 'listado'" class="flex flex-col gap-4">
      <header
        class="grid grid-cols-2 items-end gap-3 md:grid-cols-3 xl:grid-cols-4"
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

        <div class="col-span-2 flex items-end md:col-span-3 xl:col-span-1">
          <button
            type="button"
            class="min-h-[42px] cursor-pointer whitespace-nowrap rounded-md border border-[#304bbc] bg-[#304bbc] px-3 text-sm font-bold text-white hover:bg-[#253d9f]"
            @click="irNuevo"
          >
            + Nuevo reporte
          </button>
        </div>
      </header>

      <section class="rounded-[9px] border border-[#c8cbd1] bg-white p-4 shadow-sm" aria-label="Lista de reportes">
        <div class="overflow-x-auto">
          <table
            class="w-full border-collapse text-left text-[13px] [&_tbody_tr:last-child>td]:border-b-0"
          >
            <thead class="bg-[#f1f2f5] text-[#59606c]">
              <tr>
                <th scope="col" :class="claseEncabezado">Fecha / hora</th>
                <th scope="col" :class="claseEncabezado">Estudiante</th>
                <th scope="col" :class="claseEncabezado">Nivel</th>
                <th scope="col" :class="claseEncabezado">Tipo</th>
                <th scope="col" :class="claseEncabezado">Gravedad</th>
                <th scope="col" :class="claseEncabezado">Docente</th>
                <th scope="col" :class="claseEncabezado">Asignatura</th>
                <th scope="col" :class="claseEncabezado"><span class="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="cargando">
                <td colspan="8" class="border-b border-[#e1e3e7] px-6 py-6 text-center whitespace-normal text-[#777d87]">
                  Cargando reportes…
                </td>
              </tr>
              <template v-else>
                <tr v-for="reporte in reportesPaginados" :key="reporte.id">
                  <td
                    :class="[
                      claseCelda,
                      reporte.gravedad === 'GRAVE' ? 'border-l-4 border-l-[#d59a13]' : '',
                    ]"
                  >
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
                  <td :class="claseCelda">{{ reporte.asignatura || '—' }}</td>
                  <td :class="claseCelda">
                    <div class="flex flex-wrap items-center gap-2">
                      <button
                        class="cursor-pointer border-0 bg-transparent text-[#304bbc] underline"
                        type="button"
                        @click="abrirFicha(reporte.id)"
                      >
                        Ver
                      </button>
                      <button
                        class="cursor-pointer border-0 bg-transparent text-[#5b6a72] underline"
                        type="button"
                        @click="irEditar(reporte.id)"
                      >
                        Editar
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="!reportesFiltrados.length">
                  <td
                    class="border-b border-[#e1e3e7] px-6 py-6 text-center whitespace-normal text-[#777d87]"
                    colspan="8"
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
        </footer>
      </section>
    </div>

    <section v-else class="mx-auto w-full max-w-[1032px]">
      <header class="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p class="m-0 text-xs font-bold uppercase tracking-wide text-[#5b6a72]">Reportes</p>
          <h1 class="m-0 text-[22px] font-bold">
            {{ idEdicion ? `Editar reporte #${idEdicion}` : 'Nuevo reporte' }}
          </h1>
        </div>
        <button
          type="button"
          class="min-h-[38px] cursor-pointer rounded-lg border border-[#c8cbd1] bg-white px-3 text-sm font-semibold text-[#414752] hover:bg-[#f4f5f7]"
          @click="volverListado"
        >
          ← Volver al historial
        </button>
      </header>

      <p v-if="cargandoEdicion" class="mb-3 rounded-xl bg-[#eef3fb] px-4 py-2 text-sm text-[#233E47]">
        Cargando reporte…
      </p>

      <ReporteIncidente
        :guardando="guardando"
        :reporte="reporteEdicion"
        :error-carga="errorEdicion"
        @cancel="volverListado"
        @submit="guardarReporte"
      />
    </section>

    <ReporteFicha
      v-if="reporteFicha && vista === 'listado'"
      :reporte="reporteFicha"
      :estudiante="estudianteFicha"
      :cargando="cargandoFicha"
      :error="errorFicha"
      :exportando-pdf="exportandoPdf"
      @cerrar="cerrarFicha"
      @editar="irEditar"
      @eliminar="idEliminando = $event"
      @descargar="descargarAdjunto"
      @exportar-pdf="descargarPdf"
    />

    <div
      v-if="idEliminando"
      class="fixed inset-0 z-[60] flex items-center justify-center bg-[#0c1c22]/55 p-4"
      @click.self="idEliminando = null"
    >
      <section
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="eliminar-reporte-titulo"
        class="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"
      >
        <h2 id="eliminar-reporte-titulo" class="m-0 text-lg font-bold text-[#1b2a47]">
          Eliminar reporte #{{ idEliminando }}
        </h2>
        <p class="mt-2 text-sm text-[#59606c]">
          El reporte se dará de baja y dejará de aparecer en el historial. Esta acción no se puede deshacer desde la interfaz.
        </p>
        <div class="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            class="min-h-10 rounded-lg border border-[#c8cbd1] bg-white px-4 text-sm font-semibold text-[#414752] hover:bg-[#f4f5f7]"
            @click="idEliminando = null"
          >
            Cancelar
          </button>
          <button
            type="button"
            class="min-h-10 rounded-lg border border-[#b23b32] bg-[#b23b32] px-4 text-sm font-bold text-white hover:bg-[#8a1c14]"
            @click="eliminarReporteConfirmado"
          >
            Eliminar
          </button>
        </div>
      </section>
    </div>
  </main>
</template>

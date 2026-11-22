<script setup>
import { computed, ref, watch } from 'vue'
import ReporteIncidente from '@/components/reportes/ReporteIncidente.vue'

const estudiantes = ['Brandon', 'Kevin Valera', 'Hermes Morado']
const reportes = ref([
  {
    id: 1,
    fecha: '2026-10-24',
    estudiante: 'Brandon',
    curso: '3ro B',
    tipo: 'Conductual',
    gravedad: 'Grave',
    docente: 'Prof. Vásquez',
    estado: 'Enviado',
    descripcion: 'Reporte de conducta del estudiante.',
  },
  {
    id: 2,
    fecha: '2026-10-24',
    estudiante: 'Kevin Valera',
    curso: '1ro B',
    tipo: 'Conductual',
    gravedad: 'Leve',
    docente: 'Prof. Vásquez',
    estado: 'Atendido',
    descripcion: 'Reporte de conducta del estudiante.',
  },
  {
    id: 3,
    fecha: '2026-10-24',
    estudiante: 'Hermes Morado',
    curso: '4to U',
    tipo: 'Académico',
    gravedad: 'Leve',
    docente: 'Vásquez',
    estado: 'Borrador',
    descripcion: 'Reporte académico del estudiante.',
  },
])

const mostrarFormulario = ref(false)
const detalleAbierto = ref(null)
const paginaActual = ref(1)
const reportesPorPagina = 10
const filtros = ref({
  estudiante: '',
  estado: '',
  curso: '',
  gravedad: '',
  tipo: '',
  fecha: '',
})

// Clases compartidas por encabezados y celdas de la tabla
const claseCelda = 'whitespace-nowrap border-b border-[#e1e3e7] px-[10px] py-[11px]'
const claseEncabezado = `${claseCelda} font-bold`

const reportesFiltrados = computed(() => {
  const busqueda = filtros.value.estudiante.trim().toLocaleLowerCase()

  return reportes.value.filter((reporte) => {
    return (
      (!busqueda || reporte.estudiante.toLocaleLowerCase().includes(busqueda)) &&
      (!filtros.value.estado || reporte.estado === filtros.value.estado) &&
      (!filtros.value.curso ||
        reporte.curso.toLocaleLowerCase().includes(filtros.value.curso.toLocaleLowerCase())) &&
      (!filtros.value.gravedad || reporte.gravedad === filtros.value.gravedad) &&
      (!filtros.value.tipo || reporte.tipo === filtros.value.tipo) &&
      (!filtros.value.fecha || reporte.fecha === filtros.value.fecha)
    )
  })
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
  },
  { deep: true },
)

function formatearFecha(fecha) {
  return new Intl.DateTimeFormat('es', {
    day: 'numeric',
    month: 'short',
  }).format(new Date(`${fecha}T12:00:00`))
}

function claseGravedad(gravedad) {
  return gravedad === 'Grave'
    ? 'bg-[#faedc8] text-[#72520b]'
    : 'bg-[#d9f1e2] text-[#285d3b]'
}

function exportarReportes() {
  const encabezados = [
    'N.º',
    'Fecha',
    'Hora',
    'Estudiante',
    'Curso',
    'Tipo',
    'Gravedad',
    'Docente',
    'Estado',
  ]
  const filas = reportesFiltrados.value.map((reporte) => [
    reporte.id,
    reporte.fecha,
    reporte.hora || '',
    reporte.estudiante,
    reporte.curso,
    reporte.tipo,
    reporte.gravedad,
    reporte.docente,
    reporte.estado,
  ])
  const csv = [encabezados, ...filas]
    .map((fila) => fila.map((valor) => `"${String(valor).replaceAll('"', '""')}"`).join(','))
    .join('\r\n')
  const archivo = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' })
  const enlace = document.createElement('a')
  const url = URL.createObjectURL(archivo)

  enlace.href = url
  enlace.download = 'reportes.csv'
  enlace.click()
  URL.revokeObjectURL(url)
}

function guardarReporte(datos, estado) {
  reportes.value.unshift({
    id: Math.max(...reportes.value.map((reporte) => reporte.id), 199) + 1,
    fecha: datos.fechaHora,
    hora: datos.hora,
    estudiante: datos.estudiante || 'Sin estudiante',
    curso: datos.curso || 'Sin curso',
    tipo: datos.tipoIncidente === 'academico' ? 'Académico' : 'Conductual',
    gravedad: datos.gravedad === 'grave' ? 'Grave' : 'Leve',
    docente: datos.docente || 'Sin docente',
    estado,
    descripcion: datos.descripcion,
  })
  mostrarFormulario.value = false
}
</script>

<template>
  <main class="w-full text-[#242a35]">
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
            list="estudiantes-disponibles"
            placeholder="Nombre del estudiante"
            class="min-h-[42px] w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]"
          />
          <datalist id="estudiantes-disponibles">
            <option v-for="estudiante in estudiantes" :key="estudiante" :value="estudiante" />
          </datalist>
        </label>

        <label class="grid min-w-0 gap-1.5 text-xs font-semibold text-[#414752]">
          <span>Estado</span>
          <select
            v-model="filtros.estado"
            class="min-h-[42px] w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]"
          >
            <option value="">Todos</option>
            <option value="Enviado">Enviado</option>
            <option value="Atendido">Atendido</option>
            <option value="Borrador">Borrador</option>
          </select>
        </label>

        <label class="grid min-w-0 gap-1.5 text-xs font-semibold text-[#414752]">
          <span>Curso</span>
          <input
            v-model="filtros.curso"
            type="search"
            placeholder="Ej. 3ro B"
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
            <option value="Leve">Leve</option>
            <option value="Grave">Grave</option>
          </select>
        </label>

        <label class="grid min-w-0 gap-1.5 text-xs font-semibold text-[#414752]">
          <span>Tipo</span>
          <select
            v-model="filtros.tipo"
            class="min-h-[42px] w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]"
          >
            <option value="">Todos</option>
            <option value="Conductual">Conductual</option>
            <option value="Académico">Académico</option>
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
          @click="mostrarFormulario = true"
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
                <th scope="col" :class="claseEncabezado">Curso</th>
                <th scope="col" :class="claseEncabezado">Tipo</th>
                <th scope="col" :class="claseEncabezado">Gravedad</th>
                <th scope="col" :class="claseEncabezado">Docente</th>
                <th scope="col" :class="claseEncabezado">Estado</th>
                <th scope="col" :class="claseEncabezado"><span class="sr-only">Detalle</span></th>
              </tr>
            </thead>
            <tbody>
              <template v-for="reporte in reportesPaginados" :key="reporte.id">
                <tr>
                  <td
                    :class="[
                      claseCelda,
                      reporte.estado === 'Enviado' ? 'border-l-4 border-l-[#d59a13]' : '',
                    ]"
                  >
                    #{{ reporte.id }}
                  </td>
                  <td :class="claseCelda">
                    {{ formatearFecha(reporte.fecha) }}
                    <span v-if="reporte.hora"> · {{ reporte.hora }}</span>
                  </td>
                  <td :class="claseCelda">{{ reporte.estudiante }}</td>
                  <td :class="claseCelda">{{ reporte.curso }}</td>
                  <td :class="claseCelda">{{ reporte.tipo }}</td>
                  <td :class="claseCelda">
                    <span
                      :class="[
                        'inline-block rounded-full px-[9px] py-1 text-xs font-bold',
                        claseGravedad(reporte.gravedad),
                      ]"
                    >
                      {{ reporte.gravedad }}
                    </span>
                  </td>
                  <td :class="claseCelda">{{ reporte.docente }}</td>
                  <td :class="claseCelda">
                    <span
                      class="inline-block rounded-full bg-[#e8eaf0] px-[9px] py-1 text-xs font-bold text-[#3e4552]"
                    >
                      {{ reporte.estado }}
                    </span>
                  </td>
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
                    <strong>Descripción:</strong> {{ reporte.descripcion }}
                  </td>
                </tr>
              </template>
              <tr v-if="reportesPaginados.length === 0">
                <td
                  class="border-b border-[#e1e3e7] px-6 py-6 text-center whitespace-normal text-[#777d87]"
                  colspan="9"
                >
                  No hay reportes que coincidan con los filtros.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <footer class="mt-3 flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
          <p class="m-0 text-xs text-[#777d87]">Mostrando {{ reportesFiltrados.length }} reportes</p>
          <div class="flex flex-wrap items-center gap-3">
            <button
              type="button"
              class="min-h-8 cursor-pointer rounded-[5px] border border-[#aeb2b8] bg-white px-2.5 text-xs text-[#414752] disabled:cursor-not-allowed disabled:opacity-50"
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
        @cancel="mostrarFormulario = false"
        @save-draft="guardarReporte($event, 'Borrador')"
        @submit="guardarReporte($event, 'Enviado')"
      />
    </section>
  </main>
</template>

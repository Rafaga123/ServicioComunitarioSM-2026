<script setup>
import { computed, ref, watch } from 'vue'
import ReporteIncidente from './ReporteIncidente.vue'

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
  <main class="reports-page">
    <div v-if="!mostrarFormulario" class="reports-content">
      <header class="filters" aria-label="Filtros de reportes">
        <label class="filter-field">
          <span>Buscar estudiante</span>
          <input
            v-model="filtros.estudiante"
            type="search"
            list="estudiantes-disponibles"
            placeholder="Nombre del estudiante"
          />
          <datalist id="estudiantes-disponibles">
            <option v-for="estudiante in estudiantes" :key="estudiante" :value="estudiante" />
          </datalist>
        </label>

        <label class="filter-field">
          <span>Estado</span>
          <select v-model="filtros.estado">
            <option value="">Todos</option>
            <option value="Enviado">Enviado</option>
            <option value="Atendido">Atendido</option>
            <option value="Borrador">Borrador</option>
          </select>
        </label>

        <label class="filter-field">
          <span>Curso</span>
          <input v-model="filtros.curso" type="search" placeholder="Ej. 3ro B" />
        </label>

        <label class="filter-field">
          <span>Gravedad</span>
          <select v-model="filtros.gravedad">
            <option value="">Todas</option>
            <option value="Leve">Leve</option>
            <option value="Grave">Grave</option>
          </select>
        </label>

        <label class="filter-field">
          <span>Tipo</span>
          <select v-model="filtros.tipo">
            <option value="">Todos</option>
            <option value="Conductual">Conductual</option>
            <option value="Académico">Académico</option>
          </select>
        </label>

        <label class="filter-field">
          <span>Fecha</span>
          <input v-model="filtros.fecha" type="date" />
        </label>

        <button class="new-report-button" type="button" @click="mostrarFormulario = true">
          + Nuevo reporte
        </button>
      </header>

      <section class="table-card" aria-label="Lista de reportes">
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">N.º</th>
                <th scope="col">Fecha / hora</th>
                <th scope="col">Estudiante</th>
                <th scope="col">Curso</th>
                <th scope="col">Tipo</th>
                <th scope="col">Gravedad</th>
                <th scope="col">Docente</th>
                <th scope="col">Estado</th>
                <th scope="col"><span class="sr-only">Detalle</span></th>
              </tr>
            </thead>
            <tbody>
              <template v-for="reporte in reportesPaginados" :key="reporte.id">
                <tr :class="{ 'is-pending': reporte.estado === 'Enviado' }">
                  <td>#{{ reporte.id }}</td>
                  <td>
                    {{ formatearFecha(reporte.fecha) }}
                    <span v-if="reporte.hora"> · {{ reporte.hora }}</span>
                  </td>
                  <td>{{ reporte.estudiante }}</td>
                  <td>{{ reporte.curso }}</td>
                  <td>{{ reporte.tipo }}</td>
                  <td>
                    <span class="badge" :class="`badge-${reporte.gravedad.toLowerCase()}`">
                      {{ reporte.gravedad }}
                    </span>
                  </td>
                  <td>{{ reporte.docente }}</td>
                  <td>
                    <span class="badge badge-status">{{ reporte.estado }}</span>
                  </td>
                  <td>
                    <button
                      class="details-button"
                      type="button"
                      :aria-expanded="detalleAbierto === reporte.id"
                      @click="detalleAbierto = detalleAbierto === reporte.id ? null : reporte.id"
                    >
                      {{ detalleAbierto === reporte.id ? 'Ocultar' : 'Ver' }}
                    </button>
                  </td>
                </tr>
                <tr v-if="detalleAbierto === reporte.id" class="details-row">
                  <td colspan="9"><strong>Descripción:</strong> {{ reporte.descripcion }}</td>
                </tr>
              </template>
              <tr v-if="reportesPaginados.length === 0">
                <td class="empty-state" colspan="9">No hay reportes que coincidan con los filtros.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <footer class="table-footer">
          <p class="table-note">Mostrando {{ reportesFiltrados.length }} reportes</p>
          <div class="table-tools">
            <button type="button" class="table-tool-button" @click="exportarReportes">
              Exportar CSV
            </button>
            <nav class="pagination" aria-label="Paginación de reportes">
              <button
                type="button"
                class="table-tool-button"
                :disabled="paginaActual === 1"
                @click="paginaActual -= 1"
              >
                Anterior
              </button>
              <span>Página {{ paginaActual }} de {{ totalPaginas }}</span>
              <button
                type="button"
                class="table-tool-button"
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

    <section v-else class="form-page">
      <header class="form-page-header">
        <h1>Nuevo reporte</h1>
      </header>
      <ReporteIncidente
        @cancel="mostrarFormulario = false"
        @save-draft="guardarReporte($event, 'Borrador')"
        @submit="guardarReporte($event, 'Enviado')"
      />
    </section>
  </main>
</template>

<style scoped>
@import './css/ReportesView.css';
</style>

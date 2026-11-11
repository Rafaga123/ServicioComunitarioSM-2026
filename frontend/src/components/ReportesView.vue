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
    docente: 'Prof. Vásquez',
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
  const encabezados = ['N.º', 'Fecha', 'Estudiante', 'Curso', 'Tipo', 'Gravedad', 'Docente', 'Estado']
  const filas = reportesFiltrados.value.map((reporte) => [
    reporte.id,
    reporte.fecha,
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
    estudiante: datos.estudiante || 'Sin estudiante',
    curso: datos.curso || 'Sin curso',
    tipo: datos.tipoIncidente === 'academico' ? 'Académico' : 'Conductual',
    gravedad: datos.gravedad === 'grave' ? 'Grave' : 'Leve',
    docente: 'Prof. Vásquez',
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
                <th scope="col">Fecha</th>
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
                  <td>{{ formatearFecha(reporte.fecha) }}</td>
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
.reports-page {
  box-sizing: border-box;
  min-height: 100vh;
  padding: 28px;
  background: #f1f2f5;
  color: #242a35;
  font-family: Arial, sans-serif;
}

.reports-content {
  display: grid;
  gap: 16px;
}

.filters {
  display: grid;
  grid-template-columns: repeat(6, minmax(110px, 1fr)) auto;
  align-items: end;
  gap: 12px;
}

.filter-field {
  display: grid;
  min-width: 0;
  gap: 5px;
  color: #414752;
  font-size: 12px;
  font-weight: 600;
}

.filter-field input,
.filter-field select {
  box-sizing: border-box;
  width: 100%;
  min-height: 42px;
  padding: 8px 10px;
  border: 1px solid #aeb2b8;
  border-radius: 6px;
  background: #fff;
  color: #242a35;
  font: inherit;
  font-size: 14px;
}

.filter-field input:focus,
.filter-field select:focus {
  outline: 2px solid #3454c5;
  outline-offset: 1px;
}

.new-report-button {
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid #304bbc;
  border-radius: 6px;
  background: #304bbc;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
}

.new-report-button:hover {
  background: #253d9f;
}

.table-card {
  padding: 16px;
  border: 1px solid #c8cbd1;
  border-radius: 9px;
  background: #fff;
  box-shadow: 0 1px 2px rgb(15 23 42 / 5%);
}

.table-scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 13px;
}

thead {
  background: #f1f2f5;
  color: #59606c;
}

th,
td {
  padding: 11px 10px;
  border-bottom: 1px solid #e1e3e7;
  white-space: nowrap;
}

th {
  font-weight: 700;
}

tbody tr:last-child td {
  border-bottom: 0;
}

.is-pending td:first-child {
  border-left: 4px solid #d59a13;
}

.badge {
  display: inline-block;
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.badge-leve {
  background: #d9f1e2;
  color: #285d3b;
}

.badge-grave {
  background: #faedc8;
  color: #72520b;
}

.badge-status {
  background: #e8eaf0;
  color: #3e4552;
}

.details-button {
  border: 0;
  background: transparent;
  color: #304bbc;
  cursor: pointer;
  font: inherit;
  text-decoration: underline;
}

.details-row td {
  background: #f8f9fb;
  color: #59606c;
  white-space: normal;
}

.empty-state {
  padding: 24px;
  color: #777d87;
  text-align: center;
}

.table-note {
  margin: 0;
  color: #777d87;
  font-size: 12px;
}

.table-footer,
.table-tools,
.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-footer {
  justify-content: space-between;
  margin-top: 12px;
}

.table-tools {
  flex-wrap: wrap;
}

.table-tool-button {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid #aeb2b8;
  border-radius: 5px;
  background: #fff;
  color: #414752;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
}

.table-tool-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.pagination {
  color: #59606c;
  font-size: 12px;
}

.form-page {
  width: min(100%, 1032px);
  margin: 0 auto;
}

.form-page-header {
  margin: 0 16px;
}

.form-page-header h1 {
  margin: 0;
  font-size: 22px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  clip-path: inset(50%);
}

@media (max-width: 1050px) {
  .filters {
    grid-template-columns: repeat(3, minmax(120px, 1fr));
  }
}

@media (max-width: 600px) {
  .reports-page {
    padding: 16px;
  }

  .filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .new-report-button {
    grid-column: 1 / -1;
  }

  .table-footer,
  .table-tools {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

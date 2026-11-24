<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRecursoPaginado } from '@/composables/useRecursoPaginado'
import {
  listarAuditorias,
  listarTodasAuditorias,
  MODULOS_AUDITORIA,
  ACCIONES_AUDITORIA,
} from '@/services/auditorias'

const POR_PAGINA = 10

// Los filtros los aplica el backend (ilike en usuario/módulo/acción y fecha
// exacta). El campo de usuario se retrasa un poco para no pedir una página por
// tecla; el resto recarga en cuanto cambia.
const filtroUsuario = ref('')
const filtroModulo = ref('')
const filtroAccion = ref('')
const filtroFecha = ref('')
const datos = reactive({ auditorias: [] })

const filtrosActuales = () => ({
  usuario: filtroUsuario.value.trim() || undefined,
  modulo: filtroModulo.value || undefined,
  accion: filtroAccion.value.trim() || undefined,
  fecha: filtroFecha.value || undefined,
})

const auditorias = useRecursoPaginado({
  listar: (args) => listarAuditorias({ ...args, ...filtrosActuales() }),
  listarTodos: () => listarTodasAuditorias(filtrosActuales()),
  asignar: (items) => { datos.auditorias = items },
  porDefecto: POR_PAGINA,
})
const api = auditorias.estado

const hayFiltros = computed(() =>
  Boolean(
    filtroUsuario.value.trim() ||
    filtroModulo.value ||
    filtroAccion.value ||
    filtroFecha.value,
  ),
)

const limpiarFiltros = () => {
  filtroUsuario.value = ''
  filtroModulo.value = ''
  filtroAccion.value = ''
  filtroFecha.value = ''
}

let temporizadorUsuario
watch(filtroUsuario, () => {
  clearTimeout(temporizadorUsuario)
  temporizadorUsuario = setTimeout(() => recargar(1), 300)
})
watch([filtroModulo, filtroAccion, filtroFecha], () => recargar(1))
watch(() => api.size, () => recargar(1))
onBeforeUnmount(() => clearTimeout(temporizadorUsuario))

const recargar = (pagina = 1) => auditorias.cargar(pagina)
onMounted(() => recargar(1))

const totalPaginas = computed(() => Math.max(1, Math.ceil(api.total / api.size)))
const pg = computed(() => Math.min(Math.max(1, api.page), totalPaginas.value))
const desde = computed(() => (api.total ? (pg.value - 1) * api.size + 1 : 0))
const hasta = computed(() => Math.min(pg.value * api.size, api.total))

const irPagina = (n) => {
  const destino = Math.min(Math.max(1, n), totalPaginas.value)
  if (destino !== api.page) recargar(destino)
}

const formatearFecha = (iso) => {
  if (!iso) return '—'
  const fecha = new Date(iso)
  if (Number.isNaN(fecha.getTime())) return iso
  return new Intl.DateTimeFormat('es-VE', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(fecha)
}

const claseAccion = (accion) => {
  if (accion === 'CREAR') return 'bg-emerald-100 text-emerald-800'
  if (accion === 'ACTUALIZAR') return 'bg-blue-100 text-blue-800'
  if (accion === 'ELIMINAR') return 'bg-red-100 text-red-800'
  return 'bg-amber-100 text-amber-800'
}

// ───────────── Exportación a CSV ─────────────
const exportando = ref(false)
const errorExportar = ref('')

const exportarCSV = async () => {
  exportando.value = true
  errorExportar.value = ''
  try {
    const { items } = await listarTodasAuditorias(filtrosActuales())
    if (!items.length) return

    const escapar = (valor) => `"${String(valor ?? '').replace(/"/g, '""')}"`
    const encabezados = ['N.º', 'Fecha / Hora', 'Usuario', 'Acción', 'Módulo', 'Detalle']
    const filas = items.map((log, index) => [
      escapar(index + 1),
      escapar(formatearFecha(log.fechaCreacion)),
      escapar(log.usuario),
      escapar(log.accion),
      escapar(log.modulo),
      escapar(log.descripcion),
    ].join(','))

    const contenido = [encabezados.map(escapar).join(','), ...filas].join('\n')
    const url = URL.createObjectURL(new Blob(['\uFEFF' + contenido], { type: 'text/csv;charset=utf-8;' }))
    const enlace = document.createElement('a')
    enlace.href = url
    enlace.setAttribute('download', `auditoria_${new Date().toISOString().slice(0, 10)}.csv`)
    document.body.appendChild(enlace)
    enlace.click()
    document.body.removeChild(enlace)
    URL.revokeObjectURL(url)
  } catch (error) {
    errorExportar.value = error?.message || 'No se pudo exportar la auditoría.'
  } finally {
    exportando.value = false
  }
}
</script>

<template>
  <div class="w-full space-y-6">
    <!-- Filtros enviados al backend -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-4">
      <div>
        <label for="aud-usuario" class="mb-1.5 block text-xs font-semibold text-gray-600">Usuario</label>
        <input id="aud-usuario" v-model="filtroUsuario" type="search" placeholder="Nombre de usuario"
               class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-600" />
      </div>
      <div>
        <label for="aud-modulo" class="mb-1.5 block text-xs font-semibold text-gray-600">Módulo</label>
        <select id="aud-modulo" v-model="filtroModulo"
                class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-600">
          <option value="">Todos</option>
          <option v-for="modulo in MODULOS_AUDITORIA" :key="modulo" :value="modulo">{{ modulo }}</option>
        </select>
      </div>
      <div>
        <label for="aud-accion" class="mb-1.5 block text-xs font-semibold text-gray-600">Acción</label>
        <input id="aud-accion" v-model="filtroAccion" type="search" list="sugerencias-accion" placeholder="Ej: CREAR"
               class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-600" />
        <datalist id="sugerencias-accion">
          <option v-for="accion in ACCIONES_AUDITORIA" :key="accion" :value="accion"></option>
        </datalist>
      </div>
      <div>
        <label for="aud-fecha" class="mb-1.5 block text-xs font-semibold text-gray-600">Fecha</label>
        <input id="aud-fecha" v-model="filtroFecha" type="date"
               class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-600" />
      </div>
    </div>

    <div class="flex flex-wrap items-center justify-between gap-3">
      <button v-if="hayFiltros" type="button" class="text-sm font-medium text-blue-600 hover:underline" @click="limpiarFiltros">
        Limpiar filtros
      </button>
      <span v-else class="text-sm text-gray-500">Historial de acciones del sistema</span>
      <label class="flex items-center gap-2 text-xs font-semibold text-gray-600">
        Por página
        <select v-model.number="api.size" class="rounded-lg border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-700">
          <option :value="10">10</option>
          <option :value="25">25</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </label>
    </div>

    <div class="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <p v-if="api.error" role="alert" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
        {{ api.error }}
        <button type="button" class="ml-2 font-bold underline" @click="recargar(1)">Reintentar</button>
      </p>
      <p v-if="errorExportar" role="alert" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
        {{ errorExportar }}
      </p>

      <div class="overflow-x-auto">
        <table class="w-full border-collapse text-left">
          <thead>
            <tr class="bg-gray-100 text-xs font-semibold text-gray-600">
              <th class="rounded-l-lg px-4 py-3">N.º</th>
              <th class="px-4 py-3">Fecha / hora</th>
              <th class="px-4 py-3">Usuario</th>
              <th class="px-4 py-3">Acción</th>
              <th class="px-4 py-3">Módulo</th>
              <th class="rounded-r-lg px-4 py-3">Detalle</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 text-sm text-gray-700">
            <tr v-for="(log, index) in datos.auditorias" :key="log.id" class="transition-colors hover:bg-gray-50/80">
              <td class="px-4 py-3.5 font-medium text-gray-900">#{{ (pg - 1) * api.size + index + 1 }}</td>
              <td class="whitespace-nowrap px-4 py-3.5 text-gray-600">{{ formatearFecha(log.fechaCreacion) }}</td>
              <td class="px-4 py-3.5 font-medium text-gray-900">{{ log.usuario || '—' }}</td>
              <td class="px-4 py-3.5">
                <span class="rounded-full px-3 py-0.5 text-xs font-medium" :class="claseAccion(log.accion)">
                  {{ log.accion }}
                </span>
              </td>
              <td class="px-4 py-3.5">{{ log.modulo }}</td>
              <td class="px-4 py-3.5 text-gray-600">{{ log.descripcion }}</td>
            </tr>

            <tr v-if="api.loading && !datos.auditorias.length">
              <td colspan="6" class="py-8 text-center text-sm text-gray-400">Cargando auditoría…</td>
            </tr>
            <tr v-if="!api.loading && !datos.auditorias.length">
              <td colspan="6" class="py-8 text-center text-sm text-gray-400">
                No se encontraron registros de auditoría con los filtros seleccionados.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-2 flex flex-wrap items-center justify-between gap-4 border-t border-gray-100 pt-4 text-xs text-gray-500">
        <span>Mostrando {{ desde }}–{{ hasta }} de {{ api.total }} registros</span>
        <div class="flex flex-wrap items-center gap-2">
          <button type="button" :disabled="exportando || !api.total" @click="exportarCSV"
                  class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-400">
            {{ exportando ? 'Exportando…' : 'Exportar CSV' }}
          </button>
          <button type="button" :disabled="pg === 1 || api.loading" @click="irPagina(pg - 1)"
                  class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 disabled:cursor-not-allowed disabled:text-gray-400">Anterior</button>
          <span class="px-2 font-medium text-gray-600">Página {{ pg }} de {{ totalPaginas }}</span>
          <button type="button" :disabled="pg === totalPaginas || api.loading" @click="irPagina(pg + 1)"
                  class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 disabled:cursor-not-allowed disabled:text-gray-400">Siguiente</button>
        </div>
      </div>
    </div>
  </div>
</template>

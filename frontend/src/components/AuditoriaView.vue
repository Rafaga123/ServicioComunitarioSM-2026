<script setup>
import { ref, computed } from 'vue'

// --- DATOS SIMULADOS ---
const registros = ref([
    {
        id: 1,
        fechaISO: '2026-11-15',
        fechaTexto: '15 nov, 07:45 AM',
        usuario: 'rtelles',
        accion: 'Crear',
        modulo: 'Retardos',
        detalle: 'Registro retardo #145'
    },
    {
        id: 2,
        fechaISO: '2026-11-15',
        fechaTexto: '15 nov, 08:10 AM',
        usuario: 'mvillanueva',
        accion: 'Anular',
        modulo: 'Retardos',
        detalle: 'Anuló #142, motivo: error de registro'
    },
    {
        id: 3,
        fechaISO: '2026-11-14',
        fechaTexto: '14 nov, 09:00 AM',
        usuario: 'kvarela',
        accion: 'Iniciar sesión',
        modulo: 'Acceso',
        detalle: 'Ingreso exitoso al sistema'
    },
    {
        id: 4,
        fechaISO: '2026-11-14',
        fechaTexto: '14 nov, 10:25 AM',
        usuario: 'kvarela',
        accion: 'Actualizar',
        modulo: 'Usuarios',
        detalle: 'Cambio de rol para usuario rtelles'
    }
])

// --- VARIABLES REACTIVAS DE FILTRO (Usuario, Módulo y Fecha) ---
const filtroUsuario = ref('')
const filtroModulo = ref('')
const filtroFecha = ref('')

const hayFiltrosActivos = computed(() => {
    return (
        filtroUsuario.value.trim() !== '' ||
        filtroModulo.value !== '' ||
        filtroFecha.value !== ''
    )
})

const limpiarFiltros = () => {
    filtroUsuario.value = ''
    filtroModulo.value = ''
    filtroFecha.value = ''
}

// --- LÓGICA DE FILTRADO EN TIEMPO REAL ---
const registrosFiltrados = computed(() => {
    return registros.value.filter((log) => {
        const coincideUsuario = log.usuario
            .toLowerCase()
            .includes(filtroUsuario.value.trim().toLowerCase())
        const coincideModulo = filtroModulo.value === '' || log.modulo === filtroModulo.value
        const coincideFecha = filtroFecha.value === '' || log.fechaISO === filtroFecha.value

        return coincideUsuario && coincideModulo && coincideFecha
    })
})

// --- LÓGICA DE EXPORTACIÓN A CSV ---
const exportarCSV = () => {
    if (registrosFiltrados.value.length === 0) return

    const encabezados = ['N.º', 'Fecha / Hora', 'Usuario', 'Acción', 'Módulo', 'Detalle']

    const escaparCelda = (valor) => {
        const texto = String(valor ?? '').replace(/"/g, '""')
        return `"${texto}"`
    }

    const filas = registrosFiltrados.value.map((log, index) => [
        escaparCelda(index + 1),
        escaparCelda(log.fechaTexto),
        escaparCelda(log.usuario),
        escaparCelda(log.accion),
        escaparCelda(log.modulo),
        escaparCelda(log.detalle)
    ])

    const contenidoCSV = [
        encabezados.map(escaparCelda).join(','),
        ...filas.map((fila) => fila.join(','))
    ].join('\n')

    const blob = new Blob(['\uFEFF' + contenidoCSV], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)

    const enlace = document.createElement('a')
    const fechaActual = new Date().toISOString().slice(0, 10)
    enlace.href = url
    enlace.setAttribute('download', `auditoria_${fechaActual}.csv`)

    document.body.appendChild(enlace)
    enlace.click()
    document.body.removeChild(enlace)
    URL.revokeObjectURL(url)
}
</script>

<template>
    <div class="w-full space-y-6">
        <!-- Filtros superiores (3 columnas alineadas con el resto del sistema) -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1.5">Usuario</label>
                <input v-model="filtroUsuario" type="text" placeholder="Nombre de usuario"
                    class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent" />
            </div>

            <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1.5">Módulo</label>
                <select v-model="filtroModulo"
                    class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent">
                    <option value="">Todos</option>
                    <option value="Retardos">Retardos</option>
                    <option value="Reportes">Reportes</option>
                    <option value="Usuarios">Usuarios</option>
                    <option value="Acceso">Acceso</option>
                </select>
            </div>

            <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1.5">Fecha</label>
                <input v-model="filtroFecha" type="date"
                    class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent" />
            </div>
        </div>

        <!-- Tarjeta Blanca con la Tabla -->
        <div class="bg-white border border-gray-200 rounded-xl shadow-sm p-5">
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-gray-100 text-gray-600 text-xs font-semibold">
                            <th class="py-3 px-4 rounded-l-lg">N.º</th>
                            <th class="py-3 px-4">Fecha / hora</th>
                            <th class="py-3 px-4">Usuario</th>
                            <th class="py-3 px-4">Acción</th>
                            <th class="py-3 px-4">Módulo</th>
                            <th class="py-3 px-4 rounded-r-lg">Detalle</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100 text-sm text-gray-700">
                        <tr v-for="(log, index) in registrosFiltrados" :key="log.id"
                            class="hover:bg-gray-50/80 transition-colors">
                            <td class="py-3.5 px-4 font-medium text-gray-900">#{{ index + 1 }}</td>
                            <td class="py-3.5 px-4 text-gray-600 whitespace-nowrap">{{ log.fechaTexto }}</td>
                            <td class="py-3.5 px-4 font-medium text-gray-900">{{ log.usuario }}</td>
                            <td class="py-3.5 px-4">
                                <span :class="{
                                    'bg-emerald-100 text-emerald-800': log.accion === 'Crear',
                                    'bg-blue-100 text-blue-800': log.accion === 'Actualizar',
                                    'bg-amber-100 text-amber-800': log.accion === 'Anular',
                                    'bg-gray-100 text-gray-700': log.accion === 'Iniciar sesión'
                                }" class="px-3 py-0.5 rounded-full text-xs font-medium">
                                    {{ log.accion }}
                                </span>
                            </td>
                            <td class="py-3.5 px-4">{{ log.modulo }}</td>
                            <td class="py-3.5 px-4 text-gray-600">{{ log.detalle }}</td>
                        </tr>

                        <tr v-if="registrosFiltrados.length === 0">
                            <td colspan="6" class="py-8 text-center text-gray-400 text-sm">
                                No se encontraron registros de auditoría con los filtros seleccionados.
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Pie de tabla -->
            <div
                class="flex flex-wrap items-center justify-between gap-4 pt-4 mt-2 border-t border-gray-100 text-xs text-gray-500">
                <div class="flex items-center gap-3">
                    <span>Mostrando {{ registrosFiltrados.length }} registros</span>
                    <button v-if="hayFiltrosActivos" type="button" @click="limpiarFiltros"
                        class="text-blue-600 hover:underline font-medium cursor-pointer">
                        Limpiar filtros
                    </button>
                </div>

                <div class="flex items-center gap-2">
                    <button type="button" @click="exportarCSV" :disabled="registrosFiltrados.length === 0" :class="registrosFiltrados.length === 0
                            ? 'bg-gray-50 text-gray-400 border-gray-200 cursor-not-allowed'
                            : 'bg-white hover:bg-gray-50 text-gray-700 border-gray-300 cursor-pointer'
                        " class="px-3 py-1.5 border font-medium rounded-lg transition-colors">
                        Exportar CSV
                    </button>
                    <button type="button" disabled
                        class="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-gray-400 cursor-not-allowed">
                        Anterior
                    </button>
                    <span class="px-2 text-gray-600 font-medium">Página 1 de 1</span>
                    <button type="button" disabled
                        class="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-gray-400 cursor-not-allowed">
                        Siguiente
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
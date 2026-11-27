<script setup>
import { ref, computed, onMounted } from 'vue'
import { sesion, etiquetaNivel, cargarPerfil, ROLES } from '@/services/auth'
import { listarTodosPases } from '@/services/pases'
import { listarAuditorias } from '@/services/auditorias'
import { listarUsuarios } from '@/services/usuarios'
import { listarTodosReportes } from '@/services/reportes'

const RolesUsuario = computed(() => sesion.usuario?.rol ?? 'SECRETARIA')
const nombreUsuario = computed(() => sesion.usuario?.nombre || '')
const nivelUsuario = computed(
    () => etiquetaNivel(sesion.usuario?.nivel) || 'Todos los niveles'
)
const nivelFiltro = computed(() => sesion.usuario?.nivel || undefined)

// ───────────── Fechas locales (evita desfase por UTC) ─────────────
const dosDigitos = (numero) => String(numero).padStart(2, '0')
const fechaISO = (fecha) =>
    `${fecha.getFullYear()}-${dosDigitos(fecha.getMonth() + 1)}-${dosDigitos(fecha.getDate())}`

const hoy = new Date()
const hoyISO = fechaISO(hoy)
const inicioSemana = new Date(hoy)
inicioSemana.setDate(inicioSemana.getDate() - ((inicioSemana.getDay() + 6) % 7))
const inicioSemanaISO = fechaISO(inicioSemana)

// ───────────── Datos reales del backend ─────────────
const cargando = ref(true)
const error = ref('')
const pasesMes = ref([])
const auditorias = ref([])
const reportes = ref([])
const totalReportes = ref(0)
const totalUsuarios = ref(0)

const cargarDatos = async () => {
    cargando.value = true
    error.value = ''

    try {
        const anio = hoy.getFullYear()
        const mes = hoy.getMonth() + 1
        const nivel = nivelFiltro.value

        // Los retardos son pases de ENTRADA. Se trae el mes actual y, si la
        // semana está cruzando de mes, también el anterior.
        const actuales = await listarTodosPases({ tipo: 'ENTRADA', anio, mes, nivel })
        let items = actuales.items
        if (hoy.getDate() <= 7) {
            const anterior = mes === 1 ? { anio: anio - 1, mes: 12 } : { anio, mes: mes - 1 }
            const previos = await listarTodosPases({
                tipo: 'ENTRADA',
                ...anterior,
                nivel,
            })
            items = [...previos.items, ...items]
        }
        pasesMes.value = items.sort((a, b) => String(b.fecha).localeCompare(String(a.fecha)))

        const rol = RolesUsuario.value
        if (rol === ROLES.ADMINISTRADOR) {
            const [aud, usuarios, reps] = await Promise.all([
                listarAuditorias({ size: 5 }),
                listarUsuarios({ size: 1 }),
                listarTodosReportes(),
            ])
            auditorias.value = aud.items
            totalUsuarios.value = usuarios.total
            reportes.value = reps.items
            totalReportes.value = reps.total
        } else if (rol === ROLES.COORDINADOR) {
            const reps = await listarTodosReportes()
            reportes.value = reps.items
            totalReportes.value = reps.total
        }
    } catch (e) {
        error.value = e?.message || 'No se pudo cargar la información del dashboard.'
    } finally {
        cargando.value = false
    }
}

onMounted(async () => {
    if (sesion.token && !sesion.usuario?.nombre) await cargarPerfil()
    await cargarDatos()
})

// ───────────── Derivados ─────────────
const retardosHoy = computed(() =>
    pasesMes.value.filter((p) => p.fechaISO === hoyISO)
)

const retardosSemana = computed(() =>
    pasesMes.value.filter(
        (p) => p.fechaISO >= inicioSemanaISO && p.fechaISO <= hoyISO
    )
)

// El límite del sistema es 3 pases del mismo tipo al mes: 2 = alerta, 3+ = bloqueado.
const porEstudiante = computed(() => {
    const mapa = new Map()
    for (const pase of pasesMes.value) {
        const clave = pase.idEstudiante || pase.estudiante
        if (!clave) continue
        const actual = mapa.get(clave) || {
            id: clave,
            estudiante: pase.estudiante || '—',
            nivel: pase.nivel || '',
            cantidad: 0,
        }
        actual.cantidad += 1
        mapa.set(clave, actual)
    }
    return [...mapa.values()].sort(
        (a, b) => b.cantidad - a.cantidad || a.estudiante.localeCompare(b.estudiante)
    )
})

const alertaEstudiantes = computed(() => porEstudiante.value.filter((e) => e.cantidad >= 2))
const estudiantesBloqueados = computed(() => porEstudiante.value.filter((e) => e.cantidad >= 3))

const retardosPorDia = computed(() => {
    const dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie']
    const conteos = [0, 0, 0, 0, 0]
    for (const pase of retardosSemana.value) {
        const indice = (new Date(`${pase.fechaISO}T00:00:00`).getDay() + 6) % 7
        if (indice < 5) conteos[indice] += 1
    }
    const maximo = Math.max(1, ...conteos)
    return dias.map((dia, indice) => ({
        dia,
        cantidad: conteos[indice],
        porcentaje: Math.round((conteos[indice] / maximo) * 100),
    }))
})

const hayRetardosSemana = computed(() => retardosPorDia.value.some((d) => d.cantidad > 0))

// Gráfico del dashboard: reportes por categoría (Conductual / Académica).
const reportesPorCategoria = computed(() => {
    const conteos = [
        { clave: 'CONDUCTUAL', etiqueta: 'Conductual', valor: 0 },
        { clave: 'ACADEMICO', etiqueta: 'Académica', valor: 0 },
    ]
    reportes.value.forEach((r) => {
        const encontrado = conteos.find((c) => c.clave === r.categoria)
        if (encontrado) encontrado.valor += 1
    })
    const maximo = Math.max(1, ...conteos.map((c) => c.valor))
    return conteos.map((c) => ({
        ...c,
        porcentaje: Math.round((c.valor / maximo) * 100),
    }))
})

// ───────────── Tarjetas superiores según el rol ─────────────
const statsSecretaria = computed(() => [
    { titulo: 'Retardos de Hoy', valor: retardosHoy.value.length },
    { titulo: 'Retardos de la Semana', valor: retardosSemana.value.length },
    { titulo: 'Estudiantes en Alerta', valor: alertaEstudiantes.value.length },
    { titulo: 'Estudiantes Bloqueados', valor: estudiantesBloqueados.value.length },
])

const statsCoordinador = computed(() => [
    { titulo: 'Incidencias en total', valor: totalReportes.value },
    { titulo: 'Conductuales', valor: reportes.value.filter((r) => r.categoria === 'CONDUCTUAL').length },
    { titulo: 'Académicas', valor: reportes.value.filter((r) => r.categoria === 'ACADEMICO').length },
    { titulo: 'Graves', valor: reportes.value.filter((r) => r.gravedad === 'GRAVE').length },
])

const statsAdmin = computed(() => [
    { titulo: 'Retardos de la Semana', valor: retardosSemana.value.length },
    { titulo: 'Reportes registrados', valor: totalReportes.value },
    { titulo: 'Estudiantes Bloqueados', valor: estudiantesBloqueados.value.length },
    { titulo: 'Usuarios Activos', valor: totalUsuarios.value },
])

const tarjetasActuales = computed(() => {
    if (RolesUsuario.value === ROLES.ADMINISTRADOR) return statsAdmin.value
    if (RolesUsuario.value === ROLES.COORDINADOR) return statsCoordinador.value
    return statsSecretaria.value
})

const valorStat = (valor) => (cargando.value ? '…' : valor)

// ───────────── Presentación ─────────────
const nivelLabel = (nivel) => (nivel ? etiquetaNivel(nivel) : '—')
const horaDe = (valor) => String(valor || '').slice(11, 16) || '—'
const categoriaLabel = (categoria) =>
    ({ CONDUCTUAL: 'Conductual', ACADEMICO: 'Académica' })[categoria] || categoria || '—'

const obtenerClaseGravedad = (gravedad) => {
    if (gravedad === 'LEVE') return 'bg-green-100 text-green-700'
    if (gravedad === 'GRAVE') return 'bg-red-100 text-red-700'
    return 'bg-gray-100 text-gray-700'
}
</script>

<template>
    <div class="space-y-6">

        <!--Bienvenida al usuario y botones dinamicos-->
        <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
            <h1 class="text-2xl font-bold text-[#1b2a47]">
                Bienvenido(a)<template v-if="nombreUsuario">, {{ nombreUsuario }}</template>
            </h1>
            <p class="text-sm text-[#4a5876] mt-0.5">
                Rol activo: <span class="font-semibold text-[#2c4a7a]">{{ RolesUsuario }}</span>
                <span class="mx-1 text-[#91a5c9]">·</span>
                Nivel: <span class="font-semibold text-[#2c4a7a]">{{ nivelUsuario }}</span>
            </p>
            </div>

            <!--Botones según el rol-->
            <div class="flex flex-wrap items-center gap-3">

            <!-- Botones para ADMINISTRADOR -->
            <template v-if="RolesUsuario === 'ADMINISTRADOR'">
                <router-link :to="{ name: 'auditorias' }" class="rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold text-[#1b2a47] shadow-sm transition hover:bg-gray-50">
                Ver Auditorías
                </router-link>
                <router-link :to="{ name: 'usuarios' }" class="rounded-xl bg-[#2c4a7a] px-4 py-2.5 text-sm font-semibold text-white shadow-[0_4px_12px_rgba(44,74,122,0.25)] transition hover:bg-[#233d68]">
                Gestionar usuarios
                </router-link>
            </template>

            <!--Botones para COORDINADOR-->
            <template v-else-if="RolesUsuario === 'COORDINADOR'">
                <router-link :to="{ name: 'reportes' }" class="rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold text-[#1b2a47] shadow-sm transition hover:bg-gray-50">
                Historial de Reportes
                </router-link>
                <router-link :to="{ name: 'reportes', query: { vista: 'nuevo' } }" class="rounded-xl bg-[#2c4a7a] px-4 py-2.5 text-sm font-semibold text-white shadow-[0_4px_12px_rgba(44,74,122,0.25)] transition hover:bg-[#233d68]">
                Generar Reporte
                </router-link>
            </template>

            <!--Botones para SECRETARÍA-->
            <template v-else>
                <router-link :to="{ name: 'pases' }" class="rounded-xl bg-[#2c4a7a] px-4 py-2.5 text-sm font-semibold text-white shadow-[0_4px_12px_rgba(44,74,122,0.25)] transition hover:bg-[#233d68]">
                Registrar Retardo
                </router-link>
            </template>

            </div>
        </div>

        <div v-if="error" role="alert" class="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
            <span>{{ error }}</span>
            <button type="button" class="rounded-lg border border-[#8a1c14] px-3 py-1 hover:bg-white/60" @click="cargarDatos">Reintentar</button>
        </div>

        <!--Sección de estadísticas (Se adaptan automáticamente con computed)-->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div v-for="(stat, index) in tarjetasActuales" :key="index" class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <p class="text-xs font-semibold uppercase tracking-wider text-gray-500">{{ stat.titulo }}</p>
            <p class="mt-2 text-3xl font-extrabold text-[#1b2a47]">{{ valorStat(stat.valor) }}</p>
            </div>
        </div>

        <!--Sección principal: tabla dinámica + columna lateral-->
        <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">

            <!--Tabla izquierda-->
            <div class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm lg:col-span-2 flex flex-col justify-between">

            <!--Tabla de Últimos movimientos del sistema (administrador)-->
            <div v-if="RolesUsuario === 'ADMINISTRADOR'">
                <div class="mb-4 flex items-center justify-between">
                <h2 class="text-lg font-bold text-[#1b2a47]">Últimos Movimientos en el Sistema</h2>
                <router-link :to="{ name: 'auditorias' }" class="text-xs font-bold text-[#2c4a7a] hover:underline">Ir a auditoría</router-link>
                </div>
                <p v-if="cargando" class="py-10 text-center text-sm text-gray-500">Cargando movimientos…</p>
                <p v-else-if="!auditorias.length" class="py-10 text-center text-sm text-gray-500">Todavía no hay movimientos registrados.</p>
                <div v-else class="overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-600">
                    <thead class="border-b border-gray-100 text-xs uppercase text-gray-400">
                    <tr>
                        <th class="pb-3 font-semibold w-1/5">Hora</th>
                        <th class="pb-3 font-semibold w-1/3">Usuario</th>
                        <th class="pb-3 font-semibold">Acción Realizada</th>
                    </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                    <tr v-for="aud in auditorias" :key="aud.id" class="hover:bg-gray-50/50">
                        <td class="py-3 font-medium text-gray-900">{{ horaDe(aud.fechaCreacion) }}</td>
                        <td class="py-3 font-medium text-[#2c4a7a]">{{ aud.usuario || '—' }}</td>
                        <td class="py-3 text-gray-700">
                            {{ [aud.accion, aud.modulo].filter(Boolean).join(' · ') || '—' }}
                            <span v-if="aud.descripcion" class="block text-xs text-gray-500">{{ aud.descripcion }}</span>
                        </td>
                    </tr>
                    </tbody>
                </table>
                </div>
            </div>

            <!--Tabla de últimas incidencias (coordinador)-->
            <div v-else-if="RolesUsuario === 'COORDINADOR'">
                <div class="mb-4 flex items-center justify-between">
                <h2 class="text-lg font-bold text-[#1b2a47]">Últimas Incidencias Registradas</h2>
                <router-link :to="{ name: 'reportes' }" class="text-xs font-bold text-[#2c4a7a] hover:underline">Ver todas</router-link>
                </div>
                <p v-if="cargando" class="py-10 text-center text-sm text-gray-500">Cargando incidencias…</p>
                <p v-else-if="!reportes.length" class="py-10 text-center text-sm text-gray-500">Todavía no hay incidencias registradas.</p>
                <div v-else class="overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-600">
                    <thead class="border-b border-gray-100 text-xs uppercase text-gray-400">
                    <tr>
                        <th class="pb-3 font-semibold w-1/4">Tipo</th>
                        <th class="pb-3 font-semibold w-1/3">Estudiante</th>
                        <th class="pb-3 font-semibold w-1/5">Nivel</th>
                        <th class="pb-3 font-semibold">Gravedad</th>
                    </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                    <tr v-for="inc in reportes.slice(0, 4)" :key="inc.id" class="hover:bg-gray-50/50">
                        <td class="py-3 font-semibold text-[#1b2a47]">{{ categoriaLabel(inc.categoria) }}</td>
                        <td class="py-3 font-medium text-gray-900">{{ inc.estudiante || '—' }}</td>
                        <td class="py-3">{{ nivelLabel(inc.nivel) }}</td>
                        <td class="py-3">
                            <span :class="obtenerClaseGravedad(inc.gravedad)" class="rounded-full px-2.5 py-0.5 text-xs font-semibold">
                                {{ inc.gravedad || '—' }}
                            </span>
                        </td>
                    </tr>
                    </tbody>
                </table>
                </div>
            </div>

            <!--Tabla de últimos retardos de hoy (secretaría)-->
            <div v-else>
                <div class="mb-4 flex items-center justify-between">
                <h2 class="text-lg font-bold text-[#1b2a47]">Últimos Retardos de Hoy</h2>
                <router-link :to="{ name: 'pases' }" class="text-xs font-bold text-[#2c4a7a] hover:underline">Ver todos</router-link>
                </div>
                <p v-if="cargando" class="py-10 text-center text-sm text-gray-500">Cargando retardos…</p>
                <p v-else-if="!retardosHoy.length" class="py-10 text-center text-sm text-gray-500">No hay retardos registrados hoy.</p>
                <div v-else class="overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-600">
                    <thead class="border-b border-gray-100 text-xs uppercase text-gray-400">
                    <tr>
                        <th class="pb-3 font-semibold w-1/4">Hora</th>
                        <th class="pb-3 font-semibold w-1/3">Estudiante</th>
                        <th class="pb-3 font-semibold w-1/4">Nivel</th>
                    </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                    <tr v-for="item in retardosHoy.slice(0, 5)" :key="item.id" class="hover:bg-gray-50/50">
                        <td class="py-3 font-medium text-gray-900">{{ item.hora || '—' }}</td>
                        <td class="py-3 font-medium text-gray-900">{{ item.estudiante || '—' }}</td>
                        <td class="py-3">{{ nivelLabel(item.nivel) }}</td>
                    </tr>
                    </tbody>
                </table>
                </div>
            </div>

            </div>

            <!--Estudiantes en Alerta (Visible para los 3 roles)-->
            <div class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm flex flex-col justify-between">
            <div>
                <h2 class="text-lg font-bold text-[#1b2a47] mb-4">Estudiantes en Alerta</h2>
                <p v-if="cargando" class="py-8 text-center text-sm text-gray-500">Cargando estudiantes…</p>
                <p v-else-if="!alertaEstudiantes.length" class="py-8 text-center text-sm text-gray-500">Sin estudiantes en alerta este mes.</p>
                <div v-else class="space-y-4">
                <div v-for="alerta in alertaEstudiantes.slice(0, 5)" :key="alerta.id" class="flex items-center justify-between border-b border-gray-100 pb-3 last:border-0 last:pb-0">
                    <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-[#f5f8fd] border border-[#c5cee0] flex items-center justify-center font-bold text-[#2c4a7a]">
                        {{ (alerta.estudiante || '—').charAt(0) }}
                    </div>
                    <div>
                        <p class="text-sm font-semibold text-[#1b2a47]">{{ alerta.estudiante }}</p>
                        <p class="text-xs text-[#4a5876]">{{ nivelLabel(alerta.nivel) }}</p>
                    </div>
                    </div>
                    <span class="text-xs font-bold px-2.5 py-1 rounded-full" :class="alerta.cantidad >= 3 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'">
                    {{ alerta.cantidad }} de 3
                    </span>
                </div>
                </div>
            </div>
            </div>

        </div>

        <!-- Sección Inferior: gráfica y reportes / auditorías -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

            <!-- Gráfica (Visible para Administrador y Secretaría) -->
            <div v-if="RolesUsuario === 'ADMINISTRADOR' || RolesUsuario === 'SECRETARIA'" class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 class="text-lg font-bold text-[#1b2a47] mb-4">Retardos por Semana</h2>
            <p v-if="cargando" class="py-16 text-center text-sm text-gray-500">Cargando gráfica…</p>
            <p v-else-if="!hayRetardosSemana" class="py-16 text-center text-sm text-gray-500">Sin retardos registrados esta semana.</p>
            <template v-else>
                <div class="h-44 flex items-end justify-around gap-2 bg-gray-50 rounded-xl p-4 border border-dashed border-gray-200">
                    <div v-for="(item, index) in retardosPorDia" :key="index" class="flex flex-col items-center gap-1 h-full justify-end">
                    <span class="text-[10px] font-bold text-gray-500">{{ item.cantidad }}</span>
                    <div
                        class="w-10 bg-[#2c4a7a] rounded-t-lg transition-all duration-500 hover:bg-[#1b2a47]"
                        :style="{ height: item.porcentaje + '%' }"
                        :title="`Día: ${item.dia} | Cantidad: ${item.cantidad} (${item.porcentaje}%)`">
                    </div>
                    </div>
                </div>
                <div class="flex justify-around text-xs font-semibold text-gray-500 mt-3">
                    <span v-for="(item, index) in retardosPorDia" :key="index">{{ item.dia }}</span>
                </div>
            </template>
            </div>

            <!-- Gráfica de reportes (administrador) -->
            <div v-if="RolesUsuario === 'ADMINISTRADOR'" class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 class="text-lg font-bold text-[#1b2a47] mb-4">Reportes por Categoría</h2>
            <p v-if="cargando" class="py-16 text-center text-sm text-gray-500">Cargando reportes…</p>
            <p v-else-if="!reportes.length" class="py-16 text-center text-sm text-gray-500">Todavía no hay reportes registrados.</p>
            <template v-else>
                <div class="h-44 flex items-end justify-around gap-2 bg-gray-50 rounded-xl p-4 border border-dashed border-gray-200">
                    <div v-for="(item, index) in reportesPorCategoria" :key="index" class="flex flex-col items-center gap-1 h-full justify-end">
                    <span class="text-[10px] font-bold text-gray-500">{{ item.valor }}</span>
                    <div
                        class="w-10 bg-[#2c4a7a] rounded-t-lg transition-all duration-500 hover:bg-[#1b2a47]"
                        :style="{ height: item.porcentaje + '%' }"
                        :title="`Categoría: ${item.etiqueta} | Cantidad: ${item.valor}`">
                    </div>
                    </div>
                </div>
                <div class="flex justify-around text-xs font-semibold text-gray-500 mt-3">
                    <span v-for="(item, index) in reportesPorCategoria" :key="index">{{ item.etiqueta }}</span>
                </div>
            </template>
            </div>

            <!-- Bloque para coordinador -->
            <div v-if="RolesUsuario === 'COORDINADOR'" class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm lg:col-span-2">
            <div class="mb-4 flex items-center justify-between">
                <h2 class="text-lg font-bold text-[#1b2a47]">Reportes Recientes (Conductuales y Académicos)</h2>
                <router-link :to="{ name: 'reportes' }" class="text-xs font-bold text-[#2c4a7a] hover:underline">Gestionar todos</router-link>
            </div>
            <p v-if="cargando" class="py-8 text-center text-sm text-gray-500">Cargando reportes…</p>
            <p v-else-if="!reportes.length" class="py-8 text-center text-sm text-gray-500">Todavía no hay reportes registrados.</p>
            <div v-else class="space-y-3">
                <div v-for="item in reportes.slice(0, 5)" :key="item.id" class="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
                <div>
                    <span class="text-sm font-semibold text-[#1b2a47]">#{{ item.id }} · {{ item.estudiante || '—' }}</span>
                    <span class="ml-2 text-xs text-gray-500">({{ categoriaLabel(item.categoria) }})</span>
                </div>
                <span :class="['text-xs font-semibold px-2.5 py-1 rounded-full', obtenerClaseGravedad(item.gravedad)]">{{ item.gravedad || '—' }}</span>
                </div>
            </div>
            </div>

        </div>

        </div>
</template>

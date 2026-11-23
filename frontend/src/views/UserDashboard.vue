<script setup>
    import { ref, computed } from 'vue'
    import { sesion, etiquetaNivel } from '@/services/auth'

    // Rol y nivel salen del JWT; el nombre se completa con /auth/me.
    const RolesUsuario = computed(() => sesion.usuario?.rol ?? 'SECRETARIA')
    const nombreUsuario = computed(() => sesion.usuario?.nombre || '')
    const nivelUsuario = computed(
        () => etiquetaNivel(sesion.usuario?.nivel) || 'Todos los niveles'
    )

    //Datos para secretaría (Retardos)
    const statsSecretaria = ref([
        { titulo: 'Retardos de Hoy', valor: 12 },
        { titulo: 'Retardos de la Semana', valor: 38 },
        { titulo: 'Estudiantes en Alerta', valor: 14 },
        { titulo: 'Estudiantes Bloqueados', valor: 5 }
    ])

    const ultimosRetardos = ref([
        { id: 1, hora: '07:41', estudiante: 'Kevin Varela', curso: '2do A' },
        { id: 2, hora: '07:35', estudiante: 'Miguel Villanueva', curso: '5to C' },
        { id: 3, hora: '07:28', estudiante: 'Rafael Telles', curso: '3ro B' },
        { id: 4, hora: '07:20', estudiante: 'Ángel Bastidas', curso: '1ro A' }
    ])

    //Datos para coordinación (Incidencias)
    const statsCoordinador = ref([
        { titulo: 'Incidencias en total', valor: 30 },
        { titulo: 'Conductuales', valor: 19 },
        { titulo: 'Académicas', valor: 11 },
        { titulo: 'Reportes Pendientes', valor: 7 }
    ])

    const ultimasIncidencias = ref([
        { id: 104, tipo: 'Conductual', estudiante: 'Miguel Vasquez', curso: '4to B', gravedad: 'Leve' },
        { id: 103, tipo: 'Académico', estudiante: 'Rafael Telles', curso: '3ro B', gravedad: 'Leve' },
        { id: 102, tipo: 'Conductual', estudiante: 'Brandon Lombano', curso: '5to A', gravedad: 'Grave' },
        { id: 101, tipo: 'Académico', estudiante: 'Kevin Varela', curso: '2do A', gravedad: 'Leve' }
    ])

    //Datos para administrador
    const statsAdmin = ref([
        { titulo: 'Retardos de la Semana', valor: 38 },
        { titulo: 'Reportes Pendientes', valor: 7 },
        { titulo: 'Estudiantes Bloqueados', valor: 5 },
        { titulo: 'Usuarios Activos', valor: 8 }
    ])

    const ultimosMovimientos = ref([
        { id: 1, hora: '08:15', usuario: 'Sec. Laura Gómez', accion: 'Registró pase de retardo #405' },
        { id: 2, hora: '08:02', usuario: 'Coord. Carlos Méndez', accion: 'Cerró reporte disciplinario #169' },
        { id: 3, hora: '07:50', usuario: 'Dir. Marta Lara', accion: 'Creó usuario nuevo (Secretaría)' },
        { id: 4, hora: '07:41', usuario: 'Sec. Laura Gómez', accion: 'Registró pase de retardo #404' }
    ])

    const ultimasAuditorias = ref([
        {
            id: 1,
            fechaHora: '15 nov, 07:45 AM',
            usuario: 'rtelles',
            accion: 'Crear',
            modulo: 'Retardos',
            detalle: 'Registro retardo #145'
        },
        {
            id: 2,
            fechaHora: '15 nov, 08:10 AM',
            usuario: 'mvillanueva',
            accion: 'Anular',
            modulo: 'Retardos',
            detalle: 'Anuló #142, motivo: error de registro'
        },
        {
            id: 3,
            fechaHora: '14 nov, 09:00 AM',
            usuario: 'kvarela',
            accion: 'Iniciar sesión',
            modulo: 'Acceso',
            detalle: 'Ingreso exitoso al sistema'
        }
    ])

    // --- DATOS COMPARTIDOS ---
    const alertaEstudiantes = ref([
        { id: 1, estudiante: 'Kevin Varela', curso: '2do A', nivel: '3 de 3', color: 'bg-red-100 text-red-700' },
        { id: 2, estudiante: 'Miguel Villanueva', curso: '5to C', nivel: '2 de 3', color: 'bg-amber-100 text-amber-700' },
        { id: 3, estudiante: 'Rafael Telles', curso: '3ro B', nivel: '2 de 3', color: 'bg-amber-100 text-amber-700' },
        { id: 4, estudiante: 'Ángel Bastidas', curso: '1ro A', nivel: '3 de 3', color: 'bg-red-100 text-red-700' }
    ])

    const reportes = ref([
        { id: 167, estudiante: 'Miguel Vasquez', tipo: 'Conductual', estado: 'Pendiente', color: 'bg-amber-100 text-amber-700' },
        { id: 168, estudiante: 'Rafael Telles', tipo: 'Académico', estado: 'Pendiente', color: 'bg-amber-100 text-amber-700' },
        { id: 169, estudiante: 'Brandon Lombano', tipo: 'Conductual', estado: 'Atendido', color: 'bg-green-100 text-green-700' }
    ])

    const retardosSemana = ref([
        { dia: 'Lun', cantidad: 5, porcentaje: 30 },
        { dia: 'Mar', cantidad: 12, porcentaje: 65 },
        { dia: 'Mié', cantidad: 16, porcentaje: 85 },
        { dia: 'Jue', cantidad: 9, porcentaje: 50 },
        { dia: 'Vie', cantidad: 13, porcentaje: 70 }
    ])

    //Propiedad computada para mostrar las 4 tarjetas superiores según el rol
    const tarjetasActuales = computed(() => {
        if (RolesUsuario.value === 'ADMINISTRADOR') return statsAdmin.value
        if (RolesUsuario.value === 'COORDINADOR') return statsCoordinador.value
        return statsSecretaria.value
    })

    const obtenerClaseGravedad = (gravedad) => {
        const nivel = (gravedad || '').toLowerCase().trim()

        if (nivel === 'leve') {
            return 'bg-green-100 text-green-700'
        }
        if (nivel === 'grave') {
            return 'bg-red-100 text-red-700'
        }
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
                + Añadir Usuario
                </router-link>
            </template>

            <!--Botones para COORDINADOR-->
            <template v-else-if="RolesUsuario === 'COORDINADOR'">
                <router-link :to="{ name: 'reportes' }" class="rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold text-[#1b2a47] shadow-sm transition hover:bg-gray-50">
                Historial de Reportes
                </router-link>
                <router-link :to="{ name: 'reportes' }" class="rounded-xl bg-[#2c4a7a] px-4 py-2.5 text-sm font-semibold text-white shadow-[0_4px_12px_rgba(44,74,122,0.25)] transition hover:bg-[#233d68]">
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

        <!--Sección de estadísticas (Se adaptan automáticamente con computed)-->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div v-for="(stat, index) in tarjetasActuales" :key="index" class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <p class="text-xs font-semibold uppercase tracking-wider text-gray-500">{{ stat.titulo }}</p>
            <p class="mt-2 text-3xl font-extrabold text-[#1b2a47]">{{ stat.valor }}</p>
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
                <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-600">
                    <thead class="border-b border-gray-100 text-xs uppercase text-gray-400">
                    <tr>
                        <th class="pb-3 font-semibold w-1/5">Hora</th>
                        <th class="pb-3 font-semibold w-1/3">Usuario</th>
                        <th class="pb-3 font-semibold">Acción Realizada</th>
                    </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                    <tr v-for="mov in ultimosMovimientos" :key="mov.id" class="hover:bg-gray-50/50">
                        <td class="py-3 font-medium text-gray-900">{{ mov.hora }}</td>
                        <td class="py-3 font-medium text-[#2c4a7a]">{{ mov.usuario }}</td>
                        <td class="py-3 text-gray-700">{{ mov.accion }}</td>
                    </tr>
                    </tbody>
                </table>
                </div>
            </div>

            <!--Tabla de últimas incidencias académicas/conductuales (coordinador) -->
            <div v-else-if="RolesUsuario === 'COORDINADOR'">
                <div class="mb-4 flex items-center justify-between">
                <h2 class="text-lg font-bold text-[#1b2a47]">Últimas Incidencias Registradas</h2>
                <router-link :to="{ name: 'reportes' }" class="text-xs font-bold text-[#2c4a7a] hover:underline">Ver todas</router-link>
                </div>
                <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-600">
                    <thead class="border-b border-gray-100 text-xs uppercase text-gray-400">
                    <tr>
                        <th class="pb-3 font-semibold w-1/4">Tipo</th>
                        <th class="pb-3 font-semibold w-1/3">Estudiante</th>
                        <th class="pb-3 font-semibold w-1/5">Curso</th>
                        <th class="pb-3 font-semibold">Gravedad</th>
                    </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                    <tr v-for="inc in ultimasIncidencias" :key="inc.id" class="hover:bg-gray-50/50">
                        <td class="py-3 font-semibold text-[#1b2a47]">{{ inc.tipo }}</td>
                        <td class="py-3 font-medium text-gray-900">{{ inc.estudiante }}</td>
                        <td class="py-3">{{ inc.curso }}</td>
                        <td class="py-3">
                            <span :class="obtenerClaseGravedad(inc.gravedad)" class="rounded-full px-2.5 py-0.5 text-xs font-semibold">
                                {{ inc.gravedad }}
                            </span>
                        </td>
                    </tr>
                    </tbody>
                </table>
                </div>
            </div>

            <!--Tabla de últimos retardos de hoy (secretaría) -->
            <div v-else>
                <div class="mb-4 flex items-center justify-between">
                <h2 class="text-lg font-bold text-[#1b2a47]">Últimos Retardos de Hoy</h2>
                <span class="text-xs font-bold text-[#2c4a7a] cursor-pointer hover:underline">Ver todos</span>
                </div>
                <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-gray-600">
                    <thead class="border-b border-gray-100 text-xs uppercase text-gray-400">
                    <tr>
                        <th class="pb-3 font-semibold w-1/4">Hora</th>
                        <th class="pb-3 font-semibold w-1/3">Estudiante</th>
                        <th class="pb-3 font-semibold w-1/4">Curso</th>
                    </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                    <tr v-for="item in ultimosRetardos" :key="item.id" class="hover:bg-gray-50/50">
                        <td class="py-3 font-medium text-gray-900">{{ item.hora }}</td>
                        <td class="py-3 font-medium text-gray-900">{{ item.estudiante }}</td>
                        <td class="py-3">{{ item.curso }}</td>
                    </tr>
                    </tbody>
                </table>
                </div>
            </div>

            </div>

            <!--Estudiantes en Alerta (Visible para los 3 roles) -->
            <div class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm flex flex-col justify-between">
            <div>
                <h2 class="text-lg font-bold text-[#1b2a47] mb-4">Estudiantes en Alerta</h2>
                <div class="space-y-4">
                <div v-for="alerta in alertaEstudiantes" :key="alerta.id" class="flex items-center justify-between border-b border-gray-100 pb-3 last:border-0 last:pb-0">
                    <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-[#f5f8fd] border border-[#c5cee0] flex items-center justify-center font-bold text-[#2c4a7a]">
                        {{ alerta.estudiante.charAt(0) }}
                    </div>
                    <div>
                        <p class="text-sm font-semibold text-[#1b2a47]">{{ alerta.estudiante }}</p>
                        <p class="text-xs text-[#4a5876]">{{ alerta.curso }}</p>
                    </div>
                    </div>
                    <span class="text-xs font-bold px-2.5 py-1 rounded-full" :class="alerta.color">
                    {{ alerta.nivel }}
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
            <div class="h-44 flex items-end justify-around gap-2 bg-gray-50 rounded-xl p-4 border border-dashed border-gray-200">
                <div v-for="(item, index) in retardosSemana" :key="index" class="flex flex-col items-center gap-1 h-full justify-end">
                <span class="text-[10px] font-bold text-gray-500">{{ item.cantidad }}</span>
                <div 
                    class="w-10 bg-[#2c4a7a] rounded-t-lg transition-all duration-500 hover:bg-[#1b2a47]" 
                    :style="{ height: item.porcentaje + '%' }"
                    :title="`Día: ${item.dia} | Cantidad: ${item.cantidad} (${item.porcentaje}%)`">
                </div>
                </div>
            </div>
            <div class="flex justify-around text-xs font-semibold text-gray-500 mt-3">
                <span v-for="(item, index) in retardosSemana" :key="index">{{ item.dia }}</span>
            </div>
            </div>

            <!-- Resumen de Últimas Auditorías (administrador)-->
            <div v-if="RolesUsuario === 'ADMINISTRADOR'" class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm flex flex-col justify-between">
            <div>
                <div class="mb-4 flex items-center justify-between">
                <h2 class="text-lg font-bold text-[#1b2a47]">Resumen de Auditorías</h2>
                <router-link :to="{ name: 'auditorias' }" class="text-xs font-bold text-[#2c4a7a] hover:underline">Ver historial completo</router-link>
                </div>
                <div class="space-y-3">
                <div v-for="aud in ultimasAuditorias" :key="aud.id" class="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
                    <div>
                    <span class="text-xs font-bold text-[#2c4a7a] uppercase">{{ aud.modulo }}</span>
                    <p class="text-sm font-medium text-[#1b2a47]">{{ aud.detalle }}</p>
                    </div>
                    <span class="text-xs font-medium text-gray-500">{{ aud.fecha }}</span>
                </div>
                </div>
            </div>
            </div>

            <!-- Bloque para coordinador -->
            <div v-if="RolesUsuario === 'COORDINADOR'" class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm lg:col-span-2">
            <div class="mb-4 flex items-center justify-between">
                <h2 class="text-lg font-bold text-[#1b2a47]">Reportes Recientes (Conductuales y Académicos)</h2>
                <router-link :to="{ name: 'reportes' }" class="text-xs font-bold text-[#2c4a7a] hover:underline">Gestionar todos</router-link>
            </div>
            <div class="space-y-3">
                <div v-for="item in reportes" :key="item.id" class="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
                <div>
                    <span class="text-sm font-semibold text-[#1b2a47]">#{{ item.id }} · {{ item.estudiante }}</span>
                    <span class="ml-2 text-xs text-gray-500">({{ item.tipo }})</span>
                </div>
                <span :class="['text-xs font-semibold px-2.5 py-1 rounded-full', item.color]">{{ item.estado }}</span>
                </div>
            </div>
            </div>

        </div>

        </div>
</template>
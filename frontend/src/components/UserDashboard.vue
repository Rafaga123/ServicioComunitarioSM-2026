<script setup>
    import { ref } from 'vue';

    const RolesUsuario = ref ('COORDINADOR')

    const stats = ref({
        retardoHoy: 38,
        estudiantesAlert: 14,
        estudiantesBloq: 5,
        reportes: 7
    })

    const ultimosRetardos= ref ([
        {id: 1, hora: '07:41',  estudiante: 'Kevin  Varela', curso: '2do A'},
        {id: 2, hora:'07:35',  estudiante: 'Miguel Villanueva', curso: '5to C'},
        {id: 3, hora:'07:28',  estudiante: 'Rafael  Telles', curso: '3ro B'},
        {id: 4, hora:'07:20',  estudiante: 'Ángel Bastidas', curso: '1ro A'}
    ])

    const alertaEstudiantes = ref ([
        {id: 1,  estudiante: 'Kevin  Varela', curso: '2do A', nivel: '3 de 3', color: 'bg-red-100 text-red-700'},
        {id: 2,  estudiante: 'Miguel Villanueva', curso: '5to C', nivel: '2 de 3', color: 'bg-amber-100 text-amber-700'},
        {id: 3,  estudiante: 'Rafael  Telles', curso: '3ro B', nivel: '2 de 3', color: 'bg-amber-100 text-amber-700'},
        {id: 4,  estudiante: 'Ángel Bastidas', curso: '1ro A', nivel: '3 de 3', color: 'bg-red-100 text-red-700'}
    ])

    const reportes = ref([
        {id: 167,  estudiante: 'Miguel Vasquez', estado: 'Pendiente', color: 'bg-amber-100 text-amber-700'},
        {id: 168,  estudiante: 'Rafael Telles', estado: 'Pendiente', color: 'bg-amber-100 text-amber-700'},
        {id: 169, estudiante: 'Brandon Lombano', estado: 'Atendido', color: 'bg-green-100 text-green-700'}
    ])

    const retardosSemana = ref([
        { dia: 'Lun', cantidad: 5, porcentaje: 30 },
        { dia: 'Mar', cantidad: 12, porcentaje: 65 },
        { dia: 'Mié', cantidad: 16, porcentaje: 85 },
        { dia: 'Jue', cantidad: 9, porcentaje: 50 },
        { dia: 'Vie', cantidad: 13, porcentaje: 70 }
    ])

</script>


<template>
    <MainLayout>
        <div class="space-y-6">
            <!--Bienvenida  y acciones-->
            <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 class="text-2xl font-bold text-[#1b2a47]">Bienvenido(a)</h1>
                    <p class="text-sm text-[#4a5878] mt-0.5">
                        <span class = "font-semibold text-[#2c4a7a]">{{ RolesUsuario }}</span>
                    </p>
                </div>

                <div  class="flex items-center gap-3">
                    <button class="rounded-xl border border-gray-300  bg-white px-4 py-2.5  text-sm font-semibold text-[#1b2a47] shadow-sm transition hover:bg-gray-50">
                        <span>Generar Reporte</span>
                    </button>

                    <button class="rounded-xl bg-[#2c4a7a] px-4 py-2.5 text-sm font-semibold text-white  shadow-[0_4px_12px_rgba(44,74,122,0.25)]  transition hover:bg-[#233d68]">
                        Registrar Retardo
                    </button>
                </div>
            </div>


            <!-- Estadísticas -->
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div class="rounded-2xl border border-gray-200 bg-white p-5  shadow-sm">
                    <p class = "text-xs font-semibold uppercase tracking-wider text-gray-500"> Retardos de la Semana</p>
                    <p class="mt-2 text-3xl font-extrabold text-[#1b2a47]">{{ stats.retardoHoy }}</p>
                </div>

                <div class="rounded-2xl border border-gray-200 bg-white p-5  shadow-sm">
                    <p class = "text-xs font-semibold uppercase tracking-wider text-gray-500"> Estudiantes en Alerta</p>
                    <p class="mt-2 text-3xl font-extrabold text-[#1b2a47]">{{ stats.estudiantesAlert }}</p>
                </div>

                <div class="rounded-2xl border border-gray-200 bg-white p-5  shadow-sm">
                    <p class = "text-xs font-semibold uppercase tracking-wider text-gray-500"> Estudiantes Bloqueados</p>
                    <p class="mt-2 text-3xl font-extrabold text-[#1b2a47]">{{ stats.estudiantesBloq}}</p>
                </div>

                <div class="rounded-2xl border border-gray-200 bg-white p-5  shadow-sm">
                    <p class = "text-xs font-semibold uppercase tracking-wider text-gray-500"> Reportes Pendientes</p>
                    <p class="mt-2 text-3xl font-extrabold text-[#1b2a47]">{{ stats.reportes }}</p>
                </div>
            </div>

            <!--Tabla de Registro de Retardos + Estudiantes en alerta-->
            <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <!--Ultimos Retardos Registrados-->
                <div class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm lg:col-span-2 flex flex-col justify-between">
                    <div>
                        <div class="mb-4 flex items-center justify-between">
                            <h2 class="text-lg font-bold text-[#1b2a47]">Últimos Retardos de Hoy</h2>
                            <span class="text-xs font-bold text-[#2c4a7a] cursor-pointer hover:underline">Ver todos</span>
                        </div>

                        <div class="overflow-x-auto">
                            <table class="w-full  text-left text-sm text-gray-600">
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
                                        <td class="py-3 font-medium text-gray-900">{{ item.estudiante}}</td>
                                        <td class="py-3">{{ item.curso }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!--Estudiantes en Alerta-->
                <div class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm flex flex-col justify-between">
                    <div>
                        <h2 class="text-lg font-bold text-[#1b2a47] mb-4">Estudiantes en Alerta</h2>
                        <div class="space-y-4">
                            <div v-for="alerta in alertaEstudiantes" :key="alerta.id" class="flex items-center justify-between border-b border-gray-100 pb-3 last:border-0 last:pb-0">
                                <div class="flex items-center gap-3">
                                    <div class="w-10 h-10 rounded-full bg-[#f5f8fd] border-[#c5cee0] flex items-center justify-center font-bold text-[#2c4a7a]">
                                        {{ alerta.estudiante.charAt(0) }}
                                    </div>

                                    <div>
                                        <p class="text-sm font-semibold text-[#1b2a47]">{{ alerta.estudiante }}</p>
                                        <p class="text-xs text-[#4a5876]">{{ alerta.curso }}</p>
                                    </div>
                                </div>
                                <span class="text-xs font-bold px-2.5 py-1 rounded-full" :class="alerta.color">{{ alerta.nivel }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
                
            <!--Grafica + Reportes-->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!--Retardos por semana-->
                <div class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
                    <div class="h-44 flex items-end justify-around gap-2 bg-gray-50 rounded-xl p-4 border border-dashed border-gray-200">
                        <!-- Iteram cada día-->
                        <div v-for="(item, index) in retardosSemana" :key="index" class="flex flex-col items-center gap-1 h-full justify-end">
                            <!-- Cantidad exacta flotando arriba de la barra -->
                            <span class="text-[10px] font-bold text-gray-500">{{ item.cantidad }}</span>
                            
                            <!-- Su altura cambia según el calculo de porcentaje -->
                            <div 
                                class="w-10 bg-[#2c4a7a] rounded-t-lg transition-all duration-500 hover:bg-[#1b2a47]" 
                                :style="{ height: item.porcentaje + '%' }"
                                :title="`Día: ${item.dia} | Cantidad: ${item.cantidad} (${item.porcentaje}%)`">
                            </div>
                        </div>
                    </div>

                    <!-- Días de la semana dinámicos -->
                    <div class="flex justify-around text-xs font-semibold text-gray-500 mt-3">
                        <span v-for="(item, index) in retardosSemana" :key="index">
                        {{ item.dia }}
                        </span>
                    </div>
                </div>

                <!--Reportes Recientes-->
                <div class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
                    <h2 class="text-lg font-bold text-[#1b2a47] mb-4">Reportes Recientes</h2>
                    <div class="space-y-3">
                        <div v-for="item in reportes" :key="item.id" class="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100">
                            <span class="text-sm font-medium text-[#1b2a47]">#{{ item.id }} · {{ item.estudiante }}</span>
                            <span :class="['text-xs font-semibold px-2.5 py-1 rounded-full',  item.color]">{{ item.estado }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </MainLayout>
</template>
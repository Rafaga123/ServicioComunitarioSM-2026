    <template>
    <div class="p-6 max-w-7xl mx-auto space-y-5">
        <!-- Encabezado Institucional -->
        <div :class="[card, 'p-6 flex flex-wrap items-center justify-between gap-4']">
        <div>
            <h1 class="text-xl font-bold text-[#1b2a2f]">
            Promoción Escolar y Trazabilidad de Período
            </h1>
            <p class="text-sm text-[#5b6a72] mt-0.5">
            Traspaso de estudiantes desde 5to Año hasta 1er Grado y asignación de secciones.
            </p>
        </div>

        <div class="flex items-center gap-3 bg-[#eef2f6] px-4 py-2.5 rounded-xl border border-[#d5dbe6] text-sm">
            <div>
            <span class="text-[#5b6a72] text-xs font-medium block">Período que cierra</span>
            <span class="font-bold text-[#1b2a2f]">{{ periodoOrigen }}-{{ periodoOrigen + 1 }}</span>
            </div>
            <span class="text-[#5b6a72] font-bold">→</span>
            <div>
            <span class="text-[#5b6a72] text-xs font-medium block">Nuevo período</span>
            <span class="font-bold text-[#233E47]">{{ periodoDestino }}-{{ periodoDestino + 1 }}</span>
            </div>
        </div>
        </div>

        <!-- Cuerpo Principal: Cascada (Izquierda) + Área de Trabajo (Derecha) -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        <div class="lg:col-span-4">
            <CascadaGradosPanel
            :grados="grados"
            :grado-activo="gradoSeleccionado"
            @seleccionar="seleccionarGrado"
            />
        </div>

        <div class="lg:col-span-8">
            <!-- FASE 2: Cambio de sección tras pasar de año -->
            <ReasignacionSeccionesPanel
            v-if="faseActual === 'secciones' && gradoSeleccionado"
            :estudiantes="estudiantesGrado"
            :periodo-destino="periodoDestino"
            :guardando="procesando"
            @volver="faseActual = 'promocion'"
            @confirmar="finalizarCambioSecciones"
            />

            <!-- FASE 1: Selección de repitientes y no inscritos -->
            <div
            v-else-if="gradoSeleccionado"
            :class="[card, 'p-6 space-y-4']"
            >
            <!-- Cabecera del grado activo y alertas de regla especial -->
            <div class="flex flex-wrap items-start justify-between gap-4 pb-4 border-b border-[#e3e8ee]">
                <div>
                <span :class="tag">
                    Fase 1 · Paso de Año
                </span>
                <h2 class="text-lg font-bold text-[#1b2a2f] mt-2">
                    {{ gradoSeleccionado.nombre }} ({{ gradoSeleccionado.nivel === 'liceo' ? 'Media General' : 'Primaria' }})
                </h2>
                <p v-if="gradoSeleccionado.numero === 11" :class="aviso2">
                    Regla de 5to Año: Los estudiantes aprobados quedarán registrados como Egresados.
                </p>
                <p v-else-if="gradoSeleccionado.numero === 6" :class="aviso2">
                    Transición de etapa: Los estudiantes promovidos pasarán directamente a 1er Año.
                </p>
                </div>

                <!-- Contadores rápidos -->
                <div class="flex flex-wrap gap-2 text-xs">
                <span class="px-3 py-1 rounded-full bg-emerald-100 text-emerald-900 font-semibold">
                    {{ gradoSeleccionado.numero === 11 ? 'Egresan' : 'Promueven' }}: {{ resumenDecisiones.principales }}
                </span>
                <span class="px-3 py-1 rounded-full bg-[#fdebc0] text-[#6b4200] font-semibold">
                    Repitientes: {{ resumenDecisiones.repitientes }}
                </span>
                <span class="px-3 py-1 rounded-full bg-rose-100 text-rose-900 font-semibold">
                    No inscritos: {{ resumenDecisiones.noInscritos }}
                </span>
                </div>
            </div>

            <!-- Filtros de búsqueda y sección -->
            <div class="flex flex-wrap items-center gap-3">
                <div class="relative flex-1 min-w-[230px]">
                <svg
                    class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#5b6a72]"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" />
                </svg>
                <input
                    v-model="busqueda"
                    type="text"
                    placeholder="Buscar por cédula, nombre o apellido..."
                    :class="[inp, 'pl-10']"
                />
                </div>

                <div class="flex items-center gap-2">
                <span class="text-sm font-semibold text-[#233E47]">Sección</span>
                <select
                    v-model="filtroSeccion"
                    :class="[inp, 'w-44']"
                >
                    <option value="">Todas</option>
                    <option value="A">Sección A</option>
                    <option value="B">Sección B</option>
                    <option value="C">Sección C</option>
                </select>
                </div>
            </div>

            <!-- Tabla de estudiantes -->
            <div v-if="cargandoEstudiantes" :class="sinRes">
                Cargando nómina de {{ gradoSeleccionado.nombre }}...
            </div>

            <div v-else-if="estudiantesFiltrados.length === 0" :class="sinRes">
                No hay estudiantes activos pendientes por procesar en este grado.
            </div>

            <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
                <table class="w-full text-left border-collapse">
                <thead>
                    <tr>
                    <th :class="th">Cédula</th>
                    <th :class="th">Estudiante</th>
                    <th :class="th">Sección</th>
                    <th :class="[th, 'text-right']">Acción para {{ periodoDestino }}-{{ periodoDestino + 1 }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                    v-for="est in estudiantesFiltrados"
                    :key="est.id"
                    class="transition-colors"
                    :class="{
                        'bg-[#fdebc0]/35': est.decision === 'repitiente',
                        'bg-rose-50/60': est.decision === 'no_inscrito',
                        'hover:bg-[#eef3fb]/60': est.decision === 'promovido' || est.decision === 'egresado',
                    }"
                    >
                    <td :class="[td, 'font-mono text-xs text-[#4a5a63]']">{{ est.cedula_estudiantil }}</td>
                    <td :class="[td, 'font-semibold text-[#1b2a2f]']">
                        {{ est.primer_apellido }}, {{ est.primer_nombre }}
                    </td>
                    <td :class="td">
                        <span class="inline-block px-2.5 py-0.5 text-xs font-semibold rounded-full bg-[#eef2f6] text-[#233E47]">
                        {{ est.seccion_actual }}
                        </span>
                    </td>
                    <td :class="td">
                        <div class="flex justify-end gap-1.5">
                        <!-- Opción por defecto: Egresado (5to) o Promovido (resto) -->
                        <button
                            type="button"
                            @click="est.decision = gradoSeleccionado.numero === 11 ? 'egresado' : 'promovido'"
                            class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors"
                            :class="
                            est.decision === 'promovido' || est.decision === 'egresado'
                                ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                                : 'bg-white text-[#4a5a63] border-[#b8c2d3] hover:bg-[#eef3fb]'
                            "
                        >
                            {{ gradoSeleccionado.numero === 11 ? 'Egresado' : 'Promovido' }}
                        </button>

                        <!-- Excepción 1: Repitiente -->
                        <button
                            type="button"
                            @click="est.decision = 'repitiente'"
                            class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors"
                            :class="
                            est.decision === 'repitiente'
                                ? 'bg-amber-500 text-white border-amber-500 shadow-xs'
                                : 'bg-white text-[#4a5a63] border-[#b8c2d3] hover:bg-[#eef3fb]'
                            "
                        >
                            Repitiente
                        </button>

                        <!-- Excepción 2: No inscrito -->
                        <button
                            type="button"
                            @click="est.decision = 'no_inscrito'"
                            class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors"
                            :class="
                            est.decision === 'no_inscrito'
                                ? 'bg-rose-600 text-white border-rose-600 shadow-xs'
                                : 'bg-white text-[#4a5a63] border-[#b8c2d3] hover:bg-[#eef3fb]'
                            "
                        >
                            No inscrito
                        </button>
                        </div>
                    </td>
                    </tr>
                </tbody>
                </table>
            </div>

            <!-- Pie de acción -->
            <div class="pt-4 border-t border-[#e3e8ee] flex flex-wrap items-center justify-between gap-4">
                <p class="text-xs text-[#5b6a72]">
                Por defecto todos están marcados para {{ gradoSeleccionado.numero === 11 ? 'egresar' : 'pasar de año' }}. Selecciona solo las excepciones.
                </p>

                <button
                type="button"
                :disabled="procesando || estudiantesGrado.length === 0"
                @click="confirmarPasoDeAnio"
                :class="[btnP, 'disabled:cursor-not-allowed disabled:opacity-50']"
                >
                {{ procesando ? 'Procesando...' : 'Procesar Paso de Año y Asignar Secciones →' }}
                </button>
            </div>
            </div>
        </div>
        </div>
    </div>
    </template>

    <script setup>
    import { computed, onMounted, ref } from 'vue'
    import CascadaGradosPanel from '@/components/promocion/CascadaGradosPanel.vue'
    import ReasignacionSeccionesPanel from '@/components/promocion/ReasignacionSeccionesPanel.vue'
    import {
    aviso2,
    btnP,
    card,
    inp,
    sinRes,
    tag,
    td,
    th,
    } from '@/components/gestion-academica/estilos.js'
    import {
    guardarReasignacionSecciones,
    obtenerEstadoCascada,
    obtenerEstudiantesGrado,
    procesarPasoDeAnio,
    } from '@/services/promocion'

    const periodoOrigen = ref(2026)
    const periodoDestino = ref(2027)

    const grados = ref([])
    const gradoSeleccionado = ref(null)
    const estudiantesGrado = ref([])
    const cargandoEstudiantes = ref(false)
    const procesando = ref(false)
    const faseActual = ref('promocion')

    const busqueda = ref('')
    const filtroSeccion = ref('')

    const resumenDecisiones = computed(() => {
    let principales = 0
    let repitientes = 0
    let noInscritos = 0
    for (const est of estudiantesGrado.value) {
        if (est.decision === 'repitiente') repitientes++
        else if (est.decision === 'no_inscrito') noInscritos++
        else principales++
    }
    return { principales, repitientes, noInscritos }
    })

    const estudiantesFiltrados = computed(() => {
    const q = busqueda.value.trim().toLowerCase()
    return estudiantesGrado.value.filter((est) => {
        const coincideSeccion = !filtroSeccion.value || est.seccion_actual === filtroSeccion.value
        const coincideTexto =
        !q ||
        est.cedula_estudiantil.toLowerCase().includes(q) ||
        est.primer_nombre.toLowerCase().includes(q) ||
        est.primer_apellido.toLowerCase().includes(q)
        return coincideSeccion && coincideTexto
    })
    })

    onMounted(async () => {
    grados.value = await obtenerEstadoCascada(periodoOrigen.value, periodoDestino.value)
    const primerPendiente = grados.value.find((g) => !g.procesado) || grados.value[0]
    if (primerPendiente) {
        await seleccionarGrado(primerPendiente)
    }
    })

    async function seleccionarGrado(grado) {
    gradoSeleccionado.value = grado
    faseActual.value = 'promocion'
    busqueda.value = ''
    filtroSeccion.value = ''
    cargandoEstudiantes.value = true

    try {
        const lista = await obtenerEstudiantesGrado(grado.numero, periodoOrigen.value)
        const accionPorDefecto = grado.numero === 11 ? 'egresado' : 'promovido'
        estudiantesGrado.value = lista.map((est) => ({
        ...est,
        decision: accionPorDefecto,
        seccion_nueva: est.seccion_actual,
        }))
    } finally {
        cargandoEstudiantes.value = false
    }
    }

    function obtenerNombreGradoDestino(numeroActual, decision) {
    if (decision === 'repitiente') return gradoSeleccionado.value.nombre
    if (numeroActual === 6) return '1er Año'
    const siguiente = grados.value.find((g) => g.numero === numeroActual + 1)
    return siguiente ? siguiente.nombre : 'Grado Siguiente'
    }

    async function confirmarPasoDeAnio() {
    procesando.value = true
    try {
        const numeroActual = gradoSeleccionado.value.numero
        const decisiones = estudiantesGrado.value.map((est) => ({
        id_estudiante: est.id,
        decision: est.decision,
        }))

        await procesarPasoDeAnio({
        periodo_origen: periodoOrigen.value,
        periodo_destino: periodoDestino.value,
        numero_grado: numeroActual,
        decisiones,
        })

        estudiantesGrado.value = estudiantesGrado.value.map((est) => ({
        ...est,
        grado_destino_numero: est.decision === 'repitiente' ? numeroActual : numeroActual + 1,
        grado_destino_nombre: obtenerNombreGradoDestino(numeroActual, est.decision),
        }))

        const hayAlumnosParaSeccion = estudiantesGrado.value.some(
        (e) => e.decision === 'promovido' || e.decision === 'repitiente'
        )
        if (hayAlumnosParaSeccion) {
        faseActual.value = 'secciones'
        } else {
        await marcarGradoCompletadoYAvanzar()
        }
    } finally {
        procesando.value = false
    }
    }

    async function finalizarCambioSecciones(asignaciones) {
    procesando.value = true
    try {
        await guardarReasignacionSecciones({
        periodo_destino: periodoDestino.value,
        asignaciones,
        })
        await marcarGradoCompletadoYAvanzar()
    } finally {
        procesando.value = false
    }
    }

    async function marcarGradoCompletadoYAvanzar() {
    const idx = grados.value.findIndex((g) => g.id === gradoSeleccionado.value.id)
    if (idx !== -1) {
        grados.value[idx].procesado = true
        grados.value[idx].total_estudiantes = 0
    }
    const siguientePendiente = grados.value.find((g) => !g.procesado)
    if (siguientePendiente) {
        await seleccionarGrado(siguientePendiente)
    } else {
        faseActual.value = 'promocion'
        estudiantesGrado.value = []
    }
    }
    </script>
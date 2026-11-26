    <template>
    <div :class="[card, 'p-6']">
        <div class="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#e3e8ee]">
        <div>
            <span :class="tag">
            Fase 2 · Distribución de Aulas
            </span>
            <h3 class="text-lg font-bold text-[#1b2a2f] mt-2">
            Asignación de Secciones ({{ periodoDestino }}-{{ periodoDestino + 1 }})
            </h3>
            <p class="text-sm text-[#5b6a72]">
            Ajusta la sección de los estudiantes promovidos o repitientes antes de cerrar este nivel.
            </p>
        </div>

        <!-- Resumen en vivo de alumnos por sección -->
        <div class="flex flex-wrap gap-2">
            <div
            v-for="letra in seccionesDisponibles"
            :key="letra"
            class="px-3 py-1.5 rounded-xl border border-[#d5dbe6] bg-[#eef2f6] text-xs"
            >
            <span class="font-bold text-[#233E47]">Sección {{ letra }}:</span>
            <span class="ml-1 font-semibold text-[#1b2a2f]">{{ contarPorSeccion(letra) }} alumnos</span>
            </div>
        </div>
        </div>

        <div v-if="estudiantesActivosNuevoPeriodo.length === 0" :class="[sinRes, 'mt-4']">
        No hay estudiantes ingresando a secciones en el nuevo período para este nivel (todos egresaron o no se inscribieron).
        </div>

        <div v-else class="overflow-x-auto mt-4 rounded-xl border border-[#e3e8ee]">
        <table class="w-full text-left border-collapse">
            <thead>
            <tr>
                <th :class="th">Cédula</th>
                <th :class="th">Estudiante</th>
                <th :class="th">Condición</th>
                <th :class="th">Grado Destino</th>
                <th :class="[th, 'w-44']">Nueva Sección</th>
            </tr>
            </thead>
            <tbody>
            <tr
                v-for="est in estudiantesActivosNuevoPeriodo"
                :key="est.id"
                class="hover:bg-[#eef3fb]/60 transition-colors"
            >
                <td :class="[td, 'font-mono text-xs text-[#4a5a63]']">{{ est.cedula_estudiantil }}</td>
                <td :class="[td, 'font-semibold text-[#1b2a2f]']">
                {{ est.primer_apellido }}, {{ est.primer_nombre }}
                </td>
                <td :class="td">
                <span
                    class="inline-block text-xs font-semibold px-2.5 py-0.5 rounded-full"
                    :class="
                    est.decision === 'repitiente'
                        ? 'bg-[#fdebc0] text-[#6b4200]'
                        : 'bg-emerald-100 text-emerald-800'
                    "
                >
                    {{ est.decision === 'repitiente' ? 'Repitiente' : 'Promovido' }}
                </span>
                </td>
                <td :class="[td, 'text-[#1b2a2f] font-medium']">
                {{ est.grado_destino_nombre }}
                </td>
                <td :class="td">
                <select
                    v-model="est.seccion_nueva"
                    class="h-10 w-full rounded-xl border border-[#b8c2d3] bg-white px-3 text-sm font-medium text-[#1b2a2f] transition focus:border-[#233E47] focus:outline-none focus:ring-4 focus:ring-[#b4d0f8]/70"
                >
                    <option v-for="letra in seccionesDisponibles" :key="letra" :value="letra">
                    Sección {{ letra }}
                    </option>
                </select>
                </td>
            </tr>
            </tbody>
        </table>
        </div>

        <div class="mt-6 pt-4 border-t border-[#e3e8ee] flex flex-wrap items-center justify-between gap-3">
        <button
            type="button"
            @click="$emit('volver')"
            :class="btnS"
        >
            ← Volver a revisar promoción
        </button>

        <button
            type="button"
            :disabled="guardando"
            @click="confirmarSecciones"
            :class="[btnP, 'disabled:cursor-not-allowed disabled:opacity-50']"
        >
            {{ guardando ? 'Guardando...' : 'Confirmar Secciones y Siguiente Grado →' }}
        </button>
        </div>
    </div>
    </template>

    <script setup>
    import { computed } from 'vue'
    import { btnP, btnS, card, sinRes, tag, td, th } from '@/components/gestion-academica/estilos.js'

    const props = defineProps({
    estudiantes: { type: Array, required: true },
    periodoDestino: { type: Number, required: true },
    seccionesDisponibles: { type: Array, default: () => ['A', 'B', 'C'] },
    guardando: { type: Boolean, default: false },
    })

    const emit = defineEmits(['volver', 'confirmar'])

    const estudiantesActivosNuevoPeriodo = computed(() =>
    props.estudiantes.filter((e) => e.decision === 'promovido' || e.decision === 'repitiente')
    )

    function contarPorSeccion(letra) {
    return estudiantesActivosNuevoPeriodo.value.filter((e) => e.seccion_nueva === letra).length
    }

    function confirmarSecciones() {
    const asignaciones = estudiantesActivosNuevoPeriodo.value.map((e) => ({
        id_estudiante: e.id,
        grado_destino_numero: e.grado_destino_numero,
        seccion_nueva: e.seccion_nueva,
    }))
    emit('confirmar', asignaciones)
    }
    </script>
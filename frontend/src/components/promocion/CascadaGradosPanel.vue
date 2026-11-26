    <template>
    <aside :class="[card, 'p-5']">
        <div class="mb-4 pb-3 border-b border-[#e3e8ee]">
        <h2 class="text-sm font-bold uppercase tracking-wider text-[#233E47]">
            Orden de Traspaso
        </h2>
        <p class="text-xs text-[#5b6a72] mt-1">
            Procesa desde 5to Año hacia abajo para liberar cupos sin choques.
        </p>
        </div>

        <ol class="space-y-2">
        <li
            v-for="(grado, index) in grados"
            :key="grado.id"
        >
            <button
            type="button"
            :disabled="!puedeSeleccionar(index)"
            @click="$emit('seleccionar', grado)"
            class="w-full text-left px-3.5 py-2.5 rounded-xl border transition-all flex items-center justify-between gap-2"
            :class="clasesItem(grado, index)"
            >
            <div>
                <div class="flex items-center gap-2">
                <span class="font-bold text-sm">{{ grado.nombre }}</span>
                <span
                    v-if="grado.numero === 11"
                    class="text-[11px] font-semibold px-2 py-0.5 rounded-full"
                    :class="
                    gradoActivo?.id === grado.id
                        ? 'bg-white/20 text-white'
                        : 'bg-[#b4d0f8] text-[#233E47]'
                    "
                >
                    Egreso
                </span>
                <span
                    v-else-if="grado.numero === 6"
                    class="text-[11px] font-semibold px-2 py-0.5 rounded-full"
                    :class="
                    gradoActivo?.id === grado.id
                        ? 'bg-white/20 text-white'
                        : 'bg-[#b4d0f8] text-[#233E47]'
                    "
                >
                    Pasa a 1er Año
                </span>
                </div>
                <p class="text-xs opacity-85 mt-0.5">
                {{ grado.procesado ? 'Nivel limpiado' : `${grado.total_estudiantes} alumnos activos` }}
                </p>
            </div>

            <span
                class="text-xs font-semibold px-2.5 py-0.5 rounded-full shrink-0"
                :class="badgeEstado(grado, index)"
            >
                {{ textoEstado(grado, index) }}
            </span>
            </button>
        </li>
        </ol>
    </aside>
    </template>

    <script setup>
    import { card } from '@/components/gestion-academica/estilos.js'

    const props = defineProps({
    grados: { type: Array, required: true },
    gradoActivo: { type: Object, default: null },
    })

    defineEmits(['seleccionar'])

    function puedeSeleccionar(index) {
    if (props.grados[index].procesado) return true
    for (let i = 0; i < index; i++) {
        if (!props.grados[i].procesado) return false
    }
    return true
    }

    function clasesItem(grado, index) {
    const activo = props.gradoActivo?.id === grado.id
    if (activo) {
        return 'bg-[#233E47] text-white border-[#233E47] shadow-sm'
    }
    if (grado.procesado) {
        return 'bg-emerald-50/80 text-emerald-950 border-emerald-200 hover:bg-emerald-100/70'
    }
    if (!puedeSeleccionar(index)) {
        return 'bg-[#f8fafc] text-[#5b6a72] border-[#e3e8ee] cursor-not-allowed opacity-65'
    }
    return 'bg-white text-[#1b2a2f] border-[#d5dbe6] hover:border-[#233E47] hover:bg-[#eef3fb]'
    }

    function textoEstado(grado, index) {
    if (grado.procesado) return 'Listo'
    if (props.gradoActivo?.id === grado.id) return 'Activo'
    return puedeSeleccionar(index) ? 'Siguiente' : 'Bloqueado'
    }

    function badgeEstado(grado, index) {
    if (props.gradoActivo?.id === grado.id) return 'bg-white/20 text-white'
    if (grado.procesado) return 'bg-emerald-100 text-emerald-800'
    return puedeSeleccionar(index)
        ? 'bg-[#fdebc0] text-[#6b4200]'
        : 'bg-[#eef2f6] text-[#5b6a72]'
    }
    </script>
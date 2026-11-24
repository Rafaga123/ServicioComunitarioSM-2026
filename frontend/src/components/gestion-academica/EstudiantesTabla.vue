<script setup>
import { etiquetaNivel } from '@/services/auth'
import { nomEst } from './helpers'
import { th, td, btnMini, tag, nada, sinRes } from './estilos'

defineProps({
  filas: { type: Array, required: true },
  buscando: { type: Boolean, default: false },
  cargando: { type: Boolean, default: false },
  filtrando: { type: Boolean, default: false },
  // Solo el administrador puede crear, editar y eliminar estudiantes.
  puedeGestionar: { type: Boolean, default: false },
})

const emit = defineEmits(['editar', 'eliminar'])
</script>

<template>
  <p v-if="buscando && cargando" :class="sinRes">Buscando en todos los estudiantes…</p>
  <p v-else-if="buscando" :class="sinRes">No se pudo cargar la lista completa para filtrar.</p>
  <p v-else-if="filtrando && !filas.length" :class="sinRes">Ningún estudiante coincide con el filtro.</p>
  <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
    <table class="w-full border-collapse">
      <thead>
        <tr>
          <th :class="th">Estudiante</th>
          <th :class="th">Cédula</th>
          <th :class="th">Nivel</th>
          <th :class="th">Grado y sección</th>
          <th :class="th">Representante</th>
          <th v-if="puedeGestionar" :class="[th, 'text-right']">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in filas" :key="e.id">
          <td :class="[td, 'font-semibold']">{{ nomEst(e) }}</td>
          <td :class="[td, 'whitespace-nowrap']">{{ e.cedula || '—' }}</td>
          <td :class="[td, 'whitespace-nowrap']">
            <span v-if="e.nivel" :class="tag">{{ etiquetaNivel(e.nivel) }}</span>
            <span v-else class="text-[#5b6a72]">—</span>
          </td>
          <td :class="[td, 'whitespace-nowrap']">
            {{ e.gradoNombre || '—' }}<template v-if="e.seccionLetra"> · Sección {{ e.seccionLetra }}</template>
          </td>
          <td :class="td">
            <span v-if="e.representanteNombre">{{ e.representanteNombre }}</span>
            <span v-else :class="nada">Sin representante vinculado</span>
          </td>
          <td v-if="puedeGestionar" :class="[td, 'whitespace-nowrap text-right']">
            <button
              type="button"
              :class="btnMini"
              :aria-label="'Editar ' + nomEst(e)"
              @click="emit('editar', e)"
            >
              Editar
            </button>
            <button
              type="button"
              :class="[btnMini, '!text-[#8a1c14]']"
              :aria-label="'Eliminar ' + nomEst(e)"
              @click="emit('eliminar', e)"
            >
              Eliminar
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

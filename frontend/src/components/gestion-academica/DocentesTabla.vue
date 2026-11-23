<script setup>
import { nomDocente } from './helpers'
import { etiquetaNivel } from '@/services/auth'
import { th, td, btnMini, tag, sinRes } from './estilos'

defineProps({
  filas: { type: Array, required: true },
  buscando: { type: Boolean, default: false },
  cargando: { type: Boolean, default: false },
  filtrando: { type: Boolean, default: false },
  // Solo el administrador puede crear, editar y eliminar docentes.
  puedeGestionar: { type: Boolean, default: false },
})

const emit = defineEmits(['editar', 'eliminar'])
</script>

<template>
  <p v-if="buscando && cargando" :class="sinRes">Buscando en todos los docentes…</p>
  <p v-else-if="buscando" :class="sinRes">No se pudo cargar la lista completa para filtrar.</p>
  <p v-else-if="filtrando && !filas.length" :class="sinRes">Ningún docente coincide con el filtro.</p>
  <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
    <table class="w-full border-collapse">
      <thead>
        <tr>
          <th :class="th">Docente</th>
          <th :class="th">Cédula</th>
          <th :class="th">Nivel</th>
          <th v-if="puedeGestionar" :class="[th, 'text-right']">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in filas" :key="d.id">
          <td :class="[td, 'font-semibold']">{{ nomDocente(d) }}</td>
          <td :class="[td, 'whitespace-nowrap']">{{ d.cedula || '—' }}</td>
          <td :class="[td, 'whitespace-nowrap']">
            <span v-if="d.nivel" :class="tag">{{ etiquetaNivel(d.nivel) }}</span>
            <span v-else class="text-[#5b6a72]">—</span>
          </td>
          <td v-if="puedeGestionar" :class="[td, 'whitespace-nowrap text-right']">
            <button
              type="button"
              :class="btnMini"
              :aria-label="'Editar ' + nomDocente(d)"
              @click="emit('editar', d)"
            >
              Editar
            </button>
            <button
              type="button"
              :class="[btnMini, '!text-[#8a1c14]']"
              :aria-label="'Eliminar ' + nomDocente(d)"
              @click="emit('eliminar', d)"
            >
              Eliminar
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

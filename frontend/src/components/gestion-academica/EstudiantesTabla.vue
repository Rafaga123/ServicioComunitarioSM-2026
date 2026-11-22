<script setup>
import { gradoTexto, nomEst, nomPersona } from './helpers'
import { th, td, btnMini, tag, nada, sinRes } from './estilos'

const props = defineProps({
  filas: { type: Array, required: true },
  representantes: { type: Array, default: () => [] },
  grados: { type: Array, default: () => [] },
})

const emit = defineEmits(['editar', 'eliminar'])

const repPorId = (id) => props.representantes.find((r) => r.id === id)
</script>

<template>
  <p v-if="!filas.length" :class="sinRes">Ningún estudiante coincide con la búsqueda.</p>
  <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
    <table class="w-full border-collapse">
      <thead>
        <tr>
          <th :class="th">Estudiante</th>
          <th :class="th">Grado y sección</th>
          <th :class="th">Representantes</th>
          <th :class="[th, 'text-right']">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="e in filas" :key="e.id">
          <td :class="[td, 'font-semibold']">{{ nomEst(e) }}</td>
          <td :class="[td, 'whitespace-nowrap']">{{ gradoTexto(grados, e.gradoId) }}</td>
          <td :class="td">
            <span v-if="!e.representanteIds.length" :class="nada">Sin representante vinculado aún</span>
            <div v-else class="flex flex-wrap gap-1">
              <span v-for="id in e.representanteIds" :key="id" :class="tag">
                {{ repPorId(id) ? nomPersona(repPorId(id)) : '—' }}
              </span>
            </div>
          </td>
          <td :class="[td, 'whitespace-nowrap text-right']">
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

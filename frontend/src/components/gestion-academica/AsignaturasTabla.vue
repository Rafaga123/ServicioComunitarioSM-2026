<script setup>
import { nomDocente } from './helpers'
import { th, td, btnMini, tag, nada, sinRes } from './estilos'

const props = defineProps({
  filas: { type: Array, required: true },
  docentes: { type: Array, default: () => [] },
})

const emit = defineEmits(['editar', 'eliminar'])

const docentesDe = (asigId) => props.docentes.filter((d) => (d.asignaturaIds ?? []).includes(asigId))
</script>

<template>
  <p v-if="!filas.length" :class="sinRes">Ninguna asignatura coincide con la búsqueda.</p>
  <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
    <table class="w-full border-collapse">
      <thead>
        <tr>
          <th :class="th">Asignatura</th>
          <th :class="th">Docentes</th>
          <th :class="[th, 'text-right']">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in filas" :key="a.id">
          <td :class="[td, 'font-semibold']">{{ a.nombre }}</td>
          <td :class="td">
            <span v-if="!docentesDe(a.id).length" :class="nada">Sin docente asignado aún</span>
            <div v-else class="flex flex-wrap gap-1">
              <span v-for="d in docentesDe(a.id)" :key="d.id" :class="tag">{{ nomDocente(d) }}</span>
            </div>
          </td>
          <td :class="[td, 'whitespace-nowrap text-right']">
            <button
              type="button"
              :class="btnMini"
              :aria-label="'Editar ' + a.nombre"
              @click="emit('editar', a)"
            >
              Editar
            </button>
            <button
              type="button"
              :class="[btnMini, '!text-[#8a1c14]']"
              :aria-label="'Eliminar ' + a.nombre"
              @click="emit('eliminar', a)"
            >
              Eliminar
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

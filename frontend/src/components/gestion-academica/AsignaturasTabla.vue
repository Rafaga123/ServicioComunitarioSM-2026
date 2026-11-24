<script setup>
import { nomDocente } from './helpers'
import { th, td, btnMini, tag, nada, sinRes } from './estilos'

defineProps({
  filas: { type: Array, required: true },
  buscando: { type: Boolean, default: false },
  cargando: { type: Boolean, default: false },
  filtrando: { type: Boolean, default: false },
  puedeGestionar: { type: Boolean, default: false },
})

const emit = defineEmits(['editar', 'eliminar'])
</script>

<template>
  <p v-if="buscando && cargando" :class="sinRes">Buscando en todas las asignaturas…</p>
  <p v-else-if="buscando" :class="sinRes">No se pudo cargar la lista completa para filtrar.</p>
  <p v-else-if="filtrando && !filas.length" :class="sinRes">Ninguna asignatura coincide con el filtro.</p>
  <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
    <table class="w-full border-collapse">
      <thead>
        <tr>
          <th :class="th">Asignatura</th>
          <th :class="th">Grado / año</th>
          <th :class="th">Período</th>
          <th :class="th">Docentes</th>
          <th :class="[th, 'text-right']">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in filas" :key="a.id">
          <td :class="[td, 'font-semibold text-[#233E47]']">{{ a.nombre }}</td>
          <td :class="td">{{ a.gradoNombre || '—' }}</td>
          <td :class="td">{{ a.periodoLectivo }}</td>
          <td :class="td">
            <span v-if="!a.docentes?.length" :class="nada">Sin docente vinculado</span>
            <div v-else class="flex flex-wrap gap-1">
              <span v-for="d in a.docentes" :key="d.id" :class="tag">{{ nomDocente(d) }}</span>
            </div>
          </td>
          <td :class="[td, 'whitespace-nowrap text-right']">
            <button
              v-if="puedeGestionar"
              type="button"
              :class="btnMini"
              :aria-label="'Editar ' + a.nombre"
              @click="emit('editar', a)"
            >
              Editar
            </button>
            <button
              v-if="puedeGestionar"
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

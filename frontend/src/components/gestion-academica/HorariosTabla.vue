<script setup>
import { diaNombre, gradoTexto, nomDocente } from './helpers'
import { th, td, btnMini, tag, nada, sinRes } from './estilos'

const props = defineProps({
  filas: { type: Array, required: true },
  asignaturas: { type: Array, default: () => [] },
  docentes: { type: Array, default: () => [] },
  grados: { type: Array, default: () => [] },
})

const emit = defineEmits(['editar', 'eliminar'])

const asignaturaPorId = (id) => props.asignaturas.find((a) => a.id === id)
const docentesDe = (asigId) => props.docentes.filter((d) => (d.asignaturaIds ?? []).includes(asigId))
</script>

<template>
  <p v-if="!filas.length" :class="sinRes">Ningún horario coincide con la búsqueda.</p>
  <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
    <table class="w-full border-collapse">
      <thead>
        <tr>
          <th :class="th">Grado y sección</th>
          <th :class="th">Día</th>
          <th :class="th">Hora</th>
          <th :class="th">Asignatura</th>
          <th :class="th">Docentes</th>
          <th :class="[th, 'text-right']">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="h in filas" :key="h.id">
          <td :class="[td, 'whitespace-nowrap font-semibold']">{{ gradoTexto(grados, h.gradoId) }}</td>
          <td :class="td">{{ diaNombre(h.diaSemana) }}</td>
          <td :class="[td, 'whitespace-nowrap']">{{ h.hora.slice(0, 5) }}</td>
          <td :class="td">{{ asignaturaPorId(h.asignaturaId)?.nombre ?? '—' }}</td>
          <td :class="td">
            <span v-if="!docentesDe(h.asignaturaId).length" :class="nada">Sin docente asignado aún</span>
            <div v-else class="flex flex-wrap gap-1">
              <span v-for="d in docentesDe(h.asignaturaId)" :key="d.id" :class="tag">{{ nomDocente(d) }}</span>
            </div>
          </td>
          <td :class="[td, 'whitespace-nowrap text-right']">
            <button type="button" :class="btnMini" @click="emit('editar', h)">Editar</button>
            <button
              type="button"
              :class="[btnMini, '!text-[#8a1c14]']"
              @click="emit('eliminar', h)"
            >
              Eliminar
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

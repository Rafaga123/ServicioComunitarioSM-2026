<script setup>
import { diaNombre } from './helpers'
import { th, td, btnMini, tag, nada, sinRes } from './estilos'

defineProps({
  filas: { type: Array, required: true },
  buscando: { type: Boolean, default: false },
  cargando: { type: Boolean, default: false },
  filtrando: { type: Boolean, default: false },
  puedeGestionar: { type: Boolean, default: false },
})

const emit = defineEmits(['editar', 'eliminar'])

const rango = (h) =>
  h.horaInicio || h.horaFin
    ? `${String(h.horaInicio ?? '').slice(0, 5)}–${String(h.horaFin ?? '').slice(0, 5)}`
    : '—'
</script>

<template>
  <p v-if="buscando && cargando" :class="sinRes">Buscando en todos los horarios…</p>
  <p v-else-if="buscando" :class="sinRes">No se pudo cargar la lista completa para filtrar.</p>
  <p v-else-if="filtrando && !filas.length" :class="sinRes">Ningún horario coincide con el filtro.</p>
  <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
    <table class="w-full border-collapse">
      <thead>
        <tr>
          <th :class="th">Sección / grado</th>
          <th :class="th">Día</th>
          <th :class="th">Bloque</th>
          <th :class="th">Horario</th>
          <th :class="th">Asignatura</th>
          <th :class="th">Docente</th>
          <th :class="th">Período</th>
          <th :class="[th, 'text-right']">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="h in filas" :key="h.id">
          <td :class="[td, 'whitespace-nowrap font-semibold text-[#233E47]']">
            {{ h.seccion || '—' }}
            <span v-if="h.grado" class="block text-xs font-normal text-[#5b6a72]">{{ h.grado }}</span>
          </td>
          <td :class="td">{{ diaNombre(h.diaSemana) }}</td>
          <td :class="[td, 'whitespace-nowrap']">{{ h.bloque || '—' }}</td>
          <td :class="[td, 'whitespace-nowrap']">{{ rango(h) }}</td>
          <td :class="td">{{ h.asignatura || '—' }}</td>
          <td :class="td">
            <span v-if="!h.docente" :class="nada">Sin docente</span>
            <span v-else :class="tag">{{ h.docente }}</span>
          </td>
          <td :class="td">{{ h.periodoLectivo }}</td>
          <td :class="[td, 'whitespace-nowrap text-right']">
            <button
              v-if="puedeGestionar"
              type="button"
              :class="btnMini"
              :aria-label="'Editar horario de ' + (h.seccion || 'sección')"
              @click="emit('editar', h)"
            >
              Editar
            </button>
            <button
              v-if="puedeGestionar"
              type="button"
              :class="[btnMini, '!text-[#8a1c14]']"
              :aria-label="'Eliminar horario de ' + (h.seccion || 'sección')"
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

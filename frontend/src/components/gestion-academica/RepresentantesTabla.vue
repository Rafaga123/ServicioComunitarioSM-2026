<script setup>
import { nomPersona } from './helpers'
import { th, td, btnMini, tag, nada, sinRes } from './estilos'

const props = defineProps({
  filas: { type: Array, required: true },
  estudiantes: { type: Array, default: () => [] },
})

const emit = defineEmits(['editar', 'eliminar'])

const estudiantesDe = (repId) => props.estudiantes.filter((e) => (e.representanteIds ?? []).includes(repId))
</script>

<template>
  <p v-if="!filas.length" :class="sinRes">Ningún representante coincide con la búsqueda.</p>
  <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
    <table class="w-full border-collapse">
      <thead>
        <tr>
          <th :class="th">Representante</th>
          <th :class="th">Teléfono</th>
          <th :class="th">Estudiantes a cargo</th>
          <th :class="[th, 'text-right']">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in filas" :key="r.id">
          <td :class="[td, 'font-semibold']">{{ nomPersona(r) }}</td>
          <td :class="[td, 'whitespace-nowrap']">{{ r.telefono }}</td>
          <td :class="td">
            <span v-if="!estudiantesDe(r.id).length" :class="nada">Sin estudiantes vinculados aún</span>
            <div v-else class="flex flex-wrap gap-1">
              <span v-for="e in estudiantesDe(r.id).slice(0, 3)" :key="e.id" :class="tag">
                {{ e.primerNombre }} {{ e.primerApellido }}
              </span>
              <span v-if="estudiantesDe(r.id).length > 3" :class="tag">
                +{{ estudiantesDe(r.id).length - 3 }}
              </span>
            </div>
          </td>
          <td :class="[td, 'whitespace-nowrap text-right']">
            <button
              type="button"
              :class="btnMini"
              :aria-label="'Editar ' + nomPersona(r)"
              @click="emit('editar', r)"
            >
              Editar
            </button>
            <button
              type="button"
              :class="[btnMini, '!text-[#8a1c14]']"
              :aria-label="'Eliminar ' + nomPersona(r)"
              @click="emit('eliminar', r)"
            >
              Eliminar
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

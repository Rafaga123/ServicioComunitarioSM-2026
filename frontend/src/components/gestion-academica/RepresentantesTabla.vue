<script setup>
import { nomPersona } from './helpers'
import { th, td, btnMini, tag, nada, sinRes } from './estilos'

const props = defineProps({
  filas: { type: Array, required: true },
  estudiantes: { type: Array, default: () => [] },
  buscando: { type: Boolean, default: false },
  cargando: { type: Boolean, default: false },
  filtrando: { type: Boolean, default: false },
  // Solo el administrador puede crear, editar y eliminar representantes.
  puedeGestionar: { type: Boolean, default: false },
})

const emit = defineEmits(['editar', 'eliminar'])

// El backend guarda un solo representante por estudiante (idRepresentante).
const estudiantesDe = (repId) =>
  props.estudiantes.filter((e) => e.idRepresentante === repId)
</script>

<template>
  <p v-if="buscando && cargando" :class="sinRes">Buscando en todos los representantes…</p>
  <p v-else-if="buscando" :class="sinRes">No se pudo cargar la lista completa para filtrar.</p>
  <p v-else-if="filtrando && !filas.length" :class="sinRes">Ningún representante coincide con el filtro.</p>
  <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
    <table class="w-full border-collapse">
      <thead>
        <tr>
          <th :class="th">Representante</th>
          <th :class="th">Teléfono</th>
          <!-- La API de representantes no incluye a sus estudiantes; la columna
               aparece cuando la pestaña Estudiantes esté conectada. -->
          <th v-if="estudiantes.length" :class="th">Estudiantes a cargo</th>
          <th v-if="puedeGestionar" :class="[th, 'text-right']">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in filas" :key="r.id">
          <td :class="[td, 'font-semibold']">{{ nomPersona(r) }}</td>
          <td :class="[td, 'whitespace-nowrap']">{{ r.telefono || '—' }}</td>
          <td v-if="estudiantes.length" :class="td">
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
          <td v-if="puedeGestionar" :class="[td, 'whitespace-nowrap text-right']">
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

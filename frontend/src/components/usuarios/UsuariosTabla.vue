<script setup>
// Tabla de cuentas de usuario con las mismas clases que los listados de
// gestión académica (th, td, tag, btnMini y sinRes).
import { etiquetaRol, etiquetaNivel } from '@/services/usuarios'
import { th, td, btnMini, tag, nada, sinRes } from '../gestion-academica/estilos'

defineProps({
  filas: { type: Array, required: true },
  buscando: { type: Boolean, default: false },
  cargando: { type: Boolean, default: false },
  filtrando: { type: Boolean, default: false },
})

const emit = defineEmits(['editar', 'eliminar'])

const esAdmin = (usuario) => usuario?.rol === 'ADMINISTRADOR'
</script>

<template>
  <p v-if="buscando && cargando" :class="sinRes">Buscando en todos los usuarios…</p>
  <p v-else-if="buscando" :class="sinRes">No se pudo cargar la lista completa para filtrar.</p>
  <p v-else-if="cargando && !filas.length" :class="sinRes">Cargando usuarios…</p>
  <p v-else-if="filtrando && !filas.length" :class="sinRes">Ningún usuario coincide con el filtro.</p>

  <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee]">
    <table class="w-full border-collapse">
      <thead>
        <tr>
          <th :class="th">Usuario</th>
          <th :class="th">Rol</th>
          <th :class="th">Nivel</th>
          <th :class="[th, 'text-right']">Acciones</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="usuario in filas" :key="usuario.id" class="hover:bg-[#f6f9fe]">
          <td :class="[td, 'font-semibold']">{{ usuario.nombre }}</td>
          <td :class="td">
            <span
              :class="[tag, esAdmin(usuario) ? '!bg-[#e4e7ee] !text-[#233E47]' : '']"
            >{{ etiquetaRol(usuario.rol) }}</span>
          </td>
          <td :class="[td, 'whitespace-nowrap']">
            <span v-if="usuario.nivel" :class="tag">{{ etiquetaNivel(usuario.nivel) }}</span>
            <span v-else :class="nada">—</span>
          </td>
          <td :class="[td, 'whitespace-nowrap text-right']">
            <template v-if="esAdmin(usuario)">
              <span :class="nada">Sin acciones</span>
            </template>
            <template v-else>
              <button
                type="button"
                :class="btnMini"
                :aria-label="'Editar ' + usuario.nombre"
                @click="emit('editar', usuario)"
              >
                Editar
              </button>
              <button
                type="button"
                :class="[btnMini, '!text-[#8a1c14]']"
                :aria-label="'Eliminar ' + usuario.nombre"
                @click="emit('eliminar', usuario)"
              >
                Eliminar
              </button>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

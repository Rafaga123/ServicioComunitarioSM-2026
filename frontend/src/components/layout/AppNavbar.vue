<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
// Reutilizamos Heroicons para mantener el mismo lenguaje de diseño
import {
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  UserCircleIcon,
} from '@heroicons/vue/24/outline'
import {
  sesion,
  cargarPerfil,
  cerrarSesion,
  etiquetaRol,
  etiquetaNivel,
} from '@/services/auth'

const emit = defineEmits(['toggle-sidebar'])
const router = useRouter()

// El rol y el nivel vienen del JWT; el nombre se completa con /auth/me.
const nombre = computed(() => sesion.usuario?.nombre || '')
const rol = computed(() => etiquetaRol())
const nivel = computed(() => etiquetaNivel())

onMounted(() => {
  if (sesion.token && !sesion.usuario?.nombre) cargarPerfil()
})

const logout = () => {
  cerrarSesion()
  router.push({ name: 'Login' })
}
</script>

<template>
  <!-- justify-between es la magia aquí para separar izquierda y derecha -->
  <header class="flex h-16 w-full items-center justify-between bg-white px-4 shadow-sm sm:px-6">

    <!-- LADO IZQUIERDO: Menú móvil, logo y título -->
    <div class="flex items-center gap-3">
      <!-- Solo visible en móvil: abre el sidebar deslizante -->
      <button
        type="button"
        aria-label="Abrir menú"
        class="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-[#233E47] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#91a5c9] lg:hidden"
        @click="emit('toggle-sidebar')"
      >
        <Bars3Icon class="h-6 w-6" aria-hidden="true" />
      </button>

      <img
        src="../../assets/logo santa marta.png"
        alt="Logo Santa Marta"
        class="h-9 w-9 object-contain drop-shadow-sm"
      />

      <!-- hidden sm:block oculta el texto en celulares para que no colapse la barra -->
      <span class="hidden text-sm font-bold text-[#233E47] sm:block">
        Unidad Educativa Privada Santa Marta
      </span>
    </div>

    <!-- LADO DERECHO: Perfil de Usuario -->
    <div class="flex items-center gap-3 sm:gap-4">

      <!-- Información del usuario (rol y nivel del JWT + nombre de /auth/me) -->
      <div class="hidden flex-col items-end sm:flex">
        <span class="text-sm font-bold text-[#233E47]">{{ nombre || 'Usuario' }}</span>
        <span class="text-xs font-medium text-gray-500">
          {{ rol }}<template v-if="nivel"> · {{ nivel }}</template>
        </span>
      </div>

      <!-- Botón del avatar -->
      <button
        type="button"
        :title="nombre ? `${nombre} · ${rol}` : rol"
        class="rounded-full bg-gray-50 p-1.5 text-gray-400 transition-all hover:bg-gray-100 hover:text-[#233E47] focus:outline-none focus:ring-2 focus:ring-[#91a5c9] focus:ring-offset-2"
      >
        <UserCircleIcon class="h-7 w-7" aria-hidden="true" />
      </button>

      <!-- Cerrar sesión -->
      <button
        type="button"
        class="flex items-center gap-2 rounded-xl border border-gray-200 px-2.5 py-2 text-sm font-semibold text-gray-500 transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#91a5c9] sm:px-3"
        @click="logout"
      >
        <ArrowRightOnRectangleIcon class="h-5 w-5" aria-hidden="true" />
        <span class="hidden sm:inline">Salir</span>
      </button>

    </div>

  </header>
</template>

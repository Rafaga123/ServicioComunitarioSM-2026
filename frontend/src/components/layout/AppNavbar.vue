<script setup>
import { Bars3Icon } from '@heroicons/vue/24/outline'

const emit = defineEmits(['toggle-sidebar'])
</script>

<template>
  <header class="flex h-16 w-full items-center justify-between bg-white px-4 shadow-sm sm:px-6">
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
  </header>
</template>

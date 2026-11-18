<script setup>
import { ClockIcon } from '@heroicons/vue/24/outline'
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-[#1b2a47]">Pases</h1>
      <p class="mt-0.5 text-sm text-[#4a5878]">Registro y control de pases de salida.</p>
    </div>

    <div
      class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 bg-white px-6 py-16 text-center shadow-sm"
    >
      <div class="grid h-14 w-14 place-items-center rounded-full bg-[#eef3fb] text-[#2c4a7a]">
        <ClockIcon class="h-7 w-7" aria-hidden="true" />
      </div>
      <h2 class="mt-4 text-lg font-semibold text-[#1b2a47]">Módulo en construcción</h2>
      <p class="mt-1 max-w-md text-sm text-[#4a5878]">
        Aquí se gestionarán los pases de salida de los estudiantes. Por ahora la vista está
        disponible para navegar desde el menú.
      </p>
    </div>
  </div>
</template>

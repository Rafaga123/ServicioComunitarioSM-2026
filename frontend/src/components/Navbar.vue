<script setup>
// Reutilizamos Heroicons para mantener el mismo lenguaje de diseño
import { UserCircleIcon } from '@heroicons/vue/24/outline'
</script>

<template>
    <!-- justify-between es la magia aquí para separar izquierda y derecha -->
    <header class="flex h-16 w-full items-center justify-between bg-white px-6 shadow-sm">

    <!-- LADO IZQUIERDO: Logo y Título -->
    <div class="flex items-center gap-3">
        <!-- Reutilizamos el logo que tienes en tu carpeta public/ -->
        <img src="../assets/logo santa marta.png" alt="Logo Santa Marta" class="h-9 w-9 object-contain drop-shadow-sm" />
        
        <!-- hidden sm:block oculta el texto en celulares para que no colapse la barra -->
        <span class="hidden text-sm font-bold text-[#233E47] sm:block">
        Unidad Educativa Privada Santa Marta
        </span>
    </div>

    <!-- LADO DERECHO: Perfil de Usuario -->
    <div class="flex items-center gap-4">
        
        <!-- Información del usuario (Opcional, pero le da un toque muy profesional) -->
        <div class="hidden flex-col items-end sm:flex">
        <span class="text-sm font-bold text-[#233E47]">Administrador</span>
        <span class="text-xs font-medium text-gray-500">Marta Lara</span>
        </div>
        
        <!-- Botón del avatar -->
        <button type="button" class="rounded-full bg-gray-50 p-1.5 text-gray-400 transition-all hover:bg-gray-100 hover:text-[#233E47] focus:outline-none focus:ring-2 focus:ring-[#91a5c9] focus:ring-offset-2">
        <UserCircleIcon class="h-7 w-7" aria-hidden="true" />
        </button>

    </div>

    </header>
</template>
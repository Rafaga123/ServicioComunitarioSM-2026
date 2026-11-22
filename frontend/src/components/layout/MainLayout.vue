<script setup>
import { ref } from 'vue'
import AppSidebar from './AppSidebar.vue'
import AppNavbar from './AppNavbar.vue'

// Controla el sidebar deslizante en móvil
const sidebarOpen = ref(false)
</script>

<template>

    <div class="flex h-screen w-full overflow-hidden bg-gray-50">

        <!-- Fondo oscuro en móvil: tocar fuera del menú lo cierra -->
        <div
            v-if="sidebarOpen"
            aria-hidden="true"
            class="fixed inset-0 z-30 bg-black/40 lg:hidden"
            @click="sidebarOpen = false"
        ></div>

        <!-- Sidebar (Columna Izquierda) -->
        <AppSidebar :open="sidebarOpen" @close="sidebarOpen = false" />

        <!-- Contenedor Derecho (Navbar + Main) -->
        <div class="flex min-w-0 flex-1 flex-col overflow-hidden">

            <!-- Navbar (Fila Superior) -->
            <AppNavbar @toggle-sidebar="sidebarOpen = !sidebarOpen" />

            <main class="flex-1 overflow-y-auto p-6 md:p-8">
                <RouterView />
            </main>
        </div>
    </div>
</template>

<script setup>
import Sidebar from './Sidebar.vue'
import Navbar from './Navbar.vue'
</script>

<template>

    <div class="flex h-screen w-full overflow-hidden bg-gray-50">
        
        <!-- Sidebar (Columna Izquierda) -->
        <Sidebar class="flex-shrink-0" />

        <!-- Contenedor Derecho (Navbar + Main) -->
        <div class="flex flex-1 flex-col overflow-hidden">
            
            <!-- Navbar (Fila Superior) -->
            <Navbar class="flex-shrink-0" />
            
            <main class="flex-1 overflow-y-auto p-6 md:p-8">
                <slot />
            </main>
        </div>
    </div>
</template>
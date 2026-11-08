<script setup>
import { ref, markRaw } from "vue";
import { useRoute } from "vue-router";
// 1. Importamos los íconos que necesitamos (versión outline/bordes)
import {
  Squares2X2Icon,
  ClockIcon,
  DocumentTextIcon,
  AcademicCapIcon,
  UsersIcon,
  ShieldCheckIcon,
} from "@heroicons/vue/24/outline";

const route = useRoute(); // Para saber en qué ruta estamos

// 2. Inyectamos los componentes en la matriz usando markRaw por rendimiento
const menuItems = [
  { name: "Dashboard", path: "/", icon: markRaw(Squares2X2Icon) },
  { name: "Pases", path: "/pases", icon: markRaw(ClockIcon) },
  { name: "Reportes", path: "/reportes", icon: markRaw(DocumentTextIcon) },
  {
    name: "Gestión Académica",
    path: "/academico",
    icon: markRaw(AcademicCapIcon),
  },
  { name: "Usuarios", path: "/usuarios", icon: markRaw(UsersIcon) },
  { name: "Auditoría", path: "/auditoria", icon: markRaw(ShieldCheckIcon) },
];

const activeMenu = ref("dashboard");
</script>

<template>
  <aside class="flex w-64 flex-col bg-[#233E47] text-white">
    <div class="flex h-16 items-center justify-center border-b border-white/10">
      <span class="text-lg font-bold tracking-wider">CONTROL DE PASES</span>
    </div>

    <nav class="flex-1 space-y-1 px-3 py-4">
      <!-- RouterLink reemplaza a <a> -->
      <RouterLink
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        :class="[
          'flex items-center rounded-lg px-4 py-3 text-sm font-medium transition-colors',
          // Compara la ruta actual con el destino del botón para aplicar estilos activos
          route.path === item.path
            ? 'bg-white/15 text-white'
            : 'text-[#91a5c9] hover:bg-white/5 hover:text-white',
        ]"
      >
        <component :is="item.icon" class="mr-3 h-5 w-5" aria-hidden="true" />
        {{ item.name }}
      </RouterLink>
    </nav>
  </aside>
</template>

<script setup>
import { computed, markRaw } from "vue";
import { useRoute } from "vue-router";
// 1. Importamos los íconos que necesitamos (versión outline/bordes)
import {
  Squares2X2Icon,
  ClockIcon,
  DocumentTextIcon,
  AcademicCapIcon,
  UsersIcon,
  ShieldCheckIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import {
  sesion,
  puedeAccederRuta,
  etiquetaRol,
  etiquetaNivel,
} from "@/services/auth";

defineProps({
  // En móvil controla la entrada/salida del panel deslizante
  open: { type: Boolean, default: false },
});

const emit = defineEmits(["close"]);

const route = useRoute(); // Para saber en qué ruta estamos

// 2. Inyectamos los componentes en la matriz usando markRaw por rendimiento
// Navegamos por nombre de ruta: si cambia la URL, el menú sigue funcionando
const todosLosItems = [
  { name: "Dashboard", route: "dashboard", icon: markRaw(Squares2X2Icon) },
  { name: "Pases", route: "pases", icon: markRaw(ClockIcon) },
  { name: "Reportes", route: "reportes", icon: markRaw(DocumentTextIcon) },
  {
    name: "Gestión Académica",
    route: "gestion-academica",
    icon: markRaw(AcademicCapIcon),
  },
  { name: "Usuarios", route: "usuarios", icon: markRaw(UsersIcon) },
  { name: "Auditoría", route: "auditorias", icon: markRaw(ShieldCheckIcon) },
];

// El rol sale del JWT: el menú se recalcula solo cuando cambia la sesión.
const menuItems = computed(() =>
  todosLosItems.filter((item) => puedeAccederRuta(item.route)),
);

const nombreUsuario = computed(
  () => sesion.usuario?.nombre || "Usuario",
);
const rolUsuario = computed(() => etiquetaRol());
const nivelUsuario = computed(() => etiquetaNivel());

// Marca activo también las rutas hijas (ej. /pases/123)
const isActive = (name) => route.matched.some((record) => record.name === name);
</script>

<template>
  <aside
    class="fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-[#233E47] text-white transition-transform duration-200 lg:static lg:z-auto lg:shrink-0 lg:translate-x-0"
    :class="open ? 'translate-x-0' : '-translate-x-full'"
  >
    <div
      class="flex h-16 items-center justify-between border-b border-white/10 px-4 lg:justify-center"
    >
      <span class="text-lg font-bold tracking-wider">CONTROL DE PASES</span>
      <button
        type="button"
        aria-label="Cerrar menú"
        class="rounded-lg p-1.5 text-white/70 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#91a5c9] lg:hidden"
        @click="emit('close')"
      >
        <XMarkIcon class="h-5 w-5" aria-hidden="true" />
      </button>
    </div>

    <nav class="flex-1 space-y-1 overflow-y-auto px-3 py-4">
      <!-- RouterLink reemplaza a <a> -->
      <RouterLink
        v-for="item in menuItems"
        :key="item.route"
        :to="{ name: item.route }"
        :class="[
          'flex items-center rounded-lg px-4 py-3 text-sm font-medium transition-colors',
          // Compara el nombre de la ruta actual con el destino del botón
          isActive(item.route)
            ? 'bg-white/15 text-white'
            : 'text-[#91a5c9] hover:bg-white/5 hover:text-white',
        ]"
        @click="emit('close')"
      >
        <component :is="item.icon" class="mr-3 h-5 w-5" aria-hidden="true" />
        {{ item.name }}
      </RouterLink>
    </nav>

    <!-- Usuario y rol leídos del JWT -->
    <div class="border-t border-white/10 px-4 py-3">
      <p class="truncate text-sm font-semibold text-white">
        {{ nombreUsuario }}
      </p>
      <p class="mt-0.5 text-xs text-[#91a5c9]">
        {{ rolUsuario }}<template v-if="nivelUsuario"> · {{ nivelUsuario }}</template>
      </p>
    </div>
  </aside>
</template>

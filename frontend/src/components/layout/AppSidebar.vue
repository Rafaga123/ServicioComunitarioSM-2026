<script setup>
import { computed, markRaw, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowRightOnRectangleIcon,
  Squares2X2Icon,
  ClockIcon,
  DocumentTextIcon,
  AcademicCapIcon,
  UsersIcon,
  ShieldCheckIcon,
  XMarkIcon,
  TicketIcon,
} from "@heroicons/vue/24/outline";
import {
  sesion,
  puedeAccederRuta,
  etiquetaRol,
  etiquetaNivel,
  cargarPerfil,
  cerrarSesion,
} from "@/services/auth";

defineProps({
  // En móvil controla la entrada/salida del panel deslizante
  open: { type: Boolean, default: false },
});

const emit = defineEmits(["close"]);

const route = useRoute();
const router = useRouter();

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

const nombreUsuario = computed(() => sesion.usuario?.nombre || "Usuario");
const rolUsuario = computed(() => etiquetaRol());
const nivelUsuario = computed(() => etiquetaNivel());
const iniciales = computed(() =>
  nombreUsuario.value
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((palabra) => palabra[0]?.toUpperCase() ?? "")
    .join("") || "U",
);

// Marca activo también las rutas hijas (ej. /pases/123)
const isActive = (name) => route.matched.some((record) => record.name === name);

onMounted(() => {
  if (sesion.token && !sesion.usuario?.nombre) cargarPerfil();
});

const logout = () => {
  cerrarSesion();
  router.push({ name: "Login" });
};
</script>

<template>
  <aside
    class="fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-[#233E47] text-white transition-transform duration-200 lg:static lg:z-auto lg:shrink-0 lg:translate-x-0"
    :class="open ? 'translate-x-0' : '-translate-x-full'"
  >
    <div class="flex h-20 shrink-0 items-center gap-3 border-b border-white/10 px-4">
      <span
        class="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-white/10 text-white ring-1 ring-white/15"
      >
        <TicketIcon class="h-6 w-6" aria-hidden="true" />
      </span>
      <div class="min-w-0">
        <p class="truncate text-sm font-bold tracking-wide">CONTROL DE PASES</p>
      </div>
      <button
        type="button"
        aria-label="Cerrar menú"
        class="ml-auto rounded-xl p-1.5 text-white/70 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#91a5c9] lg:hidden"
        @click="emit('close')"
      >
        <XMarkIcon class="h-5 w-5" aria-hidden="true" />
      </button>
    </div>

    <nav class="min-h-0 flex-1 overflow-y-auto px-4 py-5">
      <p class="mb-3 px-3 text-[11px] font-bold uppercase tracking-[0.18em] text-[#91a5c9]/80">
        Menú principal
      </p>
      <div class="space-y-2">
        <RouterLink
          v-for="item in menuItems"
          :key="item.route"
          :to="{ name: item.route }"
          :class="[
            'group flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-semibold transition-all',
            isActive(item.route)
              ? 'bg-[#e4ecf8] text-[#233E47] shadow-[0_10px_24px_-14px_rgba(228,236,248,0.9)]'
              : 'text-[#b7c6d9] hover:bg-white/10 hover:text-white',
          ]"
          @click="emit('close')"
        >
          <span
            :class="[
              'grid h-9 w-9 shrink-0 place-items-center rounded-xl transition-colors',
              isActive(item.route)
                ? 'bg-[#233E47]/10 text-[#233E47]'
                : 'bg-white/5 text-[#91a5c9] group-hover:text-white',
            ]"
          >
            <component :is="item.icon" class="h-5 w-5" aria-hidden="true" />
          </span>
          <span class="truncate">{{ item.name }}</span>
          <span
            v-if="isActive(item.route)"
            class="ml-auto h-2 w-2 shrink-0 rounded-full bg-[#233E47]"
            aria-hidden="true"
          ></span>
        </RouterLink>
      </div>
    </nav>

    <div class="shrink-0 border-t border-white/10 p-4">
      <div class="rounded-2xl bg-white/5 p-3 ring-1 ring-white/10">
        <div class="flex items-center gap-3">
          <span
            class="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[#91a5c9]/20 text-sm font-bold text-white"
          >
            {{ iniciales }}
          </span>
          <div class="min-w-0">
            <p class="truncate text-sm font-semibold text-white">{{ nombreUsuario }}</p>
            <p class="truncate text-xs text-[#91a5c9]">
              {{ rolUsuario }}<template v-if="nivelUsuario"> · {{ nivelUsuario }}</template>
            </p>
          </div>
        </div>
        <button
          type="button"
          class="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-white/10 px-3 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-red-500/20 hover:text-red-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-300"
          @click="logout"
        >
          <ArrowRightOnRectangleIcon class="h-5 w-5" aria-hidden="true" />
          Cerrar sesión
        </button>
      </div>
    </div>
  </aside>
</template>

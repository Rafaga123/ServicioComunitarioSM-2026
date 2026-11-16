<script setup>
import { ref, computed } from 'vue'

// --- LISTA REACTIVA DE USUARIOS ---
const usuarios = ref([
  { id: 1, usuario: 'rtelles', rol: 'Control de Estudio', estado: 'Activo', ultimaConexion: 'Hoy, 08:15 AM' },
  { id: 2, usuario: 'mvillanueva', rol: 'Secretaria', estado: 'Activo', ultimaConexion: 'Hoy, 09:40 AM' },
  { id: 3, usuario: 'kvarela', rol: 'Admin', estado: 'Activo', ultimaConexion: 'Hoy, 10:05 AM' }
])

// --- FILTROS DE LA TABLA ---
const filtroUsuario = ref('')
const filtroRol = ref('')
const filtroEstado = ref('')

const usuariosFiltrados = computed(() => {
  return usuarios.value.filter((u) => {
    const coincideNombre = u.usuario.toLowerCase().includes(filtroUsuario.value.toLowerCase())
    const coincideRol = filtroRol.value === '' || u.rol === filtroRol.value
    const coincideEstado = filtroEstado.value === '' || u.estado === filtroEstado.value
    return coincideNombre && coincideRol && coincideEstado
  })
})

// --- VENTANA 1: CREAR NUEVO USUARIO (Panel Lateral) ---
const mostrarPanelCrear = ref(false)
const errorCrear = ref('')
const formNuevo = ref({
  usuario: '',
  rol: '',
  password: '',
  confirmPassword: ''
})

const abrirPanelCrear = () => {
  mostrarModalEditar.value = false
  errorCrear.value = ''
  formNuevo.value = { usuario: '', rol: '', password: '', confirmPassword: '' }
  mostrarPanelCrear.value = !mostrarPanelCrear.value
}

const agregarUsuario = () => {
  errorCrear.value = ''

  if (!formNuevo.value.usuario.trim() || !formNuevo.value.rol || !formNuevo.value.password) {
    errorCrear.value = 'Todos los campos son obligatorios.'
    return
  }

  if (formNuevo.value.password !== formNuevo.value.confirmPassword) {
    errorCrear.value = 'Las contraseñas no coinciden.'
    return
  }

  usuarios.value.push({
    id: Date.now(),
    usuario: formNuevo.value.usuario.trim(),
    rol: formNuevo.value.rol,
    estado: 'Activo',
    ultimaConexion: 'Recién creado'
  })

  formNuevo.value = { usuario: '', rol: '', password: '', confirmPassword: '' }
  mostrarPanelCrear.value = false
}

// --- VENTANA 2: EDITAR USUARIO (Modal Independiente) ---
const mostrarModalEditar = ref(false)
const errorEditar = ref('')
const formEditar = ref({
  id: null,
  usuario: '',
  rol: '',
  estado: 'Activo',
  password: '',
  confirmPassword: ''
})

const abrirModalEditar = (user) => {
  mostrarPanelCrear.value = false
  errorEditar.value = ''
  // Clonamos el objeto para que los cambios no se apliquen hasta pulsar "Guardar cambios"
  formEditar.value = {
    id: user.id,
    usuario: user.usuario,
    rol: user.rol,
    estado: user.estado,
    password: '',
    confirmPassword: ''
  }
  mostrarModalEditar.value = true
}

const guardarEdicion = () => {
  errorEditar.value = ''

  if (!formEditar.value.usuario.trim() || !formEditar.value.rol) {
    errorEditar.value = 'El nombre de usuario y el rol son obligatorios.'
    return
  }

  // Solo validamos contraseña si el administrador escribió una nueva
  if (formEditar.value.password || formEditar.value.confirmPassword) {
    if (formEditar.value.password !== formEditar.value.confirmPassword) {
      errorEditar.value = 'Las contraseñas nuevas no coinciden.'
      return
    }
  }

  const index = usuarios.value.findIndex((u) => u.id === formEditar.value.id)
  if (index !== -1) {
    usuarios.value[index] = {
      ...usuarios.value[index],
      usuario: formEditar.value.usuario.trim(),
      rol: formEditar.value.rol,
      estado: formEditar.value.estado
    }
  }

  mostrarModalEditar.value = false
}
</script>

<template>
  <div class="w-full space-y-6">
    <!-- Sección Superior: Filtros -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div>
        <label class="block text-xs font-semibold text-gray-600 mb-1.5">Buscar usuario</label>
        <input
          v-model="filtroUsuario"
          type="text"
          placeholder="Nombre de usuario"
          class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
        />
      </div>

      <div>
        <label class="block text-xs font-semibold text-gray-600 mb-1.5">Rol</label>
        <select
          v-model="filtroRol"
          class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
        >
          <option value="">Todos</option>
          <option value="Admin">Admin</option>
          <option value="Control de Estudio">Control de Estudio</option>
          <option value="Secretaria">Secretaria</option>
        </select>
      </div>

      <div>
        <label class="block text-xs font-semibold text-gray-600 mb-1.5">Estado</label>
        <select
          v-model="filtroEstado"
          class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
        >
          <option value="">Todos</option>
          <option value="Activo">Activo</option>
          <option value="Inactivo">Inactivo</option>
        </select>
      </div>

      <!-- Botón Principal -->
      <div>
        <button
          type="button"
          @click="abrirPanelCrear"
          class="w-full py-2.5 px-4 bg-blue-700 hover:bg-blue-800 text-white font-semibold text-sm rounded-lg shadow-sm transition-colors cursor-pointer"
        >
          {{ mostrarPanelCrear ? 'Cerrar formulario' : '+ Agregar usuario' }}
        </button>
      </div>
    </div>

    <!-- Contenedor Principal: Tabla + Ventana 1 (Crear) -->
    <div class="flex flex-col xl:flex-row gap-6 items-start">
      <!-- Tarjeta de la Tabla -->
      <div class="flex-1 w-full bg-white border border-gray-200 rounded-xl shadow-sm p-5">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-gray-100 text-gray-600 text-xs font-semibold">
                <th class="py-3 px-4 rounded-l-lg">N.º</th>
                <th class="py-3 px-4">Usuario</th>
                <th class="py-3 px-4">Rol</th>
                <th class="py-3 px-4">Estado</th>
                <th class="py-3 px-4">Última conexión</th>
                <th class="py-3 px-4 rounded-r-lg text-right">Acción</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 text-sm text-gray-700">
              <tr
                v-for="(user, index) in usuariosFiltrados"
                :key="user.id"
                class="hover:bg-gray-50/80 transition-colors"
              >
                <td class="py-3.5 px-4 font-medium text-gray-900">#{{ index + 1 }}</td>
                <td class="py-3.5 px-4 font-medium text-gray-900">{{ user.usuario }}</td>
                <td class="py-3.5 px-4">
                  <span
                    :class="{
                      'bg-blue-100 text-blue-800': user.rol === 'Admin',
                      'bg-amber-100 text-amber-800': user.rol === 'Control de Estudio',
                      'bg-purple-100 text-purple-800': user.rol === 'Secretaria'
                    }"
                    class="px-3 py-0.5 rounded-full text-xs font-medium"
                  >
                    {{ user.rol }}
                  </span>
                </td>
                <td class="py-3.5 px-4">
                  <span
                    :class="
                      user.estado === 'Activo'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-gray-100 text-gray-600'
                    "
                    class="px-3 py-0.5 rounded-full text-xs font-medium"
                  >
                    {{ user.estado }}
                  </span>
                </td>
                <td class="py-3.5 px-4 text-gray-500">{{ user.ultimaConexion }}</td>
                <td class="py-3.5 px-4 text-right text-xs">
                  <button
                    type="button"
                    @click="abrirModalEditar(user)"
                    class="text-blue-600 hover:underline font-medium cursor-pointer"
                  >
                    Editar
                  </button>
                </td>
              </tr>

              <tr v-if="usuariosFiltrados.length === 0">
                <td colspan="6" class="py-8 text-center text-gray-400 text-sm">
                  No se encontraron usuarios con los filtros seleccionados.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pie de tabla -->
        <div class="flex flex-wrap items-center justify-between gap-4 pt-4 mt-2 border-t border-gray-100 text-xs text-gray-500">
          <span>Mostrando {{ usuariosFiltrados.length }} usuarios</span>

          <div class="flex items-center gap-2">
            <button
              type="button"
              disabled
              class="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-gray-400 cursor-not-allowed"
            >
              Anterior
            </button>
            <span class="px-2 text-gray-600 font-medium">Página 1 de 1</span>
            <button
              type="button"
              disabled
              class="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-gray-400 cursor-not-allowed"
            >
              Siguiente
            </button>
          </div>
        </div>
      </div>

      <!-- VENTANA 1: Panel Derecho Dinámico (Nuevo Usuario) -->
      <div
        v-if="mostrarPanelCrear"
        class="w-full xl:w-[360px] bg-white border border-gray-200 rounded-xl shadow-sm p-6 animate-fade-in"
      >
        <div class="flex items-center justify-between pb-3 mb-4 border-b border-gray-100">
          <h3 class="text-base font-semibold text-gray-800">Nuevo usuario</h3>
          <button
            type="button"
            @click="mostrarPanelCrear = false"
            class="text-gray-400 hover:text-gray-600 text-sm cursor-pointer"
          >
            ✕
          </button>
        </div>

        <form @submit.prevent="agregarUsuario" class="space-y-4">
          <div
            v-if="errorCrear"
            class="p-2.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg"
          >
            {{ errorCrear }}
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1.5">Usuario</label>
            <input
              v-model="formNuevo.usuario"
              type="text"
              placeholder="Ej: jperez"
              class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1.5">Rol</label>
            <select
              v-model="formNuevo.rol"
              class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="" disabled>Seleccione un rol</option>
              <option value="Admin">Admin</option>
              <option value="Control de Estudio">Control de Estudio</option>
              <option value="Secretaria">Secretaria</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1.5">Contraseña</label>
            <input
              v-model="formNuevo.password"
              type="password"
              placeholder="••••••••"
              class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1.5">Verificar contraseña</label>
            <input
              v-model="formNuevo.confirmPassword"
              type="password"
              placeholder="••••••••"
              class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          <div class="flex gap-3 pt-2">
            <button
              type="button"
              @click="mostrarPanelCrear = false"
              class="flex-1 py-2 px-4 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-lg transition-colors cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              class="flex-1 py-2 px-4 bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors cursor-pointer"
            >
              Guardar
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- VENTANA 2: Modal Independiente para Editar Usuario -->
    <div
      v-if="mostrarModalEditar"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 animate-fade-in"
    >
      <div class="w-full max-w-md bg-white border border-gray-200 rounded-xl shadow-lg p-6">
        <div class="flex items-center justify-between pb-3 mb-4 border-b border-gray-100">
          <div>
            <h3 class="text-base font-semibold text-gray-800">Editar usuario</h3>
            <p class="text-xs text-gray-500">Modifica los permisos, estado o contraseña</p>
          </div>
          <button
            type="button"
            @click="mostrarModalEditar = false"
            class="text-gray-400 hover:text-gray-600 text-sm cursor-pointer"
          >
            ✕
          </button>
        </div>

        <form @submit.prevent="guardarEdicion" class="space-y-4">
          <div
            v-if="errorEditar"
            class="p-2.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg"
          >
            {{ errorEditar }}
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1.5">Usuario</label>
            <input
              v-model="formEditar.usuario"
              type="text"
              class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1.5">Rol</label>
              <select
                v-model="formEditar.rol"
                class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-600"
              >
                <option value="Admin">Admin</option>
                <option value="Control de Estudio">Control de Estudio</option>
                <option value="Secretaria">Secretaria</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold text-gray-600 mb-1.5">Estado</label>
              <select
                v-model="formEditar.estado"
                class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-600"
              >
                <option value="Activo">Activo</option>
                <option value="Inactivo">Inactivo</option>
              </select>
            </div>
          </div>

          <div class="pt-2 border-t border-gray-100">
            <p class="text-xs font-semibold text-gray-700 mb-3">
              Cambiar contraseña <span class="font-normal text-gray-400">(opcional)</span>
            </p>

            <div class="space-y-3">
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1">Nueva contraseña</label>
                <input
                  v-model="formEditar.password"
                  type="password"
                  placeholder="Dejar en blanco para mantener actual"
                  class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>

              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1">Confirmar nueva contraseña</label>
                <input
                  v-model="formEditar.confirmPassword"
                  type="password"
                  placeholder="Repetir nueva contraseña"
                  class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
            </div>
          </div>

          <div class="flex gap-3 pt-3">
            <button
              type="button"
              @click="mostrarModalEditar = false"
              class="flex-1 py-2 px-4 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-lg transition-colors cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              class="flex-1 py-2 px-4 bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors cursor-pointer"
            >
              Guardar cambios
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.2s ease-out;
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
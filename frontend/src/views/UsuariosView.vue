<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRecursoPaginado } from '@/composables/useRecursoPaginado'
import { norm } from '@/components/gestion-academica/helpers'
import {
  listarUsuarios,
  listarTodosUsuarios,
  crearUsuario,
  actualizarUsuario,
  eliminarUsuario,
  cambiarMiClave,
  ROLES_ASIGNABLES,
  ROLES_USUARIO,
  NIVELES,
  etiquetaRol,
  etiquetaNivel,
} from '@/services/usuarios'

const POR_PAGINA = 10

// Filtros: rol y nivel los aplica el backend; el nombre se filtra en cliente
// sobre la lista completa porque /usuarios/ no tiene búsqueda por texto.
const filtroNombre = ref('')
const filtroRol = ref('')
const filtroNivel = ref('')
const pagina = ref(1)
const datos = reactive({ usuarios: [] })

const usuarios = useRecursoPaginado({
  listar: (args) => listarUsuarios({
    ...args,
    rol: filtroRol.value || undefined,
  }),
  listarTodos: (args) => listarTodosUsuarios({
    ...args,
    rol: filtroRol.value || undefined,
  }),
  getNivel: () => filtroNivel.value,
  asignar: (items) => { datos.usuarios = items },
  porDefecto: POR_PAGINA,
})
const api = usuarios.estado

const aviso = ref('')
const busqueda = computed(() => norm(filtroNombre.value).trim())
const filtrando = computed(() => busqueda.value !== '')
const filtrados = computed(() =>
  filtrando.value
    ? api.todos.filter((u) => norm(u.nombre).includes(busqueda.value))
    : [],
)
const buscando = computed(() => filtrando.value && !api.todosListo)
const cargando = computed(() => api.loading || api.cargandoTodos)

// Paginación del servidor salvo cuando hay búsqueda: ahí se pagina en cliente.
const totalFiltrado = computed(() => (filtrando.value ? filtrados.value.length : api.total))
const totalPaginas = computed(() => Math.max(1, Math.ceil(totalFiltrado.value / api.size)))
const pg = computed(() => Math.min(filtrando.value ? pagina.value : api.page, totalPaginas.value))
const filasPagina = computed(() => {
  if (!filtrando.value) return datos.usuarios
  const inicio = (pg.value - 1) * api.size
  return filtrados.value.slice(inicio, inicio + api.size)
})
const desde = computed(() => (totalFiltrado.value ? (pg.value - 1) * api.size + 1 : 0))
const hasta = computed(() => Math.min(pg.value * api.size, totalFiltrado.value))

const irPagina = (n) => {
  const destino = Math.min(Math.max(1, n), totalPaginas.value)
  if (filtrando.value) {
    pagina.value = destino
    return
  }
  if (destino !== api.page) usuarios.cargar(destino)
}

// Al escribir se necesita la lista completa; el resto de filtros recarga la API.
watch(filtroNombre, () => {
  pagina.value = 1
  aviso.value = ''
  if (filtrando.value && !api.todosListo && !api.cargandoTodos) usuarios.cargarTodos()
})
watch([filtroRol, filtroNivel], () => {
  pagina.value = 1
  aviso.value = ''
  usuarios.reiniciar()
  usuarios.cargar(1)
  // Si además hay búsqueda por nombre, la caché usada para filtrar también
  // tiene que recargarse con el nuevo rol/nivel.
  if (filtrando.value) usuarios.cargarTodos()
})
watch(() => api.size, () => {
  pagina.value = 1
  usuarios.cargar(1)
})

onMounted(() => usuarios.cargar(1))

const esAdmin = (usuario) => usuario?.rol === 'ADMINISTRADOR'

const trasCambio = async (mensaje) => {
  aviso.value = mensaje
  await usuarios.refrescar({ conTodos: filtrando.value })
}

// ───────────── Alta ─────────────
const panelCrear = ref(false)
const errorCrear = ref('')
const formNuevo = reactive({ nombre: '', clave: '', confirmar: '', rol: '', nivel: '' })

const abrirCrear = () => {
  Object.assign(formNuevo, { nombre: '', clave: '', confirmar: '', rol: '', nivel: '' })
  errorCrear.value = ''
  panelCrear.value = !panelCrear.value
}

const guardarNuevo = async () => {
  errorCrear.value = ''
  if (!formNuevo.nombre.trim() || !formNuevo.rol || !formNuevo.nivel) {
    errorCrear.value = 'El usuario, el rol y el nivel son obligatorios.'
    return
  }
  if (formNuevo.clave.length < 8) {
    errorCrear.value = 'La contraseña debe tener al menos 8 caracteres.'
    return
  }
  if (formNuevo.clave !== formNuevo.confirmar) {
    errorCrear.value = 'Las contraseñas no coinciden.'
    return
  }

  try {
    await crearUsuario(formNuevo)
    panelCrear.value = false
    await trasCambio('Usuario creado correctamente.')
  } catch (error) {
    errorCrear.value = error?.message || 'No se pudo crear el usuario.'
  }
}

// ───────────── Edición ─────────────
const modalEditar = ref(false)
const errorEditar = ref('')
const formEditar = reactive({ id: null, nombre: '', rol: '', nivel: '' })

const abrirEditar = (usuario) => {
  if (esAdmin(usuario)) return
  Object.assign(formEditar, {
    id: usuario.id,
    nombre: usuario.nombre,
    rol: usuario.rol,
    nivel: usuario.nivel || '',
  })
  errorEditar.value = ''
  modalEditar.value = true
}

const guardarEdicion = async () => {
  errorEditar.value = ''
  if (!formEditar.nombre.trim() || !formEditar.rol || !formEditar.nivel) {
    errorEditar.value = 'El usuario, el rol y el nivel son obligatorios.'
    return
  }

  try {
    await actualizarUsuario(formEditar.id, {
      nombre: formEditar.nombre,
      rol: formEditar.rol,
      nivel: formEditar.nivel,
    })
    modalEditar.value = false
    await trasCambio('Usuario actualizado correctamente.')
  } catch (error) {
    errorEditar.value = error?.message || 'No se pudo actualizar el usuario.'
  }
}

// ───────────── Baja ─────────────
const confirmacion = reactive({ abierta: false, usuario: null })
const errorBaja = ref('')

const pedirBaja = (usuario) => {
  if (esAdmin(usuario)) return
  confirmacion.usuario = usuario
  errorBaja.value = ''
  confirmacion.abierta = true
}

const confirmarBaja = async () => {
  errorBaja.value = ''
  try {
    await eliminarUsuario(confirmacion.usuario.id)
    confirmacion.abierta = false
    confirmacion.usuario = null
    await trasCambio('Usuario dado de baja correctamente.')
  } catch (error) {
    errorBaja.value = error?.message || 'No se pudo dar de baja al usuario.'
  }
}

// ───────────── Cambiar la clave de la sesión ─────────────
const modalClave = ref(false)
const errorClave = ref('')
const formClave = reactive({ actual: '', nueva: '', confirmar: '' })

const abrirClave = () => {
  Object.assign(formClave, { actual: '', nueva: '', confirmar: '' })
  errorClave.value = ''
  modalClave.value = true
}

const guardarClave = async () => {
  errorClave.value = ''
  if (!formClave.actual) {
    errorClave.value = 'Indica tu contraseña actual.'
    return
  }
  if (formClave.nueva.length < 8) {
    errorClave.value = 'La nueva contraseña debe tener al menos 8 caracteres.'
    return
  }
  if (formClave.nueva !== formClave.confirmar) {
    errorClave.value = 'Las contraseñas nuevas no coinciden.'
    return
  }

  try {
    await cambiarMiClave({ claveActual: formClave.actual, claveNueva: formClave.nueva })
    modalClave.value = false
    aviso.value = 'Tu contraseña se actualizó correctamente.'
  } catch (error) {
    errorClave.value = error?.message || 'No se pudo cambiar la contraseña.'
  }
}
</script>

<template>
  <div class="w-full space-y-6">
    <p v-if="aviso" role="status" class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-800">
      {{ aviso }}
    </p>

    <!-- Filtros -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div>
        <label for="fil-nombre" class="mb-1.5 block text-xs font-semibold text-gray-600">Buscar usuario</label>
        <input id="fil-nombre" v-model="filtroNombre" type="search" placeholder="Nombre de usuario"
               class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-600" />
      </div>
      <div>
        <label for="fil-rol" class="mb-1.5 block text-xs font-semibold text-gray-600">Rol</label>
        <select id="fil-rol" v-model="filtroRol"
                class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-600">
          <option value="">Todos</option>
          <option v-for="rol in ROLES_USUARIO" :key="rol.valor" :value="rol.valor">{{ rol.etiqueta }}</option>
        </select>
      </div>
      <div>
        <label for="fil-nivel" class="mb-1.5 block text-xs font-semibold text-gray-600">Nivel</label>
        <select id="fil-nivel" v-model="filtroNivel"
                class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-600">
          <option value="">Todos</option>
          <option v-for="nivel in NIVELES" :key="nivel.valor" :value="nivel.valor">{{ nivel.etiqueta }}</option>
        </select>
      </div>
    </div>

    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex flex-wrap gap-2">
        <button type="button" @click="abrirClave"
                class="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-50">
          Cambiar mi clave
        </button>
        <button type="button" @click="abrirCrear"
                class="rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-800">
          {{ panelCrear ? 'Cerrar formulario' : '+ Agregar usuario' }}
        </button>
      </div>
      <label class="flex items-center gap-2 text-xs font-semibold text-gray-600">
        Por página
        <select v-model.number="api.size" class="rounded-lg border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-700">
          <option :value="10">10</option>
          <option :value="25">25</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </label>
    </div>

    <div class="flex flex-col gap-6 xl:flex-row xl:items-start">
      <div class="w-full flex-1 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <p v-if="api.error" role="alert" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
          {{ api.error }}
          <button type="button" class="ml-2 font-bold underline" @click="usuarios.cargar(1)">Reintentar</button>
        </p>

        <div class="overflow-x-auto">
          <table class="w-full border-collapse text-left">
            <thead>
              <tr class="bg-gray-100 text-xs font-semibold text-gray-600">
                <th class="rounded-l-lg px-4 py-3">N.º</th>
                <th class="px-4 py-3">Usuario</th>
                <th class="px-4 py-3">Rol</th>
                <th class="px-4 py-3">Nivel</th>
                <th class="rounded-r-lg px-4 py-3 text-right">Acción</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 text-sm text-gray-700">
              <tr v-for="(usuario, index) in filasPagina" :key="usuario.id" class="transition-colors hover:bg-gray-50/80">
                <td class="px-4 py-3.5 font-medium text-gray-900">#{{ (pg - 1) * api.size + index + 1 }}</td>
                <td class="px-4 py-3.5 font-medium text-gray-900">{{ usuario.nombre }}</td>
                <td class="px-4 py-3.5">
                  <span class="rounded-full px-3 py-0.5 text-xs font-medium"
                        :class="{
                          'bg-blue-100 text-blue-800': usuario.rol === 'ADMINISTRADOR',
                          'bg-amber-100 text-amber-800': usuario.rol === 'COORDINADOR',
                          'bg-purple-100 text-purple-800': usuario.rol === 'SECRETARIA',
                        }">
                    {{ etiquetaRol(usuario.rol) }}
                  </span>
                </td>
                <td class="px-4 py-3.5">{{ etiquetaNivel(usuario.nivel) }}</td>
                <td class="px-4 py-3.5 text-right text-xs">
                  <template v-if="esAdmin(usuario)">
                    <span class="text-gray-400">Sin acciones</span>
                  </template>
                  <template v-else>
                    <button type="button" class="font-medium text-blue-600 hover:underline" @click="abrirEditar(usuario)">Editar</button>
                    <span class="mx-2 text-gray-300">·</span>
                    <button type="button" class="font-medium text-red-600 hover:underline" @click="pedirBaja(usuario)">Eliminar</button>
                  </template>
                </td>
              </tr>

              <tr v-if="!cargando && filasPagina.length === 0">
                <td colspan="5" class="py-8 text-center text-sm text-gray-400">
                  {{ filtrando ? 'No se encontraron usuarios con ese nombre.' : 'No hay usuarios registrados.' }}
                </td>
              </tr>
              <tr v-if="cargando && filasPagina.length === 0">
                <td colspan="5" class="py-8 text-center text-sm text-gray-400">Cargando usuarios…</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-2 flex flex-wrap items-center justify-between gap-4 border-t border-gray-100 pt-4 text-xs text-gray-500">
          <span v-if="buscando">Buscando en todos los usuarios…</span>
          <span v-else>Mostrando {{ desde }}–{{ hasta }} de {{ totalFiltrado }} usuarios</span>
          <div class="flex items-center gap-2">
            <button type="button" :disabled="pg === 1 || cargando" @click="irPagina(pg - 1)"
                    class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 disabled:cursor-not-allowed disabled:text-gray-400">Anterior</button>
            <span class="px-2 font-medium text-gray-600">Página {{ pg }} de {{ totalPaginas }}</span>
            <button type="button" :disabled="pg === totalPaginas || cargando" @click="irPagina(pg + 1)"
                    class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 disabled:cursor-not-allowed disabled:text-gray-400">Siguiente</button>
          </div>
        </div>
      </div>

      <!-- Alta de usuario -->
      <div v-if="panelCrear" class="w-full rounded-xl border border-gray-200 bg-white p-6 shadow-sm xl:w-[360px]">
        <div class="mb-4 flex items-center justify-between border-b border-gray-100 pb-3">
          <h3 class="text-base font-semibold text-gray-800">Nuevo usuario</h3>
          <button type="button" class="text-sm text-gray-400 hover:text-gray-600" @click="panelCrear = false">✕</button>
        </div>

        <form class="space-y-4" @submit.prevent="guardarNuevo">
          <p v-if="errorCrear" role="alert" class="rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-700">{{ errorCrear }}</p>

          <div>
            <label for="nue-nombre" class="mb-1.5 block text-xs font-semibold text-gray-600">Usuario</label>
            <input id="nue-nombre" v-model="formNuevo.nombre" type="text" placeholder="Ej: jperez"
                   class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600" />
          </div>
          <div>
            <label for="nue-rol" class="mb-1.5 block text-xs font-semibold text-gray-600">Rol</label>
            <select id="nue-rol" v-model="formNuevo.rol"
                    class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600">
              <option value="" disabled>Seleccione un rol</option>
              <option v-for="rol in ROLES_ASIGNABLES" :key="rol.valor" :value="rol.valor">{{ rol.etiqueta }}</option>
            </select>
          </div>
          <div>
            <label for="nue-nivel" class="mb-1.5 block text-xs font-semibold text-gray-600">Nivel</label>
            <select id="nue-nivel" v-model="formNuevo.nivel"
                    class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600">
              <option value="" disabled>Seleccione un nivel</option>
              <option v-for="nivel in NIVELES" :key="nivel.valor" :value="nivel.valor">{{ nivel.etiqueta }}</option>
            </select>
          </div>
          <div>
            <label for="nue-clave" class="mb-1.5 block text-xs font-semibold text-gray-600">Contraseña</label>
            <input id="nue-clave" v-model="formNuevo.clave" type="password" placeholder="Mínimo 8 caracteres"
                   class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600" />
          </div>
          <div>
            <label for="nue-confirmar" class="mb-1.5 block text-xs font-semibold text-gray-600">Verificar contraseña</label>
            <input id="nue-confirmar" v-model="formNuevo.confirmar" type="password" placeholder="Repita la contraseña"
                   class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600" />
          </div>

          <div class="flex gap-3 pt-2">
            <button type="button" class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50" @click="panelCrear = false">Cancelar</button>
            <button type="submit" class="flex-1 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800">Guardar</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edición -->
    <div v-if="modalEditar" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-lg">
        <div class="mb-4 flex items-center justify-between border-b border-gray-100 pb-3">
          <div>
            <h3 class="text-base font-semibold text-gray-800">Editar usuario</h3>
            <p class="text-xs text-gray-500">Modifica el nombre, el rol o el nivel</p>
          </div>
          <button type="button" class="text-sm text-gray-400 hover:text-gray-600" @click="modalEditar = false">✕</button>
        </div>

        <form class="space-y-4" @submit.prevent="guardarEdicion">
          <p v-if="errorEditar" role="alert" class="rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-700">{{ errorEditar }}</p>
          <div>
            <label for="edi-nombre" class="mb-1.5 block text-xs font-semibold text-gray-600">Usuario</label>
            <input id="edi-nombre" v-model="formEditar.nombre" type="text"
                   class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600" />
          </div>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label for="edi-rol" class="mb-1.5 block text-xs font-semibold text-gray-600">Rol</label>
              <select id="edi-rol" v-model="formEditar.rol"
                      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600">
                <option v-for="rol in ROLES_ASIGNABLES" :key="rol.valor" :value="rol.valor">{{ rol.etiqueta }}</option>
              </select>
            </div>
            <div>
              <label for="edi-nivel" class="mb-1.5 block text-xs font-semibold text-gray-600">Nivel</label>
              <select id="edi-nivel" v-model="formEditar.nivel"
                      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600">
                <option v-for="nivel in NIVELES" :key="nivel.valor" :value="nivel.valor">{{ nivel.etiqueta }}</option>
              </select>
            </div>
          </div>
          <div class="flex gap-3 pt-3">
            <button type="button" class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50" @click="modalEditar = false">Cancelar</button>
            <button type="submit" class="flex-1 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800">Guardar cambios</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Baja -->
    <div v-if="confirmacion.abierta" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-lg">
        <h3 class="text-base font-semibold text-gray-800">Confirmar eliminación</h3>
        <p class="mt-3 text-sm text-gray-600">
          ¿Dar de baja al usuario «{{ confirmacion.usuario?.nombre }}»? Esta acción no se puede deshacer.
        </p>
        <p v-if="errorBaja" role="alert" class="mt-3 rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-700">{{ errorBaja }}</p>
        <div class="mt-5 flex gap-3">
          <button type="button" class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50" @click="confirmacion.abierta = false">Cancelar</button>
          <button type="button" class="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700" @click="confirmarBaja">Eliminar</button>
        </div>
      </div>
    </div>

    <!-- Cambiar clave de la sesión -->
    <div v-if="modalClave" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div class="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-lg">
        <div class="mb-4 flex items-center justify-between border-b border-gray-100 pb-3">
          <h3 class="text-base font-semibold text-gray-800">Cambiar mi clave</h3>
          <button type="button" class="text-sm text-gray-400 hover:text-gray-600" @click="modalClave = false">✕</button>
        </div>
        <form class="space-y-4" @submit.prevent="guardarClave">
          <p v-if="errorClave" role="alert" class="rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-700">{{ errorClave }}</p>
          <div>
            <label for="cla-actual" class="mb-1.5 block text-xs font-semibold text-gray-600">Contraseña actual</label>
            <input id="cla-actual" v-model="formClave.actual" type="password"
                   class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600" />
          </div>
          <div>
            <label for="cla-nueva" class="mb-1.5 block text-xs font-semibold text-gray-600">Nueva contraseña</label>
            <input id="cla-nueva" v-model="formClave.nueva" type="password" placeholder="Mínimo 8 caracteres"
                   class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600" />
          </div>
          <div>
            <label for="cla-confirmar" class="mb-1.5 block text-xs font-semibold text-gray-600">Confirmar nueva contraseña</label>
            <input id="cla-confirmar" v-model="formClave.confirmar" type="password"
                   class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600" />
          </div>
          <div class="flex gap-3 pt-2">
            <button type="button" class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50" @click="modalClave = false">Cancelar</button>
            <button type="submit" class="flex-1 rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800">Guardar</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

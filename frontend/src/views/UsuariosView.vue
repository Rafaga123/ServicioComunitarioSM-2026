<script setup>
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { useRecursoPaginado } from '@/composables/useRecursoPaginado'
import { norm } from '@/components/gestion-academica/helpers'
import { card, inp, lbl, btnP, btnS, btnPag } from '@/components/gestion-academica/estilos'
import UsuariosTabla from '@/components/usuarios/UsuariosTabla.vue'
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
const hayFiltros = computed(() => Boolean(filtroRol.value || filtroNivel.value))
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

const botonesPagina = computed(() => {
  const total = totalPaginas.value
  const actual = pg.value
  const nums = [...new Set([1, total, actual - 1, actual, actual + 1].filter((n) => n >= 1 && n <= total))].sort((a, b) => a - b)
  const out = []
  nums.forEach((n, i) => {
    if (i && n - nums[i - 1] > 1) out.push('…')
    out.push(n)
  })
  return out
})

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

const limpiarFiltros = () => {
  filtroRol.value = ''
  filtroNivel.value = ''
}

const recargar = () => {
  if (filtrando.value) {
    usuarios.cargar(1)
    usuarios.cargarTodos()
  } else {
    usuarios.cargar(pg.value)
  }
}

const trasCambio = async (mensaje) => {
  aviso.value = mensaje
  await usuarios.refrescar({ conTodos: filtrando.value })
}

// ───────────── Alta y edición (un solo panel) ─────────────
const panel = reactive({ abierto: false, modo: 'crear', guardando: false })
const form = reactive({ id: null, nombre: '', rol: '', nivel: '', clave: '', confirmar: '' })
const errorForm = ref('')
const panelRef = ref(null)
const tituloPanel = computed(() => (panel.modo === 'crear' ? 'Nuevo usuario' : 'Editar usuario'))

const formVacio = () => ({ id: null, nombre: '', rol: '', nivel: '', clave: '', confirmar: '' })

const enfocarPanel = () => {
  nextTick(() => panelRef.value?.querySelector('input, select')?.focus())
}

const abrirCrear = () => {
  Object.assign(form, formVacio())
  errorForm.value = ''
  panel.modo = 'crear'
  panel.abierto = true
  enfocarPanel()
}

const abrirEditar = (usuario) => {
  if (esAdmin(usuario)) return
  Object.assign(form, {
    ...formVacio(),
    id: usuario.id,
    nombre: usuario.nombre,
    rol: usuario.rol,
    nivel: usuario.nivel || '',
  })
  errorForm.value = ''
  panel.modo = 'editar'
  panel.abierto = true
  enfocarPanel()
}

const cerrarPanel = () => {
  if (panel.guardando) return
  panel.abierto = false
  errorForm.value = ''
}

const guardar = async () => {
  if (panel.guardando) return
  errorForm.value = ''

  if (!form.nombre.trim() || !form.rol || !form.nivel) {
    errorForm.value = 'El usuario, el rol y el nivel son obligatorios.'
    return
  }

  const creando = panel.modo === 'crear'
  if (creando) {
    if (form.clave.length < 8) {
      errorForm.value = 'La contraseña debe tener al menos 8 caracteres.'
      return
    }
    if (form.clave !== form.confirmar) {
      errorForm.value = 'Las contraseñas no coinciden.'
      return
    }
  }

  panel.guardando = true
  try {
    if (creando) {
      await crearUsuario({
        nombre: form.nombre,
        clave: form.clave,
        rol: form.rol,
        nivel: form.nivel,
      })
      panel.abierto = false
      await trasCambio('Usuario creado correctamente.')
    } else {
      await actualizarUsuario(form.id, {
        nombre: form.nombre,
        rol: form.rol,
        nivel: form.nivel,
      })
      panel.abierto = false
      await trasCambio('Usuario actualizado correctamente.')
    }
  } catch (error) {
    errorForm.value = error?.message || (creando
      ? 'No se pudo crear el usuario.'
      : 'No se pudo actualizar el usuario.')
  } finally {
    panel.guardando = false
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

const cerrarBaja = () => {
  confirmacion.abierta = false
  confirmacion.usuario = null
  errorBaja.value = ''
}

const confirmarBaja = async () => {
  errorBaja.value = ''
  try {
    await eliminarUsuario(confirmacion.usuario.id)
    cerrarBaja()
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
  <div class="mx-auto flex w-full max-w-[1320px] flex-col font-sans text-[#1b2a2f]">
    <div :class="[card, 'overflow-hidden']">
      <!-- Cabecera: el botón de la propia cuenta queda separado de la gestión -->
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-[#d5dbe6] bg-[#f6f9fe] px-5 py-4 md:px-6">
        <div>
          <h1 class="text-lg font-bold text-[#233E47]">Usuarios</h1>
          <p class="mt-0.5 text-sm text-[#4a5a63]">
            Gestiona cuentas de coordinación y secretaría. Solo administradores.
          </p>
        </div>
        <button type="button" :class="btnS" @click="abrirClave">
          <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>
          Cambiar mi clave
        </button>
      </div>

      <div class="flex flex-col gap-5 p-5 md:p-6">
        <!-- Barra única: buscador + filtros + tamaño de página + acción nueva -->
        <div class="flex flex-wrap items-center gap-3">
          <div class="relative min-w-[220px] flex-1">
            <label for="fil-nombre" class="sr-only">Buscar usuario</label>
            <svg aria-hidden="true" class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#5b6a72]" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
            <input
              id="fil-nombre"
              v-model="filtroNombre"
              type="search"
              placeholder="Buscar por nombre de usuario…"
              :class="[inp, '!pl-10']"
            >
          </div>
          <div class="flex items-center gap-2">
            <label for="fil-rol" :class="lbl">Rol</label>
            <select id="fil-rol" v-model="filtroRol" :class="[inp, '!h-10 !w-auto']">
              <option value="">Todos</option>
              <option v-for="rol in ROLES_USUARIO" :key="rol.valor" :value="rol.valor">{{ rol.etiqueta }}</option>
            </select>
          </div>
          <div class="flex items-center gap-2">
            <label for="fil-nivel" :class="lbl">Nivel</label>
            <select id="fil-nivel" v-model="filtroNivel" :class="[inp, '!h-10 !w-auto']">
              <option value="">Todos</option>
              <option v-for="nivel in NIVELES" :key="nivel.valor" :value="nivel.valor">{{ nivel.etiqueta }}</option>
            </select>
          </div>
          <div class="flex items-center gap-2">
            <label for="tam-usuarios" :class="lbl">Por página</label>
            <select id="tam-usuarios" v-model.number="api.size" :class="[inp, '!h-10 !w-auto']">
              <option :value="10">10</option>
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>
          <button type="button" :class="btnP" @click="abrirCrear">
            <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
            Nuevo usuario
          </button>
        </div>

        <!-- Error de carga -->
        <p v-if="api.error" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
          {{ api.error }}
          <button type="button" class="ml-2 font-bold underline" @click="recargar">Reintentar</button>
        </p>

        <!-- Listado -->
        <UsuariosTabla
          v-if="totalFiltrado > 0 || filtrando || cargando"
          :filas="filasPagina"
          :buscando="buscando"
          :cargando="cargando"
          :filtrando="filtrando"
          @editar="abrirEditar"
          @eliminar="pedirBaja"
        />

        <!-- Estado vacío: sin datos o sin coincidencias de filtro -->
        <div
          v-else-if="!api.error"
          class="flex flex-col items-center gap-2 rounded-xl border border-dashed border-[#91a5c9] bg-[#f6f9fe] px-4 py-14 text-center"
        >
          <svg aria-hidden="true" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#91a5c9" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/></svg>
          <template v-if="hayFiltros">
            <p class="text-lg font-bold text-[#233E47]">No hay usuarios con estos filtros</p>
            <p class="max-w-md text-sm text-[#4a5a63]">Prueba con otro rol o nivel para ampliar la búsqueda.</p>
            <button type="button" :class="[btnS, 'mt-2']" @click="limpiarFiltros">Limpiar filtros</button>
          </template>
          <template v-else>
            <p class="text-lg font-bold text-[#233E47]">Aún no hay usuarios</p>
            <p class="max-w-md text-sm text-[#4a5a63]">Registra la primera cuenta de coordinación o secretaría para empezar.</p>
            <button type="button" :class="[btnS, 'mt-2']" @click="abrirCrear">Crear primer usuario</button>
          </template>
        </div>

        <!-- Paginación -->
        <nav v-if="totalFiltrado > 0" aria-label="Paginación" class="flex flex-wrap items-center justify-between gap-3">
          <p class="text-sm text-[#4a5a63]">
            Mostrando <b class="text-[#233E47]">{{ desde }}–{{ hasta }}</b> de
            <b class="text-[#233E47]">{{ totalFiltrado }}</b>
            {{ filtrando ? 'coincidencias' : 'usuarios' }}
            <span v-if="cargando" class="ml-2 italic text-[#5b6a72]">actualizando…</span>
          </p>
          <div class="flex flex-wrap items-center gap-1.5">
            <span class="mr-1 whitespace-nowrap text-sm text-[#4a5a63]">
              Página <b class="text-[#233E47]">{{ pg }}</b> de <b class="text-[#233E47]">{{ totalPaginas }}</b>
            </span>
            <button type="button" :class="btnPag" :disabled="pg === 1 || cargando" aria-label="Primera página" @click="irPagina(1)">«</button>
            <button type="button" :class="btnPag" :disabled="pg === 1 || cargando" aria-label="Página anterior" @click="irPagina(pg - 1)">← Anterior</button>
            <template v-for="(b, i) in botonesPagina" :key="i">
              <span v-if="b === '…'" class="px-1 text-[#5b6a72]" aria-hidden="true">…</span>
              <button
                v-else
                type="button"
                :aria-current="b === pg ? 'page' : null"
                :aria-label="'Página ' + b"
                :class="[btnPag, b === pg ? '!border-[#233E47] !bg-[#233E47] !text-white' : '']"
                @click="irPagina(b)"
              >{{ b }}</button>
            </template>
            <button type="button" :class="btnPag" :disabled="pg === totalPaginas || cargando" aria-label="Página siguiente" @click="irPagina(pg + 1)">Siguiente →</button>
            <button type="button" :class="btnPag" :disabled="pg === totalPaginas || cargando" aria-label="Última página" @click="irPagina(totalPaginas)">»</button>
          </div>
        </nav>
      </div>
    </div>

    <!-- ═══════════ Panel lateral, confirmación y aviso ═══════════ -->
    <Teleport to="body">
      <Transition enter-active-class="transition-opacity duration-200" enter-from-class="opacity-0" leave-active-class="transition-opacity duration-150" leave-to-class="opacity-0">
        <div v-if="panel.abierto" class="fixed inset-0 z-40 bg-[#0f1f24]/50" aria-hidden="true" @click="cerrarPanel"></div>
      </Transition>
      <Transition enter-active-class="transition-transform duration-300 ease-out" enter-from-class="translate-x-full" leave-active-class="transition-transform duration-200 ease-in" leave-to-class="translate-x-full">
        <aside
          v-if="panel.abierto"
          ref="panelRef"
          role="dialog"
          aria-modal="true"
          :aria-label="tituloPanel"
          tabindex="-1"
          @keydown.esc="cerrarPanel"
          class="fixed inset-y-0 right-0 z-50 flex w-full flex-col bg-white font-sans text-[#1b2a2f] shadow-2xl sm:max-w-[480px]"
        >
          <header class="flex items-center justify-between border-b border-[#d5dbe6] bg-[#f6f9fe] px-6 py-4">
            <div>
              <h2 class="text-lg font-bold text-[#233E47]">{{ tituloPanel }}</h2>
              <p class="mt-0.5 text-sm text-[#4a5a63]">
                {{ panel.modo === 'crear'
                  ? 'Se creará una cuenta de coordinación o secretaría.'
                  : 'Actualiza el nombre, el rol o el nivel.' }}
              </p>
            </div>
            <button type="button" aria-label="Cerrar panel" class="grid h-10 w-10 place-items-center rounded-lg text-[#233E47] hover:bg-[#e4ecf8]" @click="cerrarPanel">
              <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
            </button>
          </header>

          <form class="flex min-h-0 flex-1 flex-col" @submit.prevent="guardar">
            <div class="flex-1 space-y-4 overflow-y-auto px-6 py-5">
              <p v-if="errorForm" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">{{ errorForm }}</p>

              <div>
                <label for="u-nombre" :class="lbl">Usuario</label>
                <input id="u-nombre" v-model="form.nombre" type="text" placeholder="Ej: jperez" autocomplete="off" :class="[inp, 'mt-1']">
              </div>

              <div class="grid gap-3 sm:grid-cols-2">
                <div>
                  <label for="u-rol" :class="lbl">Rol</label>
                  <select id="u-rol" v-model="form.rol" :class="[inp, 'mt-1']">
                    <option value="" disabled>Selecciona</option>
                    <option v-for="rol in ROLES_ASIGNABLES" :key="rol.valor" :value="rol.valor">{{ rol.etiqueta }}</option>
                  </select>
                </div>
                <div>
                  <label for="u-nivel" :class="lbl">Nivel</label>
                  <select id="u-nivel" v-model="form.nivel" :class="[inp, 'mt-1']">
                    <option value="" disabled>Selecciona</option>
                    <option v-for="nivel in NIVELES" :key="nivel.valor" :value="nivel.valor">{{ nivel.etiqueta }}</option>
                  </select>
                </div>
              </div>

              <template v-if="panel.modo === 'crear'">
                <div>
                  <label for="u-clave" :class="lbl">Contraseña</label>
                  <input id="u-clave" v-model="form.clave" type="password" placeholder="Mínimo 8 caracteres" autocomplete="new-password" :class="[inp, 'mt-1']">
                </div>
                <div>
                  <label for="u-confirmar" :class="lbl">Verificar contraseña</label>
                  <input id="u-confirmar" v-model="form.confirmar" type="password" placeholder="Repite la contraseña" autocomplete="new-password" :class="[inp, 'mt-1']">
                </div>
              </template>
            </div>

            <footer class="flex gap-3 border-t border-[#d5dbe6] px-6 py-4">
              <button type="button" :class="[btnS, 'flex-1']" @click="cerrarPanel">Cancelar</button>
              <button type="submit" :class="[btnP, 'flex-1']" :disabled="panel.guardando">
                {{ panel.guardando ? 'Guardando…' : 'Guardar' }}
              </button>
            </footer>
          </form>
        </aside>
      </Transition>

      <!-- Confirmación de baja -->
      <div v-if="confirmacion.abierta" class="fixed inset-0 z-[70] grid place-items-center bg-[#0f1f24]/60 p-4 font-sans" @keydown.esc="cerrarBaja">
        <div role="alertdialog" aria-modal="true" aria-label="Confirmar eliminación" class="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
          <h2 class="text-lg font-bold text-[#233E47]">Dar de baja a este usuario</h2>
          <p class="mt-2 text-sm text-[#4a5a63]">
            ¿Dar de baja a «{{ confirmacion.usuario?.nombre }}»? Esta acción no se puede deshacer.
          </p>
          <p v-if="errorBaja" role="alert" class="mt-3 rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">{{ errorBaja }}</p>
          <div class="mt-5 flex justify-end gap-3">
            <button type="button" :class="btnS" @click="cerrarBaja">Cancelar</button>
            <button type="button" :class="btnP" class="!bg-[#b42318] hover:!bg-[#8f1c12]" @click="confirmarBaja">Eliminar</button>
          </div>
        </div>
      </div>

      <!-- Cambiar la clave de la sesión -->
      <div v-if="modalClave" class="fixed inset-0 z-[70] grid place-items-center bg-[#0f1f24]/60 p-4 font-sans" @keydown.esc="modalClave = false">
        <div role="dialog" aria-modal="true" aria-label="Cambiar mi clave" class="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
          <div class="flex items-center justify-between border-b border-[#d5dbe6] pb-4">
            <div>
              <h2 class="text-lg font-bold text-[#233E47]">Cambiar mi clave</h2>
              <p class="mt-0.5 text-sm text-[#4a5a63]">Se actualiza la contraseña de tu propia cuenta.</p>
            </div>
            <button type="button" aria-label="Cerrar" class="grid h-10 w-10 place-items-center rounded-lg text-[#233E47] hover:bg-[#e4ecf8]" @click="modalClave = false">
              <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
            </button>
          </div>

          <form class="mt-4 space-y-4" @submit.prevent="guardarClave">
            <p v-if="errorClave" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">{{ errorClave }}</p>
            <div>
              <label for="cla-actual" :class="lbl">Contraseña actual</label>
              <input id="cla-actual" v-model="formClave.actual" type="password" autocomplete="current-password" :class="[inp, 'mt-1']">
            </div>
            <div>
              <label for="cla-nueva" :class="lbl">Nueva contraseña</label>
              <input id="cla-nueva" v-model="formClave.nueva" type="password" placeholder="Mínimo 8 caracteres" autocomplete="new-password" :class="[inp, 'mt-1']">
            </div>
            <div>
              <label for="cla-confirmar" :class="lbl">Confirmar nueva contraseña</label>
              <input id="cla-confirmar" v-model="formClave.confirmar" type="password" placeholder="Repite la contraseña" autocomplete="new-password" :class="[inp, 'mt-1']">
            </div>
            <div class="flex justify-end gap-3 pt-2">
              <button type="button" :class="btnS" @click="modalClave = false">Cancelar</button>
              <button type="submit" :class="btnP">Guardar</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Aviso -->
      <p v-if="aviso" role="status" class="fixed bottom-6 right-6 z-[80] rounded-xl bg-[#233E47] px-5 py-3 font-sans text-sm font-semibold text-white shadow-xl">{{ aviso }}</p>
    </Teleport>
  </div>
</template>

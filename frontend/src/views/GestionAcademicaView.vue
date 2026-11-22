<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted } from 'vue'
import {
  listarDocentes,
  listarTodosDocentes,
  crearDocente,
  actualizarDocente,
  eliminarDocente,
} from '../services/docentes'
import RepresentantesTabla from '@/components/gestion-academica/RepresentantesTabla.vue'
import EstudiantesTabla from '@/components/gestion-academica/EstudiantesTabla.vue'
import AsignaturasTabla from '@/components/gestion-academica/AsignaturasTabla.vue'
import DocentesTabla from '@/components/gestion-academica/DocentesTabla.vue'
import HorariosTabla from '@/components/gestion-academica/HorariosTabla.vue'
import {
  anios,
  secciones,
  dias,
  norm,
  ordinal,
  nomPersona,
  nomEst,
  nomDocente,
  diaNombre,
  gradoTexto,
} from '@/components/gestion-academica/helpers'
import {
  card,
  inp,
  lbl,
  btnP,
  btnS,
  tag,
  nada,
  aviso2,
  btnPag,
  sinRes,
} from '@/components/gestion-academica/estilos'

// Uso en el layout:  <GestionAcademicaView tab-inicial="estudiantes" />
// Valores de tab-inicial: representantes | estudiantes | asignaturas | docentes | horarios
const props = defineProps({
  tabInicial: { type: String, default: 'representantes' },
})

// ───────────── Catálogos ─────────────
// anios, secciones y dias viven en components/gestion-academica/helpers.js

// Registros por página (el backend acepta size de 1 a 100)
const POR_PAGINA = 10

const tabs = [
  { id: 'representantes', label: 'Representantes', nuevo: 'Nuevo representante', singular: 'representante' },
  { id: 'estudiantes', label: 'Estudiantes', nuevo: 'Nuevo estudiante', singular: 'estudiante' },
  { id: 'asignaturas', label: 'Asignaturas', nuevo: 'Nueva asignatura', singular: 'asignatura' },
  { id: 'docentes', label: 'Docentes', nuevo: 'Nuevo docente', singular: 'docente' },
  { id: 'horarios', label: 'Horarios', nuevo: 'Nuevo horario', singular: 'horario' },
]
const placeholders = {
  representantes: 'Buscar por nombre o apellido',
  estudiantes: 'Buscar por nombre o apellido',
  asignaturas: 'Buscar por nombre de la asignatura',
  docentes: 'Buscar por nombre o cédula',
  horarios: 'Buscar por grado, sección, día o asignatura',
}
const vacios = {
  representantes: { titulo: 'Aún no hay representantes registrados', texto: 'Registra a los representantes para poder vincularlos con sus estudiantes.', boton: 'Registrar representante' },
  estudiantes: { titulo: 'Aún no hay estudiantes registrados', texto: 'Cuando registres estudiantes aparecerán aquí con su grado, sección y representantes.', boton: 'Registrar estudiante' },
  asignaturas: { titulo: 'Aún no hay asignaturas registradas', texto: 'Crea las asignaturas para poder asignarlas a docentes y armar los horarios.', boton: 'Registrar asignatura' },
  docentes: { titulo: 'Aún no hay docentes registrados', texto: 'Registra a los docentes con su cédula para poder asignarles asignaturas y horarios.', boton: 'Registrar docente' },
  horarios: { titulo: 'Aún no hay horarios registrados', texto: 'Necesitas asignaturas registradas para armar el horario de cada grado y sección.', boton: 'Registrar horario' },
}
const tab = ref(tabs.some((t) => t.id === props.tabInicial) ? props.tabInicial : 'representantes')
const tabActual = computed(() => tabs.find((t) => t.id === tab.value))

// ───────────── Datos (vacíos: se llenan desde la API) ─────────────
// representantes: { id, nombre, apellido, telefono }
// estudiantes:    { id, primerNombre, segundoNombre, primerApellido, segundoApellido, gradoId, representanteIds[] }   (Estudiantes_Representantes)
// asignaturas:    { id, nombre }
// docentes:       { id, primerNombre, segundoNombre, primerApellido, segundoApellido, cedula }  (API /docentes)
// horarios:       { id, gradoId, asignaturaId, diaSemana, hora }
// grados:         { id, grado, seccion }
const datos = reactive({ representantes: [], estudiantes: [], asignaturas: [], docentes: [], horarios: [], grados: [] })
let seq = 0
const nuevoId = () => ++seq // TODO FastAPI: el id lo asigna el servidor

// ───────────── Docentes (única pestaña conectada a la API) ─────────────
// El backend pagina con offset/size y devuelve { items, total, offset, size }.
// No admite búsqueda por texto: para filtrar se trae la lista completa una vez
// (size=100 por página) y el filtrado/orden se hace en el cliente.
const docentesApi = reactive({
  page: 1,
  size: POR_PAGINA,
  total: 0,
  loading: false,
  error: '',
  cargado: false,
  todos: [], // caché completa para la búsqueda
  todosListo: false, // ¿ya se cargó la lista completa?
  cargandoTodos: false,
})
let peticionDocentes = 0 // evita que una respuesta vieja pise a una más reciente
let peticionTodos = 0

async function cargarDocentes(paginaSolicitada = docentesApi.page) {
  const solicitud = ++peticionDocentes
  docentesApi.loading = true
  docentesApi.error = ''

  try {
    const respuesta = await listarDocentes({ page: paginaSolicitada, size: docentesApi.size })
    if (solicitud !== peticionDocentes) return

    const ultimaPagina = Math.max(1, Math.ceil(respuesta.total / docentesApi.size))

    // Si la página pedida quedó vacía (por ejemplo al borrar el último registro),
    // retrocedemos a la última página válida.
    if (respuesta.total > 0 && paginaSolicitada > ultimaPagina) {
      docentesApi.page = ultimaPagina
      await cargarDocentes(ultimaPagina)
      return
    }

    datos.docentes = respuesta.items
    docentesApi.total = respuesta.total
    docentesApi.page = Math.min(Math.max(1, paginaSolicitada), ultimaPagina)
    docentesApi.cargado = true
  } catch (error) {
    if (solicitud !== peticionDocentes) return
    docentesApi.error = error?.message || 'No se pudieron cargar los docentes.'
  } finally {
    if (solicitud === peticionDocentes) docentesApi.loading = false
  }
}

async function cargarTodosDocentes() {
  const solicitud = ++peticionTodos
  docentesApi.cargandoTodos = true
  docentesApi.todosListo = false
  docentesApi.error = ''

  try {
    const { items } = await listarTodosDocentes()
    if (solicitud !== peticionTodos) return
    docentesApi.todos = items
    docentesApi.todosListo = true
  } catch (error) {
    if (solicitud !== peticionTodos) return
    docentesApi.todos = []
    docentesApi.error = error?.message || 'No se pudo cargar la lista completa de docentes.'
  } finally {
    if (solicitud === peticionTodos) docentesApi.cargandoTodos = false
  }
}

// Tras crear/editar/eliminar: refresca la página del servidor y, si hay una
// búsqueda activa, también la caché completa para que el filtro siga al día.
async function refrescarDocentes() {
  docentesApi.todos = []
  docentesApi.todosListo = false
  await cargarDocentes(docentesApi.page)
  if (filtrandoDocentes.value) await cargarTodosDocentes()
}

onMounted(() => {
  // Las demás pestañas siguen con datos locales hasta que sus endpoints se conecten.
  if (tab.value === 'docentes') cargarDocentes(1)
})

// El resto de listas se cargará desde la API más adelante.

// ───────────── Helpers ─────────────
// norm, ordinal, nomPersona, nomEst, nomDocente, diaNombre y gradoTexto
// vienen de components/gestion-academica/helpers.js
const porId = (lista, id) => datos[lista].find((x) => x.id === id)
const buscarGrado = (grado, seccion) => datos.grados.find((g) => g.grado === grado && g.seccion === seccion)
const obtenerGrado = (grado, seccion) => {
  let g = buscarGrado(grado, seccion)
  if (!g) {
    g = { id: nuevoId(), grado, seccion } // TODO FastAPI: el backend crea el grado si no existe
    datos.grados.push(g)
  }
  return g.id
}
const etiqueta = (t, x) =>
  t === 'estudiantes'
    ? nomEst(x)
    : t === 'asignaturas'
      ? x.nombre
      : t === 'docentes'
        ? nomDocente(x)
        : t === 'horarios'
          ? `${gradoTexto(datos.grados, x.gradoId)} · ${diaNombre(x.diaSemana)} ${x.hora.slice(0, 5)}`
          : nomPersona(x)

// ───────────── Búsqueda (un solo campo por pestaña) ─────────────
const busq = reactive({ representantes: '', estudiantes: '', asignaturas: '', docentes: '', horarios: '' })

const listaRepresentantes = computed(() => {
  const q = norm(busq.representantes)
  return datos.representantes.filter((r) => !q || norm(nomPersona(r)).includes(q))
})
const listaEstudiantes = computed(() => {
  const q = norm(busq.estudiantes)
  return datos.estudiantes.filter((e) => !q || norm(nomEst(e)).includes(q))
})
const listaAsignaturas = computed(() => {
  const q = norm(busq.asignaturas)
  return datos.asignaturas.filter((a) => !q || norm(a.nombre).includes(q))
})
// Búsqueda de docentes: el backend no filtra, así que se hace en cliente sobre
// la lista completa (nombre completo o cédula, sin mayúsculas ni acentos).
const docentesFiltro = computed(() => norm(busq.docentes).trim())
const filtrandoDocentes = computed(() => tab.value === 'docentes' && docentesFiltro.value !== '')
const docentesFiltrados = computed(() => {
  const q = docentesFiltro.value
  if (!q) return []
  return docentesApi.todos.filter(
    (d) => norm(nomDocente(d)).includes(q) || norm(d.cedula).includes(q),
  )
})
const buscandoDocentes = computed(() => filtrandoDocentes.value && !docentesApi.todosListo)
const cargandoDocentes = computed(() => docentesApi.loading || docentesApi.cargandoTodos)
const listaDocentes = computed(() =>
  filtrandoDocentes.value ? docentesFiltrados.value : datos.docentes,
)
const listaHorarios = computed(() => {
  const q = norm(busq.horarios)
  return datos.horarios
    .filter((h) => {
      const g = porId('grados', h.gradoId)
      const texto = `${gradoTexto(datos.grados, h.gradoId)} ${g?.grado ?? ''}${g?.seccion ?? ''} ${diaNombre(h.diaSemana)} ${porId('asignaturas', h.asignaturaId)?.nombre ?? ''}`
      return !q || norm(texto).includes(q)
    })
    .sort((a, b) => {
      const ga = porId('grados', a.gradoId), gb = porId('grados', b.gradoId)
      return (ga?.grado - gb?.grado) || (ga?.seccion ?? '').localeCompare(gb?.seccion ?? '') || (a.diaSemana - b.diaSemana) || a.hora.localeCompare(b.hora)
    })
})

// ───────────── Paginación ─────────────
const pagina = reactive({ representantes: 1, estudiantes: 1, asignaturas: 1, docentes: 1, horarios: 1 })
Object.keys(busq).forEach((k) => watch(() => busq[k], () => { pagina[k] = 1 })) // al buscar, vuelve a la página 1

// Al buscar docentes se necesita la lista completa para filtrar en cliente.
watch(() => busq.docentes, (valor) => {
  pagina.docentes = 1
  if (norm(valor).trim() && !docentesApi.todosListo && !docentesApi.cargandoTodos) {
    cargarTodosDocentes()
  }
})

const listaTab = computed(() => ({
  representantes: listaRepresentantes.value,
  estudiantes: listaEstudiantes.value,
  asignaturas: listaAsignaturas.value,
  docentes: listaDocentes.value,
  horarios: listaHorarios.value,
}[tab.value]))

// Docentes usa el total y la página del servidor, salvo cuando hay búsqueda
// activa: entonces se pagina en cliente sobre la lista completa filtrada.
const tamanoPagina = computed(() => (tab.value === 'docentes' ? docentesApi.size : POR_PAGINA))
const totalFiltrado = computed(() => {
  if (tab.value !== 'docentes') return listaTab.value.length
  return filtrandoDocentes.value ? docentesFiltrados.value.length : docentesApi.total
})
const totalPaginas = computed(() => Math.max(1, Math.ceil(totalFiltrado.value / tamanoPagina.value)))
const pg = computed(() => {
  if (tab.value !== 'docentes') return Math.min(pagina[tab.value], totalPaginas.value)
  return Math.min(
    filtrandoDocentes.value ? pagina.docentes : docentesApi.page,
    totalPaginas.value,
  )
})
const filasPagina = computed(() => {
  if (tab.value !== 'docentes') {
    return listaTab.value.slice((pg.value - 1) * tamanoPagina.value, pg.value * tamanoPagina.value)
  }
  if (!filtrandoDocentes.value) return datos.docentes
  const inicio = (pg.value - 1) * tamanoPagina.value
  return docentesFiltrados.value.slice(inicio, inicio + tamanoPagina.value)
})
const desde = computed(() => (totalFiltrado.value ? (pg.value - 1) * tamanoPagina.value + 1 : 0))
const hasta = computed(() => Math.min(pg.value * tamanoPagina.value, totalFiltrado.value))
const irPagina = (n) => {
  const destino = Math.min(Math.max(1, n), totalPaginas.value)

  if (tab.value === 'docentes') {
    if (filtrandoDocentes.value) {
      pagina.docentes = destino
      return
    }
    if (destino === docentesApi.page) return
    docentesApi.page = destino
    cargarDocentes(destino)
    return
  }

  pagina[tab.value] = destino
}
// Se observa el tamaño en vez de usar @change en el <select>: así la recarga
// siempre ocurre después de que v-model actualizó docentesApi.size.
watch(() => docentesApi.size, () => {
  pagina.docentes = 1
  if (filtrandoDocentes.value) return // se repagina en cliente
  docentesApi.page = 1
  cargarDocentes(1)
})
const totalTab = (id) => (id === 'docentes' ? docentesApi.total : datos[id].length)
const botonesPagina = computed(() => {
  const total = totalPaginas.value, p = pg.value
  const nums = [...new Set([1, total, p - 1, p, p + 1].filter((n) => n >= 1 && n <= total))].sort((a, b) => a - b)
  const out = []
  nums.forEach((n, i) => { if (i && n - nums[i - 1] > 1) out.push('…'); out.push(n) })
  return out
})

// ───────────── Panel lateral (crear / editar) ─────────────
const panel = reactive({ abierto: false, modo: 'crear' })
const form = ref({})
const errorForm = ref('')
const panelRef = ref(null)
const repBusq = ref('')

const formVacio = {
  representantes: () => ({ nombre: '', apellido: '', telefono: '' }),
  estudiantes: () => ({ primerNombre: '', segundoNombre: '', primerApellido: '', segundoApellido: '', anio: '', seccion: '', representanteIds: [] }),
  asignaturas: () => ({ nombre: '' }),
  docentes: () => ({ primerNombre: '', segundoNombre: '', primerApellido: '', segundoApellido: '', cedula: '' }),
  horarios: () => ({ anio: '', seccion: '', diaSemana: '', hora: '', asignaturaId: '' }),
}
const tituloPanel = computed(() => (panel.modo === 'crear' ? tabActual.value.nuevo : `Editar ${tabActual.value.singular}`))

const enfocarPrimerCampo = async () => {
  await nextTick()
  panelRef.value?.querySelector('input, select, textarea')?.focus()
}
const abrirNuevo = () => {
  form.value = formVacio[tab.value]()
  panel.modo = 'crear'
  errorForm.value = ''
  repBusq.value = ''
  panel.abierto = true
  enfocarPrimerCampo()
}
const abrirEditar = (item) => {
  const copia = JSON.parse(JSON.stringify(item))
  if (tab.value === 'estudiantes' || tab.value === 'horarios') {
    const g = porId('grados', item.gradoId)
    copia.anio = g?.grado ?? ''
    copia.seccion = g?.seccion ?? ''
  }
  form.value = copia
  panel.modo = 'editar'
  errorForm.value = ''
  repBusq.value = ''
  panel.abierto = true
  enfocarPrimerCampo()
}
const cerrarPanel = () => { panel.abierto = false }
const irA = (id) => { cerrarPanel(); tab.value = id }
watch(tab, (valor) => {
  cerrarPanel()
  // La primera vez que se abre Docentes se pide la primera página al servidor.
  if (valor === 'docentes' && !docentesApi.cargado && !docentesApi.loading) cargarDocentes(1)
})

// Selector de representantes (Estudiantes_Representantes)
const repCoincidencias = computed(() => {
  const q = norm(repBusq.value.trim())
  const elegidos = form.value.representanteIds ?? []
  if (!q) return []
  return datos.representantes.filter((r) => !elegidos.includes(r.id) && norm(nomPersona(r)).includes(q)).slice(0, 6)
})
const agregarRep = (id) => { form.value.representanteIds.push(id); repBusq.value = '' }
const quitarRep = (id) => { form.value.representanteIds = form.value.representanteIds.filter((x) => x !== id) }

const validar = (t, f) => {
  const otros = datos[t].filter((x) => x.id !== f.id)
  if (t === 'asignaturas' && otros.some((x) => norm(x.nombre) === norm(f.nombre))) return 'Ya existe una asignatura con ese nombre.'
  if (t === 'horarios') {
    const g = buscarGrado(f.anio, f.seccion)
    if (g && otros.some((h) => h.gradoId === g.id && h.diaSemana === f.diaSemana && h.hora === f.hora)) return 'Ese grado y sección ya tiene una clase a esa hora.'
  }
  return ''
}
const construir = (t, f) => {
  if (t === 'estudiantes') {
    const { anio, seccion, ...r } = f
    return { ...r, gradoId: obtenerGrado(anio, seccion) }
  }
  if (t === 'horarios') {
    const { anio, seccion, ...r } = f
    return { ...r, gradoId: obtenerGrado(anio, seccion) }
  }
  return { ...f }
}

const guardando = ref(false)

const guardar = async () => {
  const t = tab.value, f = form.value
  for (const k in f) if (typeof f[k] === 'string') f[k] = f[k].trim()
  const err = validar(t, f)
  if (err) { errorForm.value = err; return }

  // Docentes: crear/actualizar en la API y recargar la página actual.
  if (t === 'docentes') {
    const creando = panel.modo === 'crear'
    errorForm.value = ''
    guardando.value = true
    try {
      if (creando) await crearDocente(f)
      else await actualizarDocente(f.id, f)
      cerrarPanel()
      avisar(creando ? 'Registro creado correctamente.' : 'Cambios guardados.')
      await refrescarDocentes()
    } catch (error) {
      errorForm.value = error?.message || 'No se pudo guardar el docente.'
    } finally {
      guardando.value = false
    }
    return
  }

  const registro = construir(t, f)
  // TODO FastAPI: POST /api/{t} (crear) o PUT /api/{t}/{id} (editar)
  if (panel.modo === 'crear') datos[t].push({ ...registro, id: nuevoId() })
  else {
    const i = datos[t].findIndex((x) => x.id === f.id)
    if (i > -1) datos[t][i] = registro
  }
  cerrarPanel()
  avisar(panel.modo === 'crear' ? 'Registro creado correctamente.' : 'Cambios guardados.')
}

// ───────────── Eliminar, confirmaciones y avisos ─────────────
const confirmacion = ref(null)
const pedirConfirmacion = (titulo, texto, boton, accion) => { confirmacion.value = { titulo, texto, boton, accion } }
const confirmar = async () => {
  const accion = confirmacion.value?.accion
  confirmacion.value = null
  if (accion) await accion()
}

const aviso = ref('')
let temporizador = null
const avisar = (msg) => {
  aviso.value = msg
  clearTimeout(temporizador)
  temporizador = setTimeout(() => (aviso.value = ''), 4000)
}

const consecuencias = {
  representantes: ' Se quitará su vínculo con los estudiantes.',
  asignaturas: ' Se quitará de los docentes y se eliminarán sus horarios.',
  docentes: '',
  estudiantes: '',
  horarios: '',
}
const eliminar = (item) => {
  const t = tab.value
  pedirConfirmacion(`Eliminar ${tabActual.value.singular}`, `¿Eliminar "${etiqueta(t, item)}"? Esta acción no se puede deshacer.${consecuencias[t]}`, 'Eliminar', async () => {
    // Docentes: borrado real en la API (soft delete) y recarga de la página.
    if (t === 'docentes') {
      try {
        await eliminarDocente(item.id)
        avisar('Registro eliminado.')
        await refrescarDocentes()
      } catch (error) {
        // Se conserva el mensaje para que el usuario pueda reintentar.
        docentesApi.error = error?.message || 'No se pudo eliminar el docente.'
        avisar(docentesApi.error)
      }
      return
    }

    // TODO FastAPI: DELETE /api/{t}/{id}
    if (t === 'representantes') datos.estudiantes.forEach((e) => { e.representanteIds = e.representanteIds.filter((id) => id !== item.id) })
    if (t === 'asignaturas') {
      datos.docentes.forEach((d) => { d.asignaturaIds = (d.asignaturaIds ?? []).filter((id) => id !== item.id) })
      datos.horarios = datos.horarios.filter((h) => h.asignaturaId !== item.id)
    }
    datos[t] = datos[t].filter((x) => x.id !== item.id)
    avisar('Registro eliminado.')
  })
}

// ───────────── Clases reutilizables ─────────────
// card, inp, lbl, btnP, btnS, tag, nada, aviso2, btnPag y sinRes
// viven en components/gestion-academica/estilos.js
</script>

<template>
  <div class="mx-auto flex w-full max-w-[1320px] flex-col font-sans text-[#1b2a2f]">

    <div :class="[card, 'overflow-hidden']">
      <!-- Pestañas (arriba, pegadas al inicio del componente) -->
      <div role="tablist" aria-label="Secciones de gestión académica" class="flex gap-1 overflow-x-auto border-b border-[#d5dbe6] bg-[#f6f9fe] px-3 pt-2.5">
        <button v-for="t in tabs" :key="t.id" role="tab" type="button" :aria-selected="tab === t.id" @click="tab = t.id"
                :class="['flex min-h-11 items-center gap-2 whitespace-nowrap rounded-t-xl border-b-[3px] px-4 text-[15px] transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#233E47]',
                         tab === t.id ? 'border-[#233E47] bg-white font-bold text-[#233E47]' : 'border-transparent font-semibold text-[#4a5a63] hover:text-[#233E47]']">
          {{ t.label }}
          <span :class="['rounded-full px-2 py-0.5 text-xs font-bold', tab === t.id ? 'bg-[#ccd5ae] text-[#233E47]' : 'bg-[#e4e7ee] text-[#4a5a63]']">{{ totalTab(t.id) }}</span>
        </button>
      </div>

      <div role="tabpanel" class="flex flex-col gap-5 p-5 md:p-6">

        <!-- Barra: buscador + tamaño de página (docentes) + botón nuevo -->
        <div class="flex flex-wrap items-center gap-3">
          <div class="relative min-w-[220px] flex-1">
            <label for="busq" class="sr-only">Buscar</label>
            <svg aria-hidden="true" class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[#5b6a72]" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
            <input id="busq" v-model="busq[tab]" type="search" :placeholder="placeholders[tab]" :class="[inp, '!pl-10']">
          </div>
          <div v-if="tab === 'docentes'" class="flex items-center gap-2">
            <label for="tam-doc" class="whitespace-nowrap text-sm font-semibold text-[#233E47]">Por página</label>
            <select id="tam-doc" v-model.number="docentesApi.size" :class="[inp, '!h-10 !w-auto']">
              <option :value="10">10</option>
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>
          <button type="button" :class="btnP" @click="abrirNuevo">
            <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
            {{ tabActual.nuevo }}
          </button>
        </div>

        <!-- Resumen del filtro y del total (sólo docentes) -->
        <p v-if="tab === 'docentes' && !(docentesApi.error && !docentesApi.cargado)" class="-mt-1 text-sm text-[#4a5a63]">
          <span v-if="buscandoDocentes">Buscando en todos los docentes…</span>
          <span v-else-if="filtrandoDocentes"><b class="text-[#233E47]">{{ totalFiltrado }}</b> coincidencia(s) de <b class="text-[#233E47]">{{ docentesApi.total }}</b> docente(s)</span>
          <span v-else><b class="text-[#233E47]">{{ docentesApi.total }}</b> docente(s) registrado(s)</span>
        </p>

        <!-- Error de carga (sólo docentes) -->
        <p v-if="tab === 'docentes' && docentesApi.error" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
          {{ docentesApi.error }}
          <button type="button" class="ml-2 font-bold underline" @click="filtrandoDocentes ? cargarTodosDocentes() : cargarDocentes(docentesApi.page)">Reintentar</button>
        </p>

        <!-- Cargando la primera página (sólo docentes) -->
        <p v-if="tab === 'docentes' && docentesApi.loading && !datos.docentes.length" :class="sinRes">Cargando docentes…</p>

        <!-- Estado vacío general (aún no hay ningún dato) -->
        <div v-if="!datos[tab].length && !(tab === 'docentes' && (docentesApi.loading || docentesApi.error))" class="flex flex-col items-center gap-2 rounded-xl border border-dashed border-[#91a5c9] bg-[#f6f9fe] px-4 py-14 text-center">
          <svg aria-hidden="true" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#91a5c9" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M7 9.5V15c0 1.5 2.2 3 5 3s5-1.5 5-3V9.5"/></svg>
          <p class="text-lg font-bold text-[#233E47]">{{ vacios[tab].titulo }}</p>
          <p class="max-w-md text-sm text-[#4a5a63]">{{ vacios[tab].texto }}</p>
          <button type="button" :class="[btnS, 'mt-2']" @click="abrirNuevo">{{ vacios[tab].boton }}</button>
        </div>

        <template v-else-if="datos[tab].length">

          <!-- Cada pestaña vive en su propio componente -->
          <RepresentantesTabla
            v-if="tab === 'representantes'"
            :filas="filasPagina"
            :estudiantes="datos.estudiantes"
            @editar="abrirEditar"
            @eliminar="eliminar"
          />

          <EstudiantesTabla
            v-else-if="tab === 'estudiantes'"
            :filas="filasPagina"
            :representantes="datos.representantes"
            :grados="datos.grados"
            @editar="abrirEditar"
            @eliminar="eliminar"
          />

          <AsignaturasTabla
            v-else-if="tab === 'asignaturas'"
            :filas="filasPagina"
            :docentes="datos.docentes"
            @editar="abrirEditar"
            @eliminar="eliminar"
          />

          <DocentesTabla
            v-else-if="tab === 'docentes'"
            :filas="filasPagina"
            :buscando="buscandoDocentes"
            :cargando="docentesApi.cargandoTodos"
            :filtrando="filtrandoDocentes"
            @editar="abrirEditar"
            @eliminar="eliminar"
          />

          <HorariosTabla
            v-else
            :filas="filasPagina"
            :asignaturas="datos.asignaturas"
            :docentes="datos.docentes"
            :grados="datos.grados"
            @editar="abrirEditar"
            @eliminar="eliminar"
          />

          <!-- Paginación -->
          <nav v-if="totalFiltrado > 0" aria-label="Paginación" class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-sm text-[#4a5a63]">
              Mostrando <b class="text-[#233E47]">{{ desde }}–{{ hasta }}</b> de <b class="text-[#233E47]">{{ totalFiltrado }}</b>
              {{ tab === 'docentes' && filtrandoDocentes ? 'coincidencias' : 'registros' }}
              <span v-if="tab === 'docentes' && cargandoDocentes" class="ml-2 italic text-[#5b6a72]">actualizando…</span>
            </p>
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="mr-1 whitespace-nowrap text-sm text-[#4a5a63]">Página <b class="text-[#233E47]">{{ pg }}</b> de <b class="text-[#233E47]">{{ totalPaginas }}</b></span>
              <button type="button" :class="btnPag" :disabled="pg === 1 || (tab === 'docentes' && cargandoDocentes)" aria-label="Primera página" @click="irPagina(1)">«</button>
              <button type="button" :class="btnPag" :disabled="pg === 1 || (tab === 'docentes' && cargandoDocentes)" aria-label="Página anterior" @click="irPagina(pg - 1)">← Anterior</button>
              <template v-for="(b, i) in botonesPagina" :key="i">
                <span v-if="b === '…'" class="px-1 text-[#5b6a72]" aria-hidden="true">…</span>
                <button v-else type="button" :aria-current="b === pg ? 'page' : null" :aria-label="'Página ' + b"
                        :class="[btnPag, b === pg ? '!border-[#233E47] !bg-[#233E47] !text-white' : '']" @click="irPagina(b)">{{ b }}</button>
              </template>
              <button type="button" :class="btnPag" :disabled="pg === totalPaginas || (tab === 'docentes' && cargandoDocentes)" aria-label="Página siguiente" @click="irPagina(pg + 1)">Siguiente →</button>
              <button type="button" :class="btnPag" :disabled="pg === totalPaginas || (tab === 'docentes' && cargandoDocentes)" aria-label="Última página" @click="irPagina(totalPaginas)">»</button>
            </div>
          </nav>
        </template>
      </div>
    </div>

    <!-- ═══════════ Panel lateral, confirmación y aviso ═══════════ -->
    <Teleport to="body">
      <Transition enter-active-class="transition-opacity duration-200" enter-from-class="opacity-0" leave-active-class="transition-opacity duration-150" leave-to-class="opacity-0">
        <div v-if="panel.abierto" class="fixed inset-0 z-40 bg-[#0f1f24]/50" aria-hidden="true" @click="cerrarPanel"></div>
      </Transition>
      <Transition enter-active-class="transition-transform duration-300 ease-out" enter-from-class="translate-x-full" leave-active-class="transition-transform duration-200 ease-in" leave-to-class="translate-x-full">
        <aside v-if="panel.abierto" ref="panelRef" role="dialog" aria-modal="true" :aria-label="tituloPanel" @keydown.esc="cerrarPanel"
               class="fixed inset-y-0 right-0 z-50 flex w-full flex-col bg-white font-sans text-[#1b2a2f] shadow-2xl sm:max-w-[480px]">
          <header class="flex items-center justify-between border-b border-[#d5dbe6] bg-[#f6f9fe] px-6 py-4">
            <h2 class="text-lg font-bold text-[#233E47]">{{ tituloPanel }}</h2>
            <button type="button" aria-label="Cerrar panel" class="grid h-10 w-10 place-items-center rounded-lg text-[#233E47] hover:bg-[#e4ecf8]" @click="cerrarPanel">
              <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
            </button>
          </header>

          <form class="flex min-h-0 flex-1 flex-col" @submit.prevent="guardar">
            <div class="flex-1 space-y-4 overflow-y-auto px-6 py-5">
              <p v-if="errorForm" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">{{ errorForm }}</p>

              <!-- Representante -->
              <template v-if="tab === 'representantes'">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div><label for="f-nombre" :class="lbl">Nombre</label><input id="f-nombre" v-model="form.nombre" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-apellido" :class="lbl">Apellido</label><input id="f-apellido" v-model="form.apellido" maxlength="50" required :class="[inp, 'mt-1']"></div>
                </div>
                <div><label for="f-tel" :class="lbl">Número telefónico</label><input id="f-tel" v-model="form.telefono" type="tel" maxlength="50" required :class="[inp, 'mt-1']"></div>
              </template>

              <!-- Estudiante -->
              <template v-else-if="tab === 'estudiantes'">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div><label for="f-pn" :class="lbl">Primer nombre</label><input id="f-pn" v-model="form.primerNombre" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-sn" :class="lbl">Segundo nombre</label><input id="f-sn" v-model="form.segundoNombre" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-pa" :class="lbl">Primer apellido</label><input id="f-pa" v-model="form.primerApellido" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-sa" :class="lbl">Segundo apellido</label><input id="f-sa" v-model="form.segundoApellido" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div>
                    <label for="f-anio" :class="lbl">Grado (año)</label>
                    <select id="f-anio" v-model="form.anio" required :class="[inp, 'mt-1']"><option value="" disabled>Selecciona</option><option v-for="a in anios" :key="a" :value="a">{{ ordinal(a) }} Año</option></select>
                  </div>
                  <div>
                    <label for="f-sec" :class="lbl">Sección</label>
                    <select id="f-sec" v-model="form.seccion" required :class="[inp, 'mt-1']"><option value="" disabled>Selecciona</option><option v-for="s in secciones" :key="s" :value="s">{{ s }}</option></select>
                  </div>
                </div>

                <div>
                  <label for="f-rep" :class="lbl">Representantes</label>
                  <div v-if="form.representanteIds.length" class="mt-2 flex flex-wrap gap-1.5">
                    <span v-for="id in form.representanteIds" :key="id" :class="[tag, 'flex items-center gap-1.5 !py-1']">
                      {{ porId('representantes', id) ? nomPersona(porId('representantes', id)) : '—' }}
                      <button type="button" class="font-bold" :aria-label="'Quitar representante'" @click="quitarRep(id)">✕</button>
                    </span>
                  </div>
                  <p v-else :class="[nada, 'mt-2']">Sin representantes vinculados aún</p>
                  <input id="f-rep" v-model="repBusq" type="search" placeholder="Buscar representante por nombre o apellido" autocomplete="off" :class="[inp, 'mt-2']">
                  <p v-if="!datos.representantes.length" :class="aviso2">
                    Aún no hay representantes registrados.
                    <button type="button" class="font-bold underline" @click="irA('representantes')">Registrar uno primero</button>
                  </p>
                  <ul v-else-if="repBusq.trim()" class="mt-1 overflow-hidden rounded-xl border border-[#d5dbe6]">
                    <li v-for="r in repCoincidencias" :key="r.id">
                      <button type="button" class="flex min-h-11 w-full items-center justify-between gap-3 px-3 text-left text-sm hover:bg-[#eef3fb]" @click="agregarRep(r.id)">
                        <span class="font-semibold">{{ nomPersona(r) }}</span><span class="text-[#4a5a63]">{{ r.telefono }}</span>
                      </button>
                    </li>
                    <li v-if="!repCoincidencias.length" class="px-3 py-3 text-sm italic text-[#5b6a72]">Ningún representante coincide con la búsqueda.</li>
                  </ul>
                </div>
              </template>

              <!-- Asignatura -->
              <template v-else-if="tab === 'asignaturas'">
                <div><label for="f-nom" :class="lbl">Nombre de la asignatura</label><input id="f-nom" v-model="form.nombre" maxlength="50" required :class="[inp, 'mt-1']"></div>
              </template>

              <!-- Docente -->
              <template v-else-if="tab === 'docentes'">
                <div class="grid gap-3 sm:grid-cols-2">
                  <div><label for="f-d-pn" :class="lbl">Primer nombre</label><input id="f-d-pn" v-model="form.primerNombre" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-d-sn" :class="lbl">Segundo nombre</label><input id="f-d-sn" v-model="form.segundoNombre" maxlength="50" :class="[inp, 'mt-1']"></div>
                  <div><label for="f-d-pa" :class="lbl">Primer apellido</label><input id="f-d-pa" v-model="form.primerApellido" maxlength="50" required :class="[inp, 'mt-1']"></div>
                  <div><label for="f-d-sa" :class="lbl">Segundo apellido</label><input id="f-d-sa" v-model="form.segundoApellido" maxlength="50" :class="[inp, 'mt-1']"></div>
                </div>
                <div>
                  <label for="f-d-ced" :class="lbl">Cédula</label>
                  <input id="f-d-ced" v-model="form.cedula" maxlength="20" required inputmode="numeric" :class="[inp, 'mt-1']">
                </div>
                <p class="text-sm text-[#4a5a63]">Las asignaturas que dicta se gestionan aparte, desde la pestaña Asignaturas.</p>
              </template>

              <!-- Horario -->
              <template v-else>
                <div class="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label for="f-anio" :class="lbl">Grado (año)</label>
                    <select id="f-anio" v-model="form.anio" required :class="[inp, 'mt-1']"><option value="" disabled>Selecciona</option><option v-for="a in anios" :key="a" :value="a">{{ ordinal(a) }} Año</option></select>
                  </div>
                  <div>
                    <label for="f-sec" :class="lbl">Sección</label>
                    <select id="f-sec" v-model="form.seccion" required :class="[inp, 'mt-1']"><option value="" disabled>Selecciona</option><option v-for="s in secciones" :key="s" :value="s">{{ s }}</option></select>
                  </div>
                  <div>
                    <label for="f-dia" :class="lbl">Día de la semana</label>
                    <select id="f-dia" v-model="form.diaSemana" required :class="[inp, 'mt-1']"><option value="" disabled>Selecciona</option><option v-for="d in dias" :key="d.v" :value="d.v">{{ d.l }}</option></select>
                  </div>
                  <div><label for="f-hora" :class="lbl">Hora</label><input id="f-hora" v-model="form.hora" type="time" required :class="[inp, 'mt-1']"></div>
                </div>
                <div>
                  <label for="f-asig" :class="lbl">Asignatura</label>
                  <select id="f-asig" v-model="form.asignaturaId" required :class="[inp, 'mt-1']">
                    <option value="" disabled>Selecciona</option>
                    <option v-for="a in datos.asignaturas" :key="a.id" :value="a.id">{{ a.nombre }}</option>
                  </select>
                  <p v-if="!datos.asignaturas.length" :class="aviso2">
                    Aún no hay asignaturas registradas.
                    <button type="button" class="font-bold underline" @click="irA('asignaturas')">Ir a Asignaturas</button>
                  </p>
                </div>
              </template>
            </div>

            <footer class="flex gap-3 border-t border-[#d5dbe6] px-6 py-4">
              <button type="button" :class="[btnS, 'flex-1']" @click="cerrarPanel">Cancelar</button>
              <button type="submit" :class="[btnP, 'flex-1']" :disabled="guardando">{{ guardando ? 'Guardando…' : 'Guardar' }}</button>
            </footer>
          </form>
        </aside>
      </Transition>

      <!-- Confirmación -->
      <div v-if="confirmacion" class="fixed inset-0 z-[70] grid place-items-center bg-[#0f1f24]/60 p-4 font-sans" @keydown.esc="confirmacion = null">
        <div role="alertdialog" aria-modal="true" :aria-label="confirmacion.titulo" class="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
          <h2 class="text-lg font-bold text-[#233E47]">{{ confirmacion.titulo }}</h2>
          <p class="mt-2 text-sm text-[#4a5a63]">{{ confirmacion.texto }}</p>
          <div class="mt-5 flex justify-end gap-3">
            <button type="button" :class="btnS" @click="confirmacion = null">Cancelar</button>
            <button type="button" :class="btnP" class="!bg-[#b42318] hover:!bg-[#8f1c12]" @click="confirmar">{{ confirmacion.boton }}</button>
          </div>
        </div>
      </div>

      <!-- Aviso -->
      <p v-if="aviso" role="status" class="fixed bottom-6 right-6 z-[80] rounded-xl bg-[#233E47] px-5 py-3 font-sans text-sm font-semibold text-white shadow-xl">{{ aviso }}</p>
    </Teleport>
  </div>
</template>
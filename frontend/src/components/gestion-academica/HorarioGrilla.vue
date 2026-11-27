<script setup>
import { computed } from 'vue'
import { dias } from './helpers'
import { sinRes } from './estilos'

const props = defineProps({
  // Sección seleccionada (objeto de /secciones).
  seccion: { type: Object, default: null },
  // ¿Hay secciones de Liceo para el período? Sirve para distinguir entre
  // "elige una sección" y "todavía no hay secciones".
  haySecciones: { type: Boolean, default: false },
  // Todos los bloques de la jornada (académicos y recesos), en orden.
  bloques: { type: Array, default: () => [] },
  // Clases de la sección para el período seleccionado.
  horarios: { type: Array, default: () => [] },
  cargando: { type: Boolean, default: false },
  cargandoBloques: { type: Boolean, default: false },
  cargandoSecciones: { type: Boolean, default: false },
  error: { type: String, default: '' },
  errorBloques: { type: String, default: '' },
  errorSecciones: { type: String, default: '' },
  puedeGestionar: { type: Boolean, default: false },
})

const emit = defineEmits(['crear', 'editar', 'eliminar', 'reintentar', 'ir-secciones'])

// Paleta estable por asignatura: el mismo nombre siempre recibe el mismo tono.
// Las clases están escritas completas para que Tailwind las genere.
const PALETA = [
  'border-[#8fb3e6] bg-[#eaf2fd] text-[#173a68]',
  'border-[#9ec89a] bg-[#eef7ec] text-[#2c5728]',
  'border-[#e0be83] bg-[#fdf4e4] text-[#6b4a12]',
  'border-[#d8a8c4] bg-[#fbeef6] text-[#6a2f57]',
  'border-[#8fc7c2] bg-[#e9f7f4] text-[#1e5550]',
  'border-[#b9a9e3] bg-[#f2eefc] text-[#4a367e]',
  'border-[#e0aaa2] bg-[#fdeeec] text-[#7a2f25]',
  'border-[#c9c39a] bg-[#f7f5e6] text-[#5c5620]',
]

const colorDe = (nombre) => {
  let hash = 0
  for (const caracter of String(nombre ?? '')) {
    hash = (hash * 31 + caracter.charCodeAt(0)) >>> 0
  }
  return PALETA[hash % PALETA.length]
}

const esReceso = (bloque) => String(bloque?.tipo ?? '').toUpperCase() === 'RECESO'

// Si el catálogo de bloques no incluye alguno que sí tenga clases, se agrega
// para no perder información.
const bloquesOrdenados = computed(() => {
  const base = [...props.bloques]
  const vistos = new Set(base.map((b) => b.id))
  for (const h of props.horarios) {
    if (vistos.has(h.idBloque)) continue
    base.push({
      id: h.idBloque,
      nombre: h.bloque,
      tipo: 'ACADEMICO',
      horaInicio: h.horaInicio,
      horaFin: h.horaFin,
      orden: h.bloqueOrden ?? 999,
    })
  }
  return base.sort((a, b) => (a.orden ?? 999) - (b.orden ?? 999))
})

const mapa = computed(() => {
  const indice = new Map()
  for (const h of props.horarios) indice.set(`${h.idBloque}-${h.diaSemana}`, h)
  return indice
})

const claseEn = (bloque, dia) => mapa.value.get(`${bloque.id}-${dia.v}`) ?? null
const rango = (bloque) =>
  bloque.horaInicio || bloque.horaFin
    ? `${String(bloque.horaInicio ?? '').slice(0, 5)}–${String(bloque.horaFin ?? '').slice(0, 5)}`
    : '—'
const nombreBloque = (bloque) =>
  bloque.nombre || (bloque.numero ? `Bloque ${bloque.numero}` : `Bloque ${bloque.orden}`)

const etiquetaSeccion = computed(() => {
  const s = props.seccion
  if (!s) return ''
  const grado = s.gradoNombre || (s.gradoNumero ? `${s.gradoNumero}° Año` : 'Grado')
  return `${grado} · Sección ${s.letra}`
})

const totalClases = computed(() => props.horarios.length)
const primerBloqueAcademico = computed(
  () => bloquesOrdenados.value.find((b) => !esReceso(b)) ?? null,
)

const crearEn = (bloque, dia) => {
  if (!props.puedeGestionar || !props.seccion || !bloque || esReceso(bloque)) return
  emit('crear', {
    idSeccion: props.seccion.id,
    idBloque: bloque.id,
    diaSemana: dia.v,
  })
}
</script>

<template>
  <section class="flex flex-col gap-3">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h3 class="text-base font-bold text-[#233E47]">Horario semanal</h3>
        <p v-if="seccion" class="text-sm text-[#4a5a63]">
          {{ etiquetaSeccion }} · Período {{ seccion.periodoLectivo }}
          <span aria-hidden="true">&nbsp;·&nbsp;</span>
          <span v-if="cargando" class="font-semibold text-[#5b6a72]">cargando…</span>
          <span v-else class="font-semibold text-[#233E47]">
            {{ totalClases }} {{ totalClases === 1 ? 'clase programada' : 'clases programadas' }}
          </span>
        </p>
        <p v-else class="text-sm text-[#4a5a63]">Selecciona una sección para ver su horario.</p>
      </div>
      <p v-if="puedeGestionar && seccion" class="text-xs font-semibold text-[#5b6a72]">
        Haz clic en una celda vacía para agregar una clase.
      </p>
    </header>

    <p v-if="errorBloques" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
      {{ errorBloques }}
      <button type="button" class="ml-2 font-bold underline" @click="emit('reintentar')">Reintentar</button>
    </p>

    <p v-else-if="error" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
      {{ error }}
      <button type="button" class="ml-2 font-bold underline" @click="emit('reintentar')">Reintentar</button>
    </p>

    <p v-else-if="errorSecciones" role="alert" class="rounded-xl bg-[#fbd5d2] px-4 py-3 text-sm font-semibold text-[#8a1c14]">
      {{ errorSecciones }}
      <button type="button" class="ml-2 font-bold underline" @click="emit('reintentar')">Reintentar</button>
    </p>

    <p v-else-if="!seccion && cargandoSecciones" :class="sinRes">Cargando secciones…</p>

    <div v-else-if="!seccion" class="flex flex-col items-center gap-2 rounded-xl border border-dashed border-[#91a5c9] bg-[#f6f9fe] px-4 py-14 text-center">
      <svg aria-hidden="true" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#91a5c9" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>
      <p class="text-lg font-bold text-[#233E47]">
        {{ haySecciones ? 'Selecciona una sección' : 'No hay secciones de Liceo' }}
      </p>
      <p class="max-w-md text-sm text-[#4a5a63]">
        {{ haySecciones
          ? 'Elige una sección en el selector para ver su horario semanal.'
          : 'Crea las secciones de Liceo del período para poder armar su horario.' }}
      </p>
      <button v-if="!haySecciones" type="button" class="mt-2 rounded-xl border border-[#233E47] bg-white px-5 py-2.5 text-sm font-bold text-[#233E47] transition hover:bg-[#eef3fb]" @click="emit('ir-secciones')">
        Ir a Secciones
      </button>
    </div>

    <p v-else-if="cargandoBloques || cargando" :class="sinRes">Cargando horario…</p>

    <div v-else-if="!bloquesOrdenados.length" class="flex flex-col items-center gap-2 rounded-xl border border-dashed border-[#91a5c9] bg-[#f6f9fe] px-4 py-14 text-center">
      <p class="text-lg font-bold text-[#233E47]">No hay bloques horarios configurados</p>
      <p class="max-w-md text-sm text-[#4a5a63]">El horario de Liceo se arma sobre los bloques de la jornada. Configúralos para poder programar clases.</p>
    </div>

    <div v-else class="overflow-x-auto rounded-xl border border-[#e3e8ee] bg-white">
      <table class="w-full min-w-[860px] border-separate border-spacing-0">
        <caption class="sr-only">Horario semanal de {{ etiquetaSeccion }}</caption>
        <thead>
          <tr>
            <th scope="col" class="sticky left-0 top-0 z-30 w-[150px] border-b border-[#d5dbe6] bg-[#eef2f6] px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-[#4a5a63]">
              Bloque / hora
            </th>
            <th v-for="d in dias" :key="d.v" scope="col" class="sticky top-0 z-20 border-b border-l border-[#d5dbe6] bg-[#eef2f6] px-3 py-2.5 text-center text-xs font-semibold uppercase tracking-wide text-[#4a5a63]">
              {{ d.l }}
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="b in bloquesOrdenados" :key="b.id">
            <!-- Receso: banda fina que cruza la semana -->
            <tr v-if="esReceso(b)" class="bg-[#f6f9fe]">
              <th scope="row" class="sticky left-0 z-10 border-b border-[#e3e8ee] bg-[#f6f9fe] px-3 py-1.5 text-left text-[11px] font-semibold uppercase tracking-wide text-[#5b6a72]">
                {{ rango(b) }}
              </th>
              <td :colspan="dias.length" class="border-b border-l border-[#e3e8ee] px-3 py-1.5 text-center text-[11px] font-semibold uppercase tracking-wide text-[#5b6a72]">
                {{ b.nombre || 'Receso' }} · {{ rango(b) }}
              </td>
            </tr>

            <!-- Bloque académico: una celda por día -->
            <tr v-else>
              <th scope="row" class="sticky left-0 z-10 border-b border-[#e3e8ee] bg-white px-3 py-2 text-left align-top">
                <span class="block text-[13px] font-bold text-[#233E47]">{{ nombreBloque(b) }}</span>
                <span class="block text-[11px] font-medium text-[#5b6a72]">{{ rango(b) }}</span>
              </th>
              <td v-for="d in dias" :key="d.v" class="border-b border-l border-[#e3e8ee] p-1 align-top">
                <template v-if="claseEn(b, d)">
                  <div class="group relative">
                    <button
                      v-if="puedeGestionar"
                      type="button"
                      :class="['flex min-h-[68px] w-full flex-col gap-0.5 rounded-lg border-l-4 px-2.5 py-2 text-left transition hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[#233E47]', colorDe(claseEn(b, d).asignatura)]"
                      :aria-label="`Editar ${claseEn(b, d).asignatura} del ${d.l}`"
                      @click="emit('editar', claseEn(b, d))"
                    >
                      <span class="line-clamp-2 text-[13px] font-bold leading-tight">{{ claseEn(b, d).asignatura }}</span>
                      <span class="line-clamp-2 text-[11px] font-medium leading-tight opacity-80">{{ claseEn(b, d).docente }}</span>
                    </button>
                    <div v-else :class="['flex min-h-[68px] w-full flex-col gap-0.5 rounded-lg border-l-4 px-2.5 py-2', colorDe(claseEn(b, d).asignatura)]">
                      <span class="line-clamp-2 text-[13px] font-bold leading-tight">{{ claseEn(b, d).asignatura }}</span>
                      <span class="line-clamp-2 text-[11px] font-medium leading-tight opacity-80">{{ claseEn(b, d).docente }}</span>
                    </div>
                    <button
                      v-if="puedeGestionar"
                      type="button"
                      class="absolute right-1 top-1 grid h-5 w-5 place-items-center rounded-full bg-white/85 text-[13px] font-bold leading-none text-[#8a1c14] opacity-100 transition hover:bg-white focus:opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
                      :aria-label="`Eliminar ${claseEn(b, d).asignatura} del ${d.l}`"
                      @click.stop="emit('eliminar', claseEn(b, d))"
                    >
                      ×
                    </button>
                  </div>
                </template>

                <button
                  v-else-if="puedeGestionar"
                  type="button"
                  class="grid min-h-[68px] w-full place-items-center rounded-lg border border-dashed border-[#c5cee0] text-lg leading-none text-[#91a5c9] transition hover:border-[#91a5c9] hover:bg-[#f6f9fe] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[#233E47]"
                  :aria-label="`Agregar clase el ${d.l} en ${nombreBloque(b)}`"
                  @click="crearEn(b, d)"
                >
                  +
                </button>

                <div v-else class="min-h-[68px] rounded-lg bg-[#fafbfd]"></div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <p v-if="seccion && !cargando && !cargandoBloques && !error && !errorBloques && bloquesOrdenados.length && !horarios.length" class="text-sm text-[#4a5a63]">
      Esta sección aún no tiene clases programadas.
      <button v-if="puedeGestionar && primerBloqueAcademico" type="button" class="font-semibold text-[#233E47] underline" @click="crearEn(primerBloqueAcademico, dias[0])">
        Agregar la primera
      </button>
    </p>

    <p v-else-if="seccion && !cargando && !cargandoBloques && !error && !errorBloques && bloquesOrdenados.length" class="text-xs text-[#5b6a72]">
      Las celdas vacías no tienen clase programada.
      <span v-if="puedeGestionar">Haz clic en una celda vacía para agregar una clase.</span>
    </p>
  </section>
</template>

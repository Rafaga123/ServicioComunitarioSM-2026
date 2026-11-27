<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { nomEst } from '@/components/gestion-academica/helpers'
import { etiquetaNivel } from '@/services/auth'
import { etiquetaCategoria, etiquetaGravedad } from '@/services/reportes'

const props = defineProps({
  reporte: { type: Object, required: true },
  estudiante: { type: Object, default: null },
  cargando: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const emit = defineEmits(['cerrar', 'editar', 'eliminar', 'descargar'])

const botonCerrar = ref(null)

const alPulsarTecla = (evento) => {
  if (evento.key === 'Escape') emit('cerrar')
}

onMounted(() => {
  document.addEventListener('keydown', alPulsarTecla)
  botonCerrar.value?.focus()
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', alPulsarTecla)
})

const fechaCompleta = computed(() => {
  const partes = String(props.reporte?.fecha ?? '').match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/,
  )
  if (!partes) return '—'

  const [, anio, mes, dia, hora, minuto] = partes.map(Number)
  return new Intl.DateTimeFormat('es', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(anio, mes - 1, dia, hora, minuto))
})

const nombreEstudiante = computed(
  () => (props.estudiante ? nomEst(props.estudiante) : props.reporte?.estudiante) || '—',
)

const cedulaEstudiante = computed(
  () => props.estudiante?.cedula || props.reporte?.cedula || '—',
)

const nivelEstudiante = computed(() =>
  etiquetaNivel(props.estudiante?.nivel || props.reporte?.nivel),
)

const gradoSeccion = computed(() => {
  if (!props.estudiante) return '—'
  const grado = props.estudiante.gradoNombre || ''
  const seccion = props.estudiante.seccionLetra || ''
  return `${grado} ${seccion}`.trim() || '—'
})

const tamanoAdjunto = computed(() => {
  const bytes = Number(props.reporte?.archivoTamano)
  if (!Number.isFinite(bytes) || bytes <= 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
})
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-[#0c1c22]/55 p-4 sm:p-6"
    @click.self="emit('cerrar')"
  >
    <section
      role="dialog"
      aria-modal="true"
      aria-labelledby="reporte-ficha-titulo"
      class="my-4 w-full max-w-3xl rounded-2xl bg-white shadow-2xl"
    >
      <header class="flex flex-wrap items-start justify-between gap-3 border-b border-[#e3e8ee] px-6 py-5">
        <div>
          <p class="m-0 text-[11px] font-bold uppercase tracking-[0.14em] text-[#5b6a72]">
            Ficha del reporte
          </p>
          <h2 id="reporte-ficha-titulo" class="mt-1 text-xl font-bold text-[#1b2a47]">
            Reporte N.º {{ reporte.id }}
          </h2>
          <div class="mt-2 flex flex-wrap items-center gap-2">
            <span class="rounded-full bg-[#eef1fa] px-2.5 py-0.5 text-xs font-bold text-[#253d9f]">
              {{ etiquetaCategoria(reporte.categoria) }}
            </span>
            <span
              class="rounded-full px-2.5 py-0.5 text-xs font-bold"
              :class="
                reporte.gravedad === 'GRAVE'
                  ? 'bg-[#faedc8] text-[#72520b]'
                  : 'bg-[#d9f1e2] text-[#285d3b]'
              "
            >
              {{ etiquetaGravedad(reporte.gravedad) }}
            </span>
            <span class="text-sm text-[#5b6a72]">{{ fechaCompleta }}</span>
          </div>
        </div>
        <button
          ref="botonCerrar"
          type="button"
          class="rounded-lg border border-[#c8cbd1] bg-white px-3 py-1.5 text-sm font-semibold text-[#414752] hover:bg-[#f4f5f7] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#3454c5]"
          @click="emit('cerrar')"
        >
          Cerrar
        </button>
      </header>

      <div class="max-h-[70vh] overflow-y-auto px-6 py-5">
        <p v-if="cargando" class="mb-4 rounded-xl bg-[#eef3fb] px-4 py-2 text-sm text-[#233E47]">
          Cargando ficha completa…
        </p>
        <p v-if="error" role="alert" class="mb-4 rounded-xl bg-[#fbd5d2] px-4 py-2 text-sm font-semibold text-[#8a1c14]">
          {{ error }}
        </p>

        <section aria-labelledby="ficha-estudiante">
          <h3 id="ficha-estudiante" class="text-sm font-bold uppercase tracking-wide text-[#34434b]">
            Estudiante
          </h3>
          <dl class="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt class="text-xs font-semibold text-[#777d87]">Nombre</dt>
              <dd class="mt-1 text-sm font-semibold text-[#1b2a2f]">{{ nombreEstudiante }}</dd>
            </div>
            <div>
              <dt class="text-xs font-semibold text-[#777d87]">Cédula</dt>
              <dd class="mt-1 text-sm text-[#1b2a2f]">{{ cedulaEstudiante }}</dd>
            </div>
            <div>
              <dt class="text-xs font-semibold text-[#777d87]">Nivel</dt>
              <dd class="mt-1 text-sm text-[#1b2a2f]">{{ nivelEstudiante }}</dd>
            </div>
            <div>
              <dt class="text-xs font-semibold text-[#777d87]">Grado y sección</dt>
              <dd class="mt-1 text-sm text-[#1b2a2f]">{{ gradoSeccion }}</dd>
            </div>
            <div>
              <dt class="text-xs font-semibold text-[#777d87]">Período lectivo</dt>
              <dd class="mt-1 text-sm text-[#1b2a2f]">{{ reporte.periodoLectivo || '—' }}</dd>
            </div>
          </dl>
        </section>

        <section class="mt-5 border-t border-[#e3e8ee] pt-5" aria-labelledby="ficha-clasificacion">
          <h3 id="ficha-clasificacion" class="text-sm font-bold uppercase tracking-wide text-[#34434b]">
            Clasificación del reporte
          </h3>
          <dl class="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt class="text-xs font-semibold text-[#777d87]">Reglamento</dt>
              <dd class="mt-1 text-sm font-semibold text-[#1b2a2f]">{{ reporte.reglamento || '—' }}</dd>
            </div>
            <div>
              <dt class="text-xs font-semibold text-[#777d87]">Artículo</dt>
              <dd class="mt-1 text-sm text-[#1b2a2f]">{{ reporte.articulo ?? '—' }}</dd>
            </div>
            <div>
              <dt class="text-xs font-semibold text-[#777d87]">Docente</dt>
              <dd class="mt-1 text-sm text-[#1b2a2f]">{{ reporte.docente || 'No aplica' }}</dd>
            </div>
            <div>
              <dt class="text-xs font-semibold text-[#777d87]">Registrado por</dt>
              <dd class="mt-1 text-sm text-[#1b2a2f]">{{ reporte.usuario || '—' }}</dd>
            </div>
          </dl>
        </section>

        <section class="mt-5 border-t border-[#e3e8ee] pt-5" aria-labelledby="ficha-descripcion">
          <h3 id="ficha-descripcion" class="text-sm font-bold uppercase tracking-wide text-[#34434b]">
            Descripción
          </h3>
          <div class="mt-3 grid gap-4">
            <div>
              <p class="m-0 text-xs font-semibold text-[#777d87]">Incidencia</p>
              <p class="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-[#1b2a2f]">
                {{ reporte.incidencia || '—' }}
              </p>
            </div>
            <div>
              <p class="m-0 text-xs font-semibold text-[#777d87]">Derecho a la defensa</p>
              <p class="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-[#1b2a2f]">
                {{ reporte.defensa || '—' }}
              </p>
            </div>
          </div>
        </section>

        <section class="mt-5 border-t border-[#e3e8ee] pt-5" aria-labelledby="ficha-adjunto">
          <h3 id="ficha-adjunto" class="text-sm font-bold uppercase tracking-wide text-[#34434b]">
            Adjunto
          </h3>
          <div
            v-if="reporte.archivoNombre"
            class="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#c8cbd1] bg-[#f8f9fb] px-4 py-3"
          >
            <div class="min-w-0">
              <p class="m-0 truncate text-sm font-semibold text-[#1b2a2f]">
                {{ reporte.archivoNombre }}
              </p>
              <p class="m-0 text-xs text-[#777d87]">
                {{ reporte.archivoMime || 'Archivo' }}
                <span v-if="tamanoAdjunto"> · {{ tamanoAdjunto }}</span>
              </p>
            </div>
            <button
              type="button"
              class="rounded-lg border border-[#304bbc] bg-white px-3 py-1.5 text-xs font-bold text-[#304bbc] hover:bg-[#eef1fa]"
              @click="emit('descargar', reporte)"
            >
              Descargar
            </button>
          </div>
          <p v-else class="mt-3 text-sm text-[#777d87]">Este reporte no tiene archivo adjunto.</p>
        </section>
      </div>

      <footer class="flex flex-wrap justify-end gap-2 border-t border-[#e3e8ee] px-6 py-4">
        <button
          type="button"
          class="min-h-10 rounded-lg border border-[#c8cbd1] bg-white px-4 text-sm font-semibold text-[#7b818b]"
          disabled
          title="El backend publicará próximamente un generador PDF de reportes, como el de gestión académica."
        >
          Exportar PDF
        </button>
        <button
          type="button"
          class="min-h-10 rounded-lg border border-[#c8cbd1] bg-white px-4 text-sm font-semibold text-[#414752] hover:bg-[#f4f5f7]"
          @click="emit('cerrar')"
        >
          Cerrar
        </button>
        <button
          type="button"
          class="min-h-10 rounded-lg border border-[#b23b32] bg-white px-4 text-sm font-semibold text-[#8a1c14] hover:bg-[#fff4f2]"
          @click="emit('eliminar', reporte.id)"
        >
          Eliminar
        </button>
        <button
          type="button"
          class="min-h-10 rounded-lg border border-[#304bbc] bg-[#304bbc] px-4 text-sm font-bold text-white hover:bg-[#253d9f]"
          @click="emit('editar', reporte.id)"
        >
          Editar reporte
        </button>
      </footer>
    </section>
  </div>
</template>

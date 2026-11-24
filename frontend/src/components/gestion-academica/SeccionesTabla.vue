<script setup>
import { computed } from 'vue'
import { etiquetaNivel } from '@/services/auth'
import { LETRAS_POR_FORMATO, etiquetaFormato, formatoSecciones } from '@/services/secciones'
import { th, td, btnMini, tag, nada, sinRes } from './estilos'

const props = defineProps({
  // Secciones visibles (pueden estar filtradas por búsqueda).
  filas: { type: Array, required: true },
  // Catálogo completo del período: de aquí se deduce el formato para que una
  // búsqueda no haga creer que falta una de las dos secciones.
  catalogo: { type: Array, default: () => [] },
  grados: { type: Array, default: () => [] },
  periodo: { type: [String, Number], default: '' },
  buscando: { type: Boolean, default: false },
  cargando: { type: Boolean, default: false },
  filtrando: { type: Boolean, default: false },
  // Solo el administrador puede crear, editar y eliminar secciones.
  puedeGestionar: { type: Boolean, default: false },
})

const emit = defineEmits(['editar', 'eliminar', 'crear', 'ver-horario', 'reiniciar'])

const ordenNivel = (nivel) => (nivel === 'ESCUELA' ? 0 : nivel === 'LICEO' ? 1 : 2)

// Agrupa por nivel -> grado, y clasifica cada grado en su formato del período.
const grupos = computed(() => {
  const porNivel = new Map()
  const porGradoId = new Map()

  const nuevaEntrada = (idGrado, gradoNumero, gradoNombre) => ({
    idGrado,
    gradoNumero,
    gradoNombre: gradoNombre || 'Grado',
    formato: formatoSecciones(props.catalogo, idGrado, props.periodo),
    porLetra: {},
  })

  for (const grado of props.grados) {
    const nivel = grado.nivel || 'OTRO'
    if (!porNivel.has(nivel)) porNivel.set(nivel, new Map())

    const entrada = nuevaEntrada(grado.id, grado.numero, grado.nombre)
    porNivel.get(nivel).set(grado.id, entrada)
    porGradoId.set(grado.id, { nivel, entrada })
  }

  // Secciones cuyo grado no esté en el catálogo (poco habitual) también se
  // muestran para no perder información.
  for (const seccion of props.filas) {
    let destino = porGradoId.get(seccion.idGrado)
    if (!destino) {
      const nivel = seccion.nivel || 'OTRO'
      if (!porNivel.has(nivel)) porNivel.set(nivel, new Map())
      const entrada = nuevaEntrada(
        seccion.idGrado,
        seccion.gradoNumero,
        seccion.gradoNombre,
      )
      porNivel.get(nivel).set(seccion.idGrado, entrada)
      destino = { nivel, entrada }
      porGradoId.set(seccion.idGrado, destino)
    }
    destino.entrada.porLetra[seccion.letra] = seccion
  }

  return [...porNivel.entries()]
    .map(([nivel, grados]) => ({
      nivel,
      grados: [...grados.values()].sort(
        (a, b) =>
          (a.gradoNumero ?? 0) - (b.gradoNumero ?? 0) ||
          a.gradoNombre.localeCompare(b.gradoNombre),
      ),
    }))
    .sort((a, b) => ordenNivel(a.nivel) - ordenNivel(b.nivel))
})

const letrasDe = (grado) =>
  LETRAS_POR_FORMATO[grado.formato] ?? Object.keys(grado.porLetra).sort()
const seccionDe = (grado, letra) => grado.porLetra[letra] ?? null
const existentes = (grado) => Object.values(grado.porLetra)

const crear = (grado, formato) =>
  emit('crear', {
    idGrado: grado.idGrado,
    formato,
    periodoLectivo: props.periodo,
  })
</script>

<template>
  <p v-if="buscando && cargando" :class="sinRes">Buscando en todas las secciones…</p>
  <p v-else-if="buscando" :class="sinRes">No se pudo cargar la lista completa para filtrar.</p>
  <p v-else-if="filtrando && !filas.length" :class="sinRes">Ninguna sección coincide con el filtro.</p>

  <div v-else class="flex flex-col gap-6">
    <section v-for="grupo in grupos" :key="grupo.nivel" class="overflow-hidden rounded-xl border border-[#e3e8ee]">
      <header class="flex items-center gap-2 bg-[#eef2f6] px-3 py-2.5">
        <h3 class="text-sm font-bold text-[#233E47]">Nivel {{ etiquetaNivel(grupo.nivel) || grupo.nivel }}</h3>
        <span :class="tag">{{ grupo.grados.length }} {{ grupo.grados.length === 1 ? 'grado' : 'grados' }}</span>
      </header>

      <div class="overflow-x-auto">
        <table class="w-full border-collapse">
          <thead>
            <tr>
              <th :class="[th, 'w-48']">Grado / año</th>
              <th :class="th">Sección</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="grado in grupo.grados" :key="grado.idGrado ?? grado.gradoNombre">
              <td :class="[td, 'font-semibold text-[#233E47]']">
                {{ grado.gradoNombre }}
                <span v-if="grado.formato !== 'sin-crear'" class="mt-1 block text-xs font-normal text-[#5b6a72]">
                  {{ etiquetaFormato(grado.formato) }}
                </span>
              </td>

              <td :class="[td, 'align-top']">
                <!-- Sin secciones: dos únicas formas válidas de empezar -->
                <div v-if="grado.formato === 'sin-crear'" class="grid gap-2 sm:grid-cols-2">
                  <button
                    v-if="puedeGestionar"
                    type="button"
                    class="grid min-h-[96px] place-items-center rounded-xl border border-dashed border-[#91a5c9] bg-[#f6f9fe] px-3 text-center text-sm font-semibold text-[#4a5a63] transition hover:border-[#233E47] hover:bg-[#eef3fb] hover:text-[#233E47]"
                    @click="crear(grado, 'unica')"
                  >
                    + Crear sección única (U)
                  </button>
                  <button
                    v-if="puedeGestionar"
                    type="button"
                    class="grid min-h-[96px] place-items-center rounded-xl border border-dashed border-[#91a5c9] bg-[#f6f9fe] px-3 text-center text-sm font-semibold text-[#4a5a63] transition hover:border-[#233E47] hover:bg-[#eef3fb] hover:text-[#233E47]"
                    @click="crear(grado, 'dividida')"
                  >
                    + Crear secciones A y B
                  </button>
                  <p v-if="!puedeGestionar" :class="nada">Sin secciones registradas.</p>
                </div>

                <!-- Datos previos o baja parcial: se avisa y se ofrece limpiar -->
                <template v-else-if="grado.formato === 'inconsistente'">
                  <div class="mb-2 flex flex-wrap items-center gap-2 rounded-lg bg-[#fdebc0] px-3 py-2 text-sm text-[#6b4200]">
                    <span><b>Secciones inconsistentes:</b> {{ Object.keys(grado.porLetra).sort().join(', ') }}. Debe haber solo U, o A y B juntas.</span>
                    <button v-if="puedeGestionar" type="button" :class="[btnMini, '!text-[#8a1c14]']" @click="emit('reiniciar', existentes(grado))">
                      Dar de baja y recrear
                    </button>
                  </div>
                  <div class="grid gap-2 sm:grid-cols-2">
                    <div
                      v-for="letra in letrasDe(grado)"
                      :key="letra"
                      class="flex min-h-[96px] flex-col justify-between gap-2 rounded-xl border border-[#d5dbe6] bg-white p-3"
                    >
                      <p class="font-bold text-[#233E47]">Sección {{ letra }}</p>
                      <p v-if="seccionDe(grado, letra)" :class="nada">Período {{ seccionDe(grado, letra).periodoLectivo }}</p>
                      <p v-else :class="nada">Falta esta sección</p>
                    </div>
                  </div>
                </template>

                <!-- Formato válido: una tarjeta para U, dos para A y B -->
                <div v-else class="grid gap-2" :class="grado.formato === 'dividida' ? 'sm:grid-cols-2' : ''">
                  <div
                    v-for="letra in letrasDe(grado)"
                    :key="letra"
                    class="flex min-h-[104px] flex-col justify-between gap-3 rounded-xl border border-[#d5dbe6] bg-white p-3"
                  >
                    <div class="space-y-1 text-sm">
                      <p class="font-bold text-[#233E47]">Sección {{ letra }}</p>
                      <p>Período {{ seccionDe(grado, letra)?.periodoLectivo ?? props.periodo }}</p>
                      <p v-if="seccionDe(grado, letra)?.docenteTitular" :class="nada">
                        Titular: {{ seccionDe(grado, letra).docenteTitular }}
                      </p>
                      <p v-else-if="grupo.nivel === 'ESCUELA'" :class="nada">Sin titular</p>
                      <p v-else :class="nada">Horario por bloques</p>
                    </div>

                    <div class="flex flex-wrap items-center gap-1">
                      <button v-if="puedeGestionar" type="button" :class="btnMini" @click="emit('editar', seccionDe(grado, letra))">
                        Editar
                      </button>
                      <button v-if="puedeGestionar" type="button" :class="[btnMini, '!text-[#8a1c14]']" @click="emit('eliminar', seccionDe(grado, letra))">
                        Eliminar
                      </button>
                      <button
                        v-if="grupo.nivel === 'LICEO'"
                        type="button"
                        :class="[btnMini, '!text-[#1c5d86]']"
                        @click="emit('ver-horario', seccionDe(grado, letra))"
                      >
                        Ver horario →
                      </button>
                      <span v-else-if="grupo.nivel === 'ESCUELA'" :class="nada">Horario corrido</span>
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

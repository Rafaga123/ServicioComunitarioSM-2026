<script setup>
import { reactive, ref } from 'vue'

const emit = defineEmits(['cancel', 'save-draft', 'submit'])

const fechaActual = new Date()
fechaActual.setMinutes(fechaActual.getMinutes() - fechaActual.getTimezoneOffset())

const formulario = reactive({
  curso: '',
  estudiante: '',
  fechaHora: fechaActual.toISOString().slice(0, 10),
  hora: '',
  docente: '',
  asignatura: '',
  tipoIncidente: '',
  tipoFalta: '',
  gravedad: '',
  descripcion: '',
  Defensa: '',
  Leyes: '',
  Articulo: '',
  archivos: [],
})

const entradaArchivos = ref(null)
const arrastrando = ref(false)

// Clases compartidas por los campos del formulario
const claseCampo =
  'w-full rounded-md border border-[#aeb2b8] bg-white px-2.5 py-2 text-sm text-[#242a35] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[#3454c5]'
const claseCampoCorto = `${claseCampo} min-h-10`

// Píldoras de gravedad: rellenas cuando están inactivas y con borde de color al seleccionarse
function claseSeveridad(valor) {
  if (formulario.gravedad === valor) {
    return valor === 'grave'
      ? 'border-current bg-white hover:bg-[#faedc8]'
      : 'border-current bg-white hover:bg-[#d9f1e2]'
  }

  return valor === 'grave'
    ? 'border-transparent bg-[#faedc8]'
    : 'border-transparent bg-[#d9f1e2]'
}

function agregarArchivos(archivos) {
  const permitidos = Array.from(archivos).filter((archivo) => {
    return archivo.type === 'application/pdf' || archivo.type.startsWith('image/')
  })

  formulario.archivos = [...formulario.archivos, ...permitidos]
}

function quitarArchivo(indice) {
  formulario.archivos.splice(indice, 1)
}

function enviarFormulario(accion) {
  const datos = {
    ...formulario,
    archivos: [...formulario.archivos],
  }

  if (accion === 'save-draft') {
    emit('save-draft', datos)
    return
  }

  emit('submit', datos)
}
</script>

<template>
  <form
    class="relative mx-auto grid w-full max-w-[1000px] gap-3.5 p-4 text-[#242a35] max-[520px]:p-2.5"
    @submit.prevent="enviarFormulario('submit')"
  >
    <section class="rounded-[9px] border border-[#c8cbd1] bg-white px-4 pt-3.5 pb-4 shadow-sm">
      <h2 class="m-0 mb-2.5 text-[17px] font-bold">1 · Datos del estudiante</h2>

      <div class="grid grid-cols-1 gap-x-3.5 gap-y-3 min-[521px]:grid-cols-2">
        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Curso</span>
          <input v-model="formulario.curso" type="text" name="curso" :class="claseCampoCorto" />
        </label>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Estudiante (con búsqueda)</span>
          <input
            v-model="formulario.estudiante"
            type="search"
            name="estudiante"
            list="estudiantes-disponibles"
            autocomplete="off"
            :class="claseCampoCorto"
          />
          <datalist id="estudiantes-disponibles">
            <option value="Brandon" />
            <option value="Kevin Valera" />
            <option value="Hermes Morado" />
          </datalist>
        </label>
      </div>

      <div class="mt-[11px] flex items-center gap-3" aria-live="polite">
        <div
          class="grid h-[46px] w-[46px] shrink-0 place-items-center rounded-full bg-[#e0e4ec] text-lg font-bold text-[#46516a]"
          aria-hidden="true"
        >
          {{ formulario.estudiante ? formulario.estudiante.charAt(0).toUpperCase() : '' }}
        </div>
        <div>
          <p class="m-0 text-xs">
            {{ formulario.estudiante || 'Tarjeta del estudiante' }}
          </p>
          <p class="m-0 text-xs text-[#777d87]">Aviso: tiene 2 reportes este año</p>
        </div>
      </div>
    </section>

    <section class="rounded-[9px] border border-[#c8cbd1] bg-white px-4 pt-3.5 pb-4 shadow-sm">
      <h2 class="m-0 mb-2.5 text-[17px] font-bold">2 · Datos del incidente</h2>

      <div
        class="grid grid-cols-1 gap-x-3.5 gap-y-3 min-[521px]:grid-cols-2 min-[761px]:grid-cols-4"
      >
        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Fecha</span>
          <input v-model="formulario.fechaHora" type="date" name="fechaHora" :class="claseCampoCorto" />
        </label>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Hora</span>
          <input v-model="formulario.hora" type="time" name="hora" :class="claseCampoCorto" />
        </label>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Docente</span>
          <input
            v-model="formulario.docente"
            type="search"
            name="docente"
            list="docentes-disponibles"
            autocomplete="off"
            :class="claseCampoCorto"
          />
          <datalist id="docentes-disponibles">
            <option value="Prof. Vásquez" />
          </datalist>
        </label>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Asignatura</span>
          <!--<input v-model="formulario.asignatura" type="text" name="asignatura" />-->
          <select v-model="formulario.asignatura" name="asignatura" :class="claseCampoCorto">
            <option value="" disabled>Seleccionar</option>
            <option value="Matemáticas">Matemáticas</option>
            <option value="Ingles">Inglés y otras lenguas</option>
            <option value="Historia">Geografia,Historia</option>
            <option value="participación en grupos">Participación en grupos</option>
            <option value="Ciencias Natu">Ciencias Naturales</option>
            <option value="castellano">Castellano</option>
            <option value="OYC">Orientación y convivencia</option>
            <option value="AYP">Arte y patrimonio</option>
            <option value="Edu fisica">Educación física</option>
            <option value="Quimica">Química</option>
            <option value="Biologia">Biología</option>
            <option value="Fisica">Física</option>
            <option value="FSN">Formación para la soberanía</option>
            <option value="CT">Ciencias de la tierra</option>
          </select>
        </label>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Tipo (académico / conductual)</span>
          <select v-model="formulario.tipoIncidente" name="tipoIncidente" :class="claseCampoCorto">
            <option value="" disabled>Seleccionar</option>
            <option value="academico">Académico</option>
            <option value="conductual">Conductual</option>
          </select>
        </label>

        <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
          <span>Tipo de falta</span>
          <input v-model="formulario.tipoFalta" type="text" name="tipoFalta" :class="claseCampoCorto" />
        </label>
      </div>

      <fieldset class="mt-2.5 flex flex-nowrap gap-3 border-0 p-0">
        <legend class="sr-only">Gravedad del incidente</legend>
        <label
          v-for="nivel in [
            { valor: 'leve', texto: 'Leve' },
            { valor: 'grave', texto: 'Grave' },
          ]"
          :key="nivel.valor"
          :class="[
            'inline-flex cursor-pointer items-center gap-2 rounded-full border-2 px-2.5 py-1 text-xs leading-none',
            nivel.valor === 'grave' ? 'text-[#72520b]' : 'text-[#285d3b]',
            claseSeveridad(nivel.valor),
          ]"
        >
          <input
            v-model="formulario.gravedad"
            class="absolute h-px w-px opacity-0"
            type="radio"
            name="gravedad"
            :value="nivel.valor"
          />
          <span>{{ nivel.texto }}</span>
        </label>
      </fieldset>
    </section>

    <section class="rounded-[9px] border border-[#c8cbd1] bg-white px-4 pt-3.5 pb-4 shadow-sm">
      <h2 class="m-0 mb-2.5 text-[17px] font-bold">3 · Descripción y acciones</h2>

      <label class="grid min-w-0 gap-1 text-xs text-[#414752]">
        <span>Descripción</span>
        <textarea
          v-model="formulario.descripcion"
          :class="[claseCampo, 'min-h-[100px] resize-y']"
          name="descripcion"
          rows="4"
          required
        ></textarea>
      </label>

      <label class="mt-2.5 grid min-w-0 gap-1 text-xs text-[#414752]">
        <span>Artículo</span>
        <input v-model="formulario.Articulo" type="text" name="Articulo" :class="claseCampoCorto" />
      </label>

      <fieldset class="mt-3 flex flex-wrap gap-2 border-0 p-0">
        <legend class="mb-2 text-xs font-bold text-[#414752]">Marco legal</legend>
        <label
          v-for="ley in ['LOPNNA', 'LOE', 'CBV', 'NC']"
          :key="ley"
          :class="[
            'inline-flex min-h-[38px] cursor-pointer items-center gap-2 rounded-lg border bg-white px-3 text-[13px] transition focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-[#3454c5]',
            formulario.Leyes === ley
              ? 'border-[#304bbc] bg-[#eef1fa] font-bold text-[#253d9f] shadow-[0_0_0_1px_#304bbc] hover:bg-[#eef1fa]'
              : 'border-[#c8cbd1] text-[#414752] hover:border-[#7d8ac2] hover:bg-[#f7f8fc]',
          ]"
        >
          <input
            v-model="formulario.Leyes"
            class="m-0 h-[18px] w-[18px] accent-[#304bbc]"
            type="radio"
            name="Leyes"
            :value="ley"
          />
          <span>{{ ley }}</span>
        </label>
      </fieldset>

      <label class="mt-2.5 grid min-w-0 gap-1 text-xs text-[#414752]">
        <span>Art.88, LOPNNA: Derecho a la Defensa</span>
        <input v-model="formulario.Defensa" type="text" name="Defensa" :class="claseCampoCorto" />
      </label>

      <div
        :class="[
          'mt-2.5 grid min-h-14 cursor-pointer place-items-center rounded-md p-2 text-center text-[13px] text-[#414752] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[#3454c5]',
          arrastrando
            ? 'bg-[#eef1fa] outline outline-2 outline-dashed outline-[#3454c5]'
            : 'bg-[#e0e4ec]',
        ]"
        @dragover.prevent="arrastrando = true"
        @dragleave.prevent="arrastrando = false"
        @drop.prevent="
          arrastrando = false;
          agregarArchivos($event.dataTransfer.files)
        "
        @click="entradaArchivos?.click()"
        @keydown.enter.prevent="entradaArchivos?.click()"
        @keydown.space.prevent="entradaArchivos?.click()"
        role="button"
        tabindex="0"
        aria-label="Adjuntar imágenes o archivos PDF"
      >
        <input
          ref="entradaArchivos"
          class="sr-only"
          type="file"
          accept="image/*,.pdf,application/pdf"
          multiple
          @change="agregarArchivos($event.target.files); $event.target.value = ''"
        />
        <span>Arrastra imágenes o PDF (opcional) o haz clic para seleccionarlos</span>
      </div>

      <ul v-if="formulario.archivos.length" class="mt-2.5 grid list-none gap-1.5 p-0">
        <li
          v-for="(archivo, indice) in formulario.archivos"
          :key="`${archivo.name}-${indice}`"
          class="flex justify-between gap-3 text-xs [overflow-wrap:anywhere]"
        >
          <span>{{ archivo.name }}</span>
          <button
            type="button"
            class="shrink-0 cursor-pointer border-0 bg-transparent text-[#3454c5] underline"
            @click="quitarArchivo(indice)"
          >
            Quitar
          </button>
        </li>
      </ul>
    </section>

    <div class="flex flex-wrap justify-end gap-2.5 pt-px max-[520px]:grid max-[520px]:grid-cols-1">
      <button
        type="button"
        class="min-h-[42px] cursor-pointer rounded-md border border-[#777d87] bg-white px-4 text-[13px] font-bold text-[#242a35] hover:bg-[#f4f5f7]"
        @click="emit('cancel')"
      >
        Cancelar
      </button>
      <button
        type="button"
        class="min-h-[42px] cursor-pointer rounded-md border border-[#777d87] bg-white px-4 text-[13px] font-bold text-[#242a35] hover:bg-[#f4f5f7]"
        @click="enviarFormulario('save-draft')"
      >
        Guardar borrador
      </button>
      <button
        type="submit"
        class="min-h-[42px] cursor-pointer rounded-md border border-[#304bbc] bg-[#304bbc] px-4 text-[13px] font-bold text-white hover:bg-[#253d9f]"
      >
        Enviar a control de estudios
      </button>
    </div>
  </form>
</template>

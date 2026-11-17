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
  <form class="incident-form" @submit.prevent="enviarFormulario('submit')">
    <section class="form-section">
      <h2>1 · Datos del estudiante</h2>

      <div class="student-fields">
        <label class="field">
          <span>Curso</span>
          <input v-model="formulario.curso" type="text" name="curso" />
        </label>

        <label class="field">
          <span>Estudiante (con búsqueda)</span>
          <input
            v-model="formulario.estudiante"
            type="search"
            name="estudiante"
            list="estudiantes-disponibles"
            autocomplete="off"
          />
          <datalist id="estudiantes-disponibles">
            <option value="Brandon" />
            <option value="Kevin Valera" />
            <option value="Hermes Morado" />
          </datalist>
        </label>
      </div>

      <div class="student-card" aria-live="polite">
        <div class="student-avatar" aria-hidden="true">
          {{ formulario.estudiante ? formulario.estudiante.charAt(0).toUpperCase() : '' }}
        </div>
        <div>
          <p class="student-card-title">
            {{ formulario.estudiante || 'Tarjeta del estudiante' }}
          </p>
          <p class="student-card-notice">Aviso: tiene 2 reportes este año</p>
        </div>
      </div>
    </section>

    <section class="form-section">
      <h2>2 · Datos del incidente</h2>

      <div class="incident-fields">
        <label class="field">
          <span>Fecha</span>
          <input v-model="formulario.fechaHora" type="date" name="fechaHora" />
        </label>

        <label class="field">
          <span>Hora</span>
          <input v-model="formulario.hora" type="time" name="hora" />
        </label>

        <label class="field">
          <span>Docente</span>
          <input
            v-model="formulario.docente"
            type="search"
            name="docente"
            list="docentes-disponibles"
            autocomplete="off"
          />
          <datalist id="docentes-disponibles">
            <option value="Prof. Vásquez" />
          </datalist>
        </label>

        <label class="field">
          <span>Asignatura</span>
          <!--<input v-model="formulario.asignatura" type="text" name="asignatura" />-->
          <select v-model="formulario.asignatura" name="asignatura">
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

        <label class="field">
          <span>Tipo (académico / conductual)</span>
          <select v-model="formulario.tipoIncidente" name="tipoIncidente">
            <option value="" disabled>Seleccionar</option>
            <option value="academico">Académico</option>
            <option value="conductual">Conductual</option>
          </select>
        </label>

        <label class="field">
          <span>Tipo de falta</span>
          <input v-model="formulario.tipoFalta" type="text" name="tipoFalta" />
        </label>
      </div>

      <fieldset class="radio-picker severity-picker">
        <legend class="sr-only">Gravedad del incidente</legend>
        <label
          v-for="nivel in [
            { valor: 'leve', texto: 'Leve' },
            { valor: 'grave', texto: 'Grave' },
          ]"
          :key="nivel.valor"
          class="radio-option severity-option"
          :class="[`severity-${nivel.valor}`, { selected: formulario.gravedad === nivel.valor }]"
        >
          <input v-model="formulario.gravedad" type="radio" name="gravedad" :value="nivel.valor" />
          <span>{{ nivel.texto }}</span>
        </label>
      </fieldset>
    </section>

    <section class="form-section">
      <h2>3 · Descripción y acciones</h2>

      <label class="field">
        <span>Descripción</span>
        <textarea
          v-model="formulario.descripcion"
          name="descripcion"
          rows="4"
          required
        ></textarea>
      </label>

      <label class="field">
        <span>Artículo</span>
        <input v-model="formulario.Articulo" type="text" name="Articulo" />
      </label>

      <fieldset class="radio-picker law-picker">
        <legend>Marco legal</legend>
        <label
          v-for="ley in ['LOPNNA', 'LOE', 'CBV', 'NC']"
          :key="ley"
          class="radio-option"
          :class="{ selected: formulario.Leyes === ley }"
        >
          <input v-model="formulario.Leyes" type="radio" name="Leyes" :value="ley" />
          <span>{{ ley }}</span>
        </label>
      </fieldset>

      <label class="field actions-field">
        <span>Art.88, LOPNNA: Derecho a la Defensa</span>
        <input v-model="formulario.Defensa" type="text" name="Defensa" />
      </label>

      <div
        class="file-drop"
        :class="{ 'is-dragging': arrastrando }"
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
          class="file-input"
          type="file"
          accept="image/*,.pdf,application/pdf"
          multiple
          @change="agregarArchivos($event.target.files); $event.target.value = ''"
        />
        <span>Arrastra imágenes o PDF (opcional) o haz clic para seleccionarlos</span>
      </div>

      <ul v-if="formulario.archivos.length" class="file-list">
        <li v-for="(archivo, indice) in formulario.archivos" :key="`${archivo.name}-${indice}`">
          <span>{{ archivo.name }}</span>
          <button type="button" class="remove-file" @click="quitarArchivo(indice)">
            Quitar
          </button>
        </li>
      </ul>
    </section>

    <div class="form-actions">
      <button type="button" class="button button-secondary" @click="emit('cancel')">
        Cancelar
      </button>
      <button type="button" class="button button-secondary" @click="enviarFormulario('save-draft')">
        Guardar borrador
      </button>
      <button type="submit" class="button button-primary">Enviar a control de estudios</button>
    </div>
  </form>
</template>

<style scoped>
@import './css/reportesincidencia.css';

</style>

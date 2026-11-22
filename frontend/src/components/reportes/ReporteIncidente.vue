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
.incident-form {
  display: grid;
  gap: 14px;
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 16px;
  color: #242a35;
  font-family: Arial, sans-serif;
}

.form-section {
  padding: 14px 16px 16px;
  border: 1px solid #c8cbd1;
  border-radius: 9px;
  background: #fff;
  box-shadow: 0 1px 2px rgb(15 23 42 / 5%);
}

.form-section h2 {
  margin: 0 0 10px;
  font-size: 17px;
  font-weight: 700;
}

.student-fields,
.incident-fields {
  display: grid;
  gap: 12px 14px;
}

.student-fields {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.incident-fields {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.field {
  display: grid;
  min-width: 0;
  gap: 4px;
  color: #414752;
  font-size: 12px;
}

.field input,
.field select,
.field textarea {
  box-sizing: border-box;
  width: 100%;
  min-height: 40px;
  padding: 8px 10px;
  border: 1px solid #aeb2b8;
  border-radius: 6px;
  background: #fff;
  color: #242a35;
  font: inherit;
  font-size: 14px;
}

.field textarea {
  min-height: 100px;
  resize: vertical;
}

.field input:focus,
.field select:focus,
.field textarea:focus,
.file-drop:focus-visible {
  outline: 2px solid #3454c5;
  outline-offset: 1px;
}

.student-card {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 11px;
}

.student-avatar {
  display: grid;
  width: 46px;
  height: 46px;
  flex: 0 0 46px;
  place-items: center;
  border-radius: 50%;
  background: #e0e4ec;
  color: #46516a;
  font-size: 18px;
  font-weight: 700;
}

.student-card-title,
.student-card-notice {
  margin: 0;
  font-size: 12px;
}

.student-card-notice {
  color: #777d87;
}

.radio-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 14px 0 0;
  padding: 0;
  border: 0;
}

.radio-picker legend {
  margin-bottom: 8px;
  color: #414752;
  font-size: 12px;
  font-weight: 700;
}

.radio-option {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid #c8cbd1;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  color: #414752;
  font-size: 13px;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    box-shadow 0.15s ease;
}

.radio-option input[type='radio'] {
  width: 18px;
  height: 18px;
  margin: 0;
  accent-color: #304bbc;
}

.radio-option:hover {
  border-color: #7d8ac2;
  background: #f7f8fc;
}

.radio-option:focus-within {
  outline: 2px solid #3454c5;
  outline-offset: 2px;
}

.radio-option.selected {
  border-color: #304bbc;
  background: #eef1fa;
  box-shadow: 0 0 0 1px #304bbc;
  color: #253d9f;
  font-weight: 700;
}

.severity-leve {
  background: #d9f1e2;
  color: #285d3b;
}

.severity-grave {
  background: #faedc8;
  color: #72520b;
}

.severity-picker {
  flex-wrap: nowrap;
  gap: 12px;
  margin-top: 10px;
}

.severity-option {
  min-height: 0;
  padding: 4px 10px;
  border: 2px solid transparent;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1;
  transition: none;
}

.severity-option input[type='radio'] {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.severity-option.selected {
  border-color: currentColor;
  background: inherit;
  box-shadow: none;
  font-weight: 400;
}

.severity-option:hover {
  border-color: transparent;
  background: #d9f1e2;
}

.severity-option.severity-grave:hover {
  background: #faedc8;
}

.severity-option.selected:hover {
  border-color: currentColor;
}

.law-picker {
  margin-top: 12px;
}

.actions-field {
  margin-top: 10px;
}

.file-drop {
  display: grid;
  min-height: 56px;
  margin-top: 10px;
  padding: 8px;
  place-items: center;
  border-radius: 6px;
  background: #e0e4ec;
  color: #414752;
  cursor: pointer;
  text-align: center;
  font-size: 13px;
}

.file-drop.is-dragging {
  outline: 2px dashed #3454c5;
  background: #eef1fa;
}

.file-input,
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  clip-path: inset(50%);
}

.file-list {
  display: grid;
  gap: 6px;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
}

.file-list li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  overflow-wrap: anywhere;
  font-size: 12px;
}

.remove-file {
  flex: 0 0 auto;
  border: 0;
  background: none;
  color: #3454c5;
  cursor: pointer;
  font: inherit;
  text-decoration: underline;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
  padding-top: 1px;
}

.button {
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid #777d87;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
}

.button-secondary {
  background: #fff;
  color: #242a35;
}

.button-secondary:hover {
  background: #f4f5f7;
}

.button-primary {
  border-color: #304bbc;
  background: #304bbc;
  color: #fff;
}

.button-primary:hover {
  background: #253d9f;
}

@media (max-width: 760px) {
  .incident-fields {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .incident-form {
    padding: 10px;
  }

  .student-fields,
  .incident-fields {
    grid-template-columns: 1fr;
  }

  .form-actions {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>

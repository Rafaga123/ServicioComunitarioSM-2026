import { reactive, ref } from 'vue'

const emit = defineEmits(['cancel', 'save-draft', 'submit'])

const fechaActual = new Date()
fechaActual.setMinutes(fechaActual.getMinutes() - fechaActual.getTimezoneOffset())

const formulario = reactive({
  curso: '',
  estudiante: '',
  fechaHora: fechaActual.toISOString().slice(0, 10),
  asignatura: '',
  tipoIncidente: '',
  tipoFalta: '',
  gravedad: '',
  descripcion: '',
  acciones: '',
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
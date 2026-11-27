// Validación local compartida por los adjuntos de pases y reportes.
// El backend vuelve a validar la extensión y la firma binaria del contenido
// (backend/app/utils/storage.py), así que esto solo evita enviar archivos que
// ya se sabe que serán rechazados.

const MIME_POR_EXTENSION = {
  jpg: ['image/jpeg', 'image/jpg'],
  jpeg: ['image/jpeg', 'image/jpg'],
  png: ['image/png'],
  webp: ['image/webp'],
  pdf: ['application/pdf'],
}

export const EXTENSIONES_PERMITIDAS = Object.keys(MIME_POR_EXTENSION)
export const TAMANO_MAXIMO_ARCHIVO = 5 * 1024 * 1024

// Lista única para los inputs type="file": extensiones explícitas en vez de
// `image/*`, que dejaría elegir formatos no admitidos por el backend.
export const ACEPTAR_ARCHIVOS = [
  ...EXTENSIONES_PERMITIDAS.map((extension) => `.${extension}`),
  ...new Set(Object.values(MIME_POR_EXTENSION).flat()),
].join(',')

const extensionDe = (archivo) => {
  const nombre = String(archivo?.name ?? '')
  if (!nombre.includes('.')) return ''
  return nombre.toLowerCase().split('.').pop()
}

/**
 * Devuelve un mensaje de error, o '' cuando el archivo es apto para enviarse.
 * Si `file.type` viene vacío se usa solo la extensión; el backend confirma
 * después los bytes reales.
 */
export function validarArchivoAdjunto(archivo) {
  if (!archivo) return 'Selecciona un archivo.'

  const extension = extensionDe(archivo)
  const mimePosibles = MIME_POR_EXTENSION[extension]
  if (!mimePosibles) {
    return 'Solo se permiten imágenes JPG/PNG/WebP o PDF.'
  }

  const declarado = String(archivo.type ?? '').trim().toLowerCase()
  const conocidos = new Set(Object.values(MIME_POR_EXTENSION).flat())
  if (declarado && conocidos.has(declarado) && !mimePosibles.includes(declarado)) {
    return 'La extensión y el tipo del archivo no coinciden.'
  }

  if (Number(archivo.size) > TAMANO_MAXIMO_ARCHIVO) {
    return 'El archivo supera el tamaño máximo de 5 MB.'
  }

  return ''
}

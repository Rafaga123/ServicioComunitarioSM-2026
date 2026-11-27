"""Utilidades de almacenamiento físico de adjuntos (pases y reportes).

Los adjuntos se guardan físicamente bajo STORAGE_ROOT con rutas relativas
estándar:

    {etiqueta}/{pases|reportes}/{nivel}/{grado_slug}/{letra}/estudiante-{id}/archivo.{ext}

donde `etiqueta` es `2026-2027` para el año lectivo 2026. Se devuelven como
`archivo_url` en los DTO (RFC-style: ruta relativa).
"""

import os
import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import ARCHIVOS_MAX_BYTES, STORAGE_ROOT
from app.models.enums import NivelEducativo
from app.utils.fechas import ahora_caracas
from app.utils.periodos import etiqueta_periodo
from app.utils.texto import texto_legible

# Extensiones permitidas y su MIME canónico. El MIME se deriva del contenido,
# nunca del `Content-Type` declarado por el cliente.
EXTENSION_MIME = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".pdf": "application/pdf",
}

MIME_PERMITIDOS = set(EXTENSION_MIME.values())
EXTENSIONES_PERMITIDAS = set(EXTENSION_MIME)

# Slugs de los grados según el catálogo de `Grados` (1..11).
GRADO_SLUGS = {
  1: "1er_grado",
  2: "2do_grado",
  3: "3er_grado",
  4: "4to_grado",
  5: "5to_grado",
  6: "6to_grado",
  7: "1er_ano",
  8: "2do_ano",
  9: "3er_ano",
  10: "4to_ano",
  11: "5to_ano",
}


def _raiz() -> Path:
  return Path(STORAGE_ROOT).resolve()


def _sanitizar_nombre(nombre: str) -> str:
  """Devuelve un nombre seguro: sin nulos, directorios ni '..'."""
  sin_nulos = (nombre or "").replace("\x00", "")
  base = sin_nulos.replace("\\", "/").rsplit("/", 1)[-1]
  base = re.sub(r"[^\w\s.-]", "_", base).strip().strip(".").strip()
  return base[:100] or "archivo"


def ruta_absoluta(ruta_relativa: str) -> Path:
  """Resuelve una ruta relativa dentro de STORAGE_ROOT.

  Rechaza rutas absolutas, con '..' o '.' vacías.
  """
  raiz = _raiz()
  destino = (raiz / ruta_relativa).resolve()
  if not destino.is_relative_to(raiz):
    raise ValueError("Ruta fuera del directorio de almacenamiento")
  return destino


def ruta_relativa_imagen(
  periodo_lectivo: int,
  carpeta: str,
  grado_numero: int,
  seccion_letra: str,
  nivel: NivelEducativo,
  estudiante_id: int,
  registro_id: int,
  extension: str,
) -> str:
  """Construye la ruta de un adjunto con nombre `{registro_id}_{uuid8}.{ext}`."""
  extension = extension.lstrip(".").lower() or "jpg"
  slug_grado = GRADO_SLUGS.get(grado_numero, f"grado_{grado_numero}")
  nombre_archivo = f"{registro_id}_{uuid.uuid4().hex[:8]}.{extension}"
  return Path(
    etiqueta_periodo(periodo_lectivo),
    _sanitizar_nombre(carpeta),
    nivel.value.lower(),
    slug_grado,
    seccion_letra.upper(),
    f"estudiante-{estudiante_id}",
    nombre_archivo,
  ).as_posix()


def _detectar_formato(contenido: bytes) -> tuple[str, str] | None:
  """Devuelve `(extension, mime)` según la firma binaria del contenido.

  Solo reconoce los formatos permitidos. El cliente puede mentir en el nombre
  y en el `Content-Type`; los bytes son la única fuente de verdad.
  """
  if contenido.startswith(b"\xff\xd8\xff"):
    return "jpg", "image/jpeg"
  if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
    return "png", "image/png"
  if len(contenido) >= 12 and contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
    return "webp", "image/webp"
  if contenido.startswith(b"%PDF-"):
    return "pdf", "application/pdf"
  return None


def validar_upload(archivo: UploadFile) -> tuple[str, str, str, bytes]:
  """Valida un adjunto subido y devuelve (nombre_base, ext, mime, contenido).

  Acepta JPG/JPEG, PNG, WebP y PDF de hasta `ARCHIVOS_MAX_BYTES`. La extensión
  del nombre y la firma binaria deben coincidir; el MIME devuelto se calcula a
  partir de los bytes y es el que se guarda en la metadata.
  """
  nombre = archivo.filename or "archivo"
  extension = f".{nombre.rsplit('.', 1)[1].lower()}" if "." in nombre else ""
  if extension not in EXTENSIONES_PERMITIDAS:
    raise ValueError(
      "Extensión no permitida; se aceptan jpg, jpeg, png, webp y pdf"
    )

  contenido = archivo.file.read()
  if len(contenido) > ARCHIVOS_MAX_BYTES:
    raise ValueError("El archivo supera el tamaño máximo permitido")

  formato = _detectar_formato(contenido)
  if formato is None:
    raise ValueError("El contenido no es una imagen JPG/PNG/WebP ni un PDF")

  extension_detectada, mime = formato
  if EXTENSION_MIME[f".{extension_detectada}"] != EXTENSION_MIME[extension]:
    raise ValueError("La extensión no coincide con el contenido del archivo")

  nombre_legible = texto_legible(_sanitizar_nombre(nombre))
  return nombre_legible, extension_detectada, mime, contenido


def nombre_unico(ruta_relativa: str, nombre_archivo: str) -> str:
  """Devuelve el nombre con sufijo `_v2`, `_v3`, … si el archivo ya existe."""
  destino = ruta_absoluta(ruta_relativa)
  if not destino.exists():
    return nombre_archivo
  stem, sufijo = os.path.splitext(nombre_archivo)
  i = 2
  while (destino.parent / f"{stem}_v{i}{sufijo}").exists():
    i += 1
  return f"{stem}_v{i}{sufijo}"


def ruta_con_nombre(ruta_relativa: str, nombre_archivo: str) -> str:
  """Reemplaza solo el nombre final de la ruta, no el texto en los padres."""
  return Path(ruta_relativa).with_name(nombre_archivo).as_posix()


def guardar_archivo(ruta_relativa: str, contenido: bytes) -> None:
  """Escribe el contenido en la ruta indicada, creando las carpetas."""
  destino = ruta_absoluta(ruta_relativa)
  destino.parent.mkdir(parents=True, exist_ok=True)
  destino.write_bytes(contenido)


def leer_archivo(ruta_relativa: str) -> bytes:
  """Devuelve el contenido del archivo de la ruta indicada."""
  return ruta_absoluta(ruta_relativa).read_bytes()


def existe_archivo(ruta_relativa: str) -> bool:
  """Indica si la ruta corresponde a un archivo existente."""
  try:
    return ruta_absoluta(ruta_relativa).is_file()
  except ValueError:
    return False


def hash_contenido(contenido: bytes) -> str:
  """Devuelve el SHA-256 del contenido."""
  import hashlib

  return hashlib.sha256(contenido).hexdigest()


def registrar_meta_archivo(
  registro,
  ruta_relativa: str,
  nombre_base: str,
  mime: str,
  contenido: bytes,
  subido_por: int | None,
) -> None:
  """Registra los metadatos del adjunto en el registro (pase o reporte)."""
  registro.archivo_url = ruta_relativa
  registro.archivo_nombre = nombre_base
  registro.archivo_mime = mime
  registro.archivo_tamano = len(contenido)
  registro.archivo_hash = hash_contenido(contenido)
  registro.archivo_subido_por = subido_por
  registro.archivo_fecha = ahora_caracas()


def quitar_meta_archivo(registro) -> None:
  """Solo desvincula el adjunto del registro; no borra el archivo físico."""
  registro.archivo_url = None
  registro.archivo_nombre = None
  registro.archivo_mime = None
  registro.archivo_tamano = None
  registro.archivo_hash = None
  registro.archivo_subido_por = None
  registro.archivo_fecha = None

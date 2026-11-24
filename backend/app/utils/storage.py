"""Utilidades de almacenamiento físico de adjuntos (pases y reportes).

Los adjuntos se guardan físicamente bajo STORAGE_ROOT con rutas relativas
estándar:

    periodo_lectivo/{etiqueta}/{pases|reportes}/{nivel}/{grado_slug}/{letra}/estudiante-{id}/archivo.{ext}

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

# MIME permitidos para adjuntos de pases y reportes (solo imágenes).
MIME_PERMITIDOS = {
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/webp",
}

# Subfijos permitidos (incluye el punto).
EXTENSIONES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp"}

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
  """Construye la ruta relativa estándar de un adjunto de pase o reporte."""
  extension = extension.lstrip(".").lower() or "jpg"
  slug_grado = GRADO_SLUGS.get(grado_numero, f"grado_{grado_numero}")
  nombre_archivo = f"{registro_id}_{uuid.uuid4().hex[:8]}.{extension}"
  return Path(
    "periodo_lectivo",
    etiqueta_periodo(periodo_lectivo),
    _sanitizar_nombre(carpeta),
    nivel.value.lower(),
    slug_grado,
    seccion_letra.upper(),
    f"estudiante-{estudiante_id}",
    nombre_archivo,
  ).as_posix()


def validar_upload(archivo: UploadFile) -> tuple[str, str, str, bytes]:
  """Valida un adjunto subido y devuelve (nombre_base, ext, mime, contenido).

  Rechaza tamaños, MIME o extensiones fuera del allowlist.
  """
  nombre = archivo.filename or "archivo"
  extension = f".{nombre.rsplit('.', 1)[1].lower()}" if "." in nombre else ""
  if extension not in EXTENSIONES_PERMITIDAS:
    raise ValueError("Extensión no permitida; se aceptan jpg, jpeg, png y webp")

  contenido = archivo.file.read()
  if len(contenido) > ARCHIVOS_MAX_BYTES:
    raise ValueError("El archivo supera el tamaño máximo permitido")

  mime = archivo.content_type or ""
  if mime not in MIME_PERMITIDOS:
    raise ValueError("Tipo de archivo no permitido; solo imágenes")

  return _sanitizar_nombre(nombre), extension.lstrip("."), mime, contenido


def nombre_unico(ruta_relativa: str, nombre_archivo: str) -> str:
  """Añade sufijo `_v{n}` si el archivo ya existe; lo devuelve igual si no."""
  destino = ruta_absoluta(ruta_relativa)
  if not destino.exists():
    return nombre_archivo
  stem, sufijo = os.path.splitext(nombre_archivo)
  i = 2
  while (destino.parent / f"{stem}_v{i}{sufijo}").exists():
    i += 1
  return f"{stem}_v{i}{sufijo}"


def guardar_archivo(ruta_relativa: str, contenido: bytes) -> None:
  destino = ruta_absoluta(ruta_relativa)
  destino.parent.mkdir(parents=True, exist_ok=True)
  destino.write_bytes(contenido)


def leer_archivo(ruta_relativa: str) -> bytes:
  return ruta_absoluta(ruta_relativa).read_bytes()


def existe_archivo(ruta_relativa: str) -> bool:
  try:
    return ruta_absoluta(ruta_relativa).is_file()
  except ValueError:
    return False


def hash_contenido(contenido: bytes) -> str:
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

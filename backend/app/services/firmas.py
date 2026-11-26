"""Firma canónica y reutilización segura de PDFs de listados.

La firma identifica los datos que producen el listado, no los bytes del PDF.
Antes de generar se toma `pg_advisory_xact_lock(hashtext(firma))`, que se
mantiene hasta el commit, para que dos peticiones concurrentes no creen dos
PDFs con el mismo contenido. La política se activa con
`REUTILIZAR_DOCUMENTOS_IGUALES=True`; por defecto queda desactivada.
"""

import hashlib
import json

from sqlmodel import Session, select, text

from app.core.config import REUTILIZAR_DOCUMENTOS_IGUALES
from app.models.db import DocumentosFirmas, DocumentosGenerados
from app.models.enums import NivelEducativo, TipoDocumento
from app.services.listados import DocumentoListado
from app.utils.storage import existe_archivo


def firma_documento(
  tipo: TipoDocumento,
  periodo: int,
  nivel: NivelEducativo | None,
  documento: DocumentoListado,
) -> str:
  """SHA-256 canónico de los datos que determinan el contenido del PDF."""
  payload = {
    "tipo": tipo.value,
    "periodo": periodo,
    "nivel": nivel.value if nivel is not None else None,
    "id_grado": documento.grado_id,
    "id_seccion": documento.seccion_id,
    "titulo": documento.titulo,
    "descripcion": documento.seccion_descripcion,
    "encabezados": documento.encabezados,
    "col_anchos": documento.col_anchos,
    "filas": documento.filas,
    "horario_cabecera": documento.horario_cabecera,
    "horario_filas": documento.horario_filas,
    "horario_docentes": [
      list(registro) for registro in (documento.horario_docentes or [])
    ],
  }
  canonico = json.dumps(
    payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
  )
  return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def firma_si_activa(
  tipo: TipoDocumento,
  periodo: int,
  nivel: NivelEducativo | None,
  documento: DocumentoListado,
) -> str | None:
  """Devuelve la firma solo cuando la reutilización está habilitada."""
  if not REUTILIZAR_DOCUMENTOS_IGUALES:
    return None
  return firma_documento(tipo, periodo, nivel, documento)


def documento_reutilizable(
  session: Session, firma: str
) -> DocumentosGenerados | None:
  """Devuelve el PDF vigente con esa firma, bajo bloqueo transaccional.

  El bloqueo se libera al confirmar o cerrar la transacción. Un documento se
  considera reutilizable solo si sigue activo y su archivo existe en disco.
  """
  session.execute(
    text("SELECT pg_advisory_xact_lock(hashtext(:firma))"),
    {"firma": firma},
  )
  registro_firma = session.exec(
    select(DocumentosFirmas).where(
      DocumentosFirmas.firma == firma,
      DocumentosFirmas.fecha_eliminacion.is_(None),
    )
  ).first()
  if registro_firma is None:
    return None

  documento = session.get(DocumentosGenerados, registro_firma.documento_id)
  if (
    documento is None
    or documento.fecha_eliminacion is not None
    or not existe_archivo(documento.ruta_relativa)
  ):
    return None
  return documento


def registrar_firma(session: Session, firma: str, documento_id: int) -> None:
  """Asocia la firma al documento recién generado (o reactiva la entrada)."""
  registro = session.exec(
    select(DocumentosFirmas).where(DocumentosFirmas.firma == firma)
  ).first()
  if registro is None:
    session.add(DocumentosFirmas(firma=firma, documento_id=documento_id))
    return
  registro.documento_id = documento_id
  registro.fecha_eliminacion = None

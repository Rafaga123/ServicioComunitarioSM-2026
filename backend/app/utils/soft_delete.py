"""Marca registros como eliminados sin borrarlos físicamente."""

from sqlmodel import Session

from app.models.db import EsquemaBase
from app.utils.fechas import ahora_caracas


def marcar_eliminado(session: Session, registro: EsquemaBase) -> None:
  """Marca el registro como eliminado con la fecha actual."""
  registro.fecha_eliminacion = ahora_caracas()
  session.add(registro)

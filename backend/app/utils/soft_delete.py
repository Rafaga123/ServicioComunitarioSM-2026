from datetime import UTC, datetime

from sqlmodel import Session

from app.models.db import EsquemaBase


def marcar_eliminado(session: Session, registro: EsquemaBase) -> None:
  registro.fecha_eliminacion = datetime.now(UTC)
  session.add(registro)

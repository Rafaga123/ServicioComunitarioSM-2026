"""Resolución del periodo lectivo activo para los endpoints."""

from sqlmodel import Session, select

from app.models.db import PeriodosLectivos


def periodo_activo(session: Session) -> PeriodosLectivos | None:
  """Devuelve el periodo activo más reciente, si existe."""
  return session.exec(
    select(PeriodosLectivos)
    .where(
      PeriodosLectivos.activo.is_(True),
      PeriodosLectivos.fecha_eliminacion.is_(None),
    )
    .order_by(PeriodosLectivos.anio.desc())
  ).first()


def periodo_lectivo_efectivo(
  session: Session, periodo_lectivo: int | None
) -> int | None:
  """Devuelve el periodo indicado o, si falta, el año del periodo activo.

  Si no hay periodo activo se devuelve `None` para conservar el
  comportamiento previo de los listados (sin filtro de periodo).
  """
  if periodo_lectivo is not None:
    return periodo_lectivo
  activo = periodo_activo(session)
  return activo.anio if activo is not None else None

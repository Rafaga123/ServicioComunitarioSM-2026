from fastapi import Depends
from sqlmodel import Session

from app.models.db import Auditorias
from app.models.session import get_session


def registrar_auditoria(
  usuario_id: int,
  modulo: str,
  accion: str,
  descripcion: str,
  session: Session = Depends(get_session),
) -> None:
  nueva_auditoria = Auditorias(
    usuario_id=usuario_id,
    modulo=modulo,
    accion=accion,
    descripcion=descripcion,
  )
  session.add(nueva_auditoria)

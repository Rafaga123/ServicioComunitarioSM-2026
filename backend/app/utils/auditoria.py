from sqlmodel import Session

from app.models.db import Auditorias


def registrar_auditoria(
  session: Session,
  usuario_id: int,
  modulo: str,
  accion: str,
  descripcion: str,
) -> None:
  nueva_auditoria = Auditorias(
    usuario_id=usuario_id,
    modulo=modulo,
    accion=accion,
    descripcion=descripcion,
  )
  session.add(nueva_auditoria)

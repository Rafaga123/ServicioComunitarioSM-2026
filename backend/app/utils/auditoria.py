from sqlmodel import Session

from app.models.db import Auditorias
from app.models.enums import ModuloAuditoria


def registrar_auditoria(
  session: Session,
  usuario_id: int,
  modulo: ModuloAuditoria,
  accion: str,
  descripcion: str,
) -> None:
  nueva_auditoria = Auditorias(
    usuario_id=usuario_id,
    modulo=modulo.value,
    accion=accion,
    descripcion=descripcion,
  )
  session.add(nueva_auditoria)

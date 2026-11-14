from sqlmodel import Session

from app.models.db import Auditorias


def registrar_auditoria(
  session: Session,
  usuario_id: int | None,
  modulo_afectado: str,
  accion: str,
  descripcion: str,
) -> None:
  nueva_auditoria = Auditorias(
    usuario_id = usuario_id,
    modulo_afectado=modulo_afectado,
    accion=accion,
    descripcion=descripcion,
  )
  session.add(nueva_auditoria)
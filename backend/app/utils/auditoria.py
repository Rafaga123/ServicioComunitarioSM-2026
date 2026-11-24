from sqlmodel import Session, select

from app.models.db import Auditorias
from app.models.enums import ModuloAuditoria
from app.utils.texto import texto_legible

__all__ = ["registrar_auditoria", "normalizar_auditorias_existentes", "texto_legible"]


def registrar_auditoria(
  session: Session,
  usuario_id: int,
  modulo: ModuloAuditoria,
  accion: str,
  descripcion: str,
) -> None:
  modulo_valor = modulo.value if isinstance(modulo, ModuloAuditoria) else str(modulo)
  nueva_auditoria = Auditorias(
    usuario_id=usuario_id,
    modulo=texto_legible(modulo_valor),
    accion=texto_legible(accion),
    descripcion=texto_legible(descripcion),
  )
  session.add(nueva_auditoria)


def normalizar_auditorias_existentes(session: Session) -> int:
  """Normaliza auditorías ya guardadas. Devuelve cuántas cambiaron."""
  cambiadas = 0
  for auditoria in session.exec(select(Auditorias)).all():
    modulo = texto_legible(auditoria.modulo)
    accion = texto_legible(auditoria.accion)
    descripcion = texto_legible(auditoria.descripcion)
    if (
      modulo == auditoria.modulo
      and accion == auditoria.accion
      and descripcion == auditoria.descripcion
    ):
      continue
    auditoria.modulo = modulo
    auditoria.accion = accion
    auditoria.descripcion = descripcion
    cambiadas += 1
  session.commit()
  return cambiadas

import re

from sqlmodel import Session, select

from app.models.db import Auditorias
from app.models.enums import ModuloAuditoria


def texto_legible(valor: object) -> str:
  """Convierte texto técnico a texto visible legible.

  Reglas aplicadas a auditorías: `_` → espacio y `ano`/`anio` → `año`
  (respetando mayúsculas). No toca rutas ni campos de la API.
  """
  texto = str(valor or "").replace("_", " ")

  def reemplazar_año(conincidencia: re.Match[str]) -> str:
    palabra = conincidencia.group(0)
    if palabra.isupper():
      return "AÑO"
    if palabra[:1].isupper():
      return "Año"
    return "año"

  texto = re.sub(r"\b(?:ano|anio)\b", reemplazar_año, texto, flags=re.IGNORECASE)
  return re.sub(r"\s+", " ", texto).strip()


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

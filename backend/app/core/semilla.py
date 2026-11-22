from sqlmodel import Session, select

from app.models.db import Grados
from app.models.enums import NivelEducativo


# Catálogo fijo: del 1 al 6 son grados de escuela y del 7 al 11
# equivalen a primero a quinto año de liceo.
GRADOS_BASE = (
  (1, "1.º Escuela", NivelEducativo.escuela),
  (2, "2.º Escuela", NivelEducativo.escuela),
  (3, "3.º Escuela", NivelEducativo.escuela),
  (4, "4.º Escuela", NivelEducativo.escuela),
  (5, "5.º Escuela", NivelEducativo.escuela),
  (6, "6.º Escuela", NivelEducativo.escuela),
  (7, "1.º Liceo", NivelEducativo.liceo),
  (8, "2.º Liceo", NivelEducativo.liceo),
  (9, "3.º Liceo", NivelEducativo.liceo),
  (10, "4.º Liceo", NivelEducativo.liceo),
  (11, "5.º Liceo", NivelEducativo.liceo),
)


def sembrar_grados(session: Session) -> int:
  """Crea los grados que falten y devuelve cuántos se insertaron.

  La comprobación incluye los grados dados de baja para no resucitar
  un catálogo que el administrador retiró deliberadamente.
  """
  creados = 0

  for numero, nombre, nivel in GRADOS_BASE:
    existente = session.exec(
      select(Grados).where(Grados.numero == numero)
    ).first()

    if existente is not None:
      continue

    session.add(Grados(numero=numero, nombre=nombre, nivel=nivel))
    creados += 1

  return creados

"""Carga el catálogo fijo de grados y bloques horarios institucionales."""

from datetime import time

from sqlmodel import Session, select

from app.models.db import BloquesHorarios, Grados
from app.models.enums import NivelEducativo, TipoBloqueHorario

# Catálogo fijo: del 1 al 6 son grados de escuela y del 7 al 11
# equivalen a primero a quinto año de liceo.
GRADOS_BASE = (
  (1, "1er Grado", NivelEducativo.escuela),
  (2, "2do Grado", NivelEducativo.escuela),
  (3, "3er Grado", NivelEducativo.escuela),
  (4, "4to Grado", NivelEducativo.escuela),
  (5, "5to Grado", NivelEducativo.escuela),
  (6, "6to Grado", NivelEducativo.escuela),
  (7, "1er Año", NivelEducativo.liceo),
  (8, "2do Año", NivelEducativo.liceo),
  (9, "3er Año", NivelEducativo.liceo),
  (10, "4to Año", NivelEducativo.liceo),
  (11, "5to Año", NivelEducativo.liceo),
)


# Jornada del liceo: 8 bloques académicos de 40 minutos (el último de
# 30) separados por dos recesos. El orden total es de 10 tramos.
BLOQUES_BASE = (
  (1, 1, "Bloque 1", TipoBloqueHorario.academico, time(7, 0), time(7, 40)),
  (2, 2, "Bloque 2", TipoBloqueHorario.academico, time(7, 40), time(8, 20)),
  (3, None, "Receso 1", TipoBloqueHorario.receso, time(8, 20), time(8, 40)),
  (4, 3, "Bloque 3", TipoBloqueHorario.academico, time(8, 40), time(9, 20)),
  (5, 4, "Bloque 4", TipoBloqueHorario.academico, time(9, 20), time(10, 0)),
  (6, None, "Receso 2", TipoBloqueHorario.receso, time(10, 0), time(10, 10)),
  (7, 5, "Bloque 5", TipoBloqueHorario.academico, time(10, 10), time(10, 50)),
  (8, 6, "Bloque 6", TipoBloqueHorario.academico, time(10, 50), time(11, 30)),
  (9, 7, "Bloque 7", TipoBloqueHorario.academico, time(11, 30), time(12, 10)),
  (10, 8, "Bloque 8", TipoBloqueHorario.academico, time(12, 10), time(12, 40)),
)


def sembrar_grados(session: Session) -> int:
  """Crea los grados que falten y devuelve cuántos se insertaron.

  La comprobación incluye los grados dados de baja para no resucitar
  un catálogo que el administrador retiró deliberadamente.
  """
  creados = 0

  for numero, nombre, nivel in GRADOS_BASE:
    existente = session.exec(select(Grados).where(Grados.numero == numero)).first()

    if existente is not None:
      continue

    session.add(Grados(numero=numero, nombre=nombre, nivel=nivel))
    creados += 1

  return creados


def sembrar_bloques(session: Session) -> int:
  """Crea los tramos de la jornada que falten y devuelve cuántos insertó."""
  creados = 0

  for orden, numero, nombre, tipo, hora_inicio, hora_fin in BLOQUES_BASE:
    existente = session.exec(
      select(BloquesHorarios).where(BloquesHorarios.orden == orden)
    ).first()

    if existente is not None:
      continue

    session.add(
      BloquesHorarios(
        orden=orden,
        numero=numero,
        nombre=nombre,
        tipo=tipo,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
      )
    )
    creados += 1

  return creados


def sembrar_datos(session: Session) -> tuple[int, int]:
  """Ejecuta toda la semilla institucional y confirma la transacción.

  Devuelve (grados creados, bloques creados) para poder informar
  cuántos registros nuevos se insertaron en cada arranque.
  """
  grados = sembrar_grados(session)
  bloques = sembrar_bloques(session)
  session.commit()
  return grados, bloques

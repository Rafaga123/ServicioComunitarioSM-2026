from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.db import (
  Asignaturas,
  Docentes,
  Estudiantes,
  Grados,
  Horarios,
  Pases,
  Reportes,
  Representantes,
  Secciones,
  Usuarios,
)
from app.models.enums import NivelEducativo
from app.models.schemas import PeticionResumenGestion
from app.models.session import get_session
from app.utils.security import obtener_usuario_actual, resolver_nivel

router = APIRouter(prefix="/gestion", tags=["Gestión"])


def _contar_estudiantes(session: Session, nivel: NivelEducativo | None) -> int:
  consulta = (
    select(func.count(Estudiantes.id))
    .select_from(Estudiantes)
    .join(Secciones, Estudiantes.id_seccion == Secciones.id)
    .join(Grados, Secciones.id_grado == Grados.id)
    .where(
      Estudiantes.fecha_eliminacion.is_(None),
      Secciones.fecha_eliminacion.is_(None),
      Grados.fecha_eliminacion.is_(None),
    )
  )
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)

  return session.exec(consulta).one()


def _contar_secciones(session: Session, nivel: NivelEducativo | None) -> int:
  consulta = (
    select(func.count(Secciones.id))
    .select_from(Secciones)
    .join(Grados, Secciones.id_grado == Grados.id)
    .where(
      Secciones.fecha_eliminacion.is_(None),
      Grados.fecha_eliminacion.is_(None),
    )
  )
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)

  return session.exec(consulta).one()


def _contar_docentes(session: Session, nivel: NivelEducativo | None) -> int:
  consulta = select(func.count(Docentes.id)).where(Docentes.fecha_eliminacion.is_(None))
  if nivel is not None:
    consulta = consulta.where(Docentes.nivel == nivel)

  return session.exec(consulta).one()


def _contar_asignaturas(session: Session, nivel: NivelEducativo | None) -> int:
  consulta = (
    select(func.count(Asignaturas.id))
    .select_from(Asignaturas)
    .join(Grados, Asignaturas.id_grado == Grados.id)
    .where(
      Asignaturas.fecha_eliminacion.is_(None),
      Grados.fecha_eliminacion.is_(None),
    )
  )
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)

  return session.exec(consulta).one()


def _contar_horarios(session: Session, nivel: NivelEducativo | None) -> int:
  consulta = (
    select(func.count(Horarios.id))
    .select_from(Horarios)
    .join(Secciones, Horarios.id_seccion == Secciones.id)
    .join(Grados, Secciones.id_grado == Grados.id)
    .where(
      Horarios.fecha_eliminacion.is_(None),
      Secciones.fecha_eliminacion.is_(None),
      Grados.fecha_eliminacion.is_(None),
    )
  )
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)

  return session.exec(consulta).one()


def _contar_pases(session: Session, nivel: NivelEducativo | None) -> int:
  consulta = (
    select(func.count(Pases.id))
    .select_from(Pases)
    .join(Estudiantes, Pases.id_estudiante == Estudiantes.id)
    .join(Secciones, Estudiantes.id_seccion == Secciones.id)
    .join(Grados, Secciones.id_grado == Grados.id)
    .where(
      Pases.fecha_eliminacion.is_(None),
      Estudiantes.fecha_eliminacion.is_(None),
      Secciones.fecha_eliminacion.is_(None),
      Grados.fecha_eliminacion.is_(None),
    )
  )
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)

  return session.exec(consulta).one()


def _contar_reportes(session: Session, nivel: NivelEducativo | None) -> int:
  consulta = (
    select(func.count(Reportes.id))
    .select_from(Reportes)
    .join(Estudiantes, Reportes.id_estudiante == Estudiantes.id)
    .join(Secciones, Estudiantes.id_seccion == Secciones.id)
    .join(Grados, Secciones.id_grado == Grados.id)
    .where(
      Reportes.fecha_eliminacion.is_(None),
      Estudiantes.fecha_eliminacion.is_(None),
      Secciones.fecha_eliminacion.is_(None),
      Grados.fecha_eliminacion.is_(None),
    )
  )
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)

  return session.exec(consulta).one()


def _contar_representantes(session: Session, nivel: NivelEducativo | None) -> int:
  # Los representantes no tienen nivel propio: se cuentan los que tienen
  # al menos un estudiante activo dentro del nivel consultado.
  consulta = (
    select(func.count(func.distinct(Representantes.id)))
    .select_from(Representantes)
    .join(Estudiantes, Estudiantes.id_representante == Representantes.id)
    .join(Secciones, Estudiantes.id_seccion == Secciones.id)
    .join(Grados, Secciones.id_grado == Grados.id)
    .where(
      Representantes.fecha_eliminacion.is_(None),
      Estudiantes.fecha_eliminacion.is_(None),
      Secciones.fecha_eliminacion.is_(None),
      Grados.fecha_eliminacion.is_(None),
    )
  )
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)

  return session.exec(consulta).one()


@router.get("/resumen", response_model=PeticionResumenGestion)
def obtener_resumen_gestion(
  nivel: NivelEducativo | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  nivel = resolver_nivel(usuario_actual, nivel)

  return PeticionResumenGestion(
    nivel=nivel,
    representantes=_contar_representantes(session, nivel),
    estudiantes=_contar_estudiantes(session, nivel),
    secciones=_contar_secciones(session, nivel),
    docentes=_contar_docentes(session, nivel),
    asignaturas=_contar_asignaturas(session, nivel),
    horarios=_contar_horarios(session, nivel),
    pases=_contar_pases(session, nivel),
    reportes=_contar_reportes(session, nivel),
  )

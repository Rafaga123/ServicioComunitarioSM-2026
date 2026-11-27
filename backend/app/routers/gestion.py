"""Expone el resumen académico, los periodos lectivos y el cierre de año."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.db import (
  Asignaturas,
  Docentes,
  Estudiantes,
  Grados,
  Horarios,
  Pases,
  PeriodosLectivos,
  Reportes,
  Representantes,
  Secciones,
  Usuarios,
)
from app.models.enums import ModuloAuditoria, NivelEducativo, RolesUsuario
from app.models.schemas import (
  ActualizarPeriodoLectivo,
  CrearPeriodoLectivo,
  PeticionCierreAnio,
  PeticionPeriodoLectivo,
  PeticionResumenGestion,
  SolicitudCierreAnio,
)
from app.models.session import get_session
from app.services.cierre import cerrar_anio as cerrar_anio_servicio
from app.utils.auditoria import registrar_auditoria
from app.utils.periodos import periodo_activo, periodo_lectivo_efectivo
from app.utils.security import (
  obtener_usuario_actual,
  requerir_roles,
  resolver_nivel,
)

router = APIRouter(prefix="/gestion", tags=["Gestión"])


def _contar_estudiantes(
  session: Session,
  nivel: NivelEducativo | None,
  periodo_lectivo: int | None,
) -> int:
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
  if periodo_lectivo is not None:
    consulta = consulta.where(Secciones.periodo_lectivo == periodo_lectivo)

  return session.exec(consulta).one()


def _contar_secciones(
  session: Session,
  nivel: NivelEducativo | None,
  periodo_lectivo: int | None,
) -> int:
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
  if periodo_lectivo is not None:
    consulta = consulta.where(Secciones.periodo_lectivo == periodo_lectivo)

  return session.exec(consulta).one()


def _contar_docentes(session: Session, nivel: NivelEducativo | None) -> int:
  # Los docentes son un catálogo global: no dependen de un periodo lectivo.
  consulta = select(func.count(Docentes.id)).where(Docentes.fecha_eliminacion.is_(None))
  if nivel is not None:
    consulta = consulta.where(Docentes.nivel == nivel)

  return session.exec(consulta).one()


def _contar_asignaturas(
  session: Session,
  nivel: NivelEducativo | None,
  periodo_lectivo: int | None,
) -> int:
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
  if periodo_lectivo is not None:
    consulta = consulta.where(Asignaturas.periodo_lectivo == periodo_lectivo)

  return session.exec(consulta).one()


def _contar_horarios(
  session: Session,
  nivel: NivelEducativo | None,
  periodo_lectivo: int | None,
) -> int:
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
  if periodo_lectivo is not None:
    consulta = consulta.where(Horarios.periodo_lectivo == periodo_lectivo)

  return session.exec(consulta).one()


def _contar_pases(
  session: Session,
  nivel: NivelEducativo | None,
  periodo_lectivo: int | None,
) -> int:
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
  if periodo_lectivo is not None:
    consulta = consulta.where(Pases.periodo_lectivo == periodo_lectivo)

  return session.exec(consulta).one()


def _contar_reportes(
  session: Session,
  nivel: NivelEducativo | None,
  periodo_lectivo: int | None,
) -> int:
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
  if periodo_lectivo is not None:
    consulta = consulta.where(Reportes.periodo_lectivo == periodo_lectivo)

  return session.exec(consulta).one()


def _contar_representantes(
  session: Session,
  nivel: NivelEducativo | None,
  periodo_lectivo: int | None,
) -> int:
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
  if periodo_lectivo is not None:
    consulta = consulta.where(Secciones.periodo_lectivo == periodo_lectivo)

  return session.exec(consulta).one()


def _to_periodo(periodo: PeriodosLectivos) -> PeticionPeriodoLectivo:
  return PeticionPeriodoLectivo(
    id=periodo.id,
    anio=periodo.anio,
    activo=periodo.activo,
    cerrado=periodo.cerrado,
  )


@router.get("/periodos", response_model=list[PeticionPeriodoLectivo])
def listar_periodos(
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_roles(RolesUsuario.administrador)),
):
  periodos = session.exec(
    select(PeriodosLectivos)
    .where(PeriodosLectivos.fecha_eliminacion.is_(None))
    .order_by(PeriodosLectivos.anio.desc())
  ).all()

  return [_to_periodo(periodo) for periodo in periodos]


@router.get("/periodos/activo", response_model=PeticionPeriodoLectivo | None)
def obtener_periodo_activo(
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  """Devuelve el periodo activo para cualquier usuario autenticado."""
  periodo = periodo_activo(session)

  return _to_periodo(periodo) if periodo else None


@router.post(
  "/periodos",
  response_model=PeticionPeriodoLectivo,
  status_code=status.HTTP_201_CREATED,
)
def crear_periodo(
  periodo_in: CrearPeriodoLectivo,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_roles(RolesUsuario.administrador)),
):
  existente = session.exec(
    select(PeriodosLectivos).where(
      PeriodosLectivos.anio == periodo_in.anio,
      PeriodosLectivos.fecha_eliminacion.is_(None),
    )
  ).first()
  if existente:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Ya existe un periodo lectivo con ese año",
    )

  periodo = PeriodosLectivos(
    anio=periodo_in.anio, activo=periodo_in.activo, cerrado=False
  )
  session.add(periodo)
  session.flush()

  if periodo.activo:
    otros = session.exec(
      select(PeriodosLectivos).where(
        PeriodosLectivos.id != periodo.id,
        PeriodosLectivos.activo,
        PeriodosLectivos.fecha_eliminacion.is_(None),
      )
    ).all()
    for otro in otros:
      otro.activo = False

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.periodos_lectivos,
    "CREAR",
    f"Se creó el periodo lectivo {periodo_in.anio}.",
  )

  session.commit()
  session.refresh(periodo)
  return _to_periodo(periodo)


@router.patch("/periodos/{periodo_id}", response_model=PeticionPeriodoLectivo)
def actualizar_periodo(
  periodo_id: int,
  periodo_in: ActualizarPeriodoLectivo,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_roles(RolesUsuario.administrador)),
):
  periodo = session.get(PeriodosLectivos, periodo_id)
  if not periodo or periodo.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Periodo no encontrado"
    )

  datos = periodo_in.model_dump(exclude_unset=True)
  if "cerrado" in datos:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El estado 'cerrado' solo se modifica al cerrar el año lectivo",
    )
  if "activo" in datos and datos["activo"] is None:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El campo 'activo' no puede ser nulo",
    )
  if datos.get("activo") is True and periodo.cerrado:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="No se puede activar un periodo lectivo cerrado",
    )

  if datos.get("activo") is True:
    otros = session.exec(
      select(PeriodosLectivos).where(
        PeriodosLectivos.id != periodo_id,
        PeriodosLectivos.activo,
        PeriodosLectivos.fecha_eliminacion.is_(None),
      )
    ).all()
    for otro in otros:
      otro.activo = False

  for campo, valor in datos.items():
    setattr(periodo, campo, valor)

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.periodos_lectivos,
    "ACTUALIZAR",
    f"Se actualizó el periodo lectivo {periodo.anio} "
    f"(activo={periodo.activo}, cerrado={periodo.cerrado}).",
  )

  session.add(periodo)
  session.flush()
  session.commit()
  session.refresh(periodo)
  return _to_periodo(periodo)


@router.get("/resumen", response_model=PeticionResumenGestion)
def obtener_resumen_gestion(
  nivel: NivelEducativo | None = None,
  periodo_lectivo: int | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  nivel = resolver_nivel(usuario_actual, nivel)
  periodo_lectivo = periodo_lectivo_efectivo(session, periodo_lectivo)

  if periodo_lectivo is None:
    return PeticionResumenGestion(
      nivel=nivel,
      periodo_lectivo=None,
      representantes=0,
      estudiantes=0,
      secciones=0,
      docentes=0,
      asignaturas=0,
      horarios=0,
      pases=0,
      reportes=0,
    )

  return PeticionResumenGestion(
    nivel=nivel,
    periodo_lectivo=periodo_lectivo,
    representantes=_contar_representantes(session, nivel, periodo_lectivo),
    estudiantes=_contar_estudiantes(session, nivel, periodo_lectivo),
    secciones=_contar_secciones(session, nivel, periodo_lectivo),
    docentes=_contar_docentes(session, nivel),
    asignaturas=_contar_asignaturas(session, nivel, periodo_lectivo),
    horarios=_contar_horarios(session, nivel, periodo_lectivo),
    pases=_contar_pases(session, nivel, periodo_lectivo),
    reportes=_contar_reportes(session, nivel, periodo_lectivo),
  )


@router.post("/cerrar-anio", response_model=PeticionCierreAnio)
def cerrar_anio(
  peticion: SolicitudCierreAnio,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(
    requerir_roles(RolesUsuario.administrador)
  ),
):
  """Cierra el periodo actual: genera listados y traspasa estudiantes.

  El periodo siguiente se crea si no existe (activo y vacío de secciones).
  """
  return cerrar_anio_servicio(
    session,
    usuario_actual,
    peticion.periodo_actual,
    peticion.periodo_siguiente,
  )

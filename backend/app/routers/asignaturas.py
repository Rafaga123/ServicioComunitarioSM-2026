"""Gestiona asignaturas, su vinculación con docentes y los horarios asociados."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  filtro_activos,
  paginar,
)
from app.models.db import (
  Asignaturas,
  AsignaturasDocentes,
  Docentes,
  Grados,
  Horarios,
  PeriodosLectivos,
  Usuarios,
)
from app.models.enums import (
  ModuloAuditoria,
  NivelEducativo,
  RolesUsuario,
)
from app.models.schemas import (
  ActualizarAsignatura,
  CrearAsignatura,
  PeticionAsignatura,
  PeticionDocente,
)
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.nombres import nombre_completo
from app.utils.periodos import periodo_lectivo_efectivo
from app.utils.security import (
  obtener_usuario_actual,
  requerir_roles,
  resolver_nivel,
  validar_acceso_nivel,
)
from app.utils.soft_delete import marcar_eliminado

router = APIRouter(prefix="/asignaturas", tags=["Asignaturas"])
requerir_admin = requerir_roles(RolesUsuario.administrador)


def _obtener_asignatura_activa(session: Session, asignatura_id: int) -> Asignaturas:
  asignatura = session.get(Asignaturas, asignatura_id)

  if not asignatura or asignatura.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Asignatura no encontrada",
    )

  return asignatura


def _obtener_docente_activo(session: Session, docente_id: int) -> Docentes:
  docente = session.get(Docentes, docente_id)

  if not docente or docente.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Docente no encontrado"
    )

  return docente


def _dto_docente(docente: Docentes) -> PeticionDocente:
  return PeticionDocente(
    id=docente.id,
    primer_nombre=docente.primer_nombre,
    segundo_nombre=docente.segundo_nombre,
    primer_apellido=docente.primer_apellido,
    segundo_apellido=docente.segundo_apellido,
    cedula=docente.cedula,
    nivel=docente.nivel,
  )


def _obtener_docentes_vinculados(
  session: Session, asignatura_id: int
) -> list[PeticionDocente]:
  consulta = (
    select(Docentes)
    .join(AsignaturasDocentes, Docentes.id == AsignaturasDocentes.id_docente)
    .where(
      AsignaturasDocentes.id_asignatura == asignatura_id,
      AsignaturasDocentes.fecha_eliminacion.is_(None),
      Docentes.fecha_eliminacion.is_(None),
    )
    .order_by(Docentes.id)
  )
  return [_dto_docente(d) for d in session.exec(consulta).all()]


def _mapa_docentes_vinculados(
  session: Session, ids_asignatura: list[int]
) -> dict[int, list[PeticionDocente]]:
  """Obtiene en una sola consulta los docentes activos de varias asignaturas."""
  if not ids_asignatura:
    return {}

  consulta = (
    select(AsignaturasDocentes.id_asignatura, Docentes)
    .join(Docentes, Docentes.id == AsignaturasDocentes.id_docente)
    .where(
      AsignaturasDocentes.id_asignatura.in_(ids_asignatura),
      AsignaturasDocentes.fecha_eliminacion.is_(None),
      Docentes.fecha_eliminacion.is_(None),
    )
    .order_by(AsignaturasDocentes.id_asignatura, Docentes.id)
  )
  mapa: dict[int, list[PeticionDocente]] = {id_: [] for id_ in ids_asignatura}
  for id_asignatura, docente in session.exec(consulta).all():
    mapa[id_asignatura].append(_dto_docente(docente))
  return mapa


def _validar_grado_liceo(session: Session, id_grado: int) -> Grados:
  grado = session.get(Grados, id_grado)

  if not grado or grado.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Grado no encontrado"
    )

  if grado.nivel != NivelEducativo.liceo:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Las asignaturas solo pueden vincular grados de liceo",
    )

  return grado


def _validar_periodo(session: Session, periodo_lectivo: int) -> PeriodosLectivos:
  periodo = session.exec(
    select(PeriodosLectivos).where(
      PeriodosLectivos.anio == periodo_lectivo,
      PeriodosLectivos.fecha_eliminacion.is_(None),
    )
  ).first()
  if not periodo or periodo.cerrado:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El periodo lectivo no existe o está cerrado",
    )

  return periodo


def _obtener_periodo_activo(session: Session) -> PeriodosLectivos:
  periodo = session.exec(
    select(PeriodosLectivos).where(
      PeriodosLectivos.activo,
      PeriodosLectivos.fecha_eliminacion.is_(None),
    )
  ).first()
  if not periodo:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="No hay periodo lectivo activo; selecciona uno explícitamente.",
    )

  return periodo


def _validar_duplicado_asignatura(
  session: Session,
  id_grado: int,
  nombre: str,
  periodo_lectivo: int,
  excluir_id: int | None = None,
) -> None:
  statement = select(Asignaturas).where(
    Asignaturas.id_grado == id_grado,
    Asignaturas.nombre == nombre,
    Asignaturas.periodo_lectivo == periodo_lectivo,
    Asignaturas.fecha_eliminacion.is_(None),
  )
  if excluir_id is not None:
    statement = statement.where(Asignaturas.id != excluir_id)
  if session.exec(statement).first():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Ya existe una asignatura activa en este grado con ese nombre",
    )


def _asignatura_dto(
  asignatura: Asignaturas,
  session: Session,
  docentes: list[PeticionDocente] | None = None,
) -> PeticionAsignatura:
  grado = asignatura.grado
  return PeticionAsignatura(
    id=asignatura.id,
    id_grado=asignatura.id_grado,
    periodo_lectivo=asignatura.periodo_lectivo,
    nombre=asignatura.nombre,
    grado_numero=grado.numero if grado else None,
    grado_nombre=grado.nombre if grado else None,
    nivel=grado.nivel if grado else None,
    docentes=(
      _obtener_docentes_vinculados(session, asignatura.id)
      if docentes is None
      else docentes
    ),
  )


@router.get("/", response_model=RespuestaPaginada[PeticionAsignatura])
def listar_asignaturas(
  paginacion: Paginacion = Depends(),
  nivel: NivelEducativo | None = None,
  id_grado: int | None = None,
  periodo_lectivo: int | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  """Devuelve una página de asignaturas activas."""
  consulta = filtro_activos(select(Asignaturas), Asignaturas)
  consulta = consulta.join(Grados, Asignaturas.id_grado == Grados.id)

  nivel = resolver_nivel(usuario_actual, nivel)
  periodo_lectivo = periodo_lectivo_efectivo(session, periodo_lectivo)
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)
  if id_grado is not None:
    consulta = consulta.where(Asignaturas.id_grado == id_grado)
  if periodo_lectivo is not None:
    consulta = consulta.where(Asignaturas.periodo_lectivo == periodo_lectivo)

  consulta = consulta.options(selectinload(Asignaturas.grado))
  items, total = paginar(session, consulta, paginacion)

  por_asignatura = _mapa_docentes_vinculados(
    session, [a.id for a in items if a.id is not None]
  )
  return construir_pagina(
    [_asignatura_dto(a, session, por_asignatura.get(a.id, [])) for a in items],
    total,
    paginacion,
  )


@router.get("/{asignatura_id}", response_model=PeticionAsignatura)
def obtener_asignatura(
  asignatura_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  """Devuelve una asignatura activa por su identificador."""
  asignatura = _obtener_asignatura_activa(session, asignatura_id)
  validar_acceso_nivel(usuario_actual, asignatura.grado.nivel)
  return _asignatura_dto(asignatura, session)


@router.post(
  "/", response_model=PeticionAsignatura, status_code=status.HTTP_201_CREATED
)
def registrar_asignatura(
  asignatura_in: CrearAsignatura,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  """Registra una asignatura de liceo."""
  grado = _validar_grado_liceo(session, asignatura_in.id_grado)
  if asignatura_in.periodo_lectivo is not None:
    periodo = _validar_periodo(session, asignatura_in.periodo_lectivo)
  else:
    periodo = _obtener_periodo_activo(session)
  _validar_duplicado_asignatura(
    session, asignatura_in.id_grado, asignatura_in.nombre, periodo.anio
  )

  nueva_asignatura = Asignaturas(
    id_grado=asignatura_in.id_grado,
    nombre=asignatura_in.nombre,
    periodo_lectivo=periodo.anio,
  )

  session.add(nueva_asignatura)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.asignaturas,
    "CREAR",
    f"Se registró la asignatura '{nueva_asignatura.nombre}' en {grado.nombre}.",
  )

  session.commit()
  session.refresh(nueva_asignatura)

  return _asignatura_dto(nueva_asignatura, session)


@router.put("/{asignatura_id}", response_model=PeticionAsignatura)
def actualizar_asignatura(
  asignatura_id: int,
  asignatura_in: ActualizarAsignatura,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  """Actualiza una asignatura activa."""
  asignatura_db = _obtener_asignatura_activa(session, asignatura_id)
  datos_actualizar = asignatura_in.model_dump(exclude_unset=True, exclude_none=True)

  if "periodo_lectivo" in datos_actualizar:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=(
        "El periodo lectivo de una asignatura no puede cambiar después del"
        " registro; se crea una asignatura nueva en el nuevo periodo."
      ),
    )

  if not datos_actualizar:
    return _asignatura_dto(asignatura_db, session)

  nuevo_grado_id = datos_actualizar.get("id_grado", asignatura_db.id_grado)
  if "id_grado" in datos_actualizar and nuevo_grado_id != asignatura_db.id_grado:
    _validar_grado_liceo(session, nuevo_grado_id)
    _validar_duplicado_asignatura(
      session,
      nuevo_grado_id,
      datos_actualizar.get("nombre", asignatura_db.nombre),
      periodo_lectivo=asignatura_db.periodo_lectivo,
      excluir_id=asignatura_id,
    )
    if session.exec(
      select(Horarios).where(
        Horarios.id_asignatura == asignatura_id,
        Horarios.fecha_eliminacion.is_(None),
      )
    ).first():
      raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="La asignatura tiene horarios activos",
      )

  if (
    "nombre" in datos_actualizar and datos_actualizar["nombre"] != asignatura_db.nombre
  ):
    _validar_duplicado_asignatura(
      session,
      asignatura_db.id_grado,
      datos_actualizar["nombre"],
      periodo_lectivo=asignatura_db.periodo_lectivo,
      excluir_id=asignatura_id,
    )

  for campo, valor in datos_actualizar.items():
    setattr(asignatura_db, campo, valor)

  session.add(asignatura_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.asignaturas,
    "ACTUALIZAR",
    f"Se actualizó la asignatura '{asignatura_db.nombre}'.",
  )

  session.commit()
  session.refresh(asignatura_db)

  return _asignatura_dto(asignatura_db, session)


@router.delete("/{asignatura_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asignatura(
  asignatura_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  """Marca una asignatura como eliminada."""
  asignatura_db = _obtener_asignatura_activa(session, asignatura_id)

  if session.exec(
    select(Horarios).where(
      Horarios.id_asignatura == asignatura_id,
      Horarios.fecha_eliminacion.is_(None),
    )
  ).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="La asignatura tiene horarios activos",
    )
  if session.exec(
    select(AsignaturasDocentes).where(
      AsignaturasDocentes.id_asignatura == asignatura_id,
      AsignaturasDocentes.fecha_eliminacion.is_(None),
    )
  ).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="La asignatura tiene vinculaciones activas con docentes",
    )

  marcar_eliminado(session, asignatura_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.asignaturas,
    "ELIMINAR",
    f"Se dio de baja la asignatura '{asignatura_db.nombre}'.",
  )

  session.commit()


@router.get("/{asignatura_id}/docentes", response_model=list[PeticionDocente])
def listar_docentes_asignatura(
  asignatura_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  """Devuelve los docentes vinculados a una asignatura."""
  asignatura = _obtener_asignatura_activa(session, asignatura_id)
  validar_acceso_nivel(usuario_actual, asignatura.grado.nivel)
  return _obtener_docentes_vinculados(session, asignatura_id)


@router.post("/{asignatura_id}/docentes/{docente_id}")
def vincular_docente(
  asignatura_id: int,
  docente_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  """Vincula un docente a una asignatura."""
  asignatura = _obtener_asignatura_activa(session, asignatura_id)
  docente = _obtener_docente_activo(session, docente_id)

  if docente.nivel != NivelEducativo.liceo:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Solo se pueden vincular docentes de liceo a asignaturas",
    )

  if session.exec(
    select(AsignaturasDocentes).where(
      AsignaturasDocentes.id_asignatura == asignatura.id,
      AsignaturasDocentes.id_docente == docente.id,
      AsignaturasDocentes.fecha_eliminacion.is_(None),
    )
  ).first():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El docente ya está vinculado a esta asignatura",
    )

  session.add(AsignaturasDocentes(id_asignatura=asignatura.id, id_docente=docente.id))
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.asignaturas,
    "VINCULAR DOCENTE",
    (
      f"Se vinculó al docente '{nombre_completo(docente)}' "
      f"con la asignatura '{asignatura.nombre}'."
    ),
  )

  session.commit()

  return {
    "mensaje": (
      f"Docente '{nombre_completo(docente)}' vinculado "
      f"a la asignatura '{asignatura.nombre}'"
    )
  }


@router.delete(
  "/{asignatura_id}/docentes/{docente_id}",
  status_code=status.HTTP_204_NO_CONTENT,
)
def desvincular_docente(
  asignatura_id: int,
  docente_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  """Desvincula un docente de una asignatura."""
  asignatura = _obtener_asignatura_activa(session, asignatura_id)
  docente = _obtener_docente_activo(session, docente_id)
  link = session.exec(
    select(AsignaturasDocentes).where(
      AsignaturasDocentes.id_asignatura == asignatura_id,
      AsignaturasDocentes.id_docente == docente_id,
      AsignaturasDocentes.fecha_eliminacion.is_(None),
    )
  ).first()

  if not link:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="El docente no está vinculado a esta asignatura",
    )

  marcar_eliminado(session, link)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.asignaturas,
    "DESVINCULAR DOCENTE",
    (
      f"Se desvinculó el docente '{nombre_completo(docente)}' "
      f"de la asignatura '{asignatura.nombre}'."
    ),
  )

  session.commit()

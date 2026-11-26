from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, status
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
  BloquesHorarios,
  Docentes,
  Estudiantes,
  Grados,
  Horarios,
  PeriodosLectivos,
  Secciones,
  Usuarios,
)
from app.models.enums import (
  ModuloAuditoria,
  NivelEducativo,
  RolesUsuario,
  TipoBloqueHorario,
)
from app.models.schemas import (
  ActualizarHorario,
  CrearHorario,
  PeticionConsultaHorario,
  PeticionHorario,
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

router = APIRouter(prefix="/horarios", tags=["Horarios"])
requerir_admin = requerir_roles(RolesUsuario.administrador)


def _obtener_activo(session: Session, modelo, registro_id: int, mensaje: str):
  registro = session.get(modelo, registro_id)

  if not registro or registro.fecha_eliminacion is not None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=mensaje)

  return registro


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


def _validar_colision_seccion(
  session: Session,
  id_seccion: int,
  id_bloque: int,
  periodo_lectivo: int,
  dia_semana: int,
  excluir_id: int | None = None,
) -> None:
  consulta = select(Horarios).where(
    Horarios.id_seccion == id_seccion,
    Horarios.id_bloque == id_bloque,
    Horarios.periodo_lectivo == periodo_lectivo,
    Horarios.dia_semana == dia_semana,
    Horarios.fecha_eliminacion.is_(None),
  )
  if excluir_id is not None:
    consulta = consulta.where(Horarios.id != excluir_id)
  if session.exec(consulta).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="La sección ya tiene una clase en ese bloque y día",
    )


def _validar_colision_docente(
  session: Session,
  id_docente: int,
  id_bloque: int,
  periodo_lectivo: int,
  dia_semana: int,
  excluir_id: int | None = None,
) -> None:
  consulta = select(Horarios).where(
    Horarios.id_docente == id_docente,
    Horarios.id_bloque == id_bloque,
    Horarios.periodo_lectivo == periodo_lectivo,
    Horarios.dia_semana == dia_semana,
    Horarios.fecha_eliminacion.is_(None),
  )
  if excluir_id is not None:
    consulta = consulta.where(Horarios.id != excluir_id)
  if session.exec(consulta).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="El docente ya tiene una clase en ese bloque y día",
    )


def _validar_docente_titular_otra_seccion(
  session: Session,
  id_docente: int,
  id_seccion: int,
  periodo_lectivo: int,
) -> None:
  """El titular está ocupado con su sección: no puede dar clase en otra."""
  titularidades = session.exec(
    select(Secciones).where(
      Secciones.id_docente_titular == id_docente,
      Secciones.periodo_lectivo == periodo_lectivo,
      Secciones.fecha_eliminacion.is_(None),
    )
  ).all()
  if any(seccion.id != id_seccion for seccion in titularidades):
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail=(
        "El docente es titular de otra sección y no puede impartir clases fuera de ella"
      ),
    )


def _validar_horario(
  session: Session,
  id_seccion: int,
  id_bloque: int,
  id_asignatura: int,
  id_docente: int,
  periodo_lectivo: int,
  dia_semana: int,
  excluir_id: int | None = None,
) -> tuple[Secciones, BloquesHorarios, Asignaturas, Docentes]:
  seccion = _obtener_activo(session, Secciones, id_seccion, "Sección no encontrada")
  grado = seccion.grado

  if grado.nivel != NivelEducativo.liceo:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Los horarios solo aplican a secciones de liceo",
    )

  if seccion.periodo_lectivo != periodo_lectivo:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="La sección pertenece a otro período lectivo",
    )

  bloque = _obtener_activo(session, BloquesHorarios, id_bloque, "Bloque no encontrado")
  if bloque.tipo != TipoBloqueHorario.academico:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Solo se pueden programar bloques académicos",
    )

  asignatura = _obtener_activo(
    session, Asignaturas, id_asignatura, "Asignatura no encontrada"
  )
  if asignatura.id_grado != seccion.id_grado:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="La asignatura no pertenece al grado de la sección",
    )
  if asignatura.periodo_lectivo != periodo_lectivo:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="La asignatura no pertenece al periodo lectivo de la sección",
    )

  docente = _obtener_activo(session, Docentes, id_docente, "Docente no encontrado")
  if docente.nivel != NivelEducativo.liceo:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Solo se pueden asignar docentes de liceo",
    )

  _validar_docente_titular_otra_seccion(
    session, id_docente, id_seccion, periodo_lectivo
  )

  vinculado = session.exec(
    select(AsignaturasDocentes).where(
      AsignaturasDocentes.id_asignatura == id_asignatura,
      AsignaturasDocentes.id_docente == id_docente,
      AsignaturasDocentes.fecha_eliminacion.is_(None),
    )
  ).first()
  if not vinculado:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El docente no está vinculado a la asignatura",
    )

  _validar_colision_seccion(
    session,
    id_seccion,
    id_bloque,
    periodo_lectivo,
    dia_semana,
    excluir_id,
  )
  _validar_colision_docente(
    session,
    id_docente,
    id_bloque,
    periodo_lectivo,
    dia_semana,
    excluir_id,
  )

  return seccion, bloque, asignatura, docente


def _horario_dto(horario: Horarios) -> PeticionHorario:
  seccion = horario.seccion
  grado = seccion.grado
  bloque = horario.bloque

  return PeticionHorario(
    id=horario.id,
    id_seccion=horario.id_seccion,
    id_bloque=horario.id_bloque,
    id_asignatura=horario.id_asignatura,
    id_docente=horario.id_docente,
    periodo_lectivo=horario.periodo_lectivo,
    dia_semana=horario.dia_semana,
    seccion=f"{grado.nombre} {seccion.letra}",
    grado=grado.nombre,
    nivel=grado.nivel,
    bloque=bloque.nombre,
    bloque_orden=bloque.orden,
    hora_inicio=bloque.hora_inicio,
    hora_fin=bloque.hora_fin,
    asignatura=horario.asignatura.nombre,
    docente=nombre_completo(horario.docente),
  )


@router.get("/registros/", response_model=RespuestaPaginada[PeticionHorario])
def listar_horarios(
  id_seccion: int | None = None,
  id_grado: int | None = None,
  id_asignatura: int | None = None,
  id_docente: int | None = None,
  id_bloque: int | None = None,
  periodo_lectivo: int | None = None,
  dia_semana: int | None = None,
  nivel: NivelEducativo | None = None,
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  consulta = filtro_activos(select(Horarios), Horarios)
  consulta = consulta.join(Secciones, Horarios.id_seccion == Secciones.id)
  consulta = consulta.join(Grados, Secciones.id_grado == Grados.id)
  consulta = consulta.join(BloquesHorarios, Horarios.id_bloque == BloquesHorarios.id)

  nivel = resolver_nivel(usuario_actual, nivel)
  periodo_lectivo = periodo_lectivo_efectivo(session, periodo_lectivo)
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)
  if id_seccion is not None:
    consulta = consulta.where(Horarios.id_seccion == id_seccion)
  if id_grado is not None:
    consulta = consulta.where(Secciones.id_grado == id_grado)
  if id_asignatura is not None:
    consulta = consulta.where(Horarios.id_asignatura == id_asignatura)
  if id_docente is not None:
    consulta = consulta.where(Horarios.id_docente == id_docente)
  if id_bloque is not None:
    consulta = consulta.where(Horarios.id_bloque == id_bloque)
  if periodo_lectivo is not None:
    consulta = consulta.where(Horarios.periodo_lectivo == periodo_lectivo)
  if dia_semana is not None:
    consulta = consulta.where(Horarios.dia_semana == dia_semana)

  consulta = consulta.order_by(Horarios.dia_semana, BloquesHorarios.orden)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(
    [_horario_dto(horario) for horario in items], total, paginacion
  )


@router.get("/registros/{horario_id}", response_model=PeticionHorario)
def obtener_horario(
  horario_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  horario = _obtener_activo(session, Horarios, horario_id, "Horario no encontrado")
  validar_acceso_nivel(usuario_actual, horario.seccion.grado.nivel)

  return _horario_dto(horario)


@router.post(
  "/registros/",
  response_model=PeticionHorario,
  status_code=status.HTTP_201_CREATED,
)
def registrar_horario(
  horario_in: CrearHorario,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  _validar_periodo(session, horario_in.periodo_lectivo)
  seccion, bloque, asignatura, docente = _validar_horario(
    session,
    horario_in.id_seccion,
    horario_in.id_bloque,
    horario_in.id_asignatura,
    horario_in.id_docente,
    horario_in.periodo_lectivo,
    horario_in.dia_semana,
  )

  nuevo_horario = Horarios(
    id_seccion=horario_in.id_seccion,
    id_bloque=horario_in.id_bloque,
    id_asignatura=horario_in.id_asignatura,
    id_docente=horario_in.id_docente,
    periodo_lectivo=horario_in.periodo_lectivo,
    dia_semana=horario_in.dia_semana,
  )

  session.add(nuevo_horario)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.horarios,
    "CREAR",
    (
      f"Se programó '{asignatura.nombre}' para {seccion.grado.nombre} "
      f"{seccion.letra} el día {nuevo_horario.dia_semana} en "
      f"{bloque.nombre} con el docente '{nombre_completo(docente)}'."
    ),
  )

  session.commit()
  session.refresh(nuevo_horario)

  return _horario_dto(nuevo_horario)


@router.put("/registros/{horario_id}", response_model=PeticionHorario)
def actualizar_horario(
  horario_id: int,
  horario_in: ActualizarHorario,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  horario_db = _obtener_activo(session, Horarios, horario_id, "Horario no encontrado")
  datos_actualizar = horario_in.model_dump(exclude_unset=True, exclude_none=True)

  if not datos_actualizar:
    return _horario_dto(horario_db)

  valores_finales = {
    "id_seccion": datos_actualizar.get("id_seccion", horario_db.id_seccion),
    "id_bloque": datos_actualizar.get("id_bloque", horario_db.id_bloque),
    "id_asignatura": datos_actualizar.get("id_asignatura", horario_db.id_asignatura),
    "id_docente": datos_actualizar.get("id_docente", horario_db.id_docente),
    "periodo_lectivo": datos_actualizar.get(
      "periodo_lectivo", horario_db.periodo_lectivo
    ),
    "dia_semana": datos_actualizar.get("dia_semana", horario_db.dia_semana),
  }

  _validar_periodo(session, valores_finales["periodo_lectivo"])
  seccion, bloque, asignatura, docente = _validar_horario(
    session,
    valores_finales["id_seccion"],
    valores_finales["id_bloque"],
    valores_finales["id_asignatura"],
    valores_finales["id_docente"],
    valores_finales["periodo_lectivo"],
    valores_finales["dia_semana"],
    excluir_id=horario_id,
  )

  for campo, valor in valores_finales.items():
    setattr(horario_db, campo, valor)

  session.add(horario_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.horarios,
    "ACTUALIZAR",
    (
      f"Se actualizó el horario de '{asignatura.nombre}' para "
      f"{seccion.grado.nombre} {seccion.letra} el día "
      f"{horario_db.dia_semana} en {bloque.nombre} con el docente "
      f"'{nombre_completo(docente)}'."
    ),
  )

  session.commit()
  session.refresh(horario_db)

  return _horario_dto(horario_db)


@router.delete("/registros/{horario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_horario(
  horario_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  horario_db = _obtener_activo(session, Horarios, horario_id, "Horario no encontrado")

  marcar_eliminado(session, horario_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.horarios,
    "ELIMINAR",
    (
      f"Se dio de baja el horario #{horario_db.id} de "
      f"{horario_db.seccion.grado.nombre} {horario_db.seccion.letra}."
    ),
  )

  session.commit()


@router.get("/", response_model=PeticionConsultaHorario)
def consultar_horario_estudiante(
  id_estudiante: int,
  fecha: date,
  id_bloque: int | None = None,
  hora: time | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  estudiante = _obtener_activo(
    session, Estudiantes, id_estudiante, "Estudiante no encontrado"
  )
  seccion = estudiante.seccion
  validar_acceso_nivel(usuario_actual, seccion.grado.nivel)

  if fecha.year != seccion.periodo_lectivo:
    return PeticionConsultaHorario(encontrado=False)

  dia_semana = fecha.isoweekday()
  if dia_semana > 5:
    return PeticionConsultaHorario(encontrado=False)

  if id_bloque is None and hora is None:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Indica id_bloque o hora para consultar el horario",
    )

  if id_bloque is None:
    bloque = session.exec(
      select(BloquesHorarios).where(
        BloquesHorarios.tipo == TipoBloqueHorario.academico,
        BloquesHorarios.hora_inicio <= hora,
        BloquesHorarios.hora_fin > hora,
        BloquesHorarios.fecha_eliminacion.is_(None),
      )
    ).first()
    if bloque is None:
      return PeticionConsultaHorario(encontrado=False)
  else:
    bloque = _obtener_activo(
      session, BloquesHorarios, id_bloque, "Bloque no encontrado"
    )
    if bloque.tipo != TipoBloqueHorario.academico:
      return PeticionConsultaHorario(encontrado=False)

  horario = session.exec(
    select(Horarios).where(
      Horarios.id_seccion == seccion.id,
      Horarios.id_bloque == bloque.id,
      Horarios.periodo_lectivo == seccion.periodo_lectivo,
      Horarios.dia_semana == dia_semana,
      Horarios.fecha_eliminacion.is_(None),
    )
  ).first()

  if horario is None:
    return PeticionConsultaHorario(encontrado=False)

  return PeticionConsultaHorario(
    encontrado=True,
    id_horario=horario.id,
    id_bloque=bloque.id,
    id_asignatura=horario.id_asignatura,
    id_docente=horario.id_docente,
    asignatura=horario.asignatura.nombre,
    docente=nombre_completo(horario.docente),
    bloque=bloque.nombre,
    hora_inicio=bloque.hora_inicio,
    hora_fin=bloque.hora_fin,
  )

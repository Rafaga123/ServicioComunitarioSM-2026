"""Gestiona el catálogo de bloques de la jornada institucional."""

from datetime import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  filtro_activos,
  paginar,
)
from app.models.db import BloquesHorarios, Horarios, Usuarios
from app.models.enums import (
  ModuloAuditoria,
  RolesUsuario,
  TipoBloqueHorario,
)
from app.models.schemas import (
  ActualizarBloqueHorario,
  CrearBloqueHorario,
  PeticionBloqueHorario,
  validar_bloque_horario,
)
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.security import obtener_usuario_actual, requerir_roles
from app.utils.soft_delete import marcar_eliminado

router = APIRouter(prefix="/bloques-horarios", tags=["Bloques Horarios"])
requerir_admin = requerir_roles(RolesUsuario.administrador)

INICIO_JORNADA = time(7, 0)
FIN_JORNADA = time(12, 40)


def _obtener_bloque_activo(session: Session, bloque_id: int) -> BloquesHorarios:
  bloque = session.get(BloquesHorarios, bloque_id)

  if not bloque or bloque.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Bloque no encontrado"
    )

  return bloque


def _validar_orden_unico(
  session: Session,
  orden: int,
  excluir_id: int | None = None,
) -> None:
  statement = select(BloquesHorarios).where(
    BloquesHorarios.orden == orden,
    BloquesHorarios.fecha_eliminacion.is_(None),
  )
  if excluir_id is not None:
    statement = statement.where(BloquesHorarios.id != excluir_id)
  if session.exec(statement).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="Ya existe un bloque activo con ese orden",
    )


def _validar_rango(hora_inicio: time, hora_fin: time) -> None:
  if hora_fin <= hora_inicio:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="La hora de fin debe ser posterior a la hora de inicio",
    )
  if hora_inicio < INICIO_JORNADA or hora_fin > FIN_JORNADA:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El bloque debe estar dentro del tramo 07:00–12:40",
    )


def _validar_sin_solapado(
  session: Session,
  hora_inicio: time,
  hora_fin: time,
  excluir_id: int | None = None,
) -> None:
  consulta = select(BloquesHorarios).where(
    BloquesHorarios.hora_inicio < hora_fin,
    BloquesHorarios.hora_fin > hora_inicio,
    BloquesHorarios.fecha_eliminacion.is_(None),
  )
  if excluir_id is not None:
    consulta = consulta.where(BloquesHorarios.id != excluir_id)
  if session.exec(consulta).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="El bloque se solapa con otro bloque activo",
    )


def _bloque_dto(bloque: BloquesHorarios) -> PeticionBloqueHorario:
  return PeticionBloqueHorario(
    id=bloque.id,
    orden=bloque.orden,
    numero=bloque.numero,
    nombre=bloque.nombre,
    tipo=bloque.tipo,
    hora_inicio=bloque.hora_inicio,
    hora_fin=bloque.hora_fin,
  )


@router.get("/", response_model=RespuestaPaginada[PeticionBloqueHorario])
def listar_bloques(
  paginacion: Paginacion = Depends(),
  tipo: TipoBloqueHorario | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  """Devuelve una página de bloques horarios activos."""
  consulta = filtro_activos(select(BloquesHorarios), BloquesHorarios)
  if tipo is not None:
    consulta = consulta.where(BloquesHorarios.tipo == tipo)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina([_bloque_dto(b) for b in items], total, paginacion)


@router.get("/{bloque_id}", response_model=PeticionBloqueHorario)
def obtener_bloque(
  bloque_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  """Devuelve un bloque horario activo por su identificador."""
  return _bloque_dto(_obtener_bloque_activo(session, bloque_id))


@router.post(
  "/", response_model=PeticionBloqueHorario, status_code=status.HTTP_201_CREATED
)
def registrar_bloque(
  bloque_in: CrearBloqueHorario,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  """Registra un bloque horario sin solapes."""
  _validar_orden_unico(session, bloque_in.orden)
  _validar_rango(bloque_in.hora_inicio, bloque_in.hora_fin)
  _validar_sin_solapado(session, bloque_in.hora_inicio, bloque_in.hora_fin)

  nuevo_bloque = BloquesHorarios(
    orden=bloque_in.orden,
    numero=bloque_in.numero,
    nombre=bloque_in.nombre,
    tipo=bloque_in.tipo,
    hora_inicio=bloque_in.hora_inicio,
    hora_fin=bloque_in.hora_fin,
  )
  session.add(nuevo_bloque)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.bloques_horarios,
    "CREAR",
    f"Se creó el tramo {nuevo_bloque.nombre}.",
  )
  session.commit()
  session.refresh(nuevo_bloque)

  return _bloque_dto(nuevo_bloque)


@router.put("/{bloque_id}", response_model=PeticionBloqueHorario)
def actualizar_bloque(
  bloque_id: int,
  bloque_in: ActualizarBloqueHorario,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  """Actualiza un bloque horario activo."""
  bloque_db = _obtener_bloque_activo(session, bloque_id)
  datos_actualizar = bloque_in.model_dump(exclude_unset=True)
  datos_actualizar = {
    campo: valor
    for campo, valor in datos_actualizar.items()
    if valor is not None or campo == "numero"
  }

  if not datos_actualizar:
    return _bloque_dto(bloque_db)

  nuevo_orden = datos_actualizar.get("orden", bloque_db.orden)
  _validar_orden_unico(session, nuevo_orden, excluir_id=bloque_id)

  nuevo_tipo = datos_actualizar.get("tipo", bloque_db.tipo)
  nuevo_numero = datos_actualizar.get("numero", bloque_db.numero)
  nuevo_hora_inicio = datos_actualizar.get("hora_inicio", bloque_db.hora_inicio)
  nuevo_hora_fin = datos_actualizar.get("hora_fin", bloque_db.hora_fin)

  try:
    validar_bloque_horario(
      nuevo_tipo, nuevo_numero, nuevo_hora_inicio, nuevo_hora_fin
    )
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
    ) from exc

  _validar_rango(nuevo_hora_inicio, nuevo_hora_fin)
  _validar_sin_solapado(
    session, nuevo_hora_inicio, nuevo_hora_fin, excluir_id=bloque_id
  )

  for campo, valor in datos_actualizar.items():
    setattr(bloque_db, campo, valor)
  session.add(bloque_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.bloques_horarios,
    "ACTUALIZAR",
    f"Se actualizó el tramo {bloque_db.nombre}.",
  )
  session.commit()
  session.refresh(bloque_db)

  return _bloque_dto(bloque_db)


@router.delete("/{bloque_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_bloque(
  bloque_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  """Marca un bloque horario como eliminado."""
  bloque_db = _obtener_bloque_activo(session, bloque_id)

  if session.exec(
    select(Horarios).where(
      Horarios.id_bloque == bloque_id,
      Horarios.fecha_eliminacion.is_(None),
    )
  ).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="El bloque tiene horarios activos",
    )

  marcar_eliminado(session, bloque_db)
  session.flush()
  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.bloques_horarios,
    "ELIMINAR",
    f"Se dio de baja el tramo {bloque_db.nombre}.",
  )
  session.commit()

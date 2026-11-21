from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  filtro_activos,
  paginar,
)
from app.models.db import Grados, Usuarios
from app.models.enums import ModuloAuditoria, RolesUsuario
from app.models.schemas import ActualizarGrado, CrearGrado, PeticionGrado
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.security import obtener_usuario_actual, requerir_roles
from app.utils.soft_delete import marcar_eliminado

router = APIRouter(prefix="/grados", tags=["Grados"])
requerir_admin = requerir_roles(RolesUsuario.administrador)


def _obtener_grado_activo(session: Session, grado_id: int) -> Grados:
  grado = session.get(Grados, grado_id)

  if not grado or grado.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Grado no encontrado",
    )

  return grado


def _validar_duplicado(
  session: Session,
  grado: str,
  seccion: str,
  excluir_id: int | None = None,
) -> None:
  # Un grado se identifica por su número y sección. Solo se comparan los
  # activos para permitir reutilizar una sección después de una baja.
  statement = select(Grados).where(
    Grados.grado == grado,
    Grados.seccion == seccion,
    Grados.fecha_eliminacion.is_(None),
  )

  if excluir_id is not None:
    statement = statement.where(Grados.id != excluir_id)

  if session.exec(statement).first():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Ya existe un grado activo con esa sección",
    )


@router.post("/", response_model=PeticionGrado, status_code=status.HTTP_201_CREATED)
def registrar_grado(
  grado_in: CrearGrado,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  _validar_duplicado(session, grado_in.grado, grado_in.seccion)

  nuevo_grado = Grados(grado=grado_in.grado, seccion=grado_in.seccion)

  session.add(nuevo_grado)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.grados,
    "CREAR",
    f"Se registró el grado {nuevo_grado.grado} \"{nuevo_grado.seccion}\".",
  )

  session.commit()
  session.refresh(nuevo_grado)

  return nuevo_grado


@router.get("/", response_model=RespuestaPaginada[PeticionGrado])
def listar_grados(
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  consulta = filtro_activos(select(Grados), Grados)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(items, total, paginacion)


@router.get("/{grado_id}", response_model=PeticionGrado)
def obtener_grado(
  grado_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  return _obtener_grado_activo(session, grado_id)


@router.put("/{grado_id}", response_model=PeticionGrado)
def actualizar_grado(
  grado_id: int,
  grado_in: ActualizarGrado,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  grado_db = _obtener_grado_activo(session, grado_id)
  datos_actualizar = grado_in.model_dump(exclude_unset=True, exclude_none=True)

  if not datos_actualizar:
    return grado_db

  nuevo_grado = datos_actualizar.get("grado", grado_db.grado)
  nueva_seccion = datos_actualizar.get("seccion", grado_db.seccion)

  if (nuevo_grado, nueva_seccion) != (grado_db.grado, grado_db.seccion):
    _validar_duplicado(
      session,
      nuevo_grado,
      nueva_seccion,
      excluir_id=grado_id,
    )

  cambios = {
    campo: valor
    for campo, valor in datos_actualizar.items()
    if getattr(grado_db, campo) != valor
  }

  if not cambios:
    return grado_db

  for campo, valor in cambios.items():
    setattr(grado_db, campo, valor)

  session.add(grado_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.grados,
    "ACTUALIZAR",
    f"Se actualizó el grado {grado_db.grado} \"{grado_db.seccion}\".",
  )

  session.commit()
  session.refresh(grado_db)

  return grado_db


@router.delete("/{grado_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_grado(
  grado_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  grado_db = _obtener_grado_activo(session, grado_id)

  marcar_eliminado(session, grado_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.grados,
    "ELIMINAR",
    f"Se dio de baja el grado {grado_db.grado} \"{grado_db.seccion}\".",
  )

  session.commit()

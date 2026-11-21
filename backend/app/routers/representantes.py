from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  filtro_activos,
  paginar,
)
from app.models.db import Estudiantes, Representantes, Usuarios
from app.models.enums import ModuloAuditoria, RolesUsuario
from app.models.schemas import (
  ActualizarRepresentante,
  CrearRepresentante,
  PeticionRepresentante,
)
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.nombres import nombre_completo
from app.utils.security import obtener_usuario_actual, requerir_roles
from app.utils.soft_delete import marcar_eliminado

router = APIRouter(prefix="/representantes", tags=["Representantes"])
requerir_admin = requerir_roles(RolesUsuario.administrador)


def _obtener_representante_activo(
  session: Session, representante_id: int
) -> Representantes:
  representante = session.get(Representantes, representante_id)

  if not representante or representante.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Representante no encontrado",
    )

  return representante


def _obtener_estudiante_activo(session: Session, estudiante_id: int) -> Estudiantes:
  estudiante = session.get(Estudiantes, estudiante_id)

  if not estudiante or estudiante.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Estudiante no encontrado",
    )

  return estudiante


@router.post(
  "/", response_model=PeticionRepresentante, status_code=status.HTTP_201_CREATED
)
def registrar_representante(
  rep_in: CrearRepresentante,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  nuevo_rep = Representantes(
    primer_nombre=rep_in.primer_nombre,
    segundo_nombre=rep_in.segundo_nombre,
    primer_apellido=rep_in.primer_apellido,
    segundo_apellido=rep_in.segundo_apellido,
    telefono=rep_in.telefono,
  )

  session.add(nuevo_rep)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.representantes,
    "CREAR",
    f"Se registró al representante '{nombre_completo(nuevo_rep)}'.",
  )

  session.commit()
  session.refresh(nuevo_rep)

  return nuevo_rep


@router.get("/", response_model=RespuestaPaginada[PeticionRepresentante])
def listar_representantes(
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  consulta = filtro_activos(select(Representantes), Representantes)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(items, total, paginacion)


@router.get("/{representante_id}", response_model=PeticionRepresentante)
def obtener_representante(
  representante_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  return _obtener_representante_activo(session, representante_id)


@router.put("/{representante_id}", response_model=PeticionRepresentante)
def actualizar_representante(
  representante_id: int,
  rep_in: ActualizarRepresentante,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  representante_db = _obtener_representante_activo(session, representante_id)
  datos_actualizar = rep_in.model_dump(exclude_unset=True, exclude_none=True)

  cambios = {
    campo: valor
    for campo, valor in datos_actualizar.items()
    if getattr(representante_db, campo) != valor
  }

  if not cambios:
    return representante_db

  for campo, valor in cambios.items():
    setattr(representante_db, campo, valor)

  session.add(representante_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.representantes,
    "ACTUALIZAR",
    f"Se actualizaron los datos del representante "
    f"'{nombre_completo(representante_db)}'.",
  )

  session.commit()
  session.refresh(representante_db)

  return representante_db


@router.delete("/{representante_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_representante(
  representante_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  representante_db = _obtener_representante_activo(session, representante_id)

  marcar_eliminado(session, representante_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.representantes,
    "ELIMINAR",
    f"Se dio de baja al representante '{nombre_completo(representante_db)}'.",
  )

  session.commit()


@router.post(
  "/{representante_id}/vincular_estudiante/{estudiante_id}",
  status_code=status.HTTP_200_OK,
)
def vincular_estudiante_representante(
  representante_id: int,
  estudiante_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  representante = _obtener_representante_activo(session, representante_id)
  estudiante = _obtener_estudiante_activo(session, estudiante_id)

  if representante in estudiante.representantes:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El representante ya está vinculado a este estudiante",
    )

  estudiante.representantes.append(representante)

  session.add(estudiante)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.representantes,
    "VINCULAR_ESTUDIANTE",
    f"Se vinculó al representante '{nombre_completo(representante)}' "
    f"con el estudiante '{estudiante.primer_nombre} "
    f"{estudiante.primer_apellido}'.",
  )

  session.commit()

  return {
    "mensaje": (
      f"Representante {nombre_completo(representante)} vinculado exitosamente "
      f"al estudiante {estudiante.primer_nombre}"
    )
  }


@router.delete(
  "/{representante_id}/vincular_estudiante/{estudiante_id}",
  status_code=status.HTTP_204_NO_CONTENT,
)
def desvincular_estudiante_representante(
  representante_id: int,
  estudiante_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  estudiante = _obtener_estudiante_activo(session, estudiante_id)
  representante = next(
    (rep for rep in estudiante.representantes if rep.id == representante_id),
    None,
  )

  if representante is None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="El representante no está vinculado a este estudiante",
    )

  estudiante.representantes.remove(representante)

  session.add(estudiante)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.representantes,
    "DESVINCULAR_ESTUDIANTE",
    f"Se desvinculó al representante '{nombre_completo(representante)}' "
    f"del estudiante '{estudiante.primer_nombre} "
    f"{estudiante.primer_apellido}'.",
  )

  session.commit()

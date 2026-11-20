from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  filtro_activos,
  paginar,
)
from app.models.db import Docentes, Usuarios
from app.models.enums import ModuloAuditoria, RolesUsuario
from app.models.schemas import ActualizarDocente, CrearDocente, PeticionDocente
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.security import obtener_usuario_actual, requerir_roles
from app.utils.soft_delete import marcar_eliminado

router = APIRouter(prefix="/docentes", tags=["Docentes"])
requerir_admin = requerir_roles(RolesUsuario.administrador)


def _obtener_docente_activo(session: Session, docente_id: int) -> Docentes:
  docente = session.get(Docentes, docente_id)

  if not docente or docente.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Docente no encontrado"
    )

  return docente


@router.get("/", response_model=RespuestaPaginada[PeticionDocente])
def listar_docentes(
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  consulta = filtro_activos(select(Docentes), Docentes)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(items, total, paginacion)


@router.get("/{docente_id}", response_model=PeticionDocente)
def obtener_docente(
  docente_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  return _obtener_docente_activo(session, docente_id)


@router.post("/", response_model=PeticionDocente, status_code=status.HTTP_201_CREATED)
def registrar_docente(
  docente_in: CrearDocente,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  # La cédula se valida contra todos los registros, incluidos los dados de baja,
  # para no duplicar la identidad de un docente.
  statement = select(Docentes).where(Docentes.cedula == docente_in.cedula)

  if session.exec(statement).first():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Ya existe un docente con esa cédula",
    )

  nuevo_docente = Docentes(
    nombre=docente_in.nombre,
    apellido=docente_in.apellido,
    cedula=docente_in.cedula,
  )

  session.add(nuevo_docente)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.docentes,
    "CREAR",
    (
      f"Se registró al docente '{nuevo_docente.nombre} "
      f"{nuevo_docente.apellido}' con cédula {nuevo_docente.cedula}."
    ),
  )

  session.commit()
  session.refresh(nuevo_docente)

  return nuevo_docente


@router.put("/{docente_id}", response_model=PeticionDocente)
def actualizar_docente(
  docente_id: int,
  docente_in: ActualizarDocente,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  docente_db = _obtener_docente_activo(session, docente_id)
  datos_actualizar = docente_in.model_dump(exclude_unset=True, exclude_none=True)

  if not datos_actualizar:
    return docente_db

  if "cedula" in datos_actualizar and datos_actualizar["cedula"] != docente_db.cedula:
    statement = select(Docentes).where(
      Docentes.cedula == datos_actualizar["cedula"],
      Docentes.id != docente_id,
    )

    if session.exec(statement).first():
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="La nueva cédula ya está registrada en otro docente",
      )

  cambios = {
    campo: valor
    for campo, valor in datos_actualizar.items()
    if getattr(docente_db, campo) != valor
  }

  if not cambios:
    return docente_db

  for campo, valor in cambios.items():
    setattr(docente_db, campo, valor)

  session.add(docente_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.docentes,
    "ACTUALIZAR",
    (
      f"Se actualizaron los datos del docente '{docente_db.nombre} "
      f"{docente_db.apellido}' con cédula {docente_db.cedula}."
    ),
  )

  session.commit()
  session.refresh(docente_db)

  return docente_db


@router.delete("/{docente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_docente(
  docente_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  docente_db = _obtener_docente_activo(session, docente_id)

  marcar_eliminado(session, docente_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.docentes,
    "ELIMINAR",
    (
      f"Se dio de baja al docente '{docente_db.nombre} "
      f"{docente_db.apellido}' con cédula {docente_db.cedula}."
    ),
  )

  session.commit()

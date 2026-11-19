from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  filtro_activos,
  paginar,
)
from app.models.db import Asignaturas, Docentes, Usuarios
from app.models.enums import ModuloAuditoria, RolesUsuario
from app.models.schemas import (
  ActualizarAsignatura,
  CrearAsignatura,
  PeticionAsignatura,
  PeticionDocente,
)
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.security import obtener_usuario_actual, requerir_roles
from app.utils.soft_delete import marcar_eliminado

router = APIRouter(
  prefix="/asignaturas", tags=["Catálogos: Asignaturas"]
)
requerir_admin = requerir_roles(RolesUsuario.administrador)


def _obtener_asignatura_activa(
  session: Session, asignatura_id: int
) -> Asignaturas:
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


@router.get("/", response_model=RespuestaPaginada[PeticionAsignatura])
def listar_asignaturas(
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  consulta = filtro_activos(select(Asignaturas), Asignaturas)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(items, total, paginacion)


@router.get("/{asignatura_id}", response_model=PeticionAsignatura)
def obtener_asignatura(
  asignatura_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  return _obtener_asignatura_activa(session, asignatura_id)


@router.post(
  "/", response_model=PeticionAsignatura, status_code=status.HTTP_201_CREATED
)
def registrar_asignatura(
  asignatura_in: CrearAsignatura,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  statement = select(Asignaturas).where(
    Asignaturas.nombre == asignatura_in.nombre
  )

  if session.exec(statement).first():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Ya existe una asignatura con ese nombre",
    )

  nueva_asignatura = Asignaturas(nombre=asignatura_in.nombre)

  session.add(nueva_asignatura)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.asignaturas,
    "CREAR",
    f"Se registró la asignatura '{nueva_asignatura.nombre}'.",
  )

  session.commit()
  session.refresh(nueva_asignatura)

  return nueva_asignatura


@router.put("/{asignatura_id}", response_model=PeticionAsignatura)
def actualizar_asignatura(
  asignatura_id: int,
  asignatura_in: ActualizarAsignatura,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  asignatura_db = _obtener_asignatura_activa(session, asignatura_id)
  datos_actualizar = asignatura_in.model_dump(
    exclude_unset=True, exclude_none=True
  )

  if not datos_actualizar:
    return asignatura_db

  if (
    "nombre" in datos_actualizar
    and datos_actualizar["nombre"] != asignatura_db.nombre
  ):
    statement = select(Asignaturas).where(
      Asignaturas.nombre == datos_actualizar["nombre"],
      Asignaturas.id != asignatura_id,
    )

    if session.exec(statement).first():
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="La nueva asignatura ya está registrada con otro nombre",
      )

  cambios = {
    campo: valor
    for campo, valor in datos_actualizar.items()
    if getattr(asignatura_db, campo) != valor
  }

  if not cambios:
    return asignatura_db

  for campo, valor in cambios.items():
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

  return asignatura_db


@router.delete("/{asignatura_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asignatura(
  asignatura_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  asignatura_db = _obtener_asignatura_activa(session, asignatura_id)

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


@router.get(
  "/{asignatura_id}/docentes", response_model=list[PeticionDocente]
)
def listar_docentes_asignatura(
  asignatura_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  asignatura = _obtener_asignatura_activa(session, asignatura_id)

  return [
    docente
    for docente in asignatura.docentes
    if docente.fecha_eliminacion is None
  ]


@router.post("/{asignatura_id}/docentes/{docente_id}")
def vincular_docente(
  asignatura_id: int,
  docente_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  asignatura = _obtener_asignatura_activa(session, asignatura_id)
  docente = _obtener_docente_activo(session, docente_id)

  # La relación es muchos-a-muchos; evitamos duplicados antes de guardar.
  if docente in asignatura.docentes:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El docente ya está vinculado a esta asignatura",
    )

  asignatura.docentes.append(docente)

  session.add(asignatura)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.asignaturas,
    "VINCULAR_DOCENTE",
    (
      f"Se vinculó al docente '{docente.nombre} {docente.apellido}' "
      f"con la asignatura '{asignatura.nombre}'."
    ),
  )

  session.commit()

  return {
    "mensaje": (
      f"Docente '{docente.nombre} {docente.apellido}' vinculado "
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
  asignatura = _obtener_asignatura_activa(session, asignatura_id)
  docente = session.get(Docentes, docente_id)

  if not docente or docente not in asignatura.docentes:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="El docente no está vinculado a esta asignatura",
    )

  asignatura.docentes.remove(docente)

  session.add(asignatura)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.asignaturas,
    "DESVINCULAR_DOCENTE",
    (
      f"Se desvinculó al docente '{docente.nombre} {docente.apellido}' "
      f"de la asignatura '{asignatura.nombre}'."
    ),
  )

  session.commit()

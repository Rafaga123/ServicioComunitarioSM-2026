from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  filtro_activos,
  paginar,
)
from app.models.db import Estudiantes, Grados, Representantes, Secciones, Usuarios
from app.models.enums import ModuloAuditoria, NivelEducativo, RolesUsuario
from app.models.schemas import (
  ActualizarRepresentante,
  CrearRepresentante,
  PeticionRepresentante,
)
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.nombres import nombre_completo
from app.utils.security import (
  obtener_usuario_actual,
  requerir_roles,
  resolver_nivel,
)
from app.utils.soft_delete import marcar_eliminado

router = APIRouter(prefix="/representantes", tags=["Representantes"])
requerir_admin = requerir_roles(RolesUsuario.administrador)


def _validar_acceso_representante(
  session: Session, usuario: Usuarios, representante: Representantes
) -> None:
  if usuario.rol == RolesUsuario.administrador:
    return

  if usuario.nivel is None:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="La cuenta no tiene un nivel educativo asignado",
    )

  tiene_estudiante_nivel = session.exec(
    select(Estudiantes.id)
    .join(Secciones, Estudiantes.id_seccion == Secciones.id)
    .join(Grados, Secciones.id_grado == Grados.id)
    .where(
      Estudiantes.id_representante == representante.id,
      Estudiantes.fecha_eliminacion.is_(None),
      Secciones.fecha_eliminacion.is_(None),
      Grados.fecha_eliminacion.is_(None),
      Grados.nivel == usuario.nivel,
    )
  ).first()

  if tiene_estudiante_nivel is None:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="No tienes acceso a representantes de otro nivel educativo",
    )


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
  nivel: NivelEducativo | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  nivel = resolver_nivel(usuario_actual, nivel)
  consulta = filtro_activos(select(Representantes), Representantes)

  if nivel is not None:
    consulta = (
      consulta.join(Estudiantes, Estudiantes.id_representante == Representantes.id)
      .join(Secciones, Estudiantes.id_seccion == Secciones.id)
      .join(Grados, Secciones.id_grado == Grados.id)
      .where(
        Estudiantes.fecha_eliminacion.is_(None),
        Secciones.fecha_eliminacion.is_(None),
        Grados.fecha_eliminacion.is_(None),
        Grados.nivel == nivel,
      )
      .distinct()
    )

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(items, total, paginacion)


@router.get("/{representante_id}", response_model=PeticionRepresentante)
def obtener_representante(
  representante_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  representante = _obtener_representante_activo(session, representante_id)
  _validar_acceso_representante(session, usuario_actual, representante)

  return representante


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

  consulta = select(Estudiantes).where(
    Estudiantes.id_representante == representante_id,
    Estudiantes.fecha_eliminacion.is_(None),
  )
  if session.exec(consulta).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="El representante tiene estudiantes asignados",
    )

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

  if estudiante.id_representante == representante.id:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El representante ya está vinculado a este estudiante",
    )

  estudiante.id_representante = representante.id

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

  if estudiante.id_representante != representante_id:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="El representante no está vinculado a este estudiante",
    )

  representante = _obtener_representante_activo(session, representante_id)
  estudiante.id_representante = None

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

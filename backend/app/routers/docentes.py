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
  AsignaturasDocentes,
  Docentes,
  Horarios,
  Secciones,
  Usuarios,
)
from app.models.enums import ModuloAuditoria, NivelEducativo, RolesUsuario
from app.models.schemas import ActualizarDocente, CrearDocente, PeticionDocente
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.nombres import nombre_completo
from app.utils.security import (
  obtener_usuario_actual,
  requerir_roles,
  resolver_nivel,
  validar_acceso_nivel,
)
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


def _validar_docente_sin_dependencias(session: Session, docente_id: int) -> None:
  consulta = select(Secciones).where(
    Secciones.id_docente_titular == docente_id,
    Secciones.fecha_eliminacion.is_(None),
  )
  if session.exec(consulta).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="El docente es titular de una sección activa; cambia primero la titularidad",
    )

  consulta = select(Horarios).where(
    Horarios.id_docente == docente_id,
    Horarios.fecha_eliminacion.is_(None),
  )
  if session.exec(consulta).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="El docente tiene horarios activos",
    )

  consulta = select(AsignaturasDocentes).where(
    AsignaturasDocentes.id_docente == docente_id,
    AsignaturasDocentes.fecha_eliminacion.is_(None),
  )
  if session.exec(consulta).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="El docente tiene asignaturas vinculadas",
    )


@router.get("/", response_model=RespuestaPaginada[PeticionDocente])
def listar_docentes(
  paginacion: Paginacion = Depends(),
  nivel: NivelEducativo | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  consulta = filtro_activos(select(Docentes), Docentes)

  nivel = resolver_nivel(usuario_actual, nivel)
  if nivel is not None:
    consulta = consulta.where(Docentes.nivel == nivel)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(items, total, paginacion)


@router.get("/{docente_id}", response_model=PeticionDocente)
def obtener_docente(
  docente_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  docente = _obtener_docente_activo(session, docente_id)
  validar_acceso_nivel(usuario_actual, docente.nivel)
  return docente


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
    primer_nombre=docente_in.primer_nombre,
    segundo_nombre=docente_in.segundo_nombre,
    primer_apellido=docente_in.primer_apellido,
    segundo_apellido=docente_in.segundo_apellido,
    cedula=docente_in.cedula,
    nivel=docente_in.nivel,
  )

  session.add(nuevo_docente)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.docentes,
    "CREAR",
    f"Se registró al docente '{nombre_completo(nuevo_docente)}' "
    f"con cédula {nuevo_docente.cedula}.",
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

  if "nivel" in datos_actualizar and datos_actualizar["nivel"] != docente_db.nivel:
    _validar_docente_sin_dependencias(session, docente_id)

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
    f"Se actualizaron los datos del docente '{nombre_completo(docente_db)}' "
    f"con cédula {docente_db.cedula}.",
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
  _validar_docente_sin_dependencias(session, docente_id)

  marcar_eliminado(session, docente_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.docentes,
    "ELIMINAR",
    f"Se dio de baja al docente '{nombre_completo(docente_db)}' "
    f"con cédula {docente_db.cedula}.",
  )

  session.commit()

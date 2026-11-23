from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  PaginacionBusqueda,
  RespuestaPaginada,
  construir_pagina,
  filtro_activos,
  filtro_texto,
  paginar,
)
from app.models.db import (
  Estudiantes,
  Grados,
  Representantes,
  Secciones,
  Usuarios,
)
from app.models.enums import ModuloAuditoria, NivelEducativo, RolesUsuario
from app.models.schemas import ActualizarEstudiante, CrearEstudiante, PeticionEstudiante
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

router = APIRouter(prefix="/estudiantes", tags=["Estudiantes"])


def _obtener_estudiante_activo(session: Session, estudiante_id: int) -> Estudiantes:
  estudiante = session.get(Estudiantes, estudiante_id)

  if not estudiante or estudiante.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Estudiante no encontrado"
    )

  return estudiante


def _obtener_seccion_activa(session: Session, seccion_id: int) -> Secciones:
  seccion = session.get(Secciones, seccion_id)

  if not seccion or seccion.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Sección no encontrada"
    )

  return seccion


def _obtener_representante_activo(
  session: Session, representante_id: int
) -> Representantes:
  representante = session.get(Representantes, representante_id)

  if not representante or representante.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Representante no encontrado"
    )

  return representante


def _estudiante_dto(estudiante: Estudiantes) -> PeticionEstudiante:
  seccion = estudiante.seccion
  grado = seccion.grado
  representante = estudiante.representante

  return PeticionEstudiante(
    id=estudiante.id,
    id_seccion=estudiante.id_seccion,
    id_representante=estudiante.id_representante,
    cedula_estudiantil=estudiante.cedula_estudiantil,
    primer_nombre=estudiante.primer_nombre,
    segundo_nombre=estudiante.segundo_nombre,
    primer_apellido=estudiante.primer_apellido,
    segundo_apellido=estudiante.segundo_apellido,
    fecha_nacimiento=estudiante.fecha_nacimiento,
    nivel=grado.nivel,
    id_grado=seccion.id_grado,
    grado_numero=grado.numero,
    grado_nombre=grado.nombre,
    seccion_letra=seccion.letra,
    periodo_lectivo=seccion.periodo_lectivo,
    representante=nombre_completo(representante) if representante else None,
  )


@router.post(
  "/", response_model=PeticionEstudiante, status_code=status.HTTP_201_CREATED
)
def registrar_estudiante(
  estudiante_in: CrearEstudiante,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_roles(RolesUsuario.administrador)),
):
  statement = select(Estudiantes).where(
    Estudiantes.cedula_estudiantil == estudiante_in.cedula_estudiantil
  )

  if session.exec(statement).first():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Ya existe un estudiante con está cédula",
    )

  seccion = _obtener_seccion_activa(session, estudiante_in.id_seccion)
  validar_acceso_nivel(usuario_actual, seccion.grado.nivel)

  if estudiante_in.id_representante is not None:
    _obtener_representante_activo(session, estudiante_in.id_representante)

  nuevo_estudiante = Estudiantes(
    id_seccion=estudiante_in.id_seccion,
    id_representante=estudiante_in.id_representante,
    cedula_estudiantil=estudiante_in.cedula_estudiantil,
    primer_nombre=estudiante_in.primer_nombre,
    segundo_nombre=estudiante_in.segundo_nombre,
    primer_apellido=estudiante_in.primer_apellido,
    segundo_apellido=estudiante_in.segundo_apellido,
    fecha_nacimiento=estudiante_in.fecha_nacimiento,
  )

  session.add(nuevo_estudiante)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.estudiantes,
    "CREAR",
    f"Se registró al estudiante '{nombre_completo(nuevo_estudiante)}' "
    f"con cédula {nuevo_estudiante.cedula_estudiantil}.",
  )

  session.commit()
  session.refresh(nuevo_estudiante)

  return _estudiante_dto(nuevo_estudiante)


@router.get("/", response_model=RespuestaPaginada[PeticionEstudiante])
def listar_estudiantes(
  paginacion: Paginacion = Depends(),
  nivel: NivelEducativo | None = None,
  id_grado: int | None = None,
  id_seccion: int | None = None,
  periodo_lectivo: int | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  consulta = filtro_activos(select(Estudiantes), Estudiantes)
  consulta = consulta.join(Secciones, Estudiantes.id_seccion == Secciones.id)
  consulta = consulta.join(Grados, Secciones.id_grado == Grados.id)

  nivel = resolver_nivel(usuario_actual, nivel)
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)
  if id_grado is not None:
    consulta = consulta.where(Secciones.id_grado == id_grado)
  if id_seccion is not None:
    consulta = consulta.where(Estudiantes.id_seccion == id_seccion)
  if periodo_lectivo is not None:
    consulta = consulta.where(Secciones.periodo_lectivo == periodo_lectivo)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina([_estudiante_dto(e) for e in items], total, paginacion)


@router.get("/buscar/", response_model=RespuestaPaginada[PeticionEstudiante])
def buscar_estudiantes(
  termino: str,
  paginacion: PaginacionBusqueda = Depends(),
  nivel: NivelEducativo | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  consulta = filtro_activos(select(Estudiantes), Estudiantes)
  consulta = consulta.join(Secciones, Estudiantes.id_seccion == Secciones.id)
  consulta = consulta.join(Grados, Secciones.id_grado == Grados.id)
  consulta = filtro_texto(
    consulta,
    termino,
    Estudiantes.cedula_estudiantil,
    Estudiantes.primer_nombre,
    Estudiantes.primer_apellido,
  )

  nivel = resolver_nivel(usuario_actual, nivel)
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina([_estudiante_dto(e) for e in items], total, paginacion)


@router.get("/{estudiante_id}", response_model=PeticionEstudiante)
def obtener_estudiante(
  estudiante_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  estudiante = _obtener_estudiante_activo(session, estudiante_id)
  validar_acceso_nivel(usuario_actual, estudiante.seccion.grado.nivel)

  return _estudiante_dto(estudiante)


@router.put("/{estudiante_id}", response_model=PeticionEstudiante)
def actualizar_estudiante(
  estudiante_id: int,
  estudiante_in: ActualizarEstudiante,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_roles(RolesUsuario.administrador)),
):
  estudiante_db = _obtener_estudiante_activo(session, estudiante_id)

  if "id_seccion" in estudiante_in.model_fields_set:
    nueva_seccion = _obtener_seccion_activa(session, estudiante_in.id_seccion)
    validar_acceso_nivel(usuario_actual, nueva_seccion.grado.nivel)

  if (
    "id_representante" in estudiante_in.model_fields_set
    and estudiante_in.id_representante is not None
  ):
    _obtener_representante_activo(session, estudiante_in.id_representante)

  if (
    estudiante_in.cedula_estudiantil
    and estudiante_in.cedula_estudiantil != estudiante_db.cedula_estudiantil
  ):
    statement = select(Estudiantes).where(
      Estudiantes.cedula_estudiantil == estudiante_in.cedula_estudiantil
    )
    if session.exec(statement).first():
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="La nueva cédula ya está registrada en otro estudiante",
      )

  datos_actualizar = estudiante_in.model_dump(exclude_unset=True)

  if not datos_actualizar:
    return _estudiante_dto(estudiante_db)

  for key, value in datos_actualizar.items():
    setattr(estudiante_db, key, value)

  session.add(estudiante_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.estudiantes,
    "ACTUALIZAR",
    f"Se actualizaron los datos del estudiante "
    f"'{nombre_completo(estudiante_db)}' "
    f"con cédula {estudiante_db.cedula_estudiantil}.",
  )

  session.commit()
  session.refresh(estudiante_db)

  return _estudiante_dto(estudiante_db)


@router.delete("/{estudiante_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_estudiante(
  estudiante_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_roles(RolesUsuario.administrador)),
) -> None:
  estudiante_db = _obtener_estudiante_activo(session, estudiante_id)

  marcar_eliminado(session, estudiante_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.estudiantes,
    "ELIMINAR",
    f"Se dio de baja al estudiante '{nombre_completo(estudiante_db)}' "
    f"con cédula {estudiante_db.cedula_estudiantil}.",
  )

  session.commit()

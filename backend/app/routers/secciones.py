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
  Docentes,
  Estudiantes,
  Grados,
  Horarios,
  Secciones,
  Usuarios,
)
from app.models.enums import (
  ModuloAuditoria,
  NivelEducativo,
  RolesUsuario,
)
from app.models.schemas import (
  ActualizarSeccion,
  CrearSeccion,
  PeticionSeccion,
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

router = APIRouter(prefix="/secciones", tags=["Secciones"])
requerir_admin = requerir_roles(RolesUsuario.administrador)


def _obtener_seccion_activa(session: Session, seccion_id: int) -> Secciones:
  seccion = session.get(Secciones, seccion_id)

  if not seccion or seccion.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Sección no encontrada"
    )

  return seccion


def _obtener_grado_activo(session: Session, grado_id: int) -> Grados:
  grado = session.get(Grados, grado_id)

  if not grado or grado.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Grado no encontrado"
    )

  return grado


def _obtener_docente_activo(session: Session, docente_id: int) -> Docentes:
  docente = session.get(Docentes, docente_id)

  if not docente or docente.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Docente no encontrado"
    )

  return docente


def _validar_titular_escuela(
  session: Session,
  usuario: Usuarios,
  grado: Grados,
  docente_id: int | None,
) -> None:
  if docente_id is None:
    return

  if grado.nivel != NivelEducativo.escuela:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Solo se puede nombrar titular a una sección de escuela",
    )

  docente = _obtener_docente_activo(session, docente_id)
  if docente.nivel != NivelEducativo.escuela:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Solo se puede titular una sección de escuela con un docente de escuela",
    )

  validar_acceso_nivel(usuario, docente.nivel)


def _validar_titular_unico(
  session: Session,
  docente_id: int | None,
  periodo_lectivo: int,
  excluir_id: int | None = None,
) -> None:
  """Un docente solo puede ser titular de una sección por período lectivo."""
  if docente_id is None:
    return

  consulta = select(Secciones).where(
    Secciones.id_docente_titular == docente_id,
    Secciones.periodo_lectivo == periodo_lectivo,
    Secciones.fecha_eliminacion.is_(None),
  )
  if excluir_id is not None:
    consulta = consulta.where(Secciones.id != excluir_id)
  if session.exec(consulta).first():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="El docente ya es titular de otra sección en este período lectivo",
    )


def _validar_duplicado_seccion(
  session: Session,
  id_grado: int,
  letra: str,
  periodo_lectivo: int,
  excluir_id: int | None = None,
) -> None:
  statement = select(Secciones).where(
    Secciones.id_grado == id_grado,
    Secciones.letra == letra,
    Secciones.periodo_lectivo == periodo_lectivo,
    Secciones.fecha_eliminacion.is_(None),
  )
  if excluir_id is not None:
    statement = statement.where(Secciones.id != excluir_id)
  if session.exec(statement).first():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Ya existe una sección activa con ese grado, letra y período lectivo",
    )


def _tiene_dependencias(session: Session, seccion: Secciones) -> bool:
  estudiantes = session.exec(
    select(Estudiantes).where(
      Estudiantes.id_seccion == seccion.id,
      Estudiantes.fecha_eliminacion.is_(None),
    )
  ).first()
  if estudiantes:
    return True

  return bool(
    session.exec(
      select(Horarios).where(
        Horarios.id_seccion == seccion.id,
        Horarios.fecha_eliminacion.is_(None),
      )
    ).first()
  )


def _seccion_dto(seccion: Secciones, usuario: Usuarios) -> PeticionSeccion:
  grado = seccion.grado
  docente = seccion.docente_titular
  nivel = grado.nivel if grado else None

  validar_acceso_nivel(usuario, nivel)

  return PeticionSeccion(
    id=seccion.id,
    id_grado=seccion.id_grado,
    letra=seccion.letra,
    periodo_lectivo=seccion.periodo_lectivo,
    id_docente_titular=seccion.id_docente_titular,
    grado_numero=grado.numero if grado else None,
    grado_nombre=grado.nombre if grado else None,
    nivel=nivel,
    docente_titular=nombre_completo(docente) if docente else None,
  )


@router.get("/", response_model=RespuestaPaginada[PeticionSeccion])
def listar_secciones(
  paginacion: Paginacion = Depends(),
  nivel: NivelEducativo | None = None,
  id_grado: int | None = None,
  periodo_lectivo: int | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  consulta = filtro_activos(select(Secciones), Secciones)
  consulta = consulta.join(Grados, Secciones.id_grado == Grados.id)

  nivel = resolver_nivel(usuario_actual, nivel)
  periodo_lectivo = periodo_lectivo_efectivo(session, periodo_lectivo)
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)
  if id_grado is not None:
    consulta = consulta.where(Secciones.id_grado == id_grado)
  if periodo_lectivo is not None:
    consulta = consulta.where(Secciones.periodo_lectivo == periodo_lectivo)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(
    [_seccion_dto(s, usuario_actual) for s in items], total, paginacion
  )


@router.get("/{seccion_id}", response_model=PeticionSeccion)
def obtener_seccion(
  seccion_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  seccion = _obtener_seccion_activa(session, seccion_id)
  return _seccion_dto(seccion, usuario_actual)


@router.post("/", response_model=PeticionSeccion, status_code=status.HTTP_201_CREATED)
def registrar_seccion(
  seccion_in: CrearSeccion,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  grado = _obtener_grado_activo(session, seccion_in.id_grado)
  validar_acceso_nivel(usuario_actual, grado.nivel)
  _validar_titular_escuela(
    session, usuario_actual, grado, seccion_in.id_docente_titular
  )
  _validar_titular_unico(
    session, seccion_in.id_docente_titular, seccion_in.periodo_lectivo
  )
  _validar_duplicado_seccion(
    session, seccion_in.id_grado, seccion_in.letra, seccion_in.periodo_lectivo
  )

  nueva_seccion = Secciones(
    id_grado=seccion_in.id_grado,
    letra=seccion_in.letra,
    periodo_lectivo=seccion_in.periodo_lectivo,
    id_docente_titular=seccion_in.id_docente_titular,
  )
  session.add(nueva_seccion)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.secciones,
    "CREAR",
    f"Se creó la sección {nueva_seccion.letra} del {grado.nombre} para {nueva_seccion.periodo_lectivo}.",
  )
  session.commit()
  session.refresh(nueva_seccion)

  return _seccion_dto(nueva_seccion, usuario_actual)


@router.put("/{seccion_id}", response_model=PeticionSeccion)
def actualizar_seccion(
  seccion_id: int,
  seccion_in: ActualizarSeccion,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  seccion_db = _obtener_seccion_activa(session, seccion_id)
  grado = seccion_db.grado
  validar_acceso_nivel(usuario_actual, grado.nivel)
  datos_actualizar = seccion_in.model_dump(exclude_unset=True)
  datos_actualizar = {
    campo: valor
    for campo, valor in datos_actualizar.items()
    if valor is not None or campo == "id_docente_titular"
  }

  nueva_letra = datos_actualizar.get("letra", seccion_db.letra)
  nuevo_periodo = datos_actualizar.get("periodo_lectivo", seccion_db.periodo_lectivo)
  nuevo_titular = datos_actualizar.get(
    "id_docente_titular", seccion_db.id_docente_titular
  )

  if nueva_letra != seccion_db.letra or nuevo_periodo != seccion_db.periodo_lectivo:
    _validar_duplicado_seccion(
      session,
      seccion_db.id_grado,
      nueva_letra,
      nuevo_periodo,
      excluir_id=seccion_id,
    )

  _validar_titular_escuela(session, usuario_actual, seccion_db.grado, nuevo_titular)
  _validar_titular_unico(session, nuevo_titular, nuevo_periodo, excluir_id=seccion_id)

  for campo, valor in datos_actualizar.items():
    setattr(seccion_db, campo, valor)
  session.add(seccion_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.secciones,
    "ACTUALIZAR",
    f"Se actualizó la sección {seccion_db.letra} de {seccion_db.grado.nombre}.",
  )
  session.commit()
  session.refresh(seccion_db)

  return _seccion_dto(seccion_db, usuario_actual)


@router.delete("/{seccion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_seccion(
  seccion_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  seccion_db = _obtener_seccion_activa(session, seccion_id)
  if _tiene_dependencias(session, seccion_db):
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="Traslada los alumnos y revisa horarios antes de dar de baja la sección",
    )

  marcar_eliminado(session, seccion_db)
  session.flush()
  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.secciones,
    "ELIMINAR",
    f"Se dio de baja la sección {seccion_db.letra} de {seccion_db.grado.nombre}.",
  )
  session.commit()

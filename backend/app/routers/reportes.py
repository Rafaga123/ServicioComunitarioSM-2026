from pathlib import Path

from fastapi import (
  APIRouter,
  Depends,
  File,
  HTTPException,
  Query,
  UploadFile,
  status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func
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
  Reportes,
  Secciones,
  Usuarios,
)
from app.models.enums import (
  CategoriaReportes,
  ModuloAuditoria,
  NivelEducativo,
  NivelGravedad,
  RolesUsuario,
)
from app.models.schemas import (
  ActualizarReporte,
  CrearReporte,
  PeticionReporte,
)
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.nombres import nombre_completo
from app.utils.periodos import periodo_lectivo_efectivo
from app.utils.security import (
  requerir_roles,
  resolver_nivel,
  validar_acceso_nivel,
)
from app.utils.soft_delete import marcar_eliminado
from app.utils.storage import (
  existe_archivo,
  guardar_archivo,
  quitar_meta_archivo,
  registrar_meta_archivo,
  ruta_absoluta,
  ruta_relativa_imagen,
  validar_upload,
)

router = APIRouter(prefix="/reportes", tags=["Reportes"])
requerir_personal = requerir_roles(
  RolesUsuario.administrador,
  RolesUsuario.coordinador,
  RolesUsuario.secretaria,
)


def _obtener_reporte_activo(session: Session, reporte_id: int) -> Reportes:
  reporte = session.get(Reportes, reporte_id)

  if not reporte or reporte.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Reporte no encontrado"
    )

  return reporte


def _obtener_estudiante_activo(session: Session, estudiante_id: int) -> Estudiantes:
  estudiante = session.get(Estudiantes, estudiante_id)

  if not estudiante or estudiante.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Estudiante no encontrado"
    )

  return estudiante


def _nivel_estudiante(estudiante: Estudiantes) -> NivelEducativo:
  return estudiante.seccion.grado.nivel


def _validar_docente(
  session: Session,
  estudiante: Estudiantes,
  id_docente: int | None,
) -> None:
  if id_docente is None:
    return

  docente = session.get(Docentes, id_docente)
  if not docente or docente.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Docente no encontrado"
    )

  if docente.nivel != _nivel_estudiante(estudiante):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El docente no pertenece al nivel del estudiante",
    )


def _reporte_dto(reporte: Reportes) -> PeticionReporte:
  estudiante = reporte.estudiante
  seccion = estudiante.seccion
  grado = seccion.grado
  docente = reporte.docente

  return PeticionReporte(
    id=reporte.id,
    id_estudiante=reporte.id_estudiante,
    id_usuario=reporte.id_usuario,
    id_docente=reporte.id_docente,
    articulo=reporte.articulo,
    reglamento=reporte.reglamento,
    incidencia=reporte.incidencia,
    defensa=reporte.defensa,
    nivel_gravedad=reporte.nivel_gravedad,
    categoria=reporte.categoria,
    fecha=reporte.fecha,
    periodo_lectivo=reporte.periodo_lectivo,
    archivo_url=reporte.archivo_url,
    archivo_nombre=reporte.archivo_nombre,
    archivo_mime=reporte.archivo_mime,
    archivo_tamano=reporte.archivo_tamano,
    archivo_hash=reporte.archivo_hash,
    archivo_subido_por=reporte.archivo_subido_por,
    archivo_fecha=reporte.archivo_fecha,
    estudiante=nombre_completo(estudiante),
    cedula_estudiantil=estudiante.cedula_estudiantil,
    nivel=grado.nivel,
    usuario=reporte.usuario.nombre,
    docente=nombre_completo(docente) if docente else None,
  )


@router.get("/", response_model=RespuestaPaginada[PeticionReporte])
def listar_reportes(
  id_estudiante: int | None = None,
  id_seccion: int | None = None,
  id_docente: int | None = None,
  anio: int | None = None,
  mes: int | None = Query(default=None, ge=1, le=12),
  periodo_lectivo: int | None = None,
  categoria: CategoriaReportes | None = None,
  nivel_gravedad: NivelGravedad | None = None,
  nivel: NivelEducativo | None = None,
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  consulta = filtro_activos(select(Reportes), Reportes)
  consulta = consulta.join(Estudiantes, Reportes.id_estudiante == Estudiantes.id)
  consulta = consulta.join(Secciones, Estudiantes.id_seccion == Secciones.id)
  consulta = consulta.join(Grados, Secciones.id_grado == Grados.id)

  nivel = resolver_nivel(usuario_actual, nivel)
  periodo_lectivo = periodo_lectivo_efectivo(session, periodo_lectivo)
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)
  if id_estudiante is not None:
    consulta = consulta.where(Reportes.id_estudiante == id_estudiante)
  if id_seccion is not None:
    consulta = consulta.where(Estudiantes.id_seccion == id_seccion)
  if id_docente is not None:
    consulta = consulta.where(Reportes.id_docente == id_docente)
  if anio is not None:
    consulta = consulta.where(func.extract("year", Reportes.fecha) == anio)
  if mes is not None:
    consulta = consulta.where(func.extract("month", Reportes.fecha) == mes)
  if periodo_lectivo is not None:
    consulta = consulta.where(Reportes.periodo_lectivo == periodo_lectivo)
  if categoria is not None:
    consulta = consulta.where(Reportes.categoria == categoria)
  if nivel_gravedad is not None:
    consulta = consulta.where(Reportes.nivel_gravedad == nivel_gravedad)

  consulta = consulta.order_by(Reportes.fecha.desc())

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(
    [_reporte_dto(reporte) for reporte in items], total, paginacion
  )


@router.get("/{reporte_id}", response_model=PeticionReporte)
def obtener_reporte(
  reporte_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  reporte = _obtener_reporte_activo(session, reporte_id)
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(reporte.estudiante))

  return _reporte_dto(reporte)


@router.post("/", response_model=PeticionReporte, status_code=status.HTTP_201_CREATED)
def registrar_reporte(
  reporte_in: CrearReporte,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  estudiante = _obtener_estudiante_activo(session, reporte_in.id_estudiante)
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(estudiante))
  _validar_docente(session, estudiante, reporte_in.id_docente)

  nuevo_reporte = Reportes(
    id_estudiante=estudiante.id,
    id_usuario=usuario_actual.id,
    id_docente=reporte_in.id_docente,
    articulo=reporte_in.articulo,
    reglamento=reporte_in.reglamento,
    incidencia=reporte_in.incidencia,
    defensa=reporte_in.defensa,
    nivel_gravedad=reporte_in.nivel_gravedad,
    categoria=reporte_in.categoria,
    fecha=reporte_in.fecha,
    periodo_lectivo=estudiante.seccion.periodo_lectivo,
  )

  session.add(nuevo_reporte)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.reportes,
    "CREAR",
    f"Se registró un reporte para '{nombre_completo(estudiante)}'.",
  )

  session.commit()
  session.refresh(nuevo_reporte)

  return _reporte_dto(nuevo_reporte)


@router.put("/{reporte_id}", response_model=PeticionReporte)
def actualizar_reporte(
  reporte_id: int,
  reporte_in: ActualizarReporte,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  reporte_db = _obtener_reporte_activo(session, reporte_id)
  estudiante = reporte_db.estudiante
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(estudiante))

  datos_actualizar = reporte_in.model_dump(exclude_unset=True)
  datos_actualizar = {
    campo: valor
    for campo, valor in datos_actualizar.items()
    if valor is not None or campo in {"id_docente"}
  }

  if not datos_actualizar:
    return _reporte_dto(reporte_db)

  id_docente = datos_actualizar.get("id_docente", reporte_db.id_docente)
  _validar_docente(session, estudiante, id_docente)

  for campo, valor in datos_actualizar.items():
    setattr(reporte_db, campo, valor)

  session.add(reporte_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.reportes,
    "ACTUALIZAR",
    (f"Se actualizó el reporte #{reporte_db.id} de '{nombre_completo(estudiante)}'."),
  )

  session.commit()
  session.refresh(reporte_db)

  return _reporte_dto(reporte_db)


@router.delete("/{reporte_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_reporte(
  reporte_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
) -> None:
  reporte_db = _obtener_reporte_activo(session, reporte_id)
  estudiante = reporte_db.estudiante
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(estudiante))

  marcar_eliminado(session, reporte_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.reportes,
    "ELIMINAR",
    (f"Se dio de baja el reporte #{reporte_db.id} de '{nombre_completo(estudiante)}'."),
  )

  session.commit()


def _ruta_archivo_segura(archivo_url: str | None) -> Path:
  if not archivo_url or not existe_archivo(archivo_url):
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="El archivo adjunto no está disponible localmente",
    )
  return ruta_absoluta(archivo_url)


@router.post("/{reporte_id}/archivo", response_model=PeticionReporte)
def subir_reporte_archivo(
  reporte_id: int,
  archivo: UploadFile = File(...),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  reporte = _obtener_reporte_activo(session, reporte_id)
  estudiante = reporte.estudiante
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(estudiante))

  try:
    nombre_base, extension, mime, contenido = validar_upload(archivo)
  except ValueError as error:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

  seccion = estudiante.seccion
  ruta_relativa = ruta_relativa_imagen(
    reporte.fecha,
    seccion.grado.numero,
    seccion.letra,
    seccion.grado.nivel,
    estudiante.id,
    reporte.id,
    extension,
  )
  guardar_archivo(ruta_relativa, contenido)
  registrar_meta_archivo(
    reporte, ruta_relativa, nombre_base, mime, contenido, usuario_actual.id
  )

  session.add(reporte)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.reportes,
    "SUBIR_ARCHIVO",
    (
      f"Subió el adjunto '{nombre_base}' ({len(contenido)} bytes) "
      f"del reporte #{reporte.id} de '{nombre_completo(estudiante)}'."
    ),
  )

  session.commit()
  session.refresh(reporte)
  return _reporte_dto(reporte)


@router.get("/{reporte_id}/archivo")
def descargar_reporte_archivo(
  reporte_id: int,
  inline: bool = Query(default=False),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  reporte = _obtener_reporte_activo(session, reporte_id)
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(reporte.estudiante))

  ruta = _ruta_archivo_segura(reporte.archivo_url)

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.reportes,
    "DESCARGAR_ARCHIVO",
    (
      f"Descargó el adjunto '{reporte.archivo_nombre}' "
      f"del reporte #{reporte.id} de '{nombre_completo(reporte.estudiante)}'."
    ),
  )
  session.flush()
  session.commit()

  return FileResponse(
    path=str(ruta),
    media_type=reporte.archivo_mime or "application/octet-stream",
    filename=reporte.archivo_nombre or f"reporte-{reporte.id}",
    content_disposition_type="inline" if inline else "attachment",
  )


@router.delete("/{reporte_id}/archivo", status_code=status.HTTP_204_NO_CONTENT)
def quitar_reporte_archivo(
  reporte_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
) -> None:
  reporte = _obtener_reporte_activo(session, reporte_id)
  estudiante = reporte.estudiante
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(estudiante))

  quitar_meta_archivo(reporte)
  session.add(reporte)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.reportes,
    "QUITAR_ARCHIVO",
    f"Quitó el adjunto del reporte #{reporte.id} de '{nombre_completo(estudiante)}'.",
  )

  session.commit()

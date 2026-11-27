"""Gestiona pases disciplinarios, adjuntos y validaciones de nivel."""

from datetime import datetime
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
  Asignaturas,
  AsignaturasDocentes,
  Docentes,
  Estudiantes,
  Grados,
  Pases,
  Secciones,
  Usuarios,
)
from app.models.enums import (
  ModuloAuditoria,
  NivelEducativo,
  RolesUsuario,
  TipoPase,
)
from app.models.schemas import (
  ActualizacionPase,
  CrearPase,
  PeticionPase,
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

router = APIRouter(prefix="/pases", tags=["Pases"])
requerir_personal = requerir_roles(
  RolesUsuario.administrador,
  RolesUsuario.coordinador,
  RolesUsuario.secretaria,
)

LIMITE_SIN_AUTORIZADOR = 3


def _obtener_pase_activo(session: Session, pase_id: int) -> Pases:
  pase = session.get(Pases, pase_id)

  if not pase or pase.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Pase no encontrado"
    )

  return pase


def _obtener_estudiante_activo(session: Session, estudiante_id: int) -> Estudiantes:
  estudiante = session.get(Estudiantes, estudiante_id)

  if not estudiante or estudiante.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Estudiante no encontrado"
    )

  return estudiante


def _nivel_estudiante(estudiante: Estudiantes) -> NivelEducativo:
  return estudiante.seccion.grado.nivel


def _validar_docente_asignatura(
  session: Session,
  estudiante: Estudiantes,
  id_docente: int | None,
  id_asignatura: int | None,
) -> None:
  nivel = _nivel_estudiante(estudiante)

  if id_docente is not None:
    docente = session.get(Docentes, id_docente)
    if not docente or docente.fecha_eliminacion is not None:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Docente no encontrado"
      )
    if docente.nivel != nivel:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El docente no pertenece al nivel del estudiante",
      )

  if id_asignatura is not None:
    asignatura = session.get(Asignaturas, id_asignatura)
    if not asignatura or asignatura.fecha_eliminacion is not None:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Asignatura no encontrada",
      )
    if asignatura.id_grado != estudiante.seccion.id_grado:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="La asignatura no pertenece al grado del estudiante",
      )

  if id_docente is not None and id_asignatura is not None:
    vinculado = session.exec(
      select(AsignaturasDocentes).where(
        AsignaturasDocentes.id_asignatura == id_asignatura,
        AsignaturasDocentes.id_docente == id_docente,
        AsignaturasDocentes.fecha_eliminacion.is_(None),
      )
    ).first()
    if not vinculado:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El docente no está vinculado a la asignatura",
      )


def _contar_pases_mes(
  session: Session,
  id_estudiante: int,
  tipo: TipoPase,
  fecha: datetime,
  excluir_id: int | None = None,
) -> int:
  inicio = datetime(fecha.year, fecha.month, 1)
  if fecha.month == 12:
    fin = datetime(fecha.year + 1, 1, 1)
  else:
    fin = datetime(fecha.year, fecha.month + 1, 1)

  consulta = (
    select(func.count())
    .select_from(Pases)
    .where(
      Pases.id_estudiante == id_estudiante,
      Pases.tipo == tipo,
      Pases.fecha >= inicio,
      Pases.fecha < fin,
      Pases.fecha_eliminacion.is_(None),
    )
  )
  if excluir_id is not None:
    consulta = consulta.where(Pases.id != excluir_id)

  return session.exec(consulta).one()


def _validar_autorizador(
  session: Session,
  id_estudiante: int,
  tipo: TipoPase,
  fecha: datetime,
  autorizador: str | None,
  excluir_id: int | None = None,
) -> None:
  existentes = _contar_pases_mes(
    session, id_estudiante, tipo, fecha, excluir_id=excluir_id
  )

  if existentes >= LIMITE_SIN_AUTORIZADOR and not (autorizador and autorizador.strip()):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=("El cuarto pase del mes del mismo tipo requiere un autorizador"),
    )


def _pase_dto(pase: Pases) -> PeticionPase:
  estudiante = pase.estudiante
  seccion = estudiante.seccion
  grado = seccion.grado
  docente = pase.docente
  asignatura = pase.asignatura

  return PeticionPase(
    id=pase.id,
    id_estudiante=pase.id_estudiante,
    id_usuario=pase.id_usuario,
    id_docente=pase.id_docente,
    id_asignatura=pase.id_asignatura,
    tipo=pase.tipo,
    motivo=pase.motivo,
    fecha=pase.fecha,
    periodo_lectivo=pase.periodo_lectivo,
    autorizador=pase.autorizador,
    archivo_url=pase.archivo_url,
    archivo_nombre=pase.archivo_nombre,
    archivo_mime=pase.archivo_mime,
    archivo_tamano=pase.archivo_tamano,
    archivo_hash=pase.archivo_hash,
    archivo_subido_por=pase.archivo_subido_por,
    archivo_fecha=pase.archivo_fecha,
    estudiante=nombre_completo(estudiante),
    cedula_estudiantil=estudiante.cedula_estudiantil,
    nivel=grado.nivel,
    usuario=pase.usuario.nombre,
    docente=nombre_completo(docente) if docente else None,
    asignatura=asignatura.nombre if asignatura else None,
  )


@router.get("/", response_model=RespuestaPaginada[PeticionPase])
def listar_pases(
  id_estudiante: int | None = None,
  id_seccion: int | None = None,
  tipo: TipoPase | None = None,
  anio: int | None = None,
  mes: int | None = Query(default=None, ge=1, le=12),
  periodo_lectivo: int | None = None,
  nivel: NivelEducativo | None = None,
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  consulta = filtro_activos(select(Pases), Pases)
  consulta = consulta.join(Estudiantes, Pases.id_estudiante == Estudiantes.id)
  consulta = consulta.join(Secciones, Estudiantes.id_seccion == Secciones.id)
  consulta = consulta.join(Grados, Secciones.id_grado == Grados.id)

  nivel = resolver_nivel(usuario_actual, nivel)
  periodo_lectivo = periodo_lectivo_efectivo(session, periodo_lectivo)
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)
  if id_estudiante is not None:
    consulta = consulta.where(Pases.id_estudiante == id_estudiante)
  if id_seccion is not None:
    consulta = consulta.where(Estudiantes.id_seccion == id_seccion)
  if tipo is not None:
    consulta = consulta.where(Pases.tipo == tipo)
  if anio is not None:
    consulta = consulta.where(func.extract("year", Pases.fecha) == anio)
  if mes is not None:
    consulta = consulta.where(func.extract("month", Pases.fecha) == mes)
  if periodo_lectivo is not None:
    consulta = consulta.where(Pases.periodo_lectivo == periodo_lectivo)

  consulta = consulta.order_by(Pases.fecha.desc())

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina([_pase_dto(pase) for pase in items], total, paginacion)


@router.get("/{pase_id}", response_model=PeticionPase)
def obtener_pase(
  pase_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  pase = _obtener_pase_activo(session, pase_id)
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(pase.estudiante))

  return _pase_dto(pase)


@router.post("/", response_model=PeticionPase, status_code=status.HTTP_201_CREATED)
def registrar_pase(
  pase_in: CrearPase,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  estudiante = _obtener_estudiante_activo(session, pase_in.id_estudiante)
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(estudiante))
  _validar_docente_asignatura(
    session, estudiante, pase_in.id_docente, pase_in.id_asignatura
  )

  autorizador = (pase_in.autorizador or "").strip() or None
  _validar_autorizador(
    session,
    estudiante.id,
    pase_in.tipo,
    pase_in.fecha,
    autorizador,
  )

  nuevo_pase = Pases(
    id_estudiante=estudiante.id,
    id_usuario=usuario_actual.id,
    id_docente=pase_in.id_docente,
    id_asignatura=pase_in.id_asignatura,
    tipo=pase_in.tipo,
    motivo=pase_in.motivo,
    fecha=pase_in.fecha,
    periodo_lectivo=estudiante.seccion.periodo_lectivo,
    autorizador=autorizador,
  )

  session.add(nuevo_pase)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.pases,
    "CREAR",
    (
      f"Se registró un pase de {pase_in.tipo.value} para "
      f"'{nombre_completo(estudiante)}'."
    ),
  )

  session.commit()
  session.refresh(nuevo_pase)

  return _pase_dto(nuevo_pase)


@router.put("/{pase_id}", response_model=PeticionPase)
def actualizar_pase(
  pase_id: int,
  pase_in: ActualizacionPase,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  pase_db = _obtener_pase_activo(session, pase_id)
  estudiante = pase_db.estudiante
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(estudiante))

  datos_actualizar = pase_in.model_dump(exclude_unset=True)
  campos_opcionales = {"id_docente", "id_asignatura", "autorizador"}
  datos_actualizar = {
    campo: valor
    for campo, valor in datos_actualizar.items()
    if valor is not None or campo in campos_opcionales
  }

  if not datos_actualizar:
    return _pase_dto(pase_db)

  id_docente = datos_actualizar.get("id_docente", pase_db.id_docente)
  id_asignatura = datos_actualizar.get("id_asignatura", pase_db.id_asignatura)
  tipo = datos_actualizar.get("tipo", pase_db.tipo)
  fecha = datos_actualizar.get("fecha", pase_db.fecha)
  autorizador = datos_actualizar.get("autorizador", pase_db.autorizador)
  if autorizador is not None:
    autorizador = autorizador.strip() or None

  _validar_docente_asignatura(session, estudiante, id_docente, id_asignatura)
  _validar_autorizador(
    session,
    pase_db.id_estudiante,
    tipo,
    fecha,
    autorizador,
    excluir_id=pase_db.id,
  )

  for campo, valor in datos_actualizar.items():
    if campo == "autorizador":
      valor = autorizador
    setattr(pase_db, campo, valor)

  session.add(pase_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.pases,
    "ACTUALIZAR",
    f"Se actualizó el pase #{pase_db.id} de '{nombre_completo(estudiante)}'.",
  )

  session.commit()
  session.refresh(pase_db)

  return _pase_dto(pase_db)


@router.delete("/{pase_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_pase(
  pase_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
) -> None:
  pase_db = _obtener_pase_activo(session, pase_id)
  estudiante = pase_db.estudiante
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(estudiante))

  marcar_eliminado(session, pase_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.pases,
    "ELIMINAR",
    f"Se dio de baja el pase #{pase_db.id} de '{nombre_completo(estudiante)}'.",
  )

  session.commit()


def _ruta_archivo_segura(archivo_url: str | None) -> Path:
  if not archivo_url or not existe_archivo(archivo_url):
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="El archivo adjunto no está disponible localmente",
    )
  return ruta_absoluta(archivo_url)


@router.post("/{pase_id}/archivo", response_model=PeticionPase)
def subir_pase_archivo(
  pase_id: int,
  archivo: UploadFile = File(...),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  pase = _obtener_pase_activo(session, pase_id)
  estudiante = pase.estudiante
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(estudiante))

  try:
    nombre_base, extension, mime, contenido = validar_upload(archivo)
  except ValueError as error:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

  seccion = estudiante.seccion
  ruta_relativa = ruta_relativa_imagen(
    seccion.periodo_lectivo,
    "pases",
    seccion.grado.numero,
    seccion.letra,
    seccion.grado.nivel,
    estudiante.id,
    pase.id,
    extension,
  )
  guardar_archivo(ruta_relativa, contenido)
  registrar_meta_archivo(
    pase, ruta_relativa, nombre_base, mime, contenido, usuario_actual.id
  )

  session.add(pase)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.pases,
    "SUBIR ARCHIVO",
    (
      f"Subió el adjunto '{nombre_base}' ({len(contenido)} bytes) "
      f"del pase #{pase.id} de '{nombre_completo(estudiante)}'."
    ),
  )

  session.commit()
  session.refresh(pase)
  return _pase_dto(pase)


@router.get("/{pase_id}/archivo")
def descargar_pase_archivo(
  pase_id: int,
  inline: bool = Query(default=False),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
):
  pase = _obtener_pase_activo(session, pase_id)
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(pase.estudiante))

  ruta = _ruta_archivo_segura(pase.archivo_url)

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.pases,
    "DESCARGAR ARCHIVO",
    (
      f"Descargó el adjunto '{pase.archivo_nombre}' "
      f"del pase #{pase.id} de '{nombre_completo(pase.estudiante)}'."
    ),
  )
  session.flush()
  session.commit()

  return FileResponse(
    path=str(ruta),
    media_type=pase.archivo_mime or "application/octet-stream",
    filename=pase.archivo_nombre or f"pase-{pase.id}",
    content_disposition_type="inline" if inline else "attachment",
  )


@router.delete("/{pase_id}/archivo", status_code=status.HTTP_204_NO_CONTENT)
def quitar_pase_archivo(
  pase_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_personal),
) -> None:
  pase = _obtener_pase_activo(session, pase_id)
  estudiante = pase.estudiante
  validar_acceso_nivel(usuario_actual, _nivel_estudiante(estudiante))

  quitar_meta_archivo(pase)
  session.add(pase)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.pases,
    "QUITAR ARCHIVO",
    f"Quitó el adjunto del pase #{pase.id} de '{nombre_completo(estudiante)}'.",
  )

  session.commit()

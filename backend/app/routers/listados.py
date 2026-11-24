"""Router de PDFs de listados institucionales (nóminas, representantes, horarios)."""

import zipfile
from io import BytesIO

from fastapi import (
  APIRouter,
  Depends,
  HTTPException,
  Response,
  status,
)
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  paginar,
)
from app.models.db import (
  DocumentosGenerados,
  Grados,
  PeriodosLectivos,
  Secciones,
  Usuarios,
)
from app.models.enums import (
  ModuloAuditoria,
  NivelEducativo,
  RolesUsuario,
  TipoDocumento,
)
from app.models.schemas import PeticionDocumentoGenerado, SolicitudListado
from app.models.session import get_session
from app.services import listados as servicio_listados
from app.utils.auditoria import registrar_auditoria
from app.utils.fechas import ahora_caracas
from app.utils.pdf import construir_pdf, construir_pdf_horarios
from app.utils.periodos import etiqueta_periodo, periodo_lectivo_efectivo
from app.utils.security import (
  obtener_usuario_actual,
  requerir_roles,
  validar_acceso_nivel,
)
from app.utils.storage import (
  guardar_archivo,
  hash_contenido,
  leer_archivo,
  nombre_unico,
  ruta_absoluta,
)

router = APIRouter(prefix="/listados", tags=["Listados"])
requerir_admin = requerir_roles(RolesUsuario.administrador)


def _validar_periodo_lectivo(
  session: Session, periodo_lectivo: int
) -> PeriodosLectivos:
  periodo = session.exec(
    select(PeriodosLectivos).where(
      PeriodosLectivos.anio == periodo_lectivo,
      PeriodosLectivos.fecha_eliminacion.is_(None),
    )
  ).first()
  if not periodo:
    raise HTTPException(404, "Periodo lectivo no encontrado")
  return periodo


def _obtener_seccion(session: Session, id_seccion: int) -> Secciones:
  seccion = session.get(Secciones, id_seccion)
  if not seccion or seccion.fecha_eliminacion is not None:
    raise HTTPException(404, "Sección no encontrada")
  return seccion


def _validar_grado_activo(session: Session, id_grado: int) -> Grados:
  grado = session.get(Grados, id_grado)
  if not grado or grado.fecha_eliminacion is not None:
    raise HTTPException(404, "Grado no encontrado")
  return grado


def _resolver_filtros(
  session: Session, usuario_actual: Usuarios, peticion: SolicitudListado
):
  """Valida y completa filtros para generar un listado PDF.

  Devuelve `(periodo, nivel, seccion, grado)`.
  """
  seccion = None
  grado = None
  nivel = peticion.nivel
  periodo = peticion.periodo_lectivo

  if peticion.id_seccion is not None:
    seccion = _obtener_seccion(session, peticion.id_seccion)
    grado = seccion.grado
    if periodo is None:
      periodo = seccion.periodo_lectivo
    elif periodo != seccion.periodo_lectivo:
      raise HTTPException(
        status_code=400,
        detail="La sección no pertenece al periodo solicitado",
      )
    nivel = grado.nivel
  elif peticion.id_grado is not None:
    grado = _validar_grado_activo(session, peticion.id_grado)
    if nivel is not None and nivel != grado.nivel:
      raise HTTPException(
        status_code=400, detail="El grado no pertenece al nivel solicitado"
      )
    nivel = nivel or grado.nivel

  if periodo is None:
    periodo = periodo_lectivo_efectivo(session, None)
  if periodo is None:
    raise HTTPException(400, "Indica periodo_lectivo")

  periodo_obj = _validar_periodo_lectivo(session, periodo)
  if nivel is None:
    raise HTTPException(400, "Necesita indicar nivel para listados generales")

  validar_acceso_nivel(usuario_actual, nivel)
  return periodo_obj.anio, nivel, seccion, grado


def _dto(registro: DocumentosGenerados) -> PeticionDocumentoGenerado:
  grado = registro.grado
  return PeticionDocumentoGenerado(
    id=registro.id,
    tipo=registro.tipo,
    periodo_lectivo=registro.periodo_lectivo,
    nivel=registro.nivel,
    id_grado=registro.id_grado,
    id_seccion=registro.id_seccion,
    nombre_archivo=registro.nombre_archivo,
    ruta_relativa=registro.ruta_relativa,
    hash=registro.hash,
    tamano=registro.tamano,
    mime=registro.mime,
    fecha_generacion=registro.fecha_generacion,
    generado_por=registro.generado_por,
    grado_numero=grado.numero if grado else None,
    grado_nombre=grado.nombre if grado else None,
  )


@router.post(
  "/{tipo}",
  response_model=PeticionDocumentoGenerado,
  status_code=status.HTTP_201_CREATED,
)
def generar_listado(
  tipo: TipoDocumento,
  peticion: SolicitudListado,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  """Genera y guarda un PDF de listados: por sección o general por nivel."""
  periodo, nivel, seccion, grado = _resolver_filtros(session, usuario_actual, peticion)
  if tipo == TipoDocumento.horarios:
    if seccion is None:
      raise HTTPException(400, "Los horarios requieren sección")
    if seccion.grado.nivel != NivelEducativo.liceo:
      raise HTTPException(400, "Los horarios solo aplican a secciones de liceo")

  documento = servicio_listados.construir_documento(
    tipo, periodo, nivel, grado, seccion, session
  )
  if tipo == TipoDocumento.horarios:
    assert documento.horario_cabecera is not None
    assert documento.horario_filas is not None
    assert documento.horario_docentes is not None
    pdf = construir_pdf_horarios(
      documento.horario_cabecera,
      documento.horario_filas,
      documento.horario_docentes,
    )
  else:
    pdf = construir_pdf(
      documento.titulo,
      documento.encabezados,
      documento.filas,
      col_anchos=documento.col_anchos,
      nivel=nivel.value if nivel else None,
      grado=None,
      seccion=documento.seccion_descripcion,
      periodo_lectivo=etiqueta_periodo(periodo),
    )
  ruta_relativa = servicio_listados.ruta_relativa_listado(
    tipo, periodo, nivel, documento.grado, seccion, documento.nombre_archivo
  )
  # Versionado: no sobrescribir un PDF que ya existe.
  nombre_archivo = nombre_unico(ruta_relativa, documento.nombre_archivo)
  ruta_relativa = ruta_relativa.replace(documento.nombre_archivo, nombre_archivo)
  guardar_archivo(ruta_relativa, pdf)

  registro = DocumentosGenerados(
    tipo=tipo,
    periodo_lectivo=periodo,
    nivel=nivel,
    id_grado=documento.grado_id,
    id_seccion=documento.seccion_id,
    nombre_archivo=nombre_archivo,
    ruta_relativa=ruta_relativa,
    hash=hash_contenido(pdf),
    tamano=len(pdf),
    mime="application/pdf",
    fecha_generacion=ahora_caracas(),
    generado_por=usuario_actual.id,
  )
  session.add(registro)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.documentos,
    "GENERAR",
    f"Generó el documento {registro.nombre_archivo} ({tipo.value}).",
  )
  session.commit()
  session.refresh(registro)
  return _dto(registro)


@router.get("/documentos", response_model=RespuestaPaginada[PeticionDocumentoGenerado])
def listar_documentos(
  tipo: TipoDocumento | None = None,
  periodo_lectivo: int | None = None,
  nivel: NivelEducativo | None = None,
  id_grado: int | None = None,
  id_seccion: int | None = None,
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  consulta = select(DocumentosGenerados).where(
    DocumentosGenerados.fecha_eliminacion.is_(None)
  )
  periodo_lectivo = periodo_lectivo_efectivo(session, periodo_lectivo)
  if tipo is not None:
    consulta = consulta.where(DocumentosGenerados.tipo == tipo)
  if periodo_lectivo is not None:
    consulta = consulta.where(DocumentosGenerados.periodo_lectivo == periodo_lectivo)
  if nivel is not None:
    consulta = consulta.where(DocumentosGenerados.nivel == nivel)
  if id_grado is not None:
    consulta = consulta.where(DocumentosGenerados.id_grado == id_grado)
  if id_seccion is not None:
    consulta = consulta.where(DocumentosGenerados.id_seccion == id_seccion)
  consulta = consulta.order_by(DocumentosGenerados.fecha_generacion.desc())

  items, total = paginar(session, consulta, paginacion)
  return construir_pagina([_dto(d) for d in items], total, paginacion)


@router.get("/documentos/{documento_id}/archivo")
def descargar_documento(
  documento_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  documento = session.get(DocumentosGenerados, documento_id)
  if not documento or documento.fecha_eliminacion is not None:
    raise HTTPException(404, "Documento no encontrado")
  if documento.nivel is not None:
    validar_acceso_nivel(usuario_actual, documento.nivel)

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.documentos,
    "DESCARGAR_ARCHIVO",
    f"Descargó el PDF {documento.nombre_archivo} (#{documento.id}).",
  )
  session.flush()
  session.commit()

  return FileResponse(
    path=str(ruta_absoluta(documento.ruta_relativa)),
    media_type=documento.mime or "application/pdf",
    filename=documento.nombre_archivo or f"listado-{documento.id}.pdf",
    content_disposition_type="attachment",
  )


@router.get("/documentos/paquete")
def descargar_paquete(
  tipo: TipoDocumento,
  periodo_lectivo: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  """ZIP con todos los PDFs de un tipo y periodo lectivo."""
  documentos = session.exec(
    select(DocumentosGenerados).where(
      DocumentosGenerados.tipo == tipo,
      DocumentosGenerados.periodo_lectivo == periodo_lectivo,
      DocumentosGenerados.fecha_eliminacion.is_(None),
    )
  ).all()

  buf = BytesIO()
  with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    for doc in documentos:
      z.writestr(doc.ruta_relativa, leer_archivo(doc.ruta_relativa))

  return Response(
    content=buf.getvalue(),
    media_type="application/zip",
    headers={"Content-Disposition": 'attachment; filename="listados.zip"'},
  )

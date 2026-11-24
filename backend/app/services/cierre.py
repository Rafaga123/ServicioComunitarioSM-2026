"""Servicios para cerrar el año lectivo: generar listados y traspasar estudiantes.

Flujo de `POST /api/gestion/cerrar-anio`:
1. Validar periodo actual (activo) y periodo siguiente (¿existe? crear).
2. Generar PDFs de listados (nóminas/representantes/horarios-liceo por sección
   y docentes generales por nivel) en RAM y guardarlos en staging.
3. Mover los archivos staging → destino final en STORAGE_ROOT.
4. En una sola transacción: insertar los `DocumentosGenerados` y ejecutar el
   traspaso de estudiantes (6to Año→egreso, grados intermedios→siguiente).
5. Commit. Si falla, se revierten inserts y se eliminan archivos movidos.
"""

import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import STORAGE_ROOT
from app.models.db import (
  Asignaturas,
  DocumentosGenerados,
  Estudiantes,
  Grados,
  PeriodosLectivos,
  Secciones,
)
from app.models.enums import ModuloAuditoria, NivelEducativo, TipoDocumento
from app.models.schemas import PeticionCierreAnio
from app.services import listados as servicio_listados
from app.utils.auditoria import registrar_auditoria
from app.utils.fechas import ahora_caracas
from app.utils.pdf import construir_pdf, construir_pdf_horarios
from app.utils.periodos import etiqueta_periodo
from app.utils.storage import hash_contenido, nombre_unico, ruta_absoluta

GRADOS_PROMOVIDOS_MAX = 11  # 11 = 5to Año, último grado del liceo (egreso)


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


def _obtener_o_crear_periodo_siguiente(
  session: Session, periodo_siguiente: int
) -> PeriodosLectivos:
  periodo = session.exec(
    select(PeriodosLectivos).where(
      PeriodosLectivos.anio == periodo_siguiente,
      PeriodosLectivos.fecha_eliminacion.is_(None),
    )
  ).first()
  if periodo is None:
    periodo = PeriodosLectivos(anio=periodo_siguiente, activo=True, cerrado=False)
    session.add(periodo)
    session.flush()
  elif periodo.cerrado:
    raise HTTPException(
      status_code=400,
      detail="El periodo siguiente ya está cerrado; crea uno nuevo",
    )

  secciones_nuevas = session.exec(
    select(Secciones).where(
      Secciones.periodo_lectivo == periodo_siguiente,
      Secciones.fecha_eliminacion.is_(None),
    )
  ).all()
  if secciones_nuevas:
    raise HTTPException(
      status_code=400,
      detail="El periodo siguiente ya tiene secciones creadas",
    )

  return periodo


def _secciones_activas(session: Session, periodo_lectivo: int) -> list[Secciones]:
  return session.exec(
    select(Secciones)
    .where(
      Secciones.periodo_lectivo == periodo_lectivo,
      Secciones.fecha_eliminacion.is_(None),
    )
    .order_by(Secciones.id)
  ).all()


def _estudiantes_activos_periodo(
  session: Session, periodo_lectivo: int
) -> list[Estudiantes]:
  return session.exec(
    select(Estudiantes)
    .join(Secciones, Estudiantes.id_seccion == Secciones.id)
    .where(
      Estudiantes.fecha_eliminacion.is_(None),
      Secciones.fecha_eliminacion.is_(None),
      Secciones.periodo_lectivo == periodo_lectivo,
    )
    .order_by(Estudiantes.id)
  ).all()


def _crear_secciones_nuevas(
  session: Session,
  periodo_siguiente: int,
  secciones_actuales: list[Secciones],
) -> dict[tuple[int, str], Secciones]:
  """Replica las secciones reales del periodo y crea sus destinos.

  Solo se crean las combinaciones (grado, letra) que existen actualmente y la
  sección destino (grado + 1, misma letra) de cada cohorte. Los estudiantes de
  `GRADOS_PROMOVIDOS_MAX` egresan, por lo que no requieren sección destino.
  """
  grados = {
    g.numero: g
    for g in session.exec(select(Grados).where(Grados.fecha_eliminacion.is_(None)))
  }

  combinaciones = {(s.grado.numero, s.letra) for s in secciones_actuales}
  destinos = {
    (numero + 1, letra)
    for numero, letra in combinaciones
    if numero < GRADOS_PROMOVIDOS_MAX
  }

  grados_faltantes = sorted({numero for numero, _ in destinos} - grados.keys())
  if grados_faltantes:
    raise HTTPException(
      status_code=400,
      detail=(
        f"No existe el grado destino {grados_faltantes[0]} en el catálogo de grados"
      ),
    )

  creadas: dict[tuple[int, str], Secciones] = {}
  for numero, letra in sorted(combinaciones | destinos):
    seccion = Secciones(
      id_grado=grados[numero].id,
      letra=letra,
      periodo_lectivo=periodo_siguiente,
      id_docente_titular=None,
    )
    session.add(seccion)
    session.flush()
    creadas[(numero, letra)] = seccion
  return creadas


def _clonar_asignaturas(
  session: Session, periodo_actual: int, periodo_siguiente: int
) -> int:
  """Copia los nombres de asignaturas de liceo al nuevo periodo sin docentes."""
  asignaturas = session.exec(
    select(Asignaturas)
    .join(Grados, Asignaturas.id_grado == Grados.id)
    .where(
      Asignaturas.periodo_lectivo == periodo_actual,
      Asignaturas.fecha_eliminacion.is_(None),
      Grados.nivel == NivelEducativo.liceo,
      Grados.fecha_eliminacion.is_(None),
    )
  ).all()

  creadas = 0
  for asignatura in asignaturas:
    session.add(
      Asignaturas(
        id_grado=asignatura.id_grado,
        nombre=asignatura.nombre,
        periodo_lectivo=periodo_siguiente,
      )
    )
    creadas += 1
  session.flush()
  return creadas


def _guardar_doc_staged(
  session: Session,
  usuario: object,
  tipo: TipoDocumento,
  periodo: int,
  nivel: NivelEducativo,
  grado: Grados,
  seccion: Secciones,
  staging_root: Path,
) -> DocumentosGenerados:
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
  nombre_archivo = nombre_unico(ruta_relativa, documento.nombre_archivo)
  ruta_relativa = ruta_relativa.replace(documento.nombre_archivo, nombre_archivo)

  staging_file = staging_root / ruta_relativa
  staging_file.parent.mkdir(parents=True, exist_ok=True)
  staging_file.write_bytes(pdf)

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
    generado_por=usuario.id,
  )
  session.add(registro)
  return registro


def _guardar_doc_general_staged(
  session: Session,
  usuario: object,
  tipo: TipoDocumento,
  periodo: int,
  nivel: NivelEducativo,
  staging_root: Path,
) -> DocumentosGenerados:
  """Prepara un PDF general por nivel (p. ej. el listado de docentes)."""
  documento = servicio_listados.construir_documento(
    tipo, periodo, nivel, None, None, session
  )
  pdf = construir_pdf(
    documento.titulo,
    documento.encabezados,
    documento.filas,
    col_anchos=documento.col_anchos,
    nivel=nivel.value,
    seccion=documento.seccion_descripcion,
    periodo_lectivo=etiqueta_periodo(periodo),
  )
  ruta_relativa = servicio_listados.ruta_relativa_listado(
    tipo, periodo, nivel, None, None, documento.nombre_archivo
  )
  nombre_archivo = nombre_unico(ruta_relativa, documento.nombre_archivo)
  ruta_relativa = ruta_relativa.replace(documento.nombre_archivo, nombre_archivo)

  staging_file = staging_root / ruta_relativa
  staging_file.parent.mkdir(parents=True, exist_ok=True)
  staging_file.write_bytes(pdf)

  registro = DocumentosGenerados(
    tipo=tipo,
    periodo_lectivo=periodo,
    nivel=nivel,
    nombre_archivo=nombre_archivo,
    ruta_relativa=ruta_relativa,
    hash=hash_contenido(pdf),
    tamano=len(pdf),
    mime="application/pdf",
    fecha_generacion=ahora_caracas(),
    generado_por=usuario.id,
  )
  session.add(registro)
  return registro


def cerrar_anio(
  session: Session,
  usuario,
  periodo_actual: int,
  periodo_siguiente: int,
) -> PeticionCierreAnio:
  pa = _validar_periodo_lectivo(session, periodo_actual)
  if not pa.activo:
    raise HTTPException(status_code=400, detail="El periodo actual no está activo")
  if pa.cerrado:
    raise HTTPException(status_code=400, detail="El periodo actual ya está cerrado")
  if periodo_siguiente <= periodo_actual:
    raise HTTPException(
      status_code=400,
      detail="El periodo siguiente debe ser mayor al actual",
    )

  staging_root = Path(STORAGE_ROOT) / ".staging" / str(uuid.uuid4())
  documentos: list[DocumentosGenerados] = []
  movidos: list[Path] = []
  promovidos = 0
  egresados = 0
  secciones_nuevas: dict[tuple[int, str], Secciones] = {}
  asignaturas_creadas = 0
  completado = False

  try:
    ps = _obtener_o_crear_periodo_siguiente(session, periodo_siguiente)

    # 1. Generar PDFs de listados por sección activa.
    for seccion in _secciones_activas(session, pa.anio):
      nivel = seccion.grado.nivel
      documentos.append(
        _guardar_doc_staged(
          session,
          usuario,
          TipoDocumento.nominas,
          pa.anio,
          nivel,
          seccion.grado,
          seccion,
          staging_root,
        )
      )
      documentos.append(
        _guardar_doc_staged(
          session,
          usuario,
          TipoDocumento.representantes,
          pa.anio,
          nivel,
          seccion.grado,
          seccion,
          staging_root,
        )
      )
      if nivel == NivelEducativo.liceo:
        documentos.append(
          _guardar_doc_staged(
            session,
            usuario,
            TipoDocumento.horarios,
            pa.anio,
            nivel,
            seccion.grado,
            seccion,
            staging_root,
          )
        )

    # 1b. Listado general de docentes por nivel.
    for nivel in (NivelEducativo.escuela, NivelEducativo.liceo):
      documentos.append(
        _guardar_doc_general_staged(
          session,
          usuario,
          TipoDocumento.docentes,
          pa.anio,
          nivel,
          staging_root,
        )
      )

    # 2. Mover archivos de staging al destino final.
    for doc in documentos:
      destino = ruta_absoluta(doc.ruta_relativa)
      destino.parent.mkdir(parents=True, exist_ok=True)
      if destino.exists():
        # Ya existe el PDF en destino: no se registra ni se cuenta.
        (staging_root / doc.ruta_relativa).unlink(missing_ok=True)
        if doc.id is None:
          session.expunge(doc)
        else:
          session.delete(doc)
        continue
      shutil.move(str(staging_root / doc.ruta_relativa), str(destino))
      movidos.append(destino)

    # 3. Traspaso de estudiantes y clonación de estructura.
    secciones_nuevas = _crear_secciones_nuevas(
      session, ps.anio, _secciones_activas(session, pa.anio)
    )
    promovidos, egresados = _traspasar_estudiantes(
      session, pa.anio, ps.anio, secciones_nuevas
    )
    asignaturas_creadas = _clonar_asignaturas(session, pa.anio, ps.anio)

    # 4. Cerrar periodo actual y activar el nuevo.
    pa.cerrado = True
    pa.activo = False
    pa.fecha_cierre = ahora_caracas()
    for otro in session.exec(
      select(PeriodosLectivos).where(
        PeriodosLectivos.id != ps.id,
        PeriodosLectivos.activo.is_(True),
        PeriodosLectivos.fecha_eliminacion.is_(None),
      )
    ).all():
      otro.activo = False
    ps.activo = True

    registrar_auditoria(
      session,
      usuario.id,
      ModuloAuditoria.cierre_anio,
      "CIERRE_ANIO",
      f"Se cerró el periodo lectivo {pa.anio} y se activó {ps.anio}.",
    )

    session.flush()
    session.commit()
    completado = True

    return PeticionCierreAnio(
      periodo_cerrado=pa.anio,
      periodo_activado=ps.anio,
      documentos_generados=len(movidos),
      estudiantes_promovidos=promovidos,
      egresados=egresados,
      secciones_creadas=len(secciones_nuevas),
      asignaturas_creadas=asignaturas_creadas,
    )

  except Exception:
    session.rollback()
    raise
  finally:
    if not completado:
      for destino in movidos:
        destino.unlink(missing_ok=True)
    shutil.rmtree(staging_root, ignore_errors=True)


def _traspasar_estudiantes(
  session: Session,
  periodo_actual: int,
  periodo_siguiente: int,
  secciones_nuevas: dict[tuple[int, str], Secciones],
) -> tuple[int, int]:
  """Ejecuta el traspaso de estudiantes activos del periodo actual.

  Devuelve (promovidos, egresados). 6to Grado → 1er Año, intermedios →
  siguiente grado; 5to Año → egreso.
  """
  estudiantes = _estudiantes_activos_periodo(session, periodo_actual)
  promovidos = 0
  egresados = 0

  for estudiante in estudiantes:
    seccion = estudiante.seccion
    grado = seccion.grado

    if grado.numero == GRADOS_PROMOVIDOS_MAX:  # último grado -> egreso
      estudiante.fecha_egreso = ahora_caracas()
      egresados += 1
      continue

    nueva_seccion = secciones_nuevas.get((grado.numero + 1, seccion.letra))
    if nueva_seccion is None:
      raise HTTPException(
        status_code=500,
        detail="No se encontró la sección destino para promover un estudiante",
      )
    estudiante.id_seccion = nueva_seccion.id
    promovidos += 1

  return promovidos, egresados

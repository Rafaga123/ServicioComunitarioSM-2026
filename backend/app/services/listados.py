"""Generación de PDFs de listados institucionales.

Construye los datos de nóminas, representantes y horarios de una sección
(o general por nivel/periodo) para ser convertidos a PDF por el router
`routers/listados.py`.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sqlmodel import Session, select

from app.models.db import (
  Asignaturas,
  BloquesHorarios,
  Docentes,
  Estudiantes,
  Grados,
  Horarios,
  Representantes,
  Secciones,
)
from app.models.enums import NivelEducativo, TipoDocumento
from app.utils.nombres import nombre_completo
from app.utils.storage import GRADO_SLUGS

DIAS_SEMANA = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes"}


@dataclass
class DocumentoListado:
  seccion_id: int | None
  grado_id: int | None
  grado: Grados | None
  nombre_archivo: str
  filas: list[list[str]]
  encabezados: list[str]
  col_anchos: list[float]
  titulo: str
  seccion_descripcion: str | None


def _nombre_archivo(
  tipo: TipoDocumento,
  periodo: int,
  nivel: NivelEducativo,
  grado: Grados | None,
  seccion: Secciones | None,
) -> str:
  stem = {
    "nominas": "nomina",
    "representantes": "representantes",
    "horarios": "horario",
  }[tipo.value]
  if grado is not None and seccion is not None:
    slug = GRADO_SLUGS.get(grado.numero, grado.nombre.lower().replace(" ", "_"))
    return f"{stem}_{periodo}_{slug}_{seccion.letra}.pdf"
  return f"{stem}_{periodo}_{nivel.value}_general.pdf"


def _titulo(
  tipo: TipoDocumento,
  nivel: NivelEducativo,
  grado: Grados | None,
  seccion: Secciones | None,
) -> str:
  if seccion is not None and grado is not None:
    return f"{tipo.value} — {grado.nombre} {seccion.letra}"
  return f"{tipo.value} — {nivel.value} general"


# =====
# Consultas por sección
# =====
def _filas_nominas_seccion(session: Session, seccion: Secciones) -> list[list[str]]:
  estudiantes = session.exec(
    select(Estudiantes)
    .where(
      Estudiantes.id_seccion == seccion.id,
      Estudiantes.fecha_eliminacion.is_(None),
    )
    .order_by(Estudiantes.primer_apellido, Estudiantes.primer_nombre, Estudiantes.id)
  ).all()
  return [
    [
      e.cedula_estudiantil,
      nombre_completo(e),
      nombre_completo(e.representante) if e.representante else "-",
      e.representante.telefono if e.representante else "-",
    ]
    for e in estudiantes
  ]


def _filas_representantes_seccion(
  session: Session, seccion: Secciones
) -> list[list[str]]:
  repes = session.exec(
    select(Representantes)
    .join(Estudiantes, Estudiantes.id_representante == Representantes.id)
    .where(
      Estudiantes.id_seccion == seccion.id,
      Estudiantes.fecha_eliminacion.is_(None),
      Representantes.fecha_eliminacion.is_(None),
    )
    .distinct()
    .order_by(
      Representantes.primer_apellido, Representantes.primer_nombre, Representantes.id
    )
  ).all()
  filas = []
  for rep in repes:
    ests = session.exec(
      select(Estudiantes)
      .where(
        Estudiantes.id_representante == rep.id,
        Estudiantes.id_seccion == seccion.id,
        Estudiantes.fecha_eliminacion.is_(None),
      )
      .order_by(Estudiantes.primer_apellido, Estudiantes.primer_nombre, Estudiantes.id)
    ).all()
    filas.append(
      [
        nombre_completo(rep),
        rep.telefono,
        "; ".join(nombre_completo(e) for e in ests) or "-",
      ]
    )
  return filas


def _filas_horarios_seccion(session: Session, seccion: Secciones) -> list[list[str]]:
  horarios = session.exec(
    select(Horarios)
    .join(BloquesHorarios, Horarios.id_bloque == BloquesHorarios.id)
    .join(Asignaturas, Horarios.id_asignatura == Asignaturas.id)
    .join(Docentes, Horarios.id_docente == Docentes.id)
    .where(
      Horarios.id_seccion == seccion.id,
      Horarios.fecha_eliminacion.is_(None),
    )
    .order_by(Horarios.dia_semana, BloquesHorarios.orden)
  ).all()
  return [
    [
      DIAS_SEMANA[h.dia_semana],
      h.bloque.nombre,
      str(h.bloque.hora_inicio),
      str(h.bloque.hora_fin),
      h.asignatura.nombre,
      nombre_completo(h.docente),
    ]
    for h in horarios
  ]


# =====
# Consultas general (por nivel y periodo, sin sección)
# =====
def _filas_nominas_general(
  session: Session, periodo: int, nivel: NivelEducativo
) -> list[list[str]]:
  estudiantes = session.exec(
    select(Estudiantes)
    .join(Secciones, Estudiantes.id_seccion == Secciones.id)
    .join(Grados, Secciones.id_grado == Grados.id)
    .where(
      Secciones.periodo_lectivo == periodo,
      Grados.nivel == nivel,
      Estudiantes.fecha_eliminacion.is_(None),
      Secciones.fecha_eliminacion.is_(None),
      Grados.fecha_eliminacion.is_(None),
    )
    .order_by(Estudiantes.primer_apellido, Estudiantes.primer_nombre, Estudiantes.id)
  ).all()
  return [
    [
      e.cedula_estudiantil,
      nombre_completo(e),
      f"{e.seccion.grado.nombre} {e.seccion.letra}",
      nombre_completo(e.representante) if e.representante else "-",
      e.representante.telefono if e.representante else "-",
    ]
    for e in estudiantes
  ]


def _filas_representantes_general(
  session: Session, periodo: int, nivel: NivelEducativo
) -> list[list[str]]:
  repes = session.exec(
    select(Representantes)
    .join(Estudiantes, Estudiantes.id_representante == Representantes.id)
    .join(Secciones, Estudiantes.id_seccion == Secciones.id)
    .join(Grados, Secciones.id_grado == Grados.id)
    .where(
      Secciones.periodo_lectivo == periodo,
      Grados.nivel == nivel,
      Estudiantes.fecha_eliminacion.is_(None),
      Secciones.fecha_eliminacion.is_(None),
      Representantes.fecha_eliminacion.is_(None),
    )
    .distinct()
    .order_by(
      Representantes.primer_apellido, Representantes.primer_nombre, Representantes.id
    )
  ).all()
  filas = []
  for rep in repes:
    ests = session.exec(
      select(Estudiantes)
      .join(Secciones, Estudiantes.id_seccion == Secciones.id)
      .join(Grados, Secciones.id_grado == Grados.id)
      .where(
        Estudiantes.id_representante == rep.id,
        Secciones.periodo_lectivo == periodo,
        Grados.nivel == nivel,
        Estudiantes.fecha_eliminacion.is_(None),
        Secciones.fecha_eliminacion.is_(None),
      )
      .order_by(Estudiantes.primer_apellido, Estudiantes.primer_nombre, Estudiantes.id)
    ).all()
    filas.append(
      [
        nombre_completo(rep),
        rep.telefono,
        "; ".join(nombre_completo(e) for e in ests) or "-",
      ]
    )
  return filas


FILAS_POR_SECCION: dict[
  TipoDocumento, Callable[[Session, Secciones], list[list[str]]]
] = {
  TipoDocumento.nominas: _filas_nominas_seccion,
  TipoDocumento.representantes: _filas_representantes_seccion,
  TipoDocumento.horarios: _filas_horarios_seccion,
}

FILAS_GENERAL: dict[
  TipoDocumento, Callable[[Session, int, NivelEducativo], list[list[str]]]
] = {
  TipoDocumento.nominas: _filas_nominas_general,
  TipoDocumento.representantes: _filas_representantes_general,
}

HEADERS: dict[TipoDocumento, list[str]] = {
  TipoDocumento.nominas: ["Cédula", "Estudiante", "Representante", "Teléfono"],
  TipoDocumento.representantes: ["Representante", "Teléfono", "Estudiantes asociados"],
  TipoDocumento.horarios: ["Día", "Bloque", "Hora", "Asignatura", "Docente"],
}

COL_ANCHOS: dict[TipoDocumento, list[float]] = {
  TipoDocumento.nominas: [4.0, 8.0, 8.0, 6.0],
  TipoDocumento.representantes: [10.0, 6.0, 40.0],
  TipoDocumento.horarios: [4.0, 8.0, 6.0, 5.0, 8.0, 10.0],
}


def construir_documento(
  tipo: TipoDocumento,
  periodo: int,
  nivel: NivelEducativo,
  grado: Grados | None,
  seccion: Secciones | None,
  session: Session,
) -> DocumentoListado:
  """Resuelve las filas para un listado según tipo, nivel, grado y sección."""
  if seccion is not None:
    nombre_archivo = _nombre_archivo(tipo, periodo, nivel, grado, seccion)
    descripcion = f"{grado.nombre if grado else nivel.value} {seccion.letra}"
    filas = FILAS_POR_SECCION[tipo](session, seccion)
  else:
    nombre_archivo = _nombre_archivo(tipo, periodo, nivel, None, None)
    descripcion = f"{nivel.value} general"
    filas = FILAS_GENERAL[tipo](session, periodo, nivel)

  return DocumentoListado(
    seccion_id=seccion.id if seccion else None,
    grado_id=grado.id if grado else None,
    grado=grado,
    nombre_archivo=nombre_archivo,
    filas=filas,
    encabezados=HEADERS[tipo],
    col_anchos=COL_ANCHOS[tipo],
    titulo=_titulo(tipo, nivel, grado, seccion),
    seccion_descripcion=descripcion,
  )


def ruta_relativa_listado(
  tipo: TipoDocumento,
  periodo: int,
  nivel: NivelEducativo,
  grado: Grados | None,
  seccion: Secciones | None,
  nombre_archivo: str,
) -> str:
  """Ruta relativa dentro de STORAGE_ROOT del PDF generado.

  Sección: `listados/nominas/LICEO/1er_ano/A/nomina_2027_1er_ano_A.pdf`.
  General: `listados/nominas/LICEO/general/nomina_2027_LICEO_general.pdf`.
  """
  if seccion is not None:
    slug = GRADO_SLUGS.get(grado.numero, "general")
    return (
      f"listados/{tipo.value}/{nivel.value}/{slug}/{seccion.letra}/{nombre_archivo}"
    )
  return f"listados/{tipo.value}/{nivel.value}/general/{nombre_archivo}"

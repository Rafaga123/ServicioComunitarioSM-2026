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

TITULOS_DOCUMENTO = {
  TipoDocumento.nominas: "Listado de estudiantes",
  TipoDocumento.representantes: "Listado de representantes",
  TipoDocumento.horarios: "Horario de clases",
}


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
  periodo: int,
  nivel: NivelEducativo,
  grado: Grados | None,
  seccion: Secciones | None,
) -> str:
  titulo = TITULOS_DOCUMENTO[tipo]
  if seccion is not None and grado is not None:
    return f"{titulo} {periodo}/{grado.nombre} \"{seccion.letra.upper()}\""
  return f"{titulo} {periodo}/{nivel.value} general"


def _nombre_representante(representante: Representantes | None) -> str:
  """Nombre del representante, o '-' cuando solo se conoce su teléfono."""
  if representante is None:
    return "-"
  return nombre_completo(representante) or "-"


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
      _nombre_representante(e.representante),
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
        _nombre_representante(rep),
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
      _nombre_representante(e.representante),
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
        _nombre_representante(rep),
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

HEADERS_SECCION: dict[TipoDocumento, list[str]] = {
  TipoDocumento.nominas: ["Cédula", "Estudiante", "Representante", "Teléfono"],
  TipoDocumento.representantes: ["Representante", "Teléfono", "Estudiantes asociados"],
  TipoDocumento.horarios: [
    "Día",
    "Bloque",
    "Inicio",
    "Fin",
    "Asignatura",
    "Docente",
  ],
}

HEADERS_GENERAL: dict[TipoDocumento, list[str]] = {
  TipoDocumento.nominas: [
    "Cédula",
    "Estudiante",
    "Grado / Sección",
    "Representante",
    "Teléfono",
  ],
  TipoDocumento.representantes: ["Representante", "Teléfono", "Estudiantes asociados"],
}

COL_ANCHOS_SECCION: dict[TipoDocumento, list[float]] = {
  TipoDocumento.nominas: [2.6, 4.3, 4.3, 2.6],
  TipoDocumento.representantes: [5.0, 2.8, 6.4],
  TipoDocumento.horarios: [1.9, 1.8, 1.3, 1.3, 4.1, 3.9],
}

COL_ANCHOS_GENERAL: dict[TipoDocumento, list[float]] = {
  TipoDocumento.nominas: [2.3, 3.4, 2.6, 3.5, 2.4],
  TipoDocumento.representantes: [5.0, 2.8, 6.4],
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
    # El encabezado del PDF muestra grado y sección en un solo campo.
    descripcion = f"{grado.nombre if grado else nivel.value} {seccion.letra}".strip()
    filas = FILAS_POR_SECCION[tipo](session, seccion)
    encabezados = HEADERS_SECCION[tipo]
    col_anchos = COL_ANCHOS_SECCION[tipo]
  else:
    nombre_archivo = _nombre_archivo(tipo, periodo, nivel, None, None)
    descripcion = "general"
    filas = FILAS_GENERAL[tipo](session, periodo, nivel)
    encabezados = HEADERS_GENERAL[tipo]
    col_anchos = COL_ANCHOS_GENERAL[tipo]

  return DocumentoListado(
    seccion_id=seccion.id if seccion else None,
    grado_id=grado.id if grado else None,
    grado=grado,
    nombre_archivo=nombre_archivo,
    filas=filas,
    encabezados=encabezados,
    col_anchos=col_anchos,
    titulo=_titulo(tipo, periodo, nivel, grado, seccion),
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

  El periodo es una carpeta para separar los listados de cada año.

  Sección: `listados/nominas/2027/LICEO/1er_ano/A/nomina_2027_1er_ano_A.pdf`.
  General: `listados/nominas/2027/LICEO/general/nomina_2027_LICEO_general.pdf`.
  """
  if seccion is not None:
    slug = GRADO_SLUGS.get(grado.numero, "general")
    return (
      f"listados/{tipo.value}/{periodo}/{nivel.value}/{slug}/"
      f"{seccion.letra}/{nombre_archivo}"
    )
  return f"listados/{tipo.value}/{periodo}/{nivel.value}/general/{nombre_archivo}"

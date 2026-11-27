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
from app.models.enums import NivelEducativo, TipoBloqueHorario, TipoDocumento
from app.utils.nombres import nombre_completo
from app.utils.periodos import etiqueta_periodo
from app.utils.storage import GRADO_SLUGS

DIAS_SEMANA = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes"}

# Etiquetas solicitadas para la malla impresa del liceo (se respetan tal cual,
# aunque difieran de la hora almacenada en `bloques_horarios`).
HORAS_MALLA_LICEO = {
  1: "7:00-7:40",
  2: "7:40-8:20",
  3: "8:20-8:40",
  4: "8:40-9:20",
  5: "9:20-10:00",
  6: "10:10-10:10",
  7: "10:10-10:50",
  8: "10:10-11:30",
  9: "11:30-12:10",
  10: "12:10-12:40",
}

TITULOS_DOCUMENTO = {
  TipoDocumento.nominas: "Listado de estudiantes",
  TipoDocumento.representantes: "Listado de representantes",
  TipoDocumento.horarios: "Horario de clases",
  TipoDocumento.docentes: "Listado de docentes",
}


@dataclass
class DocumentoListado:
  """Estructura intermedia con filas, encabezados y metadata para renderizar un listado."""
  seccion_id: int | None
  grado_id: int | None
  grado: Grados | None
  nombre_archivo: str
  filas: list[list[str]]
  encabezados: list[str]
  col_anchos: list[float]
  titulo: str
  seccion_descripcion: str | None
  horario_cabecera: dict[str, str] | None = None
  horario_filas: list[list[str]] | None = None
  horario_docentes: list[tuple[str, str]] | None = None


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
    "docentes": "docentes",
  }[tipo.value]
  etiqueta = etiqueta_periodo(periodo)
  if grado is not None and seccion is not None:
    slug = GRADO_SLUGS.get(grado.numero, grado.nombre.lower().replace(" ", "_"))
    return f"{stem}_{etiqueta}_{slug}_{seccion.letra}.pdf"
  if grado is not None:
    slug = GRADO_SLUGS.get(grado.numero, grado.nombre.lower().replace(" ", "_"))
    return f"{stem}_{etiqueta}_{slug}.pdf"
  return f"{stem}_{etiqueta}_{nivel.value}_general.pdf"


def _titulo(
  tipo: TipoDocumento,
  periodo: int,
  nivel: NivelEducativo,
  grado: Grados | None,
  seccion: Secciones | None,
) -> str:
  titulo = TITULOS_DOCUMENTO[tipo]
  etiqueta = etiqueta_periodo(periodo)
  if seccion is not None and grado is not None:
    return f'{titulo} {etiqueta}/{grado.nombre} "{seccion.letra.upper()}"'
  if grado is not None:
    return f"{titulo} {etiqueta}/{grado.nombre} general"
  return f"{titulo} {etiqueta}/{nivel.value} general"


def _nombre_representante(representante: Representantes | None) -> str:
  """Devuelve el nombre del representante o '-' si no hay nombre usable."""
  if representante is None:
    return "-"
  return nombre_completo(representante) or "-"


# Consultas por sección.
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


def _datos_horarios(
  session: Session, seccion: Secciones, periodo: int
) -> tuple[dict[str, str], list[list[str]], list[tuple[str, str]]]:
  """Devuelve cabecera, malla de 10 bloques y docentes de una sección.

  Las etiquetas de hora son las definidas en `HORAS_MALLA_LICEO`; la
  asignación de materias por día/bloque se toma de los horarios activos.
  """
  bloques = session.exec(
    select(BloquesHorarios)
    .where(BloquesHorarios.fecha_eliminacion.is_(None))
    .order_by(BloquesHorarios.orden)
  ).all()
  horarios = session.exec(
    select(Horarios).where(
      Horarios.id_seccion == seccion.id,
      Horarios.fecha_eliminacion.is_(None),
    )
  ).all()
  por_bloque_dia = {(h.id_bloque, h.dia_semana): h for h in horarios}

  filas: list[list[str]] = []
  for bloque in bloques:
    hora = HORAS_MALLA_LICEO.get(
      bloque.orden,
      f"{bloque.hora_inicio.strftime('%H:%M')}-{bloque.hora_fin.strftime('%H:%M')}",
    )
    if bloque.tipo == TipoBloqueHorario.receso:
      celdas = ["RECESO"] * 5
    else:
      celdas = []
      for dia in range(1, 6):
        horario = por_bloque_dia.get((bloque.id, dia))
        celdas.append(horario.asignatura.nombre if horario is not None else "/")
    filas.append([hora, *celdas])

  vistos: set[tuple[str, str]] = set()
  docentes: list[tuple[str, str]] = []
  for horario in sorted(horarios, key=lambda h: h.asignatura.nombre):
    clave = (horario.asignatura.nombre, nombre_completo(horario.docente))
    if clave not in vistos:
      vistos.add(clave)
      docentes.append(clave)

  cabecera = {
    "periodo": etiqueta_periodo(periodo),
    "curso": seccion.grado.nombre,
    "seccion": seccion.letra.upper(),
  }
  return cabecera, filas, docentes


# Consultas generales por nivel y periodo, sin sección.
def _filas_nominas_general(
  session: Session,
  periodo: int,
  nivel: NivelEducativo,
  grado: Grados | None = None,
) -> list[list[str]]:
  consulta = (
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
  )
  if grado is not None:
    consulta = consulta.where(Secciones.id_grado == grado.id)

  estudiantes = session.exec(
    consulta.order_by(
      Grados.numero,
      Secciones.letra,
      Estudiantes.primer_apellido,
      Estudiantes.primer_nombre,
      Estudiantes.id,
    )
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
  session: Session,
  periodo: int,
  nivel: NivelEducativo,
  grado: Grados | None = None,
) -> list[list[str]]:
  consulta_repes = (
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
  )
  if grado is not None:
    consulta_repes = consulta_repes.where(Secciones.id_grado == grado.id)

  repes = session.exec(
    consulta_repes.distinct().order_by(
      Representantes.primer_apellido, Representantes.primer_nombre, Representantes.id
    )
  ).all()
  filas = []
  for rep in repes:
    consulta_estudiantes = (
      select(Estudiantes)
      .join(Secciones, Estudiantes.id_seccion == Secciones.id)
      .join(Grados, Secciones.id_grado == Grados.id)
      .where(
        Estudiantes.id_representante == rep.id,
        Secciones.periodo_lectivo == periodo,
        Grados.nivel == nivel,
        Estudiantes.fecha_eliminacion.is_(None),
        Secciones.fecha_eliminacion.is_(None),
        Grados.fecha_eliminacion.is_(None),
      )
    )
    if grado is not None:
      consulta_estudiantes = consulta_estudiantes.where(
        Secciones.id_grado == grado.id
      )

    ests = session.exec(
      consulta_estudiantes.order_by(
        Estudiantes.primer_apellido, Estudiantes.primer_nombre, Estudiantes.id
      )
    ).all()
    filas.append(
      [
        _nombre_representante(rep),
        rep.telefono,
        "; ".join(nombre_completo(e) for e in ests) or "-",
      ]
    )
  return filas


def _filas_docentes_general(
  session: Session,
  periodo: int,
  nivel: NivelEducativo,
  grado: Grados | None = None,
) -> list[list[str]]:
  """Lista activa de docentes de un nivel con su detalle del periodo.

  `grado` se acepta por uniformidad con `FILAS_GENERAL`, pero se ignora:
  los docentes se listan siempre por nivel.

  En LICEO se muestran las asignaturas con el año correspondiente para no
  repetir `Matemática` de varios grados como si fuera la misma línea. En
  ESCUELA se muestran los grados/secciones donde el docente es titular.
  """
  docentes = session.exec(
    select(Docentes)
    .where(
      Docentes.nivel == nivel,
      Docentes.fecha_eliminacion.is_(None),
    )
    .order_by(
      Docentes.primer_apellido, Docentes.primer_nombre, Docentes.cedula, Docentes.id
    )
  ).all()

  filas: list[list[str]] = []
  for docente in docentes:
    if docente.id is None:
      continue

    detalle = "-"
    if nivel == NivelEducativo.liceo:
      asignaturas = session.exec(
        select(Asignaturas)
        .join(Horarios, Horarios.id_asignatura == Asignaturas.id)
        .join(Grados, Asignaturas.id_grado == Grados.id)
        .where(
          Horarios.id_docente == docente.id,
          Horarios.periodo_lectivo == periodo,
          Horarios.fecha_eliminacion.is_(None),
          Asignaturas.periodo_lectivo == periodo,
          Asignaturas.fecha_eliminacion.is_(None),
          Grados.fecha_eliminacion.is_(None),
        )
        .order_by(Grados.numero, Asignaturas.nombre)
      ).all()
      vistos: set[tuple[str, str]] = set()
      etiquetas: list[str] = []
      for asignatura in asignaturas:
        etiqueta = f"{asignatura.nombre} {asignatura.grado.nombre}"
        clave = (asignatura.nombre, asignatura.grado.nombre)
        if clave in vistos:
          continue
        vistos.add(clave)
        etiquetas.append(etiqueta)
      detalle = ", ".join(etiquetas) or "-"
    else:
      secciones = session.exec(
        select(Secciones)
        .join(Grados, Secciones.id_grado == Grados.id)
        .where(
          Secciones.id_docente_titular == docente.id,
          Secciones.periodo_lectivo == periodo,
          Secciones.fecha_eliminacion.is_(None),
          Grados.fecha_eliminacion.is_(None),
        )
        .order_by(Grados.numero, Secciones.letra)
      ).all()
      detalle = (
        "; ".join(f'{seccion.grado.nombre} "{seccion.letra}"' for seccion in secciones)
        or "-"
      )

    filas.append([docente.cedula, nombre_completo(docente), detalle])
  return filas


FILAS_POR_SECCION: dict[
  TipoDocumento, Callable[[Session, Secciones], list[list[str]]]
] = {
  TipoDocumento.nominas: _filas_nominas_seccion,
  TipoDocumento.representantes: _filas_representantes_seccion,
  TipoDocumento.horarios: _filas_horarios_seccion,
}

FILAS_GENERAL: dict[
  TipoDocumento,
  Callable[[Session, int, NivelEducativo, Grados | None], list[list[str]]],
] = {
  TipoDocumento.nominas: _filas_nominas_general,
  TipoDocumento.representantes: _filas_representantes_general,
  TipoDocumento.docentes: _filas_docentes_general,
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
  TipoDocumento.docentes: ["Cédula", "Docente", "Asignaturas"],
}

COL_ANCHOS_SECCION: dict[TipoDocumento, list[float]] = {
  TipoDocumento.nominas: [2.6, 4.3, 4.3, 2.6],
  TipoDocumento.representantes: [5.0, 2.8, 6.4],
  TipoDocumento.horarios: [1.9, 1.8, 1.3, 1.3, 4.1, 3.9],
}

COL_ANCHOS_GENERAL: dict[TipoDocumento, list[float]] = {
  TipoDocumento.nominas: [2.3, 3.4, 2.6, 3.5, 2.4],
  TipoDocumento.representantes: [5.0, 2.8, 6.4],
  TipoDocumento.docentes: [2.8, 5.0, 6.4],
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
    nombre_archivo = _nombre_archivo(tipo, periodo, nivel, grado, None)
    descripcion = f"{grado.nombre} general" if grado else "general"
    filas = FILAS_GENERAL[tipo](session, periodo, nivel, grado)
    encabezados = HEADERS_GENERAL[tipo]
    if tipo == TipoDocumento.docentes and nivel == NivelEducativo.escuela:
      encabezados = ["Cédula", "Docente", "Grado/Sección"]
    col_anchos = COL_ANCHOS_GENERAL[tipo]

  cabecera_horario = None
  filas_horario = None
  docentes_horario = None
  if tipo == TipoDocumento.horarios and seccion is not None:
    cabecera_horario, filas_horario, docentes_horario = _datos_horarios(
      session, seccion, periodo
    )

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
    horario_cabecera=cabecera_horario,
    horario_filas=filas_horario,
    horario_docentes=docentes_horario,
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

  El periodo lectivo es la primera carpeta y usa su etiqueta legible.

  Sección: `2026-2027/listados/nominas/LICEO/1er_ano/A/nomina_2026-2027_1er_ano_A.pdf`.
  General por nivel: `2026-2027/listados/nominas/LICEO/generales/nomina_2026-2027_LICEO_general.pdf`.
  General por grado: `.../generales/nomina_2026-2027_1er_ano.pdf`.
  """
  etiqueta = etiqueta_periodo(periodo)
  if seccion is not None:
    slug = GRADO_SLUGS.get(grado.numero, "general")
    return (
      f"{etiqueta}/listados/{tipo.value}/{nivel.value}/{slug}/"
      f"{seccion.letra}/{nombre_archivo}"
    )
  return f"{etiqueta}/listados/{tipo.value}/{nivel.value}/generales/{nombre_archivo}"

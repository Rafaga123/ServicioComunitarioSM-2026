"""Generación de PDFs de listados institucionales (ReportLab)."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
  Paragraph,
  SimpleDocTemplate,
  Spacer,
  Table,
)

from app.core.config import INSTITUCION_NOMBRE

# Hoja carta con márgenes institucionales: 4 cm a la izquierda y 3 cm al resto.
MARGEN_IZQUIERDO = 4 * cm
MARGEN = 3 * cm


def _texto_parrafo(valor: object) -> str:
  """Escapa el texto para ReportLab y conserva los saltos de línea."""
  return escape(str(valor)).replace("\n", "<br/>")


def _validar_tabla(
  encabezados: list[str],
  filas: list[list[str]],
  col_anchos: list[float] | None,
) -> None:
  """Verifica que encabezados, filas y anchos tengan la misma cantidad de columnas."""
  if not encabezados:
    raise ValueError("El listado necesita al menos un encabezado")

  total_columnas = len(encabezados)
  for indice, fila in enumerate(filas, start=1):
    if len(fila) != total_columnas:
      raise ValueError(
        f"La fila {indice} tiene {len(fila)} columnas; se esperaban {total_columnas}"
      )

  if col_anchos is not None and len(col_anchos) != total_columnas:
    raise ValueError(
      f"Se definieron {len(col_anchos)} anchos para {total_columnas} columnas"
    )


def _anchos_en_puntos(
  col_anchos: list[float] | None, ancho_util: float
) -> list[float] | None:
  """Convierte los anchos de centímetros a puntos y los ajusta al ancho útil."""
  if col_anchos is None:
    return None

  # Copia explícita: ReportLab puede modificar la lista recibida.
  anchos = [float(ancho) * cm for ancho in list(col_anchos)]
  if not anchos or any(ancho <= 0 for ancho in anchos):
    raise ValueError("Los anchos de columna deben ser mayores que cero")

  total = sum(anchos)
  if total > ancho_util:
    factor = ancho_util / total
    anchos = [ancho * factor for ancho in anchos]

  return anchos


def construir_pdf(
  titulo: str,
  encabezados: list[str],
  filas: list[list[str]],
  col_anchos: list[float] | None = None,
  nivel: str | None = None,
  grado: str | None = None,
  seccion: str | None = None,
  periodo_lectivo: str | None = None,
) -> bytes:
  """Construye el PDF de un listado.

  Encabezado institucional (`INSTITUCION_NOMBRE`), metadatos de alcance
  (nivel/grado/sección/periodo, p. ej. «2026-2027») y una tabla de `filas` con `encabezados` como
  encabezado de columna. `col_anchos` en centímetros; se convierten a puntos y
  se escalan proporcionalmente si superan el ancho útil de la hoja carta.
  """
  buffer = BytesIO()
  ancho_util = letter[0] - MARGEN_IZQUIERDO - MARGEN
  doc = SimpleDocTemplate(
    buffer,
    pagesize=letter,
    leftMargin=MARGEN_IZQUIERDO,
    rightMargin=MARGEN,
    topMargin=MARGEN,
    bottomMargin=MARGEN,
  )
  estilos = getSampleStyleSheet()
  estilo_encabezado = ParagraphStyle(
    "EncabezadoListado",
    parent=estilos["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=10,
    alignment=TA_CENTER,
    textColor=colors.whitesmoke,
  )
  estilo_celda = ParagraphStyle(
    "CeldaListado",
    parent=estilos["BodyText"],
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    alignment=TA_CENTER,
  )

  _validar_tabla(encabezados, filas, col_anchos)

  elementos = [
    Paragraph(f"{INSTITUCION_NOMBRE} — {titulo}", estilos["h1"]),
    Spacer(1, 12),
  ]

  filas_info = [l for l in (nivel, grado, seccion, periodo_lectivo) if l is not None]
  if filas_info:
    elementos.append(Paragraph(" • ".join(f"{i}" for i in filas_info), estilos["h2"]))
    elementos.append(Spacer(1, 10))

  fila_encabezado = [
    Paragraph(_texto_parrafo(encabezado), estilo_encabezado)
    for encabezado in encabezados
  ]
  filas_parrafo = [
    [Paragraph(_texto_parrafo(celda), estilo_celda) for celda in fila] for fila in filas
  ]

  tabla = Table(
    [fila_encabezado] + filas_parrafo,
    colWidths=_anchos_en_puntos(col_anchos, ancho_util),
    repeatRows=1,
  )
  tabla.setStyle(
    [
      ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b2a47")),
      ("ALIGN", (0, 0), (-1, -1), "CENTER"),
      ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
      ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
      ("TOPPADDING", (0, 0), (-1, -1), 4),
      ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c4ced6")),
    ]
  )
  elementos.append(tabla)

  doc.build(elementos)
  return buffer.getvalue()

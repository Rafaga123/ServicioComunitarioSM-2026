"""Generación de PDFs de listados institucionales (ReportLab)."""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
  Paragraph,
  SimpleDocTemplate,
  Spacer,
  Table,
  TableStyle,
)

from app.core.config import INSTITUCION_NOMBRE


def construir_pdf(
  titulo: str,
  encabezados: list[str],
  filas: list[list[str]],
  col_anchos: list[float] | None = None,
  nivel: str | None = None,
  grado: str | None = None,
  seccion: str | None = None,
  periodo_lectivo: int | None = None,
) -> bytes:
  """Construye el PDF de un listado.

  Encabezado institucional (`INSTITUCION_NOMBRE`), metadatos de alcance
  (nivel/grado/sección/periodo) y una tabla de `filas` con `encabezados` como
  encabezado de columna. `col_anchos` en centímetros.
  """
  buffer = BytesIO()
  doc = SimpleDocTemplate(
    buffer,
    pagesize=A4,
    rightMargin=40,
    leftMargin=40,
    topMargin=40,
    bottomMargin=40,
  )
  estilos = getSampleStyleSheet()
  elementos = [
    Paragraph(f"{INSTITUCION_NOMBRE} — {titulo}", estilos["h1"]),
    Spacer(1, 12),
  ]

  filas_info = [l for l in (nivel, grado, seccion, periodo_lectivo) if l is not None]
  if filas_info:
    elementos.append(Paragraph(" • ".join(f"{i}" for i in filas_info), estilos["h2"]))
    elementos.append(Spacer(1, 10))

  tabla = Table([encabezados] + filas, colWidths=col_anchos)
  tabla.setStyle(
    [
      ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b2a47")),
      ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
      ("ALIGN", (0, 0), (-1, -1), "CENTER"),
      ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
      ("FONTSIZE", (0, 0), (-1, -1), 9),
      ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
      ("TOPPADDING", (0, 0), (-1, -1), 4),
      ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c4ced6")),
    ]
  )
  elementos.append(tabla)

  doc.build(elementos)
  return buffer.getvalue()

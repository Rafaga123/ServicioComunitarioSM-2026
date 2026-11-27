"""Generación de PDFs de listados institucionales (ReportLab)."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
  Paragraph,
  SimpleDocTemplate,
  Spacer,
  Table,
)

from app.core.config import INSTITUCION_NOMBRE, LOGO_PATH

# Hoja carta con márgenes institucionales: 4 cm a la izquierda y 3 cm al resto.
MARGEN_IZQUIERDO = 4 * cm
MARGEN = 3 * cm

# El membrete se dibuja dentro del área útil: 4 cm a la izquierda y 3 cm
# en el resto de márgenes. El PNG original mide 455x548 (≈0.83).
LOGO_ALTO = 2.0 * cm
LOGO_ANCHO = LOGO_ALTO * 455 / 548
LOGO_X = MARGEN_IZQUIERDO
LOGO_Y = letter[1] - MARGEN - LOGO_ALTO

# Texto a la derecha del logo, sin salirse del margen derecho de 3 cm.
COLOR_MEMBRETE = colors.HexColor("#1b2a47")
MEMBRETE_X = LOGO_X + LOGO_ANCHO + 0.25 * cm
INSTITUCION_Y = letter[1] - MARGEN - 0.35 * cm
TITULO_Y = letter[1] - MARGEN - 1.05 * cm
ESPACIO_MEMBRETE = LOGO_ALTO + 0.35 * cm


def _tamano_ajustado(
  texto: str, fuente: str, tamano_max: float, tamano_min: float, ancho_max: float
) -> float:
  """Reduce la fuente hasta que el texto quepa en una sola línea."""
  tamano = tamano_max
  while tamano > tamano_min and stringWidth(texto, fuente, tamano) > ancho_max:
    tamano -= 0.25
  return max(tamano, tamano_min)


def _membrete(titulo: str):
  """Devuelve el callback que dibuja logo + membrete en todas las páginas."""
  def dibujar(canvas, doc) -> None:
    """Dibuja el membrete y el título en cada página del PDF."""
    if not LOGO_PATH.is_file():
      raise FileNotFoundError(f"No se encontró el logo institucional: {LOGO_PATH}")
    canvas.saveState()
    try:
      canvas.drawImage(
        str(LOGO_PATH),
        LOGO_X,
        LOGO_Y,
        width=LOGO_ANCHO,
        height=LOGO_ALTO,
        mask="auto",
      )
      ancho_texto = letter[0] - MEMBRETE_X - MARGEN
      canvas.setFillColor(COLOR_MEMBRETE)

      size_institucion = _tamano_ajustado(
        INSTITUCION_NOMBRE, "Helvetica-Bold", 10.0, 8.5, ancho_texto
      )
      canvas.setFont("Helvetica-Bold", size_institucion)
      canvas.drawString(MEMBRETE_X, INSTITUCION_Y, INSTITUCION_NOMBRE)

      size_titulo = _tamano_ajustado(titulo, "Helvetica", 9.0, 7.5, ancho_texto)
      canvas.setFont("Helvetica", size_titulo)
      canvas.drawString(MEMBRETE_X, TITULO_Y, titulo)
    finally:
      canvas.restoreState()

  return dibujar


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

  El membrete institucional (logo, nombre y título con su alcance) se dibuja
  en todas las páginas desde el canvas. El cuerpo contiene únicamente la
  tabla de `filas` con `encabezados` como cabecera de columna. `col_anchos`
  en centímetros; se convierten a puntos y se escalan proporcionalmente si
  superan el ancho útil de la hoja carta.
  """
  buffer = BytesIO()
  ancho_util = letter[0] - MARGEN_IZQUIERDO - MARGEN
  doc = SimpleDocTemplate(
    buffer,
    pagesize=letter,
    leftMargin=MARGEN_IZQUIERDO,
    rightMargin=MARGEN,
    topMargin=MARGEN + ESPACIO_MEMBRETE,
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

  elementos: list = []

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

  membrete = _membrete(titulo)
  doc.build(
    elementos,
    onFirstPage=membrete,
    onLaterPages=membrete,
  )
  return buffer.getvalue()


def construir_pdf_horarios(
  cabecera: dict[str, str],
  filas: list[list[str]],
  docentes: list[tuple[str, str]],
) -> bytes:
  """Construye el PDF del horario de una sección de liceo.

  Tabla de 12 filas: periodo/curso/sección, días, y los 10 bloques de la
  jornada. Las filas de receso muestran «RECESO» en las columnas de los días.
  Al final se lista «Materia: Docente» para cada asignatura de la sección.
  """
  buffer = BytesIO()
  ancho_util = letter[0] - MARGEN_IZQUIERDO - MARGEN
  doc = SimpleDocTemplate(
    buffer,
    pagesize=letter,
    leftMargin=MARGEN_IZQUIERDO,
    rightMargin=MARGEN,
    topMargin=MARGEN + ESPACIO_MEMBRETE,
    bottomMargin=MARGEN,
  )
  estilos = getSampleStyleSheet()
  estilo_encabezado = ParagraphStyle(
    "EncabezadoHorario",
    parent=estilos["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=10,
    alignment=TA_CENTER,
    textColor=colors.white,
  )
  estilo_fila_periodo = ParagraphStyle(
    "FilaPeriodoHorario",
    parent=estilos["BodyText"],
    fontName="Helvetica",
    fontSize=7.5,
    leading=9,
    alignment=TA_CENTER,
    textColor=colors.white,
  )
  estilo_celda = ParagraphStyle(
    "CeldaHorario",
    parent=estilos["BodyText"],
    fontName="Helvetica",
    fontSize=7.5,
    leading=9,
    alignment=TA_CENTER,
  )
  estilo_izquierda = ParagraphStyle(
    "CeldaDocente",
    parent=estilo_celda,
    alignment=TA_LEFT,
  )
  estilo_titulo_seccion = ParagraphStyle(
    "TituloDocentes",
    parent=estilos["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=9,
    leading=11,
  )

  for fila in filas:
    if len(fila) != 6:
      raise ValueError("Cada fila del horario debe tener hora y cinco días")

  fila_periodo = [
    Paragraph(
      f"<b>Periodo:</b> {_texto_parrafo(cabecera['periodo'])}", estilo_fila_periodo
    ),
    "",
    Paragraph(
      f"<b>Curso:</b> {_texto_parrafo(cabecera['curso'])}", estilo_fila_periodo
    ),
    "",
    Paragraph(
      f"<b>Sección:</b> {_texto_parrafo(cabecera['seccion'])}", estilo_fila_periodo
    ),
    "",
  ]
  fila_dias = [
    Paragraph(_texto_parrafo(dia), estilo_encabezado)
    for dia in ("Hora", "LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES")
  ]
  filas_tabla = [fila_periodo, fila_dias] + [
    [Paragraph(_texto_parrafo(celda), estilo_celda) for celda in fila] for fila in filas
  ]

  ancho_hora = 2.2 * cm
  ancho_dia = (ancho_util - ancho_hora) / 5
  tabla = Table(filas_tabla, colWidths=[ancho_hora] + [ancho_dia] * 5)
  estilo_tabla = [
    ("SPAN", (0, 0), (1, 0)),
    ("SPAN", (2, 0), (3, 0)),
    ("SPAN", (4, 0), (5, 0)),
    ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#1b2a47")),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c4ced6")),
  ]
  for indice, fila in enumerate(filas, start=2):
    if any("RECESO" in celda.upper() for celda in fila[1:]):
      estilo_tabla.append(
        ("BACKGROUND", (0, indice), (-1, indice), colors.HexColor("#f2ead8"))
      )
  tabla.setStyle(estilo_tabla)

  subtitulo = (
    f"HORARIO DE CLASES · {cabecera['periodo']} · "
    f"{cabecera['curso']} {cabecera['seccion']}"
  )
  elementos = [
    tabla,
    Spacer(1, 14),
    Paragraph("Docentes:", estilo_titulo_seccion),
    Spacer(1, 4),
  ]
  for materia, docente in docentes:
    elementos.append(
      Paragraph(
        f"{_texto_parrafo(materia)}: {_texto_parrafo(docente)}", estilo_izquierda
      )
    )

  membrete = _membrete(subtitulo)
  doc.build(
    elementos,
    onFirstPage=membrete,
    onLaterPages=membrete,
  )
  return buffer.getvalue()

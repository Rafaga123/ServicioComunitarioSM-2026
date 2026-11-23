"""Genera archivos .sql (ordenados por dependencias FK) y seed_data.json
a partir de las nóminas del colegio (PDF de docentes, PDF de primaria y .xls de liceo).

Uso (desde la raíz del proyecto, con el entorno virtual activo):

    python backend/scripts/excel.py todo --carpeta "C:\\nominas_prueba"
    python backend/scripts/excel.py todo --carpeta "C:\\nominas_prueba" --nivel-docentes liceo --periodo 2026

También admite la variable de entorno NOMINAS_CARPETA.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PARTICULAS = {
    "DE",
    "DEL",
    "LA",
    "LAS",
    "LOS",
    "DA",
    "DAS",
    "DO",
    "DOS",
    "VAN",
    "VON",
    "SAN",
    "SANTA",
}

CARPETA_SALIDA = "sql"
CORRECCIONES_DOCENTES = "correcciones_docentes.csv"
CORRECCIONES_ESTUDIANTES = "correcciones_estudiantes.csv"
FECHA_NACIMIENTO_DEFECTO = "2000-01-01 00:00:00"
NIVELES_VALIDOS = ("escuela", "liceo")

# Catálogo institucional idéntico a app/core/semilla.py (GRADOS_BASE)
CATALOGO_GRADOS: dict[int, tuple[str, str]] = {
    1: ("1er Grado", "escuela"),
    2: ("2do Grado", "escuela"),
    3: ("3er Grado", "escuela"),
    4: ("4to Grado", "escuela"),
    5: ("5to Grado", "escuela"),
    6: ("6to Grado", "escuela"),
    7: ("1er Año", "liceo"),
    8: ("2do Año", "liceo"),
    9: ("3er Año", "liceo"),
    10: ("4to Año", "liceo"),
    11: ("5to Año", "liceo"),
}

ALIAS_GRADOS: dict[str, int] = {
    # Primaria (1..6 -> escuela)
    "PRIMER GRADO": 1,
    "PRIMERO": 1,
    "1ER GRADO": 1,
    "1RO GRADO": 1,
    "1RO": 1,
    "1 GRADO": 1,
    "SEGUNDO GRADO": 2,
    "SEGUNDO": 2,
    "2DO GRADO": 2,
    "2DO": 2,
    "2 GRADO": 2,
    "TERCER GRADO": 3,
    "TERCERO": 3,
    "3ER GRADO": 3,
    "3RO GRADO": 3,
    "3RO": 3,
    "3 GRADO": 3,
    "CUARTO GRADO": 4,
    "CUARTO": 4,
    "4TO GRADO": 4,
    "4TO": 4,
    "4 GRADO": 4,
    "QUINTO GRADO": 5,
    "QUINTO": 5,
    "5TO GRADO": 5,
    "5TO": 5,
    "5 GRADO": 5,
    "SEXTO GRADO": 6,
    "SEXTO": 6,
    "6TO GRADO": 6,
    "6TO": 6,
    "6 GRADO": 6,
    # Liceo (7..11 -> liceo)
    "PRIMER AÑO": 7,
    "1ER AÑO": 7,
    "1RO AÑO": 7,
    "1 AÑO": 7,
    "SEPTIMO": 7,
    "7MO": 7,
    "SEGUNDO AÑO": 8,
    "2DO AÑO": 8,
    "2 AÑO": 8,
    "OCTAVO": 8,
    "8VO": 8,
    "TERCER AÑO": 9,
    "3ER AÑO": 9,
    "3RO AÑO": 9,
    "3 AÑO": 9,
    "NOVENO": 9,
    "9NO": 9,
    "CUARTO AÑO": 10,
    "4TO AÑO": 10,
    "4 AÑO": 10,
    "DECIMO": 10,
    "QUINTO AÑO": 11,
    "5TO AÑO": 11,
    "5 AÑO": 11,
    "UNDECIMO": 11,
}


# ---------------------------------------------------------------------------
# Utilidades de limpieza y normalización
# ---------------------------------------------------------------------------
def limpiar(texto: str) -> str:
    """Mayúsculas, espacios colapsados y reparación de Ñ rota ('MONTA?EZ')."""
    texto = " ".join(texto.replace("\xa0", " ").split()).upper()
    return re.sub(r"(?<=[A-ZÁÉÍÓÚÑ])\?(?=[A-ZÁÉÍÓÚÑ])", "Ñ", texto)


def decodificar_bytes(raw: bytes) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="replace")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def solo_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def normalizar_cedula(texto: str) -> str:
    """'v-1927' / '34297038' -> 'V-1927' / 'V-34297038' (o 'E-')."""
    prefijo = "E" if texto.strip().upper().startswith("E") else "V"
    digitos = solo_digitos(texto)
    return f"{prefijo}-{digitos}" if digitos else ""


def normalizar_telefono(texto: str) -> str:
    """'0414-457.06.17' o '0412-0464169/ 0412-179834' -> '0414-4570617'."""
    if not texto:
        return ""
    primero = texto.split("/")[0].strip()
    digitos = solo_digitos(primero)
    if len(digitos) == 11 and digitos.startswith("0"):
        return f"{digitos[:4]}-{digitos[4:]}"
    if len(digitos) == 10 and not digitos.startswith("0"):
        return f"0{digitos[:3]}-{digitos[3:]}"
    return primero


def normalizar_fecha(texto: str) -> tuple[str, bool]:
    """Convierte 'DD-MM-YYYY' o 'DD/MM/YYYY' a 'YYYY-MM-DD 00:00:00'."""
    limpio = texto.strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(limpio, fmt)
            return dt.strftime("%Y-%m-%d 00:00:00"), False
        except ValueError:
            continue
    return FECHA_NACIMIENTO_DEFECTO, True


def normalizar_nivel(valor: str, defecto: str = "liceo") -> str:
    v = valor.strip().lower()
    if v in ("escuela", "primaria"):
        return "escuela"
    if v in ("liceo", "media", "media general", "secundaria"):
        return "liceo"
    return defecto


def detectar_periodo_lectivo(texto: str, respaldo: int) -> int:
    """Detecta el año de inicio del período escolar (ej. '2026-2027' -> 2026)."""
    m_periodo = re.search(
        r"PERIODO\s+ESCOLAR\s*:?\s*(20\d{2})\s*[-/]\s*(20\d{2})",
        texto,
        re.IGNORECASE,
    )
    if m_periodo:
        anio = int(m_periodo.group(1))
        if anio >= 2000:
            return anio

    m_fecha = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b", texto)
    if m_fecha:
        mes = int(m_fecha.group(2))
        anio = int(m_fecha.group(3))
        if anio >= 2000:
            return anio if mes >= 8 else anio - 1

    return respaldo


def grupos(texto: str) -> list[str]:
    """Une partículas con la palabra siguiente ('DE LOS ANGELES' = 1 unidad)."""
    salida: list[str] = []
    pendientes: list[str] = []
    for token in limpiar(texto).split():
        if token in PARTICULAS:
            pendientes.append(token)
            continue
        salida.append(" ".join([*pendientes, token]))
        pendientes = []
    if pendientes:
        salida.append(" ".join(pendientes))
    return salida


def separar_4_campos_apellidos_primero(texto: str) -> tuple[str, str, str, str, bool]:
    """'ARZOLA ROMAN JEANNA VICTORIA' -> (p_nom, s_nom, p_ape, s_ape, dudoso)."""
    gs = grupos(texto)
    n = len(gs)
    if n == 0:
        return "", "", "", "", True
    if n == 1:
        return "", "", gs[0], "", True
    if n == 2:
        return gs[1], "", gs[0], "", False
    if n == 3:
        return gs[2], "", gs[0], gs[1], True
    return gs[2], " ".join(gs[3:]), gs[0], gs[1], n > 4


def separar_4_campos_nombres_primero(texto: str) -> tuple[str, str, str, str, bool]:
    """'YADYCCY MAYBELY ANDRADE BAEZ' -> (p_nom, s_nom, p_ape, s_ape, dudoso)."""
    gs = grupos(texto)
    n = len(gs)
    if n == 0:
        return "", "", "", "", True
    if n == 1:
        return gs[0], "", "", "", True
    if n == 2:
        return gs[0], "", gs[1], "", False
    if n == 3:
        return gs[0], gs[1], gs[2], "", True
    return gs[0], gs[1], gs[2], " ".join(gs[3:]), n > 4


def separar_columnas_nombre_apellido(
    nombres_raw: str, apellidos_raw: str
) -> tuple[str, str, str, str]:
    """Cuando el .xls ya trae Nombre y Apellido en columnas distintas."""
    gn = grupos(nombres_raw)
    ga = grupos(apellidos_raw)
    p_nom = gn[0] if len(gn) >= 1 else ""
    s_nom = " ".join(gn[1:]) if len(gn) >= 2 else ""
    p_ape = ga[0] if len(ga) >= 1 else ""
    s_ape = " ".join(ga[1:]) if len(ga) >= 2 else ""
    return p_nom, s_nom, p_ape, s_ape


def resolver_grado_y_seccion(
    grado_raw: str, seccion_raw: str = ""
) -> tuple[int, str, str, str]:
    """Devuelve (grado_numero, grado_nombre, nivel, letra_seccion).

    Mapea textos como 'Primer Grado U' -> (1, '1er Grado', 'escuela', 'U')
    o ('Primer Año', 'U') -> (7, '1er Año', 'liceo', 'U').
    """
    grado = limpiar(grado_raw).replace("º", "").replace("°", "")
    seccion = limpiar(seccion_raw)

    if not seccion:
        m = re.match(r"^(.+?)\s+([A-Z])$", grado)
        if m:
            grado = m.group(1).strip()
            seccion = m.group(2).strip()
        else:
            seccion = "U"

    numero = ALIAS_GRADOS.get(grado)
    if numero is None:
        m_num = re.match(r"^(\d{1,2})\s*(?:ER|DO|RO|TO|MO|VO|NO)?\s*(GRADO|AÑO|ANO)$", grado)
        if m_num:
            n = int(m_num.group(1))
            tipo = m_num.group(2)
            if tipo == "GRADO" and 1 <= n <= 6:
                numero = n
            elif tipo in ("AÑO", "ANO") and 1 <= n <= 5:
                numero = n + 6

    if numero is None or numero not in CATALOGO_GRADOS:
        raise ValueError(f"No se pudo mapear el grado '{grado_raw}' al catálogo 1..11")

    nombre_canonico, nivel = CATALOGO_GRADOS[numero]
    return numero, nombre_canonico, nivel, seccion


def sql_texto(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def sql_texto_nullable(valor: str) -> str:
    limpio = valor.strip()
    return sql_texto(limpio) if limpio else "NULL"


# ---------------------------------------------------------------------------
# Estructuras de datos alineadas a app/models/db.py
# ---------------------------------------------------------------------------
@dataclass
class DocenteItem:
    cedula: str
    primer_nombre: str
    segundo_nombre: str
    primer_apellido: str
    segundo_apellido: str
    nivel: str  # 'escuela' | 'liceo'
    origen: str


@dataclass
class SeccionItem:
    grado_numero: int
    grado_nombre: str
    nivel: str  # 'escuela' | 'liceo'
    letra: str
    periodo_lectivo: int


@dataclass
class RepresentanteItem:
    clave_dedup: str
    primer_nombre: str
    segundo_nombre: str
    primer_apellido: str
    segundo_apellido: str
    telefono: str
    es_placeholder: bool
    cedulas_estudiantes: list[str] = field(default_factory=list)


@dataclass
class EstudianteItem:
    cedula_estudiantil: str
    primer_nombre: str
    segundo_nombre: str
    primer_apellido: str
    segundo_apellido: str
    grado_numero: int
    grado_nombre: str
    nivel: str
    seccion_letra: str
    periodo_lectivo: int
    fecha_nacimiento: str
    fecha_nacimiento_estimada: bool
    clave_representante: str | None
    origen: str


# ---------------------------------------------------------------------------
# Lectores de archivos (PDF y .xls HTML / XML / Binario)
# ---------------------------------------------------------------------------
class _TablaHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._en_celda = False
        self.filas: list[list[str]] = []
        self._fila_actual: list[str] = []
        self._celda_actual: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._fila_actual = []
        elif tag in ("td", "th"):
            self._en_celda = True
            self._celda_actual = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th"):
            self._en_celda = False
            self._fila_actual.append(" ".join("".join(self._celda_actual).split()))
        elif tag == "tr" and self._fila_actual:
            self.filas.append(self._fila_actual)

    def handle_data(self, data: str) -> None:
        if self._en_celda:
            self._celda_actual.append(data)


def texto_pdf(ruta: Path) -> str:
    try:
        import pdfplumber

        with pdfplumber.open(ruta) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except ImportError:
        import pypdf

        reader = pypdf.PdfReader(ruta)
        return "\n".join((p.extract_text() or "") for p in reader.pages)


def _filas_a_registros(filas: list[list[str]]) -> list[dict[str, str]]:
    idx_header = None
    encabezados: list[str] = []
    for i, fila in enumerate(filas):
        norm = [limpiar(c).replace("É", "E").replace("Ó", "O") for c in fila]
        if any("CEDULA" in c for c in norm) and (
            any("APELLIDO" in c for c in norm) or any("NOMBRE" in c for c in norm)
        ):
            idx_header = i
            encabezados = norm
            break

    if idx_header is None:
        return []

    registros: list[dict[str, str]] = []
    for fila in filas[idx_header + 1 :]:
        if len(fila) < 3 or limpiar(fila[0]).startswith("TOTAL"):
            continue
        registros.append(
            {
                encabezados[j]: fila[j].strip()
                for j in range(min(len(encabezados), len(fila)))
                if encabezados[j]
            }
        )
    return registros


def leer_filas_xls(ruta: Path) -> tuple[list[dict[str, str]], str, str]:
    """Lee tablas .xls y devuelve (registros, info_formato, texto_crudo)."""
    raw = ruta.read_bytes()
    if not raw:
        return [], "archivo vacío (0 bytes)", ""

    if raw.startswith(b"PK\x03\x04"):
        try:
            import openpyxl

            wb = openpyxl.load_workbook(ruta, data_only=True)
            ws = wb.active
            filas = [
                ["" if v is None else str(v) for v in row]
                for row in ws.iter_rows(values_only=True)
            ]
            texto_plano = "\n".join(" ".join(f) for f in filas[:15])
            return _filas_a_registros(filas), "XLSX", texto_plano
        except Exception as e:
            return [], f"XLSX (instala openpyxl o usa el .xls original: {e})", ""

    if raw.startswith(b"\xd0\xcf\x11\xe0"):
        try:
            import xlrd

            wb = xlrd.open_workbook(str(ruta))
            sh = wb.sheet_by_index(0)
            filas = [
                [str(sh.cell_value(r, c)) for c in range(sh.ncols)]
                for r in range(sh.nrows)
            ]
            texto_plano = "\n".join(" ".join(f) for f in filas[:15])
            return _filas_a_registros(filas), "BIFF8", texto_plano
        except Exception as e:
            return [], f"BIFF8 binario (instala xlrd o usa el .xls original: {e})", ""

    texto = decodificar_bytes(raw)
    inicio = texto.lstrip()[:200].lower()

    if inicio.startswith("<?xml") and "<workbook" in texto.lower():
        root = ET.fromstring(texto)
        filas_xml: list[list[str]] = []
        for row in root.iter():
            if row.tag.endswith("Row"):
                celdas = [
                    "".join(cell.itertext()).strip()
                    for cell in row
                    if cell.tag.endswith("Cell")
                ]
                if celdas:
                    filas_xml.append(celdas)
        texto_plano = "\n".join(" ".join(f) for f in filas_xml[:15])
        return _filas_a_registros(filas_xml), "XML2003", texto_plano

    parser = _TablaHTMLParser()
    parser.feed(texto)
    regs = _filas_a_registros(parser.filas)
    return regs, f"HTML (filas_tr={len(parser.filas)})", texto


def leer_correcciones_docentes(
    carpeta: Path,
) -> dict[str, tuple[str, str, str, str, str | None]]:
    """Lee correcciones_docentes.csv.
    Columnas soportadas:
      cedula,primer_nombre,segundo_nombre,primer_apellido,segundo_apellido[,nivel]
    o formato corto:
      cedula,nombre,apellido[,nivel]
    """
    ruta = carpeta / CORRECCIONES_DOCENTES
    if not ruta.is_file():
        return {}

    resultado: dict[str, tuple[str, str, str, str, str | None]] = {}
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        primera = f.readline()
        f.seek(0)
        delimitador = ";" if ";" in primera else ","
        for fila in csv.DictReader(f, delimiter=delimitador):
            ced = normalizar_cedula(fila.get("cedula", ""))
            if not ced:
                continue
            nivel_raw = (fila.get("nivel") or "").strip()
            nivel = normalizar_nivel(nivel_raw, "") if nivel_raw else None
            if "primer_nombre" in fila or "primer_apellido" in fila:
                resultado[ced] = (
                    limpiar(fila.get("primer_nombre", "")),
                    limpiar(fila.get("segundo_nombre", "")),
                    limpiar(fila.get("primer_apellido", "")),
                    limpiar(fila.get("segundo_apellido", "")),
                    nivel or None,
                )
            else:
                p_nom, s_nom, p_ape, s_ape = separar_columnas_nombre_apellido(
                    fila.get("nombre", ""), fila.get("apellido", "")
                )
                resultado[ced] = (p_nom, s_nom, p_ape, s_ape, nivel or None)
    return resultado


def leer_correcciones_estudiantes(
    carpeta: Path,
) -> dict[str, tuple[str, str, str, str]]:
    ruta = carpeta / CORRECCIONES_ESTUDIANTES
    if not ruta.is_file():
        return {}

    resultado: dict[str, tuple[str, str, str, str]] = {}
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        primera = f.readline()
        f.seek(0)
        delimitador = ";" if ";" in primera else ","
        for fila in csv.DictReader(f, delimiter=delimitador):
            ced = normalizar_cedula(fila.get("cedula", ""))
            if not ced:
                continue
            if "primer_nombre" in fila or "primer_apellido" in fila:
                resultado[ced] = (
                    limpiar(fila.get("primer_nombre", "")),
                    limpiar(fila.get("segundo_nombre", "")),
                    limpiar(fila.get("primer_apellido", "")),
                    limpiar(fila.get("segundo_apellido", "")),
                )
            else:
                resultado[ced] = separar_columnas_nombre_apellido(
                    fila.get("nombre", ""), fila.get("apellido", "")
                )
    return resultado


# ---------------------------------------------------------------------------
# Extracción de Docentes
# ---------------------------------------------------------------------------
RE_FILA_DOCENTE = re.compile(
    r"^(\d+)\s+([VvEe]?-?\d{5,9})\s+(.+?)(?:\s+(\S+@\S+))?(?:\s+(0\d{3}[\d.\-]+))?$"
)


def _inferir_nivel_archivo_docentes(ruta: Path, texto: str, defecto: str) -> str:
    muestra = f"{ruta.stem} {texto[:300]}".upper()
    if any(tok in muestra for tok in ("ESCUELA", "PRIMARIA")):
        return "escuela"
    if any(tok in muestra for tok in ("LICEO", "MEDIA GENERAL", "SECUNDARIA")):
        return "liceo"
    return defecto


def extraer_docentes(
    carpeta: Path, salida: Path, nivel_defecto: str = "liceo"
) -> tuple[list[DocenteItem], list[str], list[str]]:
    correcciones = leer_correcciones_docentes(carpeta)
    docentes: dict[str, DocenteItem] = {}
    por_revisar: list[str] = []
    avisos: list[str] = []

    for ruta in sorted(carpeta.rglob("*.pdf"), key=lambda p: p.name.lower()):
        if salida in ruta.parents:
            continue
        texto = texto_pdf(ruta)
        if "LISTADO DE DOCENTES" not in texto.upper():
            continue

        nivel_archivo = _inferir_nivel_archivo_docentes(ruta, texto, nivel_defecto)
        leidos = 0
        for linea in texto.splitlines():
            linea = linea.strip()
            if not re.match(r"^\d+\s+[VvEe]?-?\d{5,9}\s", linea):
                continue
            m = RE_FILA_DOCENTE.match(linea)
            if not m:
                avisos.append(f"[{ruta.name}] Fila docente sin interpretar: {linea}")
                continue

            cedula = normalizar_cedula(m.group(2))
            completo = limpiar(m.group(3))
            nivel_docente = nivel_archivo

            if cedula in correcciones:
                p_nom, s_nom, p_ape, s_ape, nivel_csv = correcciones[cedula]
                if nivel_csv in NIVELES_VALIDOS:
                    nivel_docente = nivel_csv
            else:
                p_nom, s_nom, p_ape, s_ape, dudoso = (
                    separar_4_campos_apellidos_primero(completo)
                )
                if dudoso:
                    por_revisar.append(
                        f"[DOCENTE] {completo} -> apellidos=({p_ape!r}, {s_ape!r}) "
                        f"nombres=({p_nom!r}, {s_nom!r}) ({cedula})"
                    )

            if cedula in docentes:
                avisos.append(
                    f"[{ruta.name}] Cédula docente duplicada {cedula}; se conserva la primera"
                )
            else:
                docentes[cedula] = DocenteItem(
                    cedula=cedula,
                    primer_nombre=p_nom,
                    segundo_nombre=s_nom,
                    primer_apellido=p_ape,
                    segundo_apellido=s_ape,
                    nivel=nivel_docente,
                    origen=ruta.name,
                )
            leidos += 1
        print(f"  [DOCENTES] {ruta.name} (nivel={nivel_archivo}): {leidos} registros")

    return list(docentes.values()), por_revisar, avisos


# ---------------------------------------------------------------------------
# Extracción de Secciones, Representantes y Estudiantes (.xls y .pdf)
# ---------------------------------------------------------------------------
RE_FILA_ESTUDIANTE_PDF = re.compile(
    r"^(\d+)\s+([VvEe]?-?\d{5,12})\s+(.+?)\s+([MF])\s+(.+?)\s+(0\d{3}[\d.\-]+)$"
)


def extraer_academico(
    carpeta: Path,
    salida: Path,
    periodo_defecto: int,
    forzar_periodo: bool = False,
    incluir_placeholder_pdf: bool = True,
) -> tuple[
    list[SeccionItem],
    list[RepresentanteItem],
    list[EstudianteItem],
    list[str],
    list[str],
]:
    correcciones = leer_correcciones_estudiantes(carpeta)
    secciones_map: dict[tuple[int, str, int], SeccionItem] = {}
    representantes_map: dict[str, RepresentanteItem] = {}
    estudiantes_map: dict[str, EstudianteItem] = {}
    por_revisar: list[str] = []
    avisos: list[str] = []

    def registrar_seccion(
        grado_numero: int, grado_nombre: str, nivel: str, letra: str, periodo: int
    ) -> None:
        clave = (grado_numero, letra, periodo)
        if clave not in secciones_map:
            secciones_map[clave] = SeccionItem(
                grado_numero=grado_numero,
                grado_nombre=grado_nombre,
                nivel=nivel,
                letra=letra,
                periodo_lectivo=periodo,
            )

    def vincular_representante(
        clave_dedup: str,
        p_nom: str,
        s_nom: str,
        p_ape: str,
        s_ape: str,
        telefono: str,
        es_placeholder: bool,
        cedula_est: str,
    ) -> str:
        if clave_dedup not in representantes_map:
            representantes_map[clave_dedup] = RepresentanteItem(
                clave_dedup=clave_dedup,
                primer_nombre=p_nom,
                segundo_nombre=s_nom,
                primer_apellido=p_ape,
                segundo_apellido=s_ape,
                telefono=telefono,
                es_placeholder=es_placeholder,
            )
        rep = representantes_map[clave_dedup]
        if not rep.telefono and telefono:
            rep.telefono = telefono
        if cedula_est not in rep.cedulas_estudiantes:
            rep.cedulas_estudiantes.append(cedula_est)
        return clave_dedup

    # 1. Archivos .xls (Liceo / Media General)
    for ruta in sorted(carpeta.rglob("*.xls"), key=lambda p: p.name.lower()):
        if salida in ruta.parents:
            continue
        filas, info_formato, texto_crudo = leer_filas_xls(ruta)
        periodo_archivo = (
            periodo_defecto
            if forzar_periodo
            else detectar_periodo_lectivo(texto_crudo, periodo_defecto)
        )
        leidos = 0
        for fila in filas:
            cedula = normalizar_cedula(fila.get("CEDULA", ""))
            if not cedula:
                continue

            if cedula in correcciones:
                p_nom, s_nom, p_ape, s_ape = correcciones[cedula]
            else:
                p_nom, s_nom, p_ape, s_ape = separar_columnas_nombre_apellido(
                    fila.get("NOMBRE", ""), fila.get("APELLIDO", "")
                )

            try:
                grado_num, grado_nom, nivel, seccion_letra = resolver_grado_y_seccion(
                    fila.get("AÑO/GRADO", ""), fila.get("SECCION", "")
                )
            except ValueError as err:
                avisos.append(f"[{ruta.name}] {err}")
                continue

            registrar_seccion(
                grado_num, grado_nom, nivel, seccion_letra, periodo_archivo
            )

            fecha_nac, es_estimada = normalizar_fecha(fila.get("FECHA NAC.", ""))

            nombre_rep = limpiar(fila.get("NOMBRE REP.", ""))
            ced_rep = normalizar_cedula(fila.get("CEDULA REP.", ""))
            telefono = normalizar_telefono(fila.get("CELULAR", ""))
            clave_rep_vinculada: str | None = None

            if nombre_rep:
                rp_nom, rs_nom, rp_ape, rs_ape, dudoso_rep = (
                    separar_4_campos_nombres_primero(nombre_rep)
                )
                if dudoso_rep:
                    por_revisar.append(
                        f"[REPRESENTANTE] {nombre_rep} -> nombres=({rp_nom!r}, {rs_nom!r}) "
                        f"apellidos=({rp_ape!r}, {rs_ape!r})"
                    )
                clave_rep = ced_rep or f"{rp_nom}|{rs_nom}|{rp_ape}|{rs_ape}|{telefono}"
                clave_rep_vinculada = vincular_representante(
                    clave_dedup=clave_rep,
                    p_nom=rp_nom,
                    s_nom=rs_nom,
                    p_ape=rp_ape,
                    s_ape=rs_ape,
                    telefono=telefono or "0000-0000000",
                    es_placeholder=False,
                    cedula_est=cedula,
                )

            if cedula in estudiantes_map:
                avisos.append(
                    f"[{ruta.name}] Estudiante duplicado {cedula} ({p_nom} {p_ape}); se conserva el primero"
                )
            else:
                estudiantes_map[cedula] = EstudianteItem(
                    cedula_estudiantil=cedula,
                    primer_nombre=p_nom,
                    segundo_nombre=s_nom,
                    primer_apellido=p_ape,
                    segundo_apellido=s_ape,
                    grado_numero=grado_num,
                    grado_nombre=grado_nom,
                    nivel=nivel,
                    seccion_letra=seccion_letra,
                    periodo_lectivo=periodo_archivo,
                    fecha_nacimiento=fecha_nac,
                    fecha_nacimiento_estimada=es_estimada,
                    clave_representante=clave_rep_vinculada,
                    origen=ruta.name,
                )
            leidos += 1

        if leidos == 0:
            avisos.append(f"[{ruta.name}] 0 registros leídos -> {info_formato}")
        print(
            f"  [XLS] {ruta.name} (periodo={periodo_archivo}): {leidos} estudiantes"
        )

    # 2. Archivos .pdf de grados (Escuela / Primaria)
    for ruta in sorted(carpeta.rglob("*.pdf"), key=lambda p: p.name.lower()):
        if salida in ruta.parents:
            continue
        texto = texto_pdf(ruta)
        upper = texto.upper()
        if "LISTADO DE DOCENTES" in upper or "LISTADO DE ESTUDIANTES" not in upper:
            continue

        periodo_archivo = (
            periodo_defecto
            if forzar_periodo
            else detectar_periodo_lectivo(texto, periodo_defecto)
        )
        leidos = 0
        for linea in texto.splitlines():
            linea = linea.strip()
            if not re.match(r"^\d+\s+[VvEe]?-?\d{5,12}\s", linea):
                continue
            m = RE_FILA_ESTUDIANTE_PDF.match(linea)
            if not m:
                avisos.append(
                    f"[{ruta.name}] Fila estudiante PDF sin interpretar: {linea}"
                )
                continue

            cedula = normalizar_cedula(m.group(2))
            completo = limpiar(m.group(3))
            telefono = normalizar_telefono(m.group(6))

            try:
                grado_num, grado_nom, nivel, seccion_letra = resolver_grado_y_seccion(
                    m.group(5)
                )
            except ValueError as err:
                avisos.append(f"[{ruta.name}] {err}")
                continue

            registrar_seccion(
                grado_num, grado_nom, nivel, seccion_letra, periodo_archivo
            )

            if cedula in correcciones:
                p_nom, s_nom, p_ape, s_ape = correcciones[cedula]
            else:
                p_nom, s_nom, p_ape, s_ape, dudoso = (
                    separar_4_campos_apellidos_primero(completo)
                )
                if dudoso:
                    por_revisar.append(
                        f"[ESTUDIANTE PDF] {completo} -> apellidos=({p_ape!r}, {s_ape!r}) "
                        f"nombres=({p_nom!r}, {s_nom!r}) ({cedula})"
                    )

            clave_rep_vinculada = None
            if incluir_placeholder_pdf and telefono:
                clave_rep = f"PDF_TEL|{telefono}|{p_ape}|{s_ape}"
                clave_rep_vinculada = vincular_representante(
                    clave_dedup=clave_rep,
                    p_nom="REPRESENTANTE",
                    s_nom="",
                    p_ape=p_ape,
                    s_ape=s_ape,
                    telefono=telefono,
                    es_placeholder=True,
                    cedula_est=cedula,
                )

            if cedula in estudiantes_map:
                avisos.append(
                    f"[{ruta.name}] Estudiante duplicado {cedula} ({completo}); se conserva el primero"
                )
            else:
                estudiantes_map[cedula] = EstudianteItem(
                    cedula_estudiantil=cedula,
                    primer_nombre=p_nom,
                    segundo_nombre=s_nom,
                    primer_apellido=p_ape,
                    segundo_apellido=s_ape,
                    grado_numero=grado_num,
                    grado_nombre=grado_nom,
                    nivel=nivel,
                    seccion_letra=seccion_letra,
                    periodo_lectivo=periodo_archivo,
                    fecha_nacimiento=FECHA_NACIMIENTO_DEFECTO,
                    fecha_nacimiento_estimada=True,
                    clave_representante=clave_rep_vinculada,
                    origen=ruta.name,
                )
            leidos += 1
        print(
            f"  [PDF] {ruta.name} (periodo={periodo_archivo}): {leidos} estudiantes"
        )

    secciones_ordenadas = sorted(
        secciones_map.values(),
        key=lambda s: (s.periodo_lectivo, s.grado_numero, s.letra),
    )
    return (
        secciones_ordenadas,
        list(representantes_map.values()),
        list(estudiantes_map.values()),
        por_revisar,
        avisos,
    )


# ---------------------------------------------------------------------------
# Generadores SQL (ordenados por dependencias FK del modelo actual)
# ---------------------------------------------------------------------------
def _encabezado_sql(titulo: str, total: int) -> list[str]:
    return [
        f"-- {titulo} (generado por scripts/excel.py)",
        f"-- Generado el {datetime.now(timezone.utc).astimezone():%d-%m-%Y %H:%M} | {total} registros",
        "-- Script idempotente: puede re-ejecutarse sin duplicar registros activos.",
        "",
        "SET client_encoding = 'UTF8';",
        "BEGIN;",
        "",
    ]


def sql_docentes(docentes: list[DocenteItem], envolver_tx: bool = True) -> str:
    lineas = (
        _encabezado_sql("01. Docentes (sin dependencias)", len(docentes))
        if envolver_tx
        else []
    )
    for d in docentes:
        ced = sql_texto(d.cedula)
        lineas.append(
            "INSERT INTO docentes (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, cedula, nivel, fecha_creacion, fecha_actualizacion)\n"
            f"SELECT {sql_texto(d.primer_nombre)}, {sql_texto_nullable(d.segundo_nombre)}, "
            f"{sql_texto(d.primer_apellido)}, {sql_texto_nullable(d.segundo_apellido)}, "
            f"{ced}, {sql_texto(d.nivel)}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP\n"
            f"WHERE NOT EXISTS (SELECT 1 FROM docentes WHERE cedula = {ced} AND fecha_eliminacion IS NULL);\n"
        )
    if envolver_tx:
        lineas.append("COMMIT;")
    return "\n".join(lineas) + "\n"


def sql_grados_y_secciones(
    secciones: list[SeccionItem], envolver_tx: bool = True
) -> str:
    lineas = (
        _encabezado_sql(
            "02. Grados (catálogo base) y Secciones (depende de grados.id)",
            len(secciones),
        )
        if envolver_tx
        else []
    )
    # Asegura que los grados requeridos existan en el catálogo 1..11
    numeros_usados = sorted({s.grado_numero for s in secciones})
    for num in numeros_usados:
        nombre_g, nivel_g = CATALOGO_GRADOS[num]
        lineas.append(
            "INSERT INTO grados (numero, nombre, nivel, fecha_creacion, fecha_actualizacion)\n"
            f"SELECT {num}, {sql_texto(nombre_g)}, {sql_texto(nivel_g)}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP\n"
            f"WHERE NOT EXISTS (SELECT 1 FROM grados WHERE numero = {num} AND fecha_eliminacion IS NULL);\n"
        )

    for s in secciones:
        letra = sql_texto(s.letra)
        lineas.append(
            "INSERT INTO secciones (id_grado, letra, periodo_lectivo, id_docente_titular, fecha_creacion, fecha_actualizacion)\n"
            f"SELECT g.id, {letra}, {s.periodo_lectivo}, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP\n"
            f"FROM grados g WHERE g.numero = {s.grado_numero} AND g.fecha_eliminacion IS NULL\n"
            "  AND NOT EXISTS (\n"
            "    SELECT 1 FROM secciones sec\n"
            f"    WHERE sec.id_grado = g.id AND sec.letra = {letra} "
            f"AND sec.periodo_lectivo = {s.periodo_lectivo} AND sec.fecha_eliminacion IS NULL\n"
            "  );\n"
        )
    if envolver_tx:
        lineas.append("COMMIT;")
    return "\n".join(lineas) + "\n"


def sql_representantes(
    representantes: list[RepresentanteItem], envolver_tx: bool = True
) -> str:
    lineas = (
        _encabezado_sql("03. Representantes (sin dependencias)", len(representantes))
        if envolver_tx
        else []
    )
    for r in representantes:
        p_nom = sql_texto(r.primer_nombre)
        s_nom = sql_texto_nullable(r.segundo_nombre)
        p_ape = sql_texto(r.primer_apellido)
        s_ape = sql_texto_nullable(r.segundo_apellido)
        tel = sql_texto(r.telefono)

        cond_rep = (
            f"primer_nombre = {p_nom} "
            f"AND COALESCE(segundo_nombre, '') = {sql_texto(r.segundo_nombre.strip())} "
            f"AND primer_apellido = {p_ape} "
            f"AND COALESCE(segundo_apellido, '') = {sql_texto(r.segundo_apellido.strip())} "
            f"AND telefono = {tel} AND fecha_eliminacion IS NULL"
        )

        lineas.append(
            "INSERT INTO representantes (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, telefono, fecha_creacion, fecha_actualizacion)\n"
            f"SELECT {p_nom}, {s_nom}, {p_ape}, {s_ape}, {tel}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP\n"
            f"WHERE NOT EXISTS (SELECT 1 FROM representantes WHERE {cond_rep});\n"
        )
    if envolver_tx:
        lineas.append("COMMIT;")
    return "\n".join(lineas) + "\n"


def sql_estudiantes(
    estudiantes: list[EstudianteItem],
    representantes: list[RepresentanteItem],
    envolver_tx: bool = True,
) -> str:
    lineas = (
        _encabezado_sql(
            "04. Estudiantes (depende de secciones.id y representantes.id)",
            len(estudiantes),
        )
        if envolver_tx
        else []
    )
    reps_por_clave = {r.clave_dedup: r for r in representantes}

    for e in estudiantes:
        ced = sql_texto(e.cedula_estudiantil)
        letra = sql_texto(e.seccion_letra)
        fnac = sql_texto(e.fecha_nacimiento)

        rep = reps_por_clave.get(e.clave_representante) if e.clave_representante else None
        if rep is not None:
            subquery_rep = (
                "(\n"
                "    SELECT r.id FROM representantes r\n"
                f"    WHERE r.primer_nombre = {sql_texto(rep.primer_nombre)}\n"
                f"      AND COALESCE(r.segundo_nombre, '') = {sql_texto(rep.segundo_nombre.strip())}\n"
                f"      AND r.primer_apellido = {sql_texto(rep.primer_apellido)}\n"
                f"      AND COALESCE(r.segundo_apellido, '') = {sql_texto(rep.segundo_apellido.strip())}\n"
                f"      AND r.telefono = {sql_texto(rep.telefono)}\n"
                "      AND r.fecha_eliminacion IS NULL\n"
                "    ORDER BY r.id ASC LIMIT 1\n"
                "  )"
            )
        else:
            subquery_rep = "NULL"

        lineas.append(
            "INSERT INTO estudiantes (id_seccion, id_representante, cedula_estudiantil, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, fecha_nacimiento, fecha_creacion, fecha_actualizacion)\n"
            "SELECT\n"
            "  sec.id,\n"
            f"  {subquery_rep},\n"
            f"  {ced}, {sql_texto(e.primer_nombre)}, {sql_texto_nullable(e.segundo_nombre)}, "
            f"{sql_texto(e.primer_apellido)}, {sql_texto_nullable(e.segundo_apellido)}, "
            f"TIMESTAMP {fnac}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP\n"
            "FROM secciones sec\n"
            "JOIN grados g ON sec.id_grado = g.id\n"
            f"WHERE g.numero = {e.grado_numero} AND sec.letra = {letra} "
            f"AND sec.periodo_lectivo = {e.periodo_lectivo}\n"
            "  AND sec.fecha_eliminacion IS NULL AND g.fecha_eliminacion IS NULL\n"
            f"  AND NOT EXISTS (SELECT 1 FROM estudiantes est WHERE est.cedula_estudiantil = {ced} AND est.fecha_eliminacion IS NULL);\n"
        )
    if envolver_tx:
        lineas.append("COMMIT;")
    return "\n".join(lineas) + "\n"


def sql_maestro(
    docentes: list[DocenteItem],
    secciones: list[SeccionItem],
    representantes: list[RepresentanteItem],
    estudiantes: list[EstudianteItem],
) -> str:
    total = len(docentes) + len(secciones) + len(representantes) + len(estudiantes)
    partes = _encabezado_sql("00. Seed completo en orden de dependencias FK", total)
    partes.append("-- === 1. DOCENTES ===")
    partes.append(sql_docentes(docentes, envolver_tx=False))
    partes.append("-- === 2. GRADOS Y SECCIONES ===")
    partes.append(sql_grados_y_secciones(secciones, envolver_tx=False))
    partes.append("-- === 3. REPRESENTANTES ===")
    partes.append(sql_representantes(representantes, envolver_tx=False))
    partes.append("-- === 4. ESTUDIANTES ===")
    partes.append(sql_estudiantes(estudiantes, representantes, envolver_tx=False))
    partes.append("COMMIT;")
    return "\n".join(partes) + "\n"


def construir_json(
    docentes: list[DocenteItem],
    secciones: list[SeccionItem],
    representantes: list[RepresentanteItem],
    estudiantes: list[EstudianteItem],
) -> str:
    grados_usados = [
        {
            "numero": num,
            "nombre": CATALOGO_GRADOS[num][0],
            "nivel": CATALOGO_GRADOS[num][1],
        }
        for num in sorted({s.grado_numero for s in secciones})
    ]
    payload = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "orden_dependencias": [
            "docentes",
            "grados",
            "secciones",
            "representantes",
            "estudiantes",
        ],
        "resumen": {
            "docentes": len(docentes),
            "grados": len(grados_usados),
            "secciones": len(secciones),
            "representantes": len(representantes),
            "estudiantes": len(estudiantes),
            "estudiantes_con_fecha_estimada": sum(
                1 for e in estudiantes if e.fecha_nacimiento_estimada
            ),
            "representantes_placeholder": sum(
                1 for r in representantes if r.es_placeholder
            ),
        },
        "docentes": [asdict(d) for d in docentes],
        "grados": grados_usados,
        "secciones": [asdict(s) for s in secciones],
        "representantes": [asdict(r) for r in representantes],
        "estudiantes": [asdict(e) for e in estudiantes],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main() -> None:
    now = datetime.now(timezone.utc).astimezone()
    periodo_actual = now.year if now.month >= 8 else now.year - 1

    ap = argparse.ArgumentParser(
        description="Genera .sql (en orden de dependencias) y .json a partir de las nóminas."
    )
    ap.add_argument(
        "paso",
        choices=["todo", "docentes", "secciones", "representantes", "estudiantes"],
        default="todo",
        nargs="?",
        help="Qué entidad generar (por defecto: todo)",
    )
    ap.add_argument(
        "--carpeta",
        default=os.environ.get("NOMINAS_CARPETA"),
        help="Carpeta con los PDF/.xls. También vale NOMINAS_CARPETA.",
    )
    ap.add_argument(
        "--salida",
        help=f"Carpeta de salida (por defecto <carpeta>/{CARPETA_SALIDA})",
    )
    ap.add_argument(
        "--formato",
        choices=["sql", "json", "ambos"],
        default="ambos",
        help="Formato de salida (por defecto: ambos)",
    )
    ap.add_argument(
        "--nivel-docentes",
        choices=list(NIVELES_VALIDOS),
        default="liceo",
        help="Nivel por defecto para docentes cuando el PDF no lo especifica (escuela | liceo).",
    )
    ap.add_argument(
        "--periodo",
        type=int,
        default=None,
        help="Fuerza el periodo_lectivo (ej. 2026). Si se omite, se detecta de cada archivo.",
    )
    ap.add_argument(
        "--sin-placeholder-pdf",
        action="store_true",
        help="No crear representantes placeholder para los PDF de primaria que solo traen teléfono.",
    )
    args = ap.parse_args()

    if args.periodo is not None and args.periodo < 2000:
        sys.exit("El --periodo debe ser mayor o igual a 2000 (ej. 2026).")

    if not args.carpeta:
        sys.exit(
            "Indica la carpeta de nóminas con --carpeta o con la variable NOMINAS_CARPETA"
        )
    carpeta = Path(args.carpeta).expanduser().resolve()
    if not carpeta.is_dir():
        sys.exit(f"No existe la carpeta: {carpeta}")

    salida = (
        Path(args.salida).expanduser().resolve()
        if args.salida
        else carpeta / CARPETA_SALIDA
    )
    salida.mkdir(parents=True, exist_ok=True)

    periodo_base = args.periodo if args.periodo is not None else periodo_actual
    forzar_periodo = args.periodo is not None

    print(f"Leyendo nóminas desde: {carpeta}")
    docentes, rev_doc, av_doc = extraer_docentes(
        carpeta, salida, nivel_defecto=args.nivel_docentes
    )
    secciones, representantes, estudiantes, rev_acad, av_acad = extraer_academico(
        carpeta,
        salida,
        periodo_defecto=periodo_base,
        forzar_periodo=forzar_periodo,
        incluir_placeholder_pdf=not args.sin_placeholder_pdf,
    )

    por_revisar = rev_doc + rev_acad
    avisos = av_doc + av_acad

    if args.formato in ("sql", "ambos"):
        if args.paso in ("todo", "docentes"):
            (salida / "01_docentes.sql").write_text(
                sql_docentes(docentes), encoding="utf-8"
            )
        if args.paso in ("todo", "secciones"):
            (salida / "02_grados_y_secciones.sql").write_text(
                sql_grados_y_secciones(secciones), encoding="utf-8"
            )
        if args.paso in ("todo", "representantes"):
            (salida / "03_representantes.sql").write_text(
                sql_representantes(representantes), encoding="utf-8"
            )
        if args.paso in ("todo", "estudiantes"):
            (salida / "04_estudiantes.sql").write_text(
                sql_estudiantes(estudiantes, representantes), encoding="utf-8"
            )
        if args.paso == "todo":
            (salida / "00_todo_seed.sql").write_text(
                sql_maestro(docentes, secciones, representantes, estudiantes),
                encoding="utf-8",
            )

    if args.formato in ("json", "ambos"):
        (salida / "seed_data.json").write_text(
            construir_json(docentes, secciones, representantes, estudiantes),
            encoding="utf-8",
        )

    print(
        f"\nListo -> {salida}\n"
        f"  Docentes: {len(docentes)} | Secciones: {len(secciones)} | "
        f"Representantes: {len(representantes)} | Estudiantes: {len(estudiantes)}"
    )

    if por_revisar:
        print(f"\n=== REVISAR ({len(por_revisar)}): nombres ambiguos ===")
        for linea in por_revisar:
            print("  ", linea)
        print(
            f"  Corrige docentes en {carpeta / CORRECCIONES_DOCENTES} "
            f"y estudiantes en {carpeta / CORRECCIONES_ESTUDIANTES}."
        )

    if avisos:
        print(f"\n=== AVISOS ({len(avisos)}) ===")
        for a in avisos:
            print("  ", a)

    if args.formato in ("sql", "ambos"):
        mapa_destinos = {
            "todo": "00_todo_seed.sql",
            "docentes": "01_docentes.sql",
            "secciones": "02_grados_y_secciones.sql",
            "representantes": "03_representantes.sql",
            "estudiantes": "04_estudiantes.sql",
        }
        destino_ejemplo = salida / mapa_destinos[args.paso]
        print(
            f'\nPara poblar PostgreSQL:\n  psql -U postgres -d <nombre_bd> -f "{destino_ejemplo}"'
        )


if __name__ == "__main__":
    main()
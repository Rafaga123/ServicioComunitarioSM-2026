"""Genera archivos .sql (ordenados por dependencias FK) y seed_data.json
a partir de las nóminas del colegio (PDF de docentes, PDF de primaria y .xls de media).

Uso (desde la raíz del proyecto, con el entorno virtual activo):

    python backend/scripts/excel.py todo --carpeta "C:\\nominas_prueba"
    python backend/scripts/excel.py todo --carpeta "C:\\nominas_prueba" --formato ambos

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


def separar_grado_y_seccion(grado_raw: str, seccion_raw: str = "") -> tuple[str, str]:
    """Normaliza grado y sección desde .xls ('Tercer Año', 'U') o PDF ('Cuarto Grado B')."""
    grado = limpiar(grado_raw)
    seccion = limpiar(seccion_raw)

    if not seccion:
        m = re.match(r"^(.+?)\s+([A-Z])$", grado)
        if m:
            grado = m.group(1).strip()
            seccion = m.group(2).strip()
        else:
            seccion = "U"

    return grado, seccion


def sql_texto(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------
@dataclass
class DocenteItem:
    cedula: str
    primer_nombre: str
    segundo_nombre: str
    primer_apellido: str
    segundo_apellido: str
    origen: str


@dataclass
class GradoItem:
    grado: str
    seccion: str


@dataclass
class EstudianteItem:
    cedula_estudiantil: str
    primer_nombre: str
    segundo_nombre: str
    primer_apellido: str
    segundo_apellido: str
    grado: str
    seccion: str
    fecha_nacimiento: str
    fecha_nacimiento_estimada: bool
    origen: str


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


def leer_filas_xls(ruta: Path) -> tuple[list[dict[str, str]], str]:
    """Lee tablas .xls ya sean HTML (UTF-8/UTF-16/CP1252), XML 2003, XLSX o BIFF8."""
    raw = ruta.read_bytes()
    if not raw:
        return [], "archivo vacío (0 bytes)"

    # 1. ZIP (.xlsx guardado con extensión .xls)
    if raw.startswith(b"PK\x03\x04"):
        try:
            import openpyxl

            wb = openpyxl.load_workbook(ruta, data_only=True)
            ws = wb.active
            filas = [
                ["" if v is None else str(v) for v in row]
                for row in ws.iter_rows(values_only=True)
            ]
            return _filas_a_registros(filas), "XLSX"
        except Exception as e:
            return [], f"XLSX (instala openpyxl o usa el .xls original: {e})"

    # 2. OLE2 BIFF8 (.xls binario clásico guardado desde Excel)
    if raw.startswith(b"\xd0\xcf\x11\xe0"):
        try:
            import xlrd

            wb = xlrd.open_workbook(str(ruta))
            sh = wb.sheet_by_index(0)
            filas = [
                [str(sh.cell_value(r, c)) for c in range(sh.ncols)]
                for r in range(sh.nrows)
            ]
            return _filas_a_registros(filas), "BIFF8"
        except Exception as e:
            return [], f"BIFF8 binario (instala xlrd o usa el .xls original: {e})"

    texto = decodificar_bytes(raw)
    inicio = texto.lstrip()[:200].lower()

    # 3. XML Spreadsheet 2003
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
        return _filas_a_registros(filas_xml), "XML2003"

    # 4. Tabla HTML
    parser = _TablaHTMLParser()
    parser.feed(texto)
    regs = _filas_a_registros(parser.filas)
    return regs, f"HTML (filas_tr={len(parser.filas)}, inicio={raw[:45]!r})"


def leer_correcciones(
    carpeta: Path, nombre_archivo: str
) -> dict[str, tuple[str, str, str, str]]:
    """Acepta CSV con columnas:
    cedula,primer_nombre,segundo_nombre,primer_apellido,segundo_apellido
    o formato corto: cedula,nombre,apellido
    """
    ruta = carpeta / nombre_archivo
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


def extraer_docentes(
    carpeta: Path, salida: Path
) -> tuple[list[DocenteItem], list[str], list[str]]:
    correcciones = leer_correcciones(carpeta, CORRECCIONES_DOCENTES)
    docentes: dict[str, DocenteItem] = {}
    por_revisar: list[str] = []
    avisos: list[str] = []

    for ruta in sorted(carpeta.rglob("*.pdf"), key=lambda p: p.name.lower()):
        if salida in ruta.parents:
            continue
        texto = texto_pdf(ruta)
        if "LISTADO DE DOCENTES" not in texto.upper():
            continue

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

            if cedula in correcciones:
                p_nom, s_nom, p_ape, s_ape = correcciones[cedula]
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
                    origen=ruta.name,
                )
            leidos += 1
        print(f"  [DOCENTES] {ruta.name}: {leidos} registros")

    return list(docentes.values()), por_revisar, avisos


# ---------------------------------------------------------------------------
# Extracción de Grados, Estudiantes y Representantes (.xls y .pdf)
# ---------------------------------------------------------------------------
RE_FILA_ESTUDIANTE_PDF = re.compile(
    r"^(\d+)\s+([VvEe]?-?\d{5,12})\s+(.+?)\s+([MF])\s+(.+?)\s+(0\d{3}[\d.\-]+)$"
)


def extraer_academico(
    carpeta: Path, salida: Path, incluir_placeholder_pdf: bool = True
) -> tuple[
    list[GradoItem],
    list[EstudianteItem],
    list[RepresentanteItem],
    list[str],
    list[str],
]:
    correcciones = leer_correcciones(carpeta, CORRECCIONES_ESTUDIANTES)
    grados_map: dict[tuple[str, str], GradoItem] = {}
    estudiantes_map: dict[str, EstudianteItem] = {}
    representantes_map: dict[str, RepresentanteItem] = {}
    por_revisar: list[str] = []
    avisos: list[str] = []

    def registrar_grado(grado: str, seccion: str) -> None:
        clave = (grado, seccion)
        if clave not in grados_map:
            grados_map[clave] = GradoItem(grado=grado, seccion=seccion)

    def vincular_representante(
        clave_dedup: str,
        p_nom: str,
        s_nom: str,
        p_ape: str,
        s_ape: str,
        telefono: str,
        es_placeholder: bool,
        cedula_est: str,
    ) -> None:
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

    # 1. Archivos .xls (Media General)
    for ruta in sorted(carpeta.rglob("*.xls"), key=lambda p: p.name.lower()):
        if salida in ruta.parents:
            continue
        filas, info_formato = leer_filas_xls(ruta)
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

            grado, seccion = separar_grado_y_seccion(
                fila.get("AÑO/GRADO", ""), fila.get("SECCION", "")
            )
            registrar_grado(grado, seccion)

            fecha_nac, es_estimada = normalizar_fecha(fila.get("FECHA NAC.", ""))

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
                    grado=grado,
                    seccion=seccion,
                    fecha_nacimiento=fecha_nac,
                    fecha_nacimiento_estimada=es_estimada,
                    origen=ruta.name,
                )

            nombre_rep = limpiar(fila.get("NOMBRE REP.", ""))
            ced_rep = normalizar_cedula(fila.get("CEDULA REP.", ""))
            telefono = normalizar_telefono(fila.get("CELULAR", ""))

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
                vincular_representante(
                    clave_dedup=clave_rep,
                    p_nom=rp_nom,
                    s_nom=rs_nom,
                    p_ape=rp_ape,
                    s_ape=rs_ape,
                    telefono=telefono or "0000-0000000",
                    es_placeholder=False,
                    cedula_est=cedula,
                )
            leidos += 1

        if leidos == 0:
            avisos.append(f"[{ruta.name}] 0 registros leídos -> {info_formato}")
        print(f"  [XLS] {ruta.name}: {leidos} estudiantes")

    # 2. Archivos .pdf de grados (Primaria)
    for ruta in sorted(carpeta.rglob("*.pdf"), key=lambda p: p.name.lower()):
        if salida in ruta.parents:
            continue
        texto = texto_pdf(ruta)
        upper = texto.upper()
        if "LISTADO DE DOCENTES" in upper or "LISTADO DE ESTUDIANTES" not in upper:
            continue

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
            grado, seccion = separar_grado_y_seccion(m.group(5))
            telefono = normalizar_telefono(m.group(6))
            registrar_grado(grado, seccion)

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
                    grado=grado,
                    seccion=seccion,
                    fecha_nacimiento=FECHA_NACIMIENTO_DEFECTO,
                    fecha_nacimiento_estimada=True,
                    origen=ruta.name,
                )

            if incluir_placeholder_pdf and telefono:
                clave_rep = f"PDF_TEL|{telefono}|{p_ape}|{s_ape}"
                vincular_representante(
                    clave_dedup=clave_rep,
                    p_nom="REPRESENTANTE",
                    s_nom="",
                    p_ape=p_ape,
                    s_ape=s_ape,
                    telefono=telefono,
                    es_placeholder=True,
                    cedula_est=cedula,
                )
            leidos += 1
        print(f"  [PDF] {ruta.name}: {leidos} estudiantes")

    grados_ordenados = sorted(grados_map.values(), key=lambda g: (g.grado, g.seccion))
    return (
        grados_ordenados,
        list(estudiantes_map.values()),
        list(representantes_map.values()),
        por_revisar,
        avisos,
    )


# ---------------------------------------------------------------------------
# Generadores SQL (ordenados por dependencias FK)
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
            "INSERT INTO docentes (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, cedula, fecha_creacion, fecha_actualizacion)\n"
            f"SELECT {sql_texto(d.primer_nombre)}, {sql_texto(d.segundo_nombre)}, "
            f"{sql_texto(d.primer_apellido)}, {sql_texto(d.segundo_apellido)}, {ced}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP\n"
            f"WHERE NOT EXISTS (SELECT 1 FROM docentes WHERE cedula = {ced} AND fecha_eliminacion IS NULL);\n"
        )
    if envolver_tx:
        lineas.append("COMMIT;")
    return "\n".join(lineas) + "\n"


def sql_grados(grados: list[GradoItem], envolver_tx: bool = True) -> str:
    lineas = (
        _encabezado_sql("02. Grados (sin dependencias)", len(grados))
        if envolver_tx
        else []
    )
    for g in grados:
        gr = sql_texto(g.grado)
        sec = sql_texto(g.seccion)
        lineas.append(
            "INSERT INTO grados (grado, seccion, fecha_creacion, fecha_actualizacion)\n"
            f"SELECT {gr}, {sec}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP\n"
            f"WHERE NOT EXISTS (SELECT 1 FROM grados WHERE grado = {gr} AND seccion = {sec} AND fecha_eliminacion IS NULL);\n"
        )
    if envolver_tx:
        lineas.append("COMMIT;")
    return "\n".join(lineas) + "\n"


def sql_estudiantes(estudiantes: list[EstudianteItem], envolver_tx: bool = True) -> str:
    lineas = (
        _encabezado_sql("03. Estudiantes (depende de grados.id)", len(estudiantes))
        if envolver_tx
        else []
    )
    for e in estudiantes:
        ced = sql_texto(e.cedula_estudiantil)
        gr = sql_texto(e.grado)
        sec = sql_texto(e.seccion)
        fnac = sql_texto(e.fecha_nacimiento)
        lineas.append(
            "INSERT INTO estudiantes (grado_id, cedula_estudiantil, primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, fecha_nacimiento, fecha_creacion, fecha_actualizacion)\n"
            "SELECT g.id, "
            f"{ced}, {sql_texto(e.primer_nombre)}, {sql_texto(e.segundo_nombre)}, "
            f"{sql_texto(e.primer_apellido)}, {sql_texto(e.segundo_apellido)}, TIMESTAMP {fnac}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP\n"
            f"FROM grados g WHERE g.grado = {gr} AND g.seccion = {sec} AND g.fecha_eliminacion IS NULL\n"
            f"AND NOT EXISTS (SELECT 1 FROM estudiantes WHERE cedula_estudiantil = {ced} AND fecha_eliminacion IS NULL);\n"
        )
    if envolver_tx:
        lineas.append("COMMIT;")
    return "\n".join(lineas) + "\n"


def sql_representantes(
    representantes: list[RepresentanteItem], envolver_tx: bool = True
) -> str:
    lineas = (
        _encabezado_sql(
            "04. Representantes y estudiantes_representantes (depende de estudiantes)",
            len(representantes),
        )
        if envolver_tx
        else []
    )
    for r in representantes:
        p_nom = sql_texto(r.primer_nombre)
        s_nom = sql_texto(r.segundo_nombre)
        p_ape = sql_texto(r.primer_apellido)
        s_ape = sql_texto(r.segundo_apellido)
        tel = sql_texto(r.telefono)

        cond_rep = (
            f"primer_nombre = {p_nom} AND segundo_nombre = {s_nom} "
            f"AND primer_apellido = {p_ape} AND segundo_apellido = {s_ape} "
            f"AND telefono = {tel} AND fecha_eliminacion IS NULL"
        )

        lineas.append(
            "INSERT INTO representantes (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, telefono, fecha_creacion, fecha_actualizacion)\n"
            f"SELECT {p_nom}, {s_nom}, {p_ape}, {s_ape}, {tel}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP\n"
            f"WHERE NOT EXISTS (SELECT 1 FROM representantes WHERE {cond_rep});\n"
        )
        for ced_est in r.cedulas_estudiantes:
            ced_sql = sql_texto(ced_est)
            lineas.append(
                "INSERT INTO estudiantes_representantes (id_estudiante, id_representante, fecha_creacion, fecha_actualizacion)\n"
                "SELECT e.id, r.id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP\n"
                "FROM estudiantes e, representantes r\n"
                f"WHERE e.cedula_estudiantil = {ced_sql} AND e.fecha_eliminacion IS NULL\n"
                f"  AND r.primer_nombre = {p_nom} AND r.segundo_nombre = {s_nom}\n"
                f"  AND r.primer_apellido = {p_ape} AND r.segundo_apellido = {s_ape}\n"
                f"  AND r.telefono = {tel} AND r.fecha_eliminacion IS NULL\n"
                "  AND NOT EXISTS (\n"
                "    SELECT 1 FROM estudiantes_representantes er WHERE er.id_estudiante = e.id AND er.id_representante = r.id\n"
                "  );\n"
            )
    if envolver_tx:
        lineas.append("COMMIT;")
    return "\n".join(lineas) + "\n"


def sql_maestro(
    docentes: list[DocenteItem],
    grados: list[GradoItem],
    estudiantes: list[EstudianteItem],
    representantes: list[RepresentanteItem],
) -> str:
    total = len(docentes) + len(grados) + len(estudiantes) + len(representantes)
    partes = _encabezado_sql("00. Seed completo en orden de dependencias FK", total)
    partes.append("-- === 1. DOCENTES ===")
    partes.append(sql_docentes(docentes, envolver_tx=False))
    partes.append("-- === 2. GRADOS ===")
    partes.append(sql_grados(grados, envolver_tx=False))
    partes.append("-- === 3. ESTUDIANTES ===")
    partes.append(sql_estudiantes(estudiantes, envolver_tx=False))
    partes.append("-- === 4. REPRESENTANTES Y VINCULOS ===")
    partes.append(sql_representantes(representantes, envolver_tx=False))
    partes.append("COMMIT;")
    return "\n".join(partes) + "\n"


def construir_json(
    docentes: list[DocenteItem],
    grados: list[GradoItem],
    estudiantes: list[EstudianteItem],
    representantes: list[RepresentanteItem],
) -> str:
    payload = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "orden_dependencias": [
            "docentes",
            "grados",
            "estudiantes",
            "representantes",
            "estudiantes_representantes",
        ],
        "resumen": {
            "docentes": len(docentes),
            "grados": len(grados),
            "estudiantes": len(estudiantes),
            "representantes": len(representantes),
            "estudiantes_con_fecha_estimada": sum(
                1 for e in estudiantes if e.fecha_nacimiento_estimada
            ),
            "representantes_placeholder": sum(
                1 for r in representantes if r.es_placeholder
            ),
        },
        "docentes": [asdict(d) for d in docentes],
        "grados": [asdict(g) for g in grados],
        "estudiantes": [asdict(e) for e in estudiantes],
        "representantes": [asdict(r) for r in representantes],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Genera .sql (en orden de dependencias) y .json a partir de las nóminas."
    )
    ap.add_argument(
        "paso",
        choices=["todo", "docentes", "grados", "estudiantes", "representantes"],
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
        "--sin-placeholder-pdf",
        action="store_true",
        help="No crear representantes placeholder para los PDF de primaria que solo traen teléfono.",
    )
    args = ap.parse_args()

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

    print(f"Leyendo nóminas desde: {carpeta}")
    docentes, rev_doc, av_doc = extraer_docentes(carpeta, salida)
    grados, estudiantes, representantes, rev_acad, av_acad = extraer_academico(
        carpeta, salida, incluir_placeholder_pdf=not args.sin_placeholder_pdf
    )

    por_revisar = rev_doc + rev_acad
    avisos = av_doc + av_acad

    if args.formato in ("sql", "ambos"):
        if args.paso in ("todo", "docentes"):
            (salida / "01_docentes.sql").write_text(
                sql_docentes(docentes), encoding="utf-8"
            )
        if args.paso in ("todo", "grados"):
            (salida / "02_grados.sql").write_text(
                sql_grados(grados), encoding="utf-8"
            )
        if args.paso in ("todo", "estudiantes"):
            (salida / "03_estudiantes.sql").write_text(
                sql_estudiantes(estudiantes), encoding="utf-8"
            )
        if args.paso in ("todo", "representantes"):
            (salida / "04_representantes.sql").write_text(
                sql_representantes(representantes), encoding="utf-8"
            )
        if args.paso == "todo":
            (salida / "00_todo_seed.sql").write_text(
                sql_maestro(docentes, grados, estudiantes, representantes),
                encoding="utf-8",
            )

    if args.formato in ("json", "ambos"):
        (salida / "seed_data.json").write_text(
            construir_json(docentes, grados, estudiantes, representantes),
            encoding="utf-8",
        )

    print(
        f"\nListo -> {salida}\n"
        f"  Docentes: {len(docentes)} | Grados: {len(grados)} | "
        f"Estudiantes: {len(estudiantes)} | Representantes: {len(representantes)}"
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
        destino_ejemplo = salida / (
            "00_todo_seed.sql" if args.paso == "todo" else f"01_{args.paso}.sql"
        )
        print(
            f'\nPara poblar PostgreSQL:\n  psql -U postgres -d <nombre_bd> -f "{destino_ejemplo}"'
        )


if __name__ == "__main__":
    main()
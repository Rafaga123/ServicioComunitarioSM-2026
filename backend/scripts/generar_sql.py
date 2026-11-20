"""Genera archivos .sql (con INSERT) a partir de las nóminas del colegio.

Los archivos de origen (PDF / .xls) NO viven en el repositorio: se leen desde una
carpeta que se indica al ejecutar, y los .sql generados se escriben en una
subcarpeta `sql/` dentro de esa misma carpeta.


Uso (desde backend/, con el entorno virtual activo y `pip install pdfplumber`):

    python scripts/generar_sql.py docentes --carpeta "C:\\ruta\\a\\nominas\\2026-2027"

La carpeta también puede indicarse con la variable de entorno NOMINAS_CARPETA.

Cada año escolar basta con poner los documentos nuevos en una carpeta y volver a
ejecutar. Los INSERT generados son re-ejecutables: si el docente (misma cédula)
ya está en la tabla, la sentencia no hace nada.

Correcciones de nombres: el PDF trae "APELLIDOS NOMBRES" sin separador y los
nombres de 3 palabras son ambiguos. El script los lista como "REVISAR"; se
corrigen creando en la carpeta de nóminas un archivo `correcciones_docentes.csv`:
Esto no he visto la forma de corregirlo

    cedula,nombre,apellido
    En pruebas, el de la profe carmen tuve que crear el csv
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
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
ARCHIVO_CORRECCIONES = "correcciones_docentes.csv"


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------
def limpiar(texto: str) -> str:
    """Mayúsculas, espacios colapsados y la Ñ rota ("MONTA?EZ") reparada."""
    texto = " ".join(texto.replace("\xa0", " ").split()).upper()
    return re.sub(r"(?<=[A-ZÁÉÍÓÚ])\?(?=[A-ZÁÉÍÓÚ])", "Ñ", texto)


def solo_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def normalizar_cedula(texto: str) -> str:
    """'v-1927' / '-1927' / '1927' -> 'V-1927' (o 'E-' para extranjeros)."""
    prefijo = "E" if texto.strip().upper().startswith("E") else "V"
    return f"{prefijo}-{solo_digitos(texto)}"


def grupos(texto: str) -> list[str]:
    """Divide en palabras uniendo las partículas con la siguiente
    ("DE LOS ANGELES" cuenta como una sola unidad)."""
    salida: list[str] = []
    pendientes: list[str] = []
    for token in texto.split():
        if token in PARTICULAS:
            pendientes.append(token)
            continue
        salida.append(" ".join([*pendientes, token]))
        pendientes = []
    if pendientes:
        salida.append(" ".join(pendientes))
    return salida


def separar_apellidos_primero(texto: str) -> tuple[str, str, bool]:
    """'ALCALA MEJIAS JENNY JOSENIE' -> (nombre, apellido, dudoso)."""
    gs = grupos(texto)
    n = len(gs)
    if n == 1:
        return "", gs[0], True
    if n == 2:
        return gs[1], gs[0], False
    return " ".join(gs[2:]), " ".join(gs[:2]), n != 4  # 3 o 5+ palabras: ambiguo


def sql_texto(valor: str) -> str:
    """Literal SQL seguro: comillas simples y duplicando las que haya dentro."""
    return "'" + valor.replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# Docentes
# ---------------------------------------------------------------------------
@dataclass
class Docente:
    cedula: str
    nombre: str
    apellido: str
    origen: str


RE_FILA_DOCENTE = re.compile(
    r"^(\d+)\s+([VvEe]?-?\d{5,9})\s+(.+?)(?:\s+(\S+@\S+))?(?:\s+(0\d{3}[\d.\-]+))?$"
)


def texto_pdf(ruta: Path) -> str:
    import pdfplumber  # import tardío: solo hace falta si hay PDFs

    with pdfplumber.open(ruta) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


def leer_correcciones(carpeta: Path) -> dict[str, tuple[str, str]]:
    ruta = carpeta / ARCHIVO_CORRECCIONES
    if not ruta.is_file():
        return {}
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        primera = f.readline()
        f.seek(0)
        delimitador = ";" if ";" in primera else ","  # Excel en español guarda con ';'
        return {
            normalizar_cedula(fila["cedula"]): (
                limpiar(fila["nombre"]),
                limpiar(fila["apellido"]),
            )
            for fila in csv.DictReader(f, delimiter=delimitador)
            if fila.get("cedula")
        }


def leer_docentes(
    carpeta: Path, salida: Path
) -> tuple[list[Docente], list[str], list[str]]:
    """Devuelve (docentes, por_revisar, avisos) leyendo todos los PDF 'Listado de Docentes'."""
    correcciones = leer_correcciones(carpeta)
    docentes: dict[str, Docente] = {}
    por_revisar: list[str] = []
    avisos: list[str] = []
    encontrados = 0

    for ruta in sorted(carpeta.rglob("*.pdf"), key=lambda p: p.name.lower()):
        if salida in ruta.parents:
            continue
        texto = texto_pdf(ruta)
        if "LISTADO DE DOCENTES" not in texto.upper():
            continue  # es otro tipo de listado (estudiantes); se usará en otro paso
        encontrados += 1

        numeros: list[int] = []
        leidos = 0
        for linea in texto.splitlines():
            linea = linea.strip()
            if not re.match(r"^\d+\s+[VvEe]?-?\d{5,9}\s", linea):
                continue
            m = RE_FILA_DOCENTE.match(linea)
            if not m:
                avisos.append(f"[{ruta.name}] Fila sin interpretar: {linea}")
                continue

            cedula = normalizar_cedula(m.group(2))
            completo = limpiar(m.group(3))
            if cedula in correcciones:
                nombre, apellido = correcciones[cedula]
            else:
                nombre, apellido, dudoso = separar_apellidos_primero(completo)
                if dudoso:
                    por_revisar.append(
                        f"{completo}  ->  apellido='{apellido}' nombre='{nombre}'   (cédula {cedula})"
                    )

            if cedula in docentes:
                avisos.append(
                    f"[{ruta.name}] Cédula repetida {cedula} ({completo}); se usa la primera"
                )
            else:
                docentes[cedula] = Docente(cedula, nombre, apellido, ruta.name)
            numeros.append(int(m.group(1)))
            leidos += 1

        if numeros and max(numeros) != leidos:
            avisos.append(
                f"[{ruta.name}] La numeración llega a {max(numeros)} pero solo leí {leidos} filas"
            )
        print(f"  {ruta.name}: {leidos} docentes")

    if not encontrados:
        sys.exit(f"No encontré ningún PDF 'Listado de Docentes' en {carpeta}")
    return list(docentes.values()), por_revisar, avisos


def sql_docentes(docentes: list[Docente]) -> str:
    lineas = [
        "-- Docentes (generado por scripts/generar_sql.py)",
        f"-- Generado el {datetime.now(UTC).astimezone():%d-%m-%Y %H:%M} | {len(docentes)} docentes",
        "-- Re-ejecutable: no inserta a quien ya exista (misma cédula, no eliminado).",
        "-- Requiere que las tablas ya existan (se crean al iniciar la API con `fastapi dev`).",
        "",
        "SET client_encoding = 'UTF8';",
        "BEGIN;",
        "",
    ]
    for d in docentes:
        cedula = sql_texto(d.cedula)
        lineas.append(
            "INSERT INTO docentes (nombre, apellido, cedula, fecha_creacion, fecha_actualizacion)\n"
            f"SELECT {sql_texto(d.nombre)}, {sql_texto(d.apellido)}, {cedula}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP\n"
            f"WHERE NOT EXISTS (SELECT 1 FROM docentes WHERE cedula = {cedula} AND fecha_eliminacion IS NULL);\n"
        )
    lineas.append("COMMIT;")
    return "\n".join(lineas) + "\n"


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Genera .sql con INSERT a partir de las nóminas."
    )
    ap.add_argument(
        "paso", choices=["docentes"], help="Qué tabla generar (por ahora solo docentes)"
    )
    ap.add_argument(
        "--carpeta",
        default=os.environ.get("NOMINAS_CARPETA"),
        help="Carpeta con los PDF/.xls (fuera del repo). También vale la variable NOMINAS_CARPETA",
    )
    ap.add_argument(
        "--salida",
        help=f"Carpeta donde escribir los .sql (por defecto <carpeta>/{CARPETA_SALIDA})",
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

    print(f"Leyendo {carpeta}")
    docentes, por_revisar, avisos = leer_docentes(carpeta, salida)

    salida.mkdir(parents=True, exist_ok=True)
    destino = salida / "01_docentes.sql"
    destino.write_text(sql_docentes(docentes), encoding="utf-8")

    print(f"\nListo: {len(docentes)} docentes -> {destino}")
    if por_revisar:
        print(
            f"\n=== REVISAR ({len(por_revisar)}): no se puede saber dónde cortar nombre y apellido ==="
        )
        for linea in por_revisar:
            print("  ", linea)
        print(
            f"  Para corregirlos, agrégalos a {carpeta / ARCHIVO_CORRECCIONES} y vuelve a ejecutar."
        )
    if avisos:
        print(f"\n=== AVISOS ({len(avisos)}) ===")
        for a in avisos:
            print("  ", a)
    print(f'\nPara ejecutarlo:\n  psql -U postgres -d <nombre_bd> -f "{destino}"')


if __name__ == "__main__":
    main()

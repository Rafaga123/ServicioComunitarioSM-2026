"""Carga idempotente de asignaturas, asignaturas_docentes y horarios desde JSON.

Uso (desde la carpeta backend/ con el entorno virtual activo):

    python -m scripts.sembrar_horarios
    python -m scripts.sembrar_horarios --json scripts/horarios_liceo_2026.json --actualizar
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from sqlmodel import Session, select

import app.models.enums as en
from app.models.db import (
    Asignaturas,
    AsignaturasDocentes,
    BloquesHorarios,
    Docentes,
    Grados,
    Horarios,
    Secciones,
)
from app.models.session import engine, inicializar_base_datos
from app.utils.fechas import ahora_caracas

RUTA_JSON_DEFECTO = Path(__file__).with_name("horarios_liceo_2026.json")


def normalizar_cedula(cedula: str) -> str:
    """Extrae solo los dígitos de la cédula para comparar sin importar prefijos o guiones."""
    return re.sub(r"\D", "", cedula)


def sembrar_horarios_desde_json(
    session: Session,
    datos: dict,
    actualizar_existentes: bool = False,
) -> dict[str, int]:
    """Inserta asignaturas, vínculos docentes y horarios respetando FKs y soft delete."""
    grados_por_numero: dict[int, Grados] = {
        g.numero: g
        for g in session.exec(
            select(Grados).where(Grados.fecha_eliminacion.is_(None))
        ).all()
    }

    bloques_por_numero: dict[int, BloquesHorarios] = {
        b.numero: b
        for b in session.exec(
            select(BloquesHorarios).where(
                BloquesHorarios.tipo == en.TipoBloqueHorario.academico,
                BloquesHorarios.numero.is_not(None),
                BloquesHorarios.fecha_eliminacion.is_(None),
            )
        ).all()
        if b.numero is not None
    }

    docentes_por_cedula: dict[str, Docentes] = {
        normalizar_cedula(d.cedula): d
        for d in session.exec(
            select(Docentes).where(Docentes.fecha_eliminacion.is_(None))
        ).all()
    }

    secciones_por_clave: dict[tuple[int, str, int], Secciones] = {}
    for sec in session.exec(
        select(Secciones).where(Secciones.fecha_eliminacion.is_(None))
    ).all():
        grado_sec = next(
            (g for g in grados_por_numero.values() if g.id == sec.id_grado),
            None,
        )
        if grado_sec is not None:
            secciones_por_clave[
                (grado_sec.numero, sec.letra.strip().upper(), sec.periodo_lectivo)
            ] = sec

    if not grados_por_numero or not bloques_por_numero:
        raise RuntimeError(
            "Faltan grados o bloques horarios base. Ejecuta inicializar_base_datos() primero."
        )

    contadores = {
        "asignaturas_creadas": 0,
        "asignaturas_existentes": 0,
        "vinculos_creados": 0,
        "vinculos_existentes": 0,
        "horarios_creados": 0,
        "horarios_actualizados": 0,
        "horarios_existentes": 0,
    }

    # 1. Poblar ASIGNATURAS
    asignaturas_index: dict[tuple[int, str, int], Asignaturas] = {}
    for item in datos.get("asignaturas", []):
        grado_num = int(item["grado_numero"])
        periodo = int(item["periodo_lectivo"])
        nombre = item["nombre"].strip()

        grado = grados_por_numero.get(grado_num)
        if grado is None or grado.id is None:
            raise ValueError(f"Grado {grado_num} no encontrado en la base de datos.")
        if grado.nivel != en.NivelEducativo.liceo:
            raise ValueError(
                f"El grado {grado_num} ({grado.nombre}) no pertenece al nivel LICEO."
            )

        existente = session.exec(
            select(Asignaturas).where(
                Asignaturas.id_grado == grado.id,
                Asignaturas.nombre == nombre,
                Asignaturas.periodo_lectivo == periodo,
                Asignaturas.fecha_eliminacion.is_(None),
            )
        ).first()

        if existente is not None:
            asignaturas_index[(grado_num, nombre, periodo)] = existente
            contadores["asignaturas_existentes"] += 1
            continue

        nueva = Asignaturas(
            id_grado=grado.id,
            periodo_lectivo=periodo,
            nombre=nombre,
        )
        session.add(nueva)
        session.flush()
        asignaturas_index[(grado_num, nombre, periodo)] = nueva
        contadores["asignaturas_creadas"] += 1

    # 2. Poblar ASIGNATURAS_DOCENTES
    vinculos_validos: set[tuple[int, int]] = set()
    for item in datos.get("asignaturas_docentes", []):
        grado_num = int(item["grado_numero"])
        periodo = int(item["periodo_lectivo"])
        nombre_asig = item["asignatura"].strip()
        cedula_raw = item["docente_cedula"].strip().upper()
        cedula_num = normalizar_cedula(cedula_raw)

        asignatura = asignaturas_index.get((grado_num, nombre_asig, periodo))
        if asignatura is None or asignatura.id is None:
            raise ValueError(
                f"Asignatura '{nombre_asig}' (grado {grado_num}, período {periodo}) no encontrada."
            )

        docente = docentes_por_cedula.get(cedula_num)
        if docente is None or docente.id is None:
            raise ValueError(
                f"Docente con cédula '{cedula_raw}' ({item.get('docente_nombre', '')}) no encontrado en la base de datos."
            )
        if docente.nivel != en.NivelEducativo.liceo:
            raise ValueError(
                f"El docente '{cedula_raw}' no pertenece al nivel LICEO."
            )

        vinculos_validos.add((asignatura.id, docente.id))

        existente = session.exec(
            select(AsignaturasDocentes).where(
                AsignaturasDocentes.id_asignatura == asignatura.id,
                AsignaturasDocentes.id_docente == docente.id,
                AsignaturasDocentes.fecha_eliminacion.is_(None),
            )
        ).first()

        if existente is not None:
            contadores["vinculos_existentes"] += 1
            continue

        session.add(
            AsignaturasDocentes(
                id_asignatura=asignatura.id,
                id_docente=docente.id,
            )
        )
        session.flush()
        contadores["vinculos_creados"] += 1

    # 3. Poblar HORARIOS
    for item in datos.get("horarios", []):
        grado_num = int(item["grado_numero"])
        letra = item["seccion_letra"].strip().upper()
        periodo = int(item["periodo_lectivo"])
        dia_semana = int(item["dia_semana"])
        bloque_num = int(item["bloque_numero"])
        nombre_asig = item["asignatura"].strip()
        cedula_raw = item["docente_cedula"].strip().upper()
        cedula_num = normalizar_cedula(cedula_raw)

        seccion = secciones_por_clave.get((grado_num, letra, periodo))
        if seccion is None or seccion.id is None:
            raise ValueError(
                f"Sección '{grado_num} - {letra}' (período {periodo}) no encontrada."
            )

        bloque = bloques_por_numero.get(bloque_num)
        if bloque is None or bloque.id is None:
            raise ValueError(
                f"Bloque académico número {bloque_num} no encontrado."
            )

        asignatura = asignaturas_index.get((grado_num, nombre_asig, periodo))
        if asignatura is None or asignatura.id is None:
            raise ValueError(
                f"Asignatura '{nombre_asig}' (grado {grado_num}, período {periodo}) no encontrada."
            )

        docente = docentes_por_cedula.get(cedula_num)
        if docente is None or docente.id is None:
            raise ValueError(f"Docente '{cedula_raw}' no encontrado.")

        if (asignatura.id, docente.id) not in vinculos_validos:
            raise ValueError(
                f"El docente '{cedula_raw}' no está vinculado a '{nombre_asig}' en grado {grado_num}."
            )

        existente = session.exec(
            select(Horarios).where(
                Horarios.id_seccion == seccion.id,
                Horarios.id_bloque == bloque.id,
                Horarios.periodo_lectivo == periodo,
                Horarios.dia_semana == dia_semana,
                Horarios.fecha_eliminacion.is_(None),
            )
        ).first()

        if existente is not None:
            if actualizar_existentes and (
                existente.id_asignatura != asignatura.id
                or existente.id_docente != docente.id
            ):
                existente.id_asignatura = asignatura.id
                existente.id_docente = docente.id
                existente.fecha_actualizacion = ahora_caracas()
                session.add(existente)
                contadores["horarios_actualizados"] += 1
            else:
                contadores["horarios_existentes"] += 1
            continue

        session.add(
            Horarios(
                id_seccion=seccion.id,
                id_bloque=bloque.id,
                id_asignatura=asignatura.id,
                id_docente=docente.id,
                periodo_lectivo=periodo,
                dia_semana=dia_semana,
            )
        )
        contadores["horarios_creados"] += 1

    session.commit()
    return contadores


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Siembra asignaturas, asignaturas_docentes y horarios desde JSON."
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=RUTA_JSON_DEFECTO,
        help="Ruta al archivo horarios_liceo_2026.json",
    )
    parser.add_argument(
        "--actualizar",
        action="store_true",
        help="Actualiza asignatura/docente si el bloque de la sección ya existía.",
    )
    args = parser.parse_args()

    if not args.json.is_file():
        sys.exit(f"No se encontró el archivo JSON: {args.json}")

    inicializar_base_datos()

    datos = json.loads(args.json.read_text(encoding="utf-8"))

    with Session(engine) as session:
        resumen = sembrar_horarios_desde_json(
            session,
            datos,
            actualizar_existentes=args.actualizar,
        )

    print("Siembra de horarios completada:")
    for clave, valor in resumen.items():
        print(f"  - {clave}: {valor}")


if __name__ == "__main__":
    main()
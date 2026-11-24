"""Carga completa, jerárquica e idempotente de los datos de prueba de nóminas.

Uso (desde la carpeta backend/ con el entorno virtual activo):

    python -m scripts.cargar_datos_prueba
    python -m scripts.cargar_datos_prueba --clave "OtraClave2026!"
    python -m scripts.cargar_datos_prueba --recrear-tablas

Los datos sensibles viven solo en scripts/nominas/ (carpeta ignorada por Git).
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from sqlmodel import Session, SQLModel, select

import app.models.enums as en
from app.core.semilla import sembrar_datos
from app.models.db import Usuarios
from app.models.session import create_db_tables, engine
from app.utils.security import obtener_hash_clave
from scripts.sembrar_horarios import sembrar_horarios_desde_json

RUTA_NOMINAS = Path(__file__).with_name("nominas")
RUTA_SQL = RUTA_NOMINAS / "00_todo_seed.sql"
RUTA_JSON = RUTA_NOMINAS / "horarios_liceo_2026.json"
CLAVE_PRUEBA_DEFECTO = "Prueba123*"

USUARIOS_PRUEBA = (
  ("admin_prueba", en.RolesUsuario.administrador, None),
  ("secretaria_liceo", en.RolesUsuario.secretaria, en.NivelEducativo.liceo),
  ("secretaria_escuela", en.RolesUsuario.secretaria, en.NivelEducativo.escuela),
)


def ejecutar_seed(session: Session, ruta_sql: Path) -> int:
  """Ejecuta el SQL adaptado en una sola transacción y devuelve el total de INSERT."""
  contenido = ruta_sql.read_text(encoding="utf-8")
  lineas = [
    linea
    for linea in contenido.splitlines(keepends=True)
    if not re.match(r"^\s*(SET\s+client_encoding|BEGIN;|COMMIT;)", linea, re.IGNORECASE)
  ]
  sql = "".join(lineas)
  # Ejecutar sentencia por sentencia funciona igual en psycopg y en SQLite (smokes).
  sentencias = []
  for bloque in re.split(r";\s*\n", sql):
    bloque = bloque.strip()
    if not bloque:
      continue
    codigo = "\n".join(
      linea for linea in bloque.splitlines() if not linea.strip().startswith("--")
    ).strip()
    if codigo:
      sentencias.append(bloque)
  for sentencia in sentencias:
    session.connection().exec_driver_sql(sentencia + ";")
  session.commit()
  return sql.count("INSERT INTO")


def cargar_horarios(
  session: Session, ruta_json: Path, actualizar_existentes: bool = True
) -> dict[str, int]:
  datos = json.loads(ruta_json.read_text(encoding="utf-8"))
  return sembrar_horarios_desde_json(session, datos, actualizar_existentes)


def crear_usuarios_prueba(session: Session, clave: str) -> dict[str, int]:
  contadores = {"creados": 0, "existentes": 0}
  for nombre, rol, nivel in USUARIOS_PRUEBA:
    existente = session.exec(
      select(Usuarios).where(
        Usuarios.nombre == nombre,
        Usuarios.fecha_eliminacion.is_(None),
      )
    ).first()
    if existente is not None:
      contadores["existentes"] += 1
      continue

    session.add(
      Usuarios(
        nombre=nombre,
        clave=obtener_hash_clave(clave),
        rol=rol,
        nivel=nivel,
      )
    )
    contadores["creados"] += 1

  session.commit()
  return contadores


def cargar_datos_prueba(
  session: Session,
  ruta_sql: Path = RUTA_SQL,
  ruta_json: Path = RUTA_JSON,
  clave: str = CLAVE_PRUEBA_DEFECTO,
  actualizar_horarios: bool = True,
) -> dict:
  """Carga todo en orden de dependencias. Puede ejecutarse las veces que haga falta."""
  faltantes = [str(r) for r in (ruta_sql, ruta_json) if not r.is_file()]
  if faltantes:
    raise FileNotFoundError("Faltan datos locales de nóminas: " + ", ".join(faltantes))

  grados, bloques = sembrar_datos(session)
  inserciones = ejecutar_seed(session, ruta_sql)
  horarios = cargar_horarios(session, ruta_json, actualizar_horarios)
  usuarios = crear_usuarios_prueba(session, clave)

  return {
    "catalogo": {"grados_nuevos": grados, "bloques_nuevos": bloques},
    "sql_inserciones": inserciones,
    "horarios": horarios,
    "usuarios": usuarios,
  }


def main() -> None:
  parser = argparse.ArgumentParser(
    description="Carga los datos de prueba de nóminas en orden de dependencias."
  )
  parser.add_argument("--sql", type=Path, default=RUTA_SQL)
  parser.add_argument("--json", type=Path, default=RUTA_JSON)
  parser.add_argument(
    "--clave",
    default=os.getenv("CLAVE_PRUEBA", CLAVE_PRUEBA_DEFECTO),
    help="Clave de los usuarios de prueba (defecto: Prueba123*)",
  )
  parser.add_argument(
    "--no-actualizar-horarios",
    action="store_true",
    help="No sobreescribe asignatura/docente de horarios ya existentes.",
  )
  parser.add_argument(
    "--recrear-tablas",
    action="store_true",
    help="ADVERTENCIA: borra todas las tablas y sus datos antes de cargar.",
  )
  args = parser.parse_args()

  if args.recrear_tablas:
    print("ADVERTENCIA: --recrear-tablas borra todas las tablas y sus datos.")
    SQLModel.metadata.drop_all(engine)
  create_db_tables()
  with Session(engine) as session:
    resumen = cargar_datos_prueba(
      session,
      ruta_sql=args.sql,
      ruta_json=args.json,
      clave=args.clave,
      actualizar_horarios=not args.no_actualizar_horarios,
    )

  catalogo = resumen["catalogo"]
  horarios = resumen["horarios"]
  usuarios = resumen["usuarios"]
  print(
    f"Catálogo base: {catalogo['grados_nuevos']} grados y "
    f"{catalogo['bloques_nuevos']} bloques nuevos"
  )
  print(f"SQL: {resumen['sql_inserciones']} INSERT ejecutados (idempotente)")
  print(
    "Horarios: "
    f"{horarios['asignaturas_creadas']} asignaturas creadas, "
    f"{horarios['vinculos_creados']} vínculos creados, "
    f"{horarios['horarios_creados']} horarios creados, "
    f"{horarios['horarios_actualizados']} actualizados, "
    f"{horarios['horarios_existentes']} ya existentes"
  )
  print(
    f"Usuarios: {usuarios['creados']} creados, {usuarios['existentes']} ya existían"
  )
  print("Carga finalizada. Clave de prueba documentada en README (sección 8.3).")


if __name__ == "__main__":
  main()

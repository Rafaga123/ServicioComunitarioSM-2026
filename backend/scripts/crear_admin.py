import argparse
import getpass

from sqlmodel import Session, select

from app.models.db import Usuarios
from app.models.enums import RolesUsuario
from app.models.session import engine
from app.utils.security import obtener_hash_clave


def pedir_clave() -> str:
  clave = getpass.getpass("Clave del administrador: ")
  confirmacion = getpass.getpass("Repite la clave: ")

  if clave != confirmacion:
    raise SystemExit("Las claves no coinciden.")

  if len(clave) < 8:
    raise SystemExit("La clave debe tener al menos 8 caracteres.")

  return clave


def crear_admin(session: Session, nombre: str, clave: str) -> None:
  admin_activo = session.exec(
    select(Usuarios)
    .where(Usuarios.rol == RolesUsuario.administrador)
    .where(Usuarios.fecha_eliminacion.is_(None))
  ).first()

  if admin_activo:
    raise SystemExit(
      f"Ya existe un administrador activo ({admin_activo.nombre}). "
      "La transferencia se realiza desde la aplicación."
    )

  existente = session.exec(
    select(Usuarios).where(Usuarios.nombre == nombre)
  ).first()

  if existente:
    raise SystemExit(f"El usuario '{nombre}' ya existe.")

  nuevo_admin = Usuarios(
    nombre=nombre,
    clave=obtener_hash_clave(clave),
    rol=RolesUsuario.administrador,
  )

  session.add(nuevo_admin)
  session.commit()

  print(f"Administrador '{nombre}' creado correctamente.")


def main() -> None:
  parser = argparse.ArgumentParser(
    description="Crea el administrador inicial del sistema."
  )
  parser.add_argument("--usuario", help="Nombre del administrador inicial.")

  args = parser.parse_args()

  nombre = args.usuario or input("Usuario administrador: ").strip()

  if not nombre:
    raise SystemExit("El nombre del usuario es obligatorio.")

  with Session(engine) as session:
    crear_admin(session, nombre, pedir_clave())


if __name__ == "__main__":
  main()

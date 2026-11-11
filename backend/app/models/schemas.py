from datetime import datetime

from sqlmodel import SQLModel

import app.models.enums as en


# ====
# Esquemas para Usuarios
# ====
class CrearUsuario(SQLModel):
  nombre: str
  clave: str
  rol: en.RolesUsuario


class PeticionUsuario(SQLModel):
  id: int | None
  nombre: str
  rol: en.RolesUsuario


# ====
# Esquemas para Estudiantes
# ====
class CrearEstudiante(SQLModel):
  grado_id: int | None

  cedula_estudiantil: str

  primer_nombre: str
  segundo_nombre: str = ""
  primer_apellido: str
  segundo_apellido: str = ""

  fecha_nacimiento: datetime


class PeticionEstudiante(SQLModel):
  id: int | None
  grado_id: int | None

  cedula_estudiantil: str

  primer_nombre: str
  segundo_nombre: str
  primer_apellido: str
  segundo_apellido: str

  fecha_nacimiento: datetime


class ActualizarEstudiante(SQLModel):
  grado_id: int | None = None

  cedula_estudiantil: str | None = None

  primer_nombre: str | None = None
  segundo_nombre: str | None = None
  primer_apellido: str | None = None
  segundo_apellido: str | None = None

  fecha_nacimiento: datetime | None = None

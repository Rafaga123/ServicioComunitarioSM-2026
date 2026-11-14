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

# ====
# Esquema para pases
# ====

class CrearPase(SQLModel):
  id_estudiante: int 
  id_docente: int | None = None
  id_asignatura: int | None = None
  tipo: en.TipoPase = en.TipoPase.entrada
  motivo: str
  fecha: datetime
  autorizador: str


class PeticionPase(SQLModel):
  id: int | None
  id_estudiante: int | None
  id_docente: int | None
  id_asignatura: int | None
  tipo: en.TipoPase
  motivo: str
  fecha: datetime
  autorizador: str


class ActualizacionPase(SQLModel):
  id_docente: int | None = None
  id_asignatura: int | None = None
  tipo: en.TipoPase | None = None
  motivo: str | None = None
  fecha: datetime | None = None
  autorizador: str | None = None

# ====
# Esquema para Auditoria
# ====

class PeticionAuditoria(SQLModel):
  id: int | None 
  usuario_id: int | None
  modulo_afectado: str
  accion: str
  descripcion: str
  fecha_creacion: datetime
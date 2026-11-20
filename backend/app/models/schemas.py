from datetime import datetime, time

from sqlmodel import Field, SQLModel

import app.models.enums as en


# ====
# Esquemas para Usuarios
# ====
class CrearUsuario(SQLModel):
  nombre: str
  clave: str = Field(min_length=8, max_length=72)
  rol: en.RolesAsignables


class PeticionUsuario(SQLModel):
  id: int | None
  nombre: str
  rol: en.RolesUsuario


class ActualizarUsuario(SQLModel):
  nombre: str | None = Field(default=None, min_length=1)
  rol: en.RolesAsignables | None = None


class CambiarClave(SQLModel):
  clave_actual: str
  clave_nueva: str = Field(min_length=8, max_length=72)


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
# Esquemas para Representantes
# ====
class CrearRepresentante(SQLModel):
  primer_nombre: str
  segundo_nombre: str = ""
  primer_apellido: str
  segundo_apellido: str = ""

  telefono: str


class ActualizarRepresentante(SQLModel):
  primer_nombre: str
  segundo_nombre: str = ""
  primer_apellido: str
  segundo_apellido: str = ""

  telefono: str | None = None


class PeticionRepresentante(SQLModel):
  id: int

  primer_nombre: str
  segundo_nombre: str = ""
  primer_apellido: str
  segundo_apellido: str = ""

  telefono: str


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
  usuario: str | None = None
  modulo: str
  accion: str
  descripcion: str
  fecha_creacion: datetime


# ====
# Esquemas para Grados
# ====
class CrearGrado(SQLModel):
  grado: str
  seccion: str


class PeticionGrado(SQLModel):
  id: int
  grado: str
  seccion: str


# ====
# Esquemas para Docentes y Asignaturas
# ====
class CrearDocente(SQLModel):
  primer_nombre: str
  segundo_nombre: str = ""
  primer_apellido: str
  segundo_apellido: str = ""

  cedula: str


class ActualizarDocente(SQLModel):
  primer_nombre: str
  segundo_nombre: str = ""
  primer_apellido: str
  segundo_apellido: str = ""

  cedula: str | None = None


class PeticionDocente(SQLModel):
  id: int
  primer_nombre: str
  segundo_nombre: str = ""
  primer_apellido: str
  segundo_apellido: str = ""
  cedula: str


class CrearAsignatura(SQLModel):
  nombre: str


class ActualizarAsignatura(SQLModel):
  nombre: str | None = None


class PeticionAsignatura(SQLModel):
  id: int
  nombre: str


# ====
# Esquemas para Horarios
# ====
class CrearHorario(SQLModel):
  id_grado: int
  id_asignatura: int
  id_docente: int
  periodo_lectivo: int = Field(ge=2000)
  dia_semana: int = Field(ge=1, le=5)
  hora: time


class ActualizarHorario(SQLModel):
  id_grado: int | None = None
  id_asignatura: int | None = None
  id_docente: int | None = None
  periodo_lectivo: int | None = Field(default=None, ge=2000)
  dia_semana: int | None = Field(default=None, ge=1, le=5)
  hora: time | None = None


class PeticionHorario(SQLModel):
  id: int
  id_grado: int
  id_asignatura: int
  id_docente: int
  periodo_lectivo: int
  dia_semana: int
  hora: time
  grado: str
  seccion: str
  asignatura: str
  docente: str


class PeticionBloque(SQLModel):
  # La consulta devuelve una respuesta parcial para que el frontend pueda
  # mostrar y completar el bloque aunque todavía no exista un horario.
  encontrado: bool
  id_horario: int | None = None
  id_asignatura: int | None = None
  id_docente: int | None = None
  asignatura: str | None = None
  docente: str | None = None

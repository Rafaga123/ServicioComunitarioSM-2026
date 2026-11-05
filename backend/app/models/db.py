from datetime import UTC, datetime

from sqlmodel import Field, Relationship, SQLModel

import app.models.enums as en


# Clase Padre con los atributos base de cada tabla
class EsquemaBase(SQLModel):
  create_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
  update_at: datetime = Field(
    default_factory=lambda: datetime.now(UTC),
    sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
  )
  delete_at: datetime | None = Field(default=None)


# ====
# TABLAS DE LA BASE DE DATOS
# ====


# Tabla de Usuarios
class Usuarios(EsquemaBase, table=True):
  __tablename__ = "usuarios"
  id: int | None = Field(default=None, primary_key=True)
  name: str = Field(index=True)
  password: str
  rol: en.RolesUsuario = Field(
    default=en.RolesUsuario.secretaria
  )  # ENUM: ADMINISTRADOR, COORDINADOR, SECRETARIA


# Tabla Intermedia entre Estudiantes y Representantes
class EstudiantesRepresentantes(EsquemaBase, table=True):
  __tablename__ = "estudiantes_representantes"

  id_estudiante: int | None = Field(
    default=None, foreign_key="estudiantes.id", primary_key=True
  )

  id_representante: int | None = Field(
    default=None, foreign_key="representantes.id", primary_key=True
  )


# Tabla de Estudiantes
class Estudiantes(EsquemaBase, table=True):
  __tablename__ = "estudiantes"
  id: int | None = Field(default=None, primary_key=True)
  grado_id: int | None = Field(default=None, foreign_key="grados.id")

  cedula_estudiantil: str

  first_name: str = Field(index=True)
  second_name: str = Field(index=True)
  first_lastname: str = Field(index=True)
  second_lastname: str = Field(index=True)

  date_of_birth: datetime

  representantes: list["Representantes"] = Relationship(
    link_model=EstudiantesRepresentantes
  )


# Tabla de Representantes
class Representantes(EsquemaBase, table=True):
  __tablename__ = "representantes"
  id: int | None = Field(default=None, primary_key=True)

  name: str = Field(index=True)
  lastname: str = Field(index=True)
  # cedula: str
  phone_number: str

  estudiantes: list["Estudiantes"] = Relationship(link_model=EstudiantesRepresentantes)


# Tabla de Reportes
class Reportes(EsquemaBase, table=True):
  __tablename__ = "reportes"
  id: int | None = Field(default=None, primary_key=True)
  id_estudiante: int | None = Field(default=None, foreign_key="estudiantes.id")
  id_docente: int | None = Field(default=None, foreign_key="docentes.id")

  incidental: str
  articule: int
  reglamento: en.Reglamentos  # ENUM

  defensa: str  # Defensa escrita del estudiante
  nivel_gravedad: en.NivelGravedad = Field(
    default=en.NivelGravedad.leve
  )  # ENUM: LEVE | GRAVE
  categoria: en.CategoriaReportes  # ENUM: TIPO DE REPORTE

  fecha: datetime


# Tabla de Pases
class Pases(EsquemaBase, table=True):
  __tablename__ = "pases"
  id: int | None = Field(default=None, primary_key=True)

  id_estudiante: int | None = Field(default=None, foreign_key="estudiantes.id")
  id_docente: int | None = Field(default=None, foreign_key="docentes.id")
  tipo: en.TipoPase = Field(default=en.TipoPase.entrada)  # ENUM: TIPO DE PASE DADO

  motivo: str

  fecha: datetime

  autorizador: str


# Tabla de Grados
class Grados(EsquemaBase, table=True):
  __tablename__ = "grados"
  id: int | None = Field(default=None, primary_key=True)

  seccion: str
  grado: str


# Tabla intermedia de Asignaturas y Docentes
class AsignaturasDocentes(EsquemaBase, table=True):
  __tablename__ = "asignaturas_docentes"

  id_asignatura: int | None = Field(
    default=None, foreign_key="asignaturas.id", primary_key=True
  )

  id_docente: int | None = Field(
    default=None, foreign_key="docentes.id", primary_key=True
  )


# Tabla de Asignaturas
class Asignaturas(EsquemaBase, table=True):
  __tablename__ = "asignaturas"

  id: int | None = Field(default=None, primary_key=True)

  name: str
  docentes: list["Docentes"] = Relationship(link_model=AsignaturasDocentes)


# Tabla de Docentes
class Docentes(EsquemaBase, table=True):
  __tablename__ = "docentes"

  id: int | None = Field(default=None, primary_key=True)

  name: str
  lastname: str
  cedula: str

  asignaturas: list["Asignaturas"] = Relationship(link_model=AsignaturasDocentes)


# Tabla de Auditorias
class Auditorias(EsquemaBase, table=True):
  __tablename__ = "auditorias"
  id: int | None = Field(default=None, primary_key=True)
  usuario_id: int | None = Field(default=None)
  modulo_afectado: str
  accion: str
  descripcion: str

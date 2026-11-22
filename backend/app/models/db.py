from datetime import UTC, datetime, time

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel

import app.models.enums as en


# Clase Padre con los atributos base de cada tabla
class EsquemaBase(SQLModel):
  fecha_creacion: datetime = Field(default_factory=lambda: datetime.now(UTC))
  fecha_actualizacion: datetime = Field(
    default_factory=lambda: datetime.now(UTC),
    sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
  )
  fecha_eliminacion: datetime | None = Field(default=None)


# ====
# TABLAS DE LA BASE DE DATOS
# ====


# Tabla de Usuarios
class Usuarios(EsquemaBase, table=True):
  __tablename__ = "usuarios"
  id: int | None = Field(default=None, primary_key=True)
  nombre: str = Field(index=True)
  clave: str
  rol: en.RolesUsuario = Field(
    default=en.RolesUsuario.secretaria
  )  # ENUM: ADMINISTRADOR, COORDINADOR, SECRETARIA
  # El administrador opera sin nivel (None); coordinador y secretaria
  # siempre deben pertenecer a ESCUELA o LICEO.
  nivel: en.NivelEducativo | None = Field(default=None)


# Tabla de Representantes
class Representantes(EsquemaBase, table=True):
  __tablename__ = "representantes"
  id: int | None = Field(default=None, primary_key=True)

  primer_nombre: str = Field(index=True)
  segundo_nombre: str | None = Field(default=None, index=True)
  primer_apellido: str = Field(index=True)
  segundo_apellido: str | None = Field(default=None, index=True)

  telefono: str

  estudiantes: list["Estudiantes"] = Relationship(
    back_populates="representante"
  )


# Tabla de Grados (catálogo fijo del 1 al 11)
class Grados(EsquemaBase, table=True):
  __tablename__ = "grados"
  __table_args__ = (
    CheckConstraint(
      "(numero BETWEEN 1 AND 6 AND nivel = 'escuela') OR "
      "(numero BETWEEN 7 AND 11 AND nivel = 'liceo')",
      name="ck_grados_numero_nivel",
    ),
  )

  id: int | None = Field(default=None, primary_key=True)

  numero: int
  nombre: str
  nivel: en.NivelEducativo

  secciones: list["Secciones"] = Relationship(back_populates="grado")
  asignaturas: list["Asignaturas"] = Relationship(back_populates="grado")


# Tabla intermedia de Asignaturas y Docentes
class AsignaturasDocentes(EsquemaBase, table=True):
  __tablename__ = "asignaturas_docentes"

  id: int | None = Field(default=None, primary_key=True)
  id_asignatura: int = Field(foreign_key="asignaturas.id")
  id_docente: int = Field(foreign_key="docentes.id")


# Tabla de Asignaturas
class Asignaturas(EsquemaBase, table=True):
  __tablename__ = "asignaturas"

  id: int | None = Field(default=None, primary_key=True)
  id_grado: int = Field(foreign_key="grados.id")

  nombre: str
  grado: Grados = Relationship(back_populates="asignaturas")
  horarios: list["Horarios"] = Relationship(back_populates="asignatura")


# Tabla de Docentes
class Docentes(EsquemaBase, table=True):
  __tablename__ = "docentes"

  id: int | None = Field(default=None, primary_key=True)

  primer_nombre: str = Field(index=True)
  segundo_nombre: str | None = Field(default=None, index=True)
  primer_apellido: str = Field(index=True)
  segundo_apellido: str | None = Field(default=None, index=True)

  cedula: str
  nivel: en.NivelEducativo

  horarios: list["Horarios"] = Relationship(back_populates="docente")
  secciones_titulares: list["Secciones"] = Relationship(
    back_populates="docente_titular"
  )


# Tabla de Secciones (aulas activas de un grado)
class Secciones(EsquemaBase, table=True):
  __tablename__ = "secciones"
  id: int | None = Field(default=None, primary_key=True)

  id_grado: int = Field(foreign_key="grados.id")
  letra: str
  id_docente_titular: int | None = Field(
    default=None, foreign_key="docentes.id"
  )

  grado: Grados = Relationship(back_populates="secciones")
  docente_titular: Docentes | None = Relationship(
    back_populates="secciones_titulares"
  )
  estudiantes: list["Estudiantes"] = Relationship(back_populates="seccion")
  horarios: list["Horarios"] = Relationship(back_populates="seccion")


# Tabla de Estudiantes
class Estudiantes(EsquemaBase, table=True):
  __tablename__ = "estudiantes"
  id: int | None = Field(default=None, primary_key=True)
  # Una sola FK de ubicación: fija grado y sección a la vez.
  id_seccion: int = Field(foreign_key="secciones.id")
  # Un representante puede tener varios estudiantes, pero cada
  # estudiante tiene como máximo uno.
  id_representante: int | None = Field(
    default=None, foreign_key="representantes.id"
  )

  cedula_estudiantil: str

  primer_nombre: str = Field(index=True)
  segundo_nombre: str | None = Field(default=None, index=True)
  primer_apellido: str = Field(index=True)
  segundo_apellido: str | None = Field(default=None, index=True)

  fecha_nacimiento: datetime

  seccion: Secciones = Relationship(back_populates="estudiantes")
  representante: Representantes | None = Relationship(
    back_populates="estudiantes"
  )


# Tabla de Reportes
class Reportes(EsquemaBase, table=True):
  __tablename__ = "reportes"
  id: int | None = Field(default=None, primary_key=True)
  id_estudiante: int | None = Field(default=None, foreign_key="estudiantes.id")
  id_docente: int | None = Field(default=None, foreign_key="docentes.id")

  incidencia: str
  articulo: int
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
  id_asignatura: int | None = Field(default=None, foreign_key="asignaturas.id")
  tipo: en.TipoPase = Field(default=en.TipoPase.entrada)  # ENUM: TIPO DE PASE DADO

  motivo: str

  fecha: datetime

  autorizador: str


# Tabla de Bloques Horarios (jornada institucional del liceo)
class BloquesHorarios(EsquemaBase, table=True):
  __tablename__ = "bloques_horarios"
  __table_args__ = (
    CheckConstraint("hora_fin > hora_inicio", name="ck_bloques_horarios_rango"),
    CheckConstraint(
      "(tipo = 'academico' AND numero BETWEEN 1 AND 8) OR "
      "(tipo = 'receso' AND numero IS NULL)",
      name="ck_bloques_horarios_tipo_numero",
    ),
  )

  id: int | None = Field(default=None, primary_key=True)
  orden: int
  numero: int | None = Field(default=None)
  nombre: str
  tipo: en.TipoBloqueHorario
  hora_inicio: time
  hora_fin: time

  horarios: list["Horarios"] = Relationship(back_populates="bloque")


# Tabla de Horarios
class Horarios(EsquemaBase, table=True):
  __tablename__ = "horarios"
  __table_args__ = (
    CheckConstraint("dia_semana BETWEEN 1 AND 5", name="ck_horarios_dia_semana"),
    CheckConstraint("periodo_lectivo >= 2000", name="ck_horarios_periodo"),
  )

  id: int | None = Field(default=None, primary_key=True)
  id_seccion: int = Field(foreign_key="secciones.id")
  id_bloque: int = Field(foreign_key="bloques_horarios.id")
  id_asignatura: int = Field(foreign_key="asignaturas.id")
  id_docente: int = Field(foreign_key="docentes.id")
  # Año lectivo al que pertenece el bloque; evita mezclar horarios
  # de distintos períodos en una misma consulta.
  periodo_lectivo: int = Field(index=True)
  dia_semana: int

  seccion: Secciones = Relationship(back_populates="horarios")
  bloque: BloquesHorarios = Relationship(back_populates="horarios")
  asignatura: Asignaturas = Relationship(back_populates="horarios")
  docente: Docentes = Relationship(back_populates="horarios")


# Tabla de Auditorias
class Auditorias(EsquemaBase, table=True):
  __tablename__ = "auditorias"
  id: int | None = Field(default=None, primary_key=True)
  usuario_id: int = Field(foreign_key="usuarios.id")
  modulo: str
  accion: str
  descripcion: str

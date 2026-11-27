"""Define las 17 tablas SQLModel y sus relaciones de negocio."""

from datetime import time

from pydantic import NaiveDatetime
from sqlalchemy import CheckConstraint, Index, text
from sqlmodel import Field, Relationship, SQLModel

import app.models.enums as en
from app.utils.fechas import ahora_caracas


class EsquemaBase(SQLModel):
  """Base común con fechas de creación, actualización y borrado lógico para las tablas."""
  fecha_creacion: NaiveDatetime = Field(default_factory=ahora_caracas)
  fecha_actualizacion: NaiveDatetime = Field(
    default_factory=ahora_caracas,
    sa_column_kwargs={"onupdate": ahora_caracas},
  )
  fecha_eliminacion: NaiveDatetime | None = Field(default=None)


class Usuarios(EsquemaBase, table=True):
  """Cuenta de acceso con rol, nivel educativo y versión de tokens."""
  __tablename__ = "usuarios"
  __table_args__ = (
    Index(
      "uq_usuarios_nombre_activo",
      "nombre",
      unique=True,
      postgresql_where=text("fecha_eliminacion IS NULL"),
    ),
  )
  id: int | None = Field(default=None, primary_key=True)
  nombre: str = Field(index=True)
  clave: str
  rol: en.RolesUsuario = Field(default=en.RolesUsuario.secretaria)
  # El administrador opera sin nivel (None); coordinador y secretaria
  # siempre deben pertenecer a ESCUELA o LICEO.
  nivel: en.NivelEducativo | None = Field(default=None)

  # Contador de versión del JWT. Cada cambio de clave, baja o transferencia
  # de administrador lo incrementa y revoca todos los tokens emitidos
  # con un claim `ver` anterior.
  version_tokens: int = Field(default=0, nullable=False)

  pases: list["Pases"] = Relationship(back_populates="usuario")
  reportes: list["Reportes"] = Relationship(back_populates="usuario")
  auditorias: list["Auditorias"] = Relationship(back_populates="usuario")


class Representantes(EsquemaBase, table=True):
  """Representante legal de uno o más estudiantes."""
  __tablename__ = "representantes"
  id: int | None = Field(default=None, primary_key=True)

  primer_nombre: str = Field(index=True)
  segundo_nombre: str | None = Field(default=None, index=True)
  primer_apellido: str = Field(index=True)
  segundo_apellido: str | None = Field(default=None, index=True)

  telefono: str

  estudiantes: list["Estudiantes"] = Relationship(back_populates="representante")


class Grados(EsquemaBase, table=True):
  """Grado del catálogo institucional, de primero a undécimo."""
  __tablename__ = "grados"
  __table_args__ = (
    CheckConstraint(
      "(numero BETWEEN 1 AND 6 AND nivel = 'escuela') OR "
      "(numero BETWEEN 7 AND 11 AND nivel = 'liceo')",
      name="ck_grados_numero_nivel",
    ),
    Index(
      "uq_grados_numero_activo",
      "numero",
      unique=True,
      postgresql_where=text("fecha_eliminacion IS NULL"),
    ),
  )

  id: int | None = Field(default=None, primary_key=True)

  numero: int
  nombre: str
  nivel: en.NivelEducativo

  secciones: list["Secciones"] = Relationship(back_populates="grado")
  asignaturas: list["Asignaturas"] = Relationship(back_populates="grado")


class AsignaturasDocentes(EsquemaBase, table=True):
  """Relación entre asignaturas y docentes en un periodo lectivo."""
  __tablename__ = "asignaturas_docentes"
  __table_args__ = (
    Index(
      "uq_asignaturas_docentes_activo",
      "id_asignatura",
      "id_docente",
      unique=True,
      postgresql_where=text("fecha_eliminacion IS NULL"),
    ),
  )

  id: int | None = Field(default=None, primary_key=True)
  id_asignatura: int = Field(foreign_key="asignaturas.id")
  id_docente: int = Field(foreign_key="docentes.id")


class Asignaturas(EsquemaBase, table=True):
  """Asignatura impartida a un grado en un periodo lectivo."""
  __tablename__ = "asignaturas"
  __table_args__ = (
    Index(
      "uq_asignaturas_grado_nombre_periodo_activo",
      "id_grado",
      "nombre",
      "periodo_lectivo",
      unique=True,
      postgresql_where=text("fecha_eliminacion IS NULL"),
    ),
  )

  id: int | None = Field(default=None, primary_key=True)
  id_grado: int = Field(foreign_key="grados.id")

  # Año lectivo al que pertenece la asignatura. Evita mezclar asignaturas
  # de distintos períodos lectivos dentro del mismo grado.
  periodo_lectivo: int = Field(index=True)

  nombre: str
  grado: Grados = Relationship(back_populates="asignaturas")
  horarios: list["Horarios"] = Relationship(back_populates="asignatura")


class Docentes(EsquemaBase, table=True):
  """Docente del catálogo institucional, asociado a un nivel educativo."""
  __tablename__ = "docentes"
  __table_args__ = (
    Index(
      "uq_docentes_cedula_activo",
      "cedula",
      unique=True,
      postgresql_where=text("fecha_eliminacion IS NULL"),
    ),
  )

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


class Secciones(EsquemaBase, table=True):
  """Sección activa de un grado en un periodo lectivo."""
  __tablename__ = "secciones"
  __table_args__ = (
    CheckConstraint("periodo_lectivo >= 2000", name="ck_secciones_periodo"),
    Index(
      "uq_secciones_grado_letra_periodo_activo",
      "id_grado",
      "letra",
      "periodo_lectivo",
      unique=True,
      postgresql_where=text("fecha_eliminacion IS NULL"),
    ),
  )
  id: int | None = Field(default=None, primary_key=True)

  id_grado: int = Field(foreign_key="grados.id")
  letra: str
  # Año escolar al que pertenece la sección. Permite que "1er Año A"
  # de dos períodos distintos coexista sin mezclar cohortes.
  periodo_lectivo: int = Field(index=True)
  id_docente_titular: int | None = Field(default=None, foreign_key="docentes.id")

  grado: Grados = Relationship(back_populates="secciones")
  docente_titular: Docentes | None = Relationship(back_populates="secciones_titulares")
  estudiantes: list["Estudiantes"] = Relationship(back_populates="seccion")
  horarios: list["Horarios"] = Relationship(back_populates="seccion")


class PeriodosLectivos(EsquemaBase, table=True):
  """Periodo lectivo con el año de inicio y su estado activo."""
  __tablename__ = "periodos_lectivos"
  id: int | None = Field(default=None, primary_key=True)
  anio: int = Field(index=True)
  # Solo un periodo puede estar activo; `cerrado` es terminal y lo escribe el cierre.
  activo: bool = Field(default=False, index=True)
  cerrado: bool = Field(default=False, index=True)
  fecha_cierre: NaiveDatetime | None = Field(default=None)


class Estudiantes(EsquemaBase, table=True):
  """Estudiante inscrito en una sección y representado por una cuenta."""
  __tablename__ = "estudiantes"
  __table_args__ = (
    Index(
      "uq_estudiantes_cedula_activo",
      "cedula_estudiantil",
      unique=True,
      postgresql_where=text("fecha_eliminacion IS NULL"),
    ),
  )
  id: int | None = Field(default=None, primary_key=True)
  # Una sola FK de ubicación: fija grado y sección a la vez.
  id_seccion: int = Field(foreign_key="secciones.id")
  # Un representante puede tener varios estudiantes, pero cada
  # estudiante tiene como máximo uno.
  id_representante: int | None = Field(default=None, foreign_key="representantes.id")

  cedula_estudiantil: str

  primer_nombre: str = Field(index=True)
  segundo_nombre: str | None = Field(default=None, index=True)
  primer_apellido: str = Field(index=True)
  segundo_apellido: str | None = Field(default=None, index=True)

  fecha_nacimiento: NaiveDatetime

  # Marca de egreso de los estudiantes de 5to Año al cerrar el año.
  fecha_egreso: NaiveDatetime | None = Field(default=None)

  seccion: Secciones = Relationship(back_populates="estudiantes")
  representante: Representantes | None = Relationship(back_populates="estudiantes")
  pases: list["Pases"] = Relationship(back_populates="estudiante")
  reportes: list["Reportes"] = Relationship(back_populates="estudiante")


class Reportes(EsquemaBase, table=True):
  """Reporte disciplinario de un estudiante con adjunto opcional."""
  __tablename__ = "reportes"
  id: int | None = Field(default=None, primary_key=True)
  id_estudiante: int = Field(foreign_key="estudiantes.id")
  id_usuario: int = Field(foreign_key="usuarios.id")
  id_docente: int | None = Field(default=None, foreign_key="docentes.id")

  incidencia: str
  articulo: int
  reglamento: en.Reglamentos

  defensa: str  # Defensa escrita del estudiante
  nivel_gravedad: en.NivelGravedad = Field(default=en.NivelGravedad.leve)
  categoria: en.CategoriaReportes

  fecha: NaiveDatetime

  # Año lectivo al que pertenece el reporte; se deriva de la sección.
  periodo_lectivo: int | None = Field(default=None, index=True)

  # Adjunto opcional del reporte. `archivo_url` es una ruta relativa dentro
  # de STORAGE_ROOT; el archivo físico se descarga con GET /reportes/{id}/archivo.
  archivo_url: str | None = Field(default=None)
  archivo_nombre: str | None = Field(default=None)
  archivo_mime: str | None = Field(default=None)
  archivo_tamano: int | None = Field(default=None)
  archivo_hash: str | None = Field(default=None)
  archivo_subido_por: int | None = Field(default=None)
  archivo_fecha: NaiveDatetime | None = Field(default=None)

  estudiante: Estudiantes = Relationship(back_populates="reportes")
  usuario: Usuarios = Relationship(back_populates="reportes")
  docente: Docentes | None = Relationship()


class Pases(EsquemaBase, table=True):
  """Pase disciplinario de un estudiante con adjunto y autorizador opcional."""
  __tablename__ = "pases"
  id: int | None = Field(default=None, primary_key=True)

  id_estudiante: int = Field(foreign_key="estudiantes.id")
  id_usuario: int = Field(foreign_key="usuarios.id")
  id_docente: int | None = Field(default=None, foreign_key="docentes.id")
  id_asignatura: int | None = Field(default=None, foreign_key="asignaturas.id")
  tipo: en.TipoPase = Field(default=en.TipoPase.entrada)

  motivo: str

  fecha: NaiveDatetime

  # Año lectivo al que pertenece el pase; se deriva de la sección.
  periodo_lectivo: int | None = Field(default=None, index=True)

  # Obligatorio solo desde el cuarto pase activo del mes por tipo.
  autorizador: str | None = Field(default=None)

  # Adjunto opcional del pase. `archivo_url` es una ruta relativa dentro
  # de STORAGE_ROOT; el archivo físico se descarga con GET /pases/{id}/archivo.
  archivo_url: str | None = Field(default=None)
  archivo_nombre: str | None = Field(default=None)
  archivo_mime: str | None = Field(default=None)
  archivo_tamano: int | None = Field(default=None)
  archivo_hash: str | None = Field(default=None)
  archivo_subido_por: int | None = Field(default=None)
  archivo_fecha: NaiveDatetime | None = Field(default=None)

  estudiante: Estudiantes = Relationship(back_populates="pases")
  usuario: Usuarios = Relationship(back_populates="pases")
  docente: Docentes | None = Relationship()
  asignatura: Asignaturas | None = Relationship()


class BloquesHorarios(EsquemaBase, table=True):
  """Tramo de la jornada institucional del liceo."""
  __tablename__ = "bloques_horarios"
  __table_args__ = (
    CheckConstraint("hora_fin > hora_inicio", name="ck_bloques_horarios_rango"),
    CheckConstraint(
      "(tipo = 'academico' AND numero BETWEEN 1 AND 8) OR "
      "(tipo = 'receso' AND numero IS NULL)",
      name="ck_bloques_horarios_tipo_numero",
    ),
    Index(
      "uq_bloques_horarios_orden_activo",
      "orden",
      unique=True,
      postgresql_where=text("fecha_eliminacion IS NULL"),
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


class Horarios(EsquemaBase, table=True):
  """Asignación de asignatura y docente a un bloque de una sección."""
  __tablename__ = "horarios"
  __table_args__ = (
    CheckConstraint("dia_semana BETWEEN 1 AND 5", name="ck_horarios_dia_semana"),
    CheckConstraint("periodo_lectivo >= 2000", name="ck_horarios_periodo"),
    Index(
      "uq_horarios_seccion_bloque_periodo_dia_activo",
      "id_seccion",
      "id_bloque",
      "periodo_lectivo",
      "dia_semana",
      unique=True,
      postgresql_where=text("fecha_eliminacion IS NULL"),
    ),
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


class Auditorias(EsquemaBase, table=True):
  """Registro de auditoría de una acción realizada por un usuario."""
  __tablename__ = "auditorias"
  id: int | None = Field(default=None, primary_key=True)
  usuario_id: int = Field(foreign_key="usuarios.id")
  modulo: str
  accion: str
  descripcion: str

  usuario: Usuarios = Relationship(back_populates="auditorias")


class DocumentosGenerados(EsquemaBase, table=True):
  """PDF generado y almacenado bajo una ruta relativa."""
  __tablename__ = "documentos_generados"
  id: int | None = Field(default=None, primary_key=True)
  tipo: en.TipoDocumento
  periodo_lectivo: int | None = Field(default=None, index=True)
  nivel: en.NivelEducativo | None = Field(default=None)
  id_grado: int | None = Field(default=None, foreign_key="grados.id")
  id_seccion: int | None = Field(default=None, foreign_key="secciones.id")
  nombre_archivo: str
  ruta_relativa: str
  hash: str
  tamano: int
  mime: str
  fecha_generacion: NaiveDatetime
  generado_por: int | None = Field(default=None, foreign_key="usuarios.id")

  grado: Grados | None = Relationship()
  seccion: Secciones | None = Relationship()
  usuario: Usuarios | None = Relationship()

class TokensRevocados(EsquemaBase, table=True):
  """JWT revocado por logout o cierre forzado, retenido hasta vencer y depurarse."""
  __tablename__ = "tokens_revocados"
  __table_args__ = (
    Index("uq_tokens_revocados_jti", "jti", unique=True),
    Index("ix_tokens_revocados_expira_en", "expira_en"),
  )

  id: int | None = Field(default=None, primary_key=True)
  jti: str = Field(max_length=36)
  usuario_id: int | None = Field(default=None, foreign_key="usuarios.id")
  expira_en: NaiveDatetime
  motivo: str | None = Field(default=None, max_length=50)

class DocumentosFirmas(EsquemaBase, table=True):
  """Firma canónica que vincula un listado con su PDF vigente."""
  __tablename__ = "documentos_firmas"
  __table_args__ = (
    Index(
      "uq_documentos_firmas_activa",
      "firma",
      unique=True,
      postgresql_where=text("fecha_eliminacion IS NULL"),
    ),
  )
  id: int | None = Field(default=None, primary_key=True)
  firma: str = Field(index=True)
  documento_id: int = Field(foreign_key="documentos_generados.id")

  documento: DocumentosGenerados | None = Relationship()

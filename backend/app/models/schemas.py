from datetime import datetime, time

from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel

import app.models.enums as en

LETRAS_SECCION = ("A", "B", "U")


def _normalizar_letra(valor: str) -> str:
  valor = valor.strip().upper()

  if valor not in LETRAS_SECCION:
    raise ValueError("La letra de la sección debe ser A, B o U")

  return valor


def _normalizar_fecha_caracas(fecha: datetime) -> datetime:
  # Import local para evitar un ciclo entre modelos y utilidades.
  from app.utils.fechas import normalizar_fecha

  return normalizar_fecha(fecha)


def _validar_ruta_relativa(valor: str | None) -> str | None:
  """Valida que archivo_url sea una ruta relativa segura dentro de STORAGE_ROOT."""
  if valor is None:
    return valor
  valor = valor.replace("\\", "/").strip()
  if not valor or valor.startswith("/"):
    raise ValueError("La ruta debe ser relativa al directorio de almacenamiento")
  if any(parte in ("", ".", "..") for parte in valor.split("/")):
    raise ValueError("La ruta debe ser una ruta relativa segura")
  return valor


def validar_bloque_horario(
  tipo: en.TipoBloqueHorario,
  numero: int | None,
  hora_inicio: time,
  hora_fin: time,
) -> None:
  """Valida la coherencia de un bloque académico o receso."""
  if hora_fin <= hora_inicio:
    raise ValueError("La hora de fin debe ser posterior a la hora de inicio")

  if tipo == en.TipoBloqueHorario.academico:
    if numero is None or not 1 <= numero <= 8:
      raise ValueError("Un bloque académico debe tener número entre 1 y 8")
  elif numero is not None:
    raise ValueError("Un receso no debe tener número de bloque académico")


# ====
# Esquemas para Usuarios
# ====
class CrearUsuario(SQLModel):
  nombre: str = Field(min_length=1, max_length=100)
  clave: str = Field(min_length=8, max_length=72)
  rol: en.RolesAsignables
  # Coordinador y secretaria siempre pertenecen a un nivel. El
  # administrador se crea por script con nivel None.
  nivel: en.NivelEducativo


class PeticionUsuario(SQLModel):
  id: int | None
  nombre: str
  rol: en.RolesUsuario
  nivel: en.NivelEducativo | None = None


class ActualizarUsuario(SQLModel):
  nombre: str | None = Field(default=None, min_length=1, max_length=100)
  rol: en.RolesAsignables | None = None
  nivel: en.NivelEducativo | None = None


class CambiarClave(SQLModel):
  clave_actual: str
  clave_nueva: str = Field(min_length=8, max_length=72)


# ====
# Esquemas para Grados (catálogo de solo lectura)
# ====
class PeticionGrado(SQLModel):
  id: int
  numero: int
  nombre: str
  nivel: en.NivelEducativo


# ====
# Esquemas para Secciones
# ====
class CrearSeccion(SQLModel):
  id_grado: int
  letra: str
  periodo_lectivo: int = Field(ge=2000)
  id_docente_titular: int | None = None

  @field_validator("letra")
  @classmethod
  def validar_letra(cls, valor: str) -> str:
    return _normalizar_letra(valor)


class ActualizarSeccion(SQLModel):
  letra: str | None = None
  periodo_lectivo: int | None = Field(default=None, ge=2000)
  id_docente_titular: int | None = None

  @field_validator("letra")
  @classmethod
  def validar_letra(cls, valor: str | None) -> str | None:
    return _normalizar_letra(valor) if valor is not None else None


class PeticionSeccion(SQLModel):
  id: int
  id_grado: int
  letra: str
  periodo_lectivo: int
  id_docente_titular: int | None = None

  # Datos de apoyo para listados y desplegables.
  grado_numero: int | None = None
  grado_nombre: str | None = None
  nivel: en.NivelEducativo | None = None
  docente_titular: str | None = None


# ====
# Esquemas para Representantes
# ====
class CrearRepresentante(SQLModel):
  primer_nombre: str = Field(min_length=1)
  segundo_nombre: str | None = None
  primer_apellido: str = Field(min_length=1)
  segundo_apellido: str | None = None

  telefono: str = Field(min_length=1)


class ActualizarRepresentante(SQLModel):
  primer_nombre: str | None = Field(default=None, min_length=1)
  segundo_nombre: str | None = None
  primer_apellido: str | None = Field(default=None, min_length=1)
  segundo_apellido: str | None = None
  telefono: str | None = Field(default=None, min_length=1)


class PeticionRepresentante(SQLModel):
  id: int
  primer_nombre: str
  segundo_nombre: str | None = None
  primer_apellido: str
  segundo_apellido: str | None = None
  telefono: str


# ====
# Esquemas para Docentes
# ====
class CrearDocente(SQLModel):
  primer_nombre: str = Field(min_length=1)
  segundo_nombre: str | None = None
  primer_apellido: str = Field(min_length=1)
  segundo_apellido: str | None = None

  cedula: str = Field(min_length=1)
  nivel: en.NivelEducativo


class ActualizarDocente(SQLModel):
  primer_nombre: str | None = Field(default=None, min_length=1)
  segundo_nombre: str | None = None
  primer_apellido: str | None = Field(default=None, min_length=1)
  segundo_apellido: str | None = None
  cedula: str | None = Field(default=None, min_length=1)
  nivel: en.NivelEducativo | None = None


class PeticionDocente(SQLModel):
  id: int
  primer_nombre: str
  segundo_nombre: str | None = None
  primer_apellido: str
  segundo_apellido: str | None = None
  cedula: str
  nivel: en.NivelEducativo


# ====
# Esquemas para Estudiantes
# ====
class CrearEstudiante(SQLModel):
  id_seccion: int
  id_representante: int | None = None

  cedula_estudiantil: str = Field(min_length=1)

  primer_nombre: str = Field(min_length=1)
  segundo_nombre: str | None = None
  primer_apellido: str = Field(min_length=1)
  segundo_apellido: str | None = None

  fecha_nacimiento: datetime

  @field_validator("fecha_nacimiento")
  @classmethod
  def normalizar_fecha_nacimiento(cls, valor: datetime) -> datetime:
    return _normalizar_fecha_caracas(valor)


class ActualizarEstudiante(SQLModel):
  id_seccion: int | None = None
  id_representante: int | None = None

  cedula_estudiantil: str | None = Field(default=None, min_length=1)

  primer_nombre: str | None = Field(default=None, min_length=1)
  segundo_nombre: str | None = None
  primer_apellido: str | None = Field(default=None, min_length=1)
  segundo_apellido: str | None = None

  fecha_nacimiento: datetime | None = None

  @field_validator("fecha_nacimiento")
  @classmethod
  def normalizar_fecha_nacimiento(cls, valor: datetime | None) -> datetime | None:
    return _normalizar_fecha_caracas(valor) if valor is not None else None


class PeticionEstudiante(SQLModel):
  id: int
  id_seccion: int
  id_representante: int | None = None

  cedula_estudiantil: str

  primer_nombre: str
  segundo_nombre: str | None = None
  primer_apellido: str
  segundo_apellido: str | None = None

  fecha_nacimiento: datetime

  # Datos de apoyo para listados y filtros por nivel.
  nivel: en.NivelEducativo | None = None
  id_grado: int | None = None
  grado_numero: int | None = None
  grado_nombre: str | None = None
  seccion_letra: str | None = None
  periodo_lectivo: int | None = None
  representante: str | None = None


# ====
# Esquemas para Asignaturas
# ====
class CrearAsignatura(SQLModel):
  id_grado: int
  nombre: str = Field(min_length=1)
  # Opcional: si no se envía, se usa el periodo lectivo activo.
  periodo_lectivo: int | None = Field(default=None, ge=2000)


class ActualizarAsignatura(SQLModel):
  id_grado: int | None = None
  nombre: str | None = Field(default=None, min_length=1)
  # El periodo lectivo se asigna en el registro; el cliente no puede cambiarlo.
  periodo_lectivo: int | None = None


class PeticionAsignatura(SQLModel):
  id: int
  id_grado: int
  periodo_lectivo: int
  nombre: str

  grado_numero: int | None = None
  grado_nombre: str | None = None
  nivel: en.NivelEducativo | None = None
  docentes: list[PeticionDocente] = Field(default_factory=list)


class VincularDocente(SQLModel):
  id_docente: int


# ====
# Esquemas para Bloques Horarios
# ====
class CrearBloqueHorario(SQLModel):
  orden: int = Field(ge=1, le=10)
  numero: int | None = Field(default=None, ge=1, le=8)
  nombre: str = Field(min_length=1)
  tipo: en.TipoBloqueHorario
  hora_inicio: time
  hora_fin: time

  @model_validator(mode="after")
  def validar_tramo(self):
    validar_bloque_horario(self.tipo, self.numero, self.hora_inicio, self.hora_fin)
    return self


class ActualizarBloqueHorario(SQLModel):
  orden: int | None = Field(default=None, ge=1, le=10)
  numero: int | None = Field(default=None, ge=1, le=8)
  nombre: str | None = Field(default=None, min_length=1)
  tipo: en.TipoBloqueHorario | None = None
  hora_inicio: time | None = None
  hora_fin: time | None = None


class PeticionBloqueHorario(SQLModel):
  id: int
  orden: int
  numero: int | None = None
  nombre: str
  tipo: en.TipoBloqueHorario
  hora_inicio: time
  hora_fin: time


# ====
# Esquemas para Horarios
# ====
class CrearHorario(SQLModel):
  id_seccion: int
  id_bloque: int
  id_asignatura: int
  id_docente: int
  periodo_lectivo: int = Field(ge=2000)
  dia_semana: int = Field(ge=1, le=5)


class ActualizarHorario(SQLModel):
  id_seccion: int | None = None
  id_bloque: int | None = None
  id_asignatura: int | None = None
  id_docente: int | None = None
  periodo_lectivo: int | None = Field(default=None, ge=2000)
  dia_semana: int | None = Field(default=None, ge=1, le=5)


class PeticionHorario(SQLModel):
  id: int
  id_seccion: int
  id_bloque: int
  id_asignatura: int
  id_docente: int
  periodo_lectivo: int
  dia_semana: int

  # Datos de apoyo para la grilla y los listados.
  seccion: str | None = None
  grado: str | None = None
  nivel: en.NivelEducativo | None = None
  bloque: str | None = None
  bloque_orden: int | None = None
  hora_inicio: time | None = None
  hora_fin: time | None = None
  asignatura: str | None = None
  docente: str | None = None


# Respuesta del autocompletado: resuelve la sección del estudiante y el
# bloque institucional, sin usar una hora suelta como clave del horario.
class PeticionConsultaHorario(SQLModel):
  encontrado: bool
  id_horario: int | None = None
  id_bloque: int | None = None
  id_asignatura: int | None = None
  id_docente: int | None = None
  asignatura: str | None = None
  docente: str | None = None
  bloque: str | None = None
  hora_inicio: time | None = None
  hora_fin: time | None = None


# ====
# Esquemas para Pases
# ====
class CrearPase(SQLModel):
  id_estudiante: int
  id_docente: int | None = None
  id_asignatura: int | None = None
  tipo: en.TipoPase = en.TipoPase.entrada
  motivo: str = Field(min_length=1)
  fecha: datetime
  autorizador: str | None = None
  archivo_url: str | None = None

  @field_validator("archivo_url")
  @classmethod
  def validar_archivo_url(cls, valor: str | None) -> str | None:
    return _validar_ruta_relativa(valor)

  @field_validator("fecha")
  @classmethod
  def normalizar_fecha(cls, valor: datetime) -> datetime:
    return _normalizar_fecha_caracas(valor)


class ActualizacionPase(SQLModel):
  id_docente: int | None = None
  id_asignatura: int | None = None
  tipo: en.TipoPase | None = None
  motivo: str | None = Field(default=None, min_length=1)
  fecha: datetime | None = None
  autorizador: str | None = None
  archivo_url: str | None = None

  @field_validator("archivo_url")
  @classmethod
  def validar_archivo_url(cls, valor: str | None) -> str | None:
    return _validar_ruta_relativa(valor)

  @field_validator("fecha")
  @classmethod
  def normalizar_fecha(cls, valor: datetime | None) -> datetime | None:
    return _normalizar_fecha_caracas(valor) if valor is not None else None


class PeticionPase(SQLModel):
  id: int
  id_estudiante: int
  id_usuario: int
  id_docente: int | None = None
  id_asignatura: int | None = None
  tipo: en.TipoPase
  motivo: str
  fecha: datetime
  periodo_lectivo: int | None = None
  autorizador: str | None = None
  archivo_url: str | None = None
  archivo_nombre: str | None = None
  archivo_mime: str | None = None
  archivo_tamano: int | None = None
  archivo_hash: str | None = None
  archivo_subido_por: int | None = None
  archivo_fecha: datetime | None = None

  # Datos de apoyo para listados y filtros por nivel.
  estudiante: str | None = None
  cedula_estudiantil: str | None = None
  nivel: en.NivelEducativo | None = None
  usuario: str | None = None
  docente: str | None = None
  asignatura: str | None = None


class PeticionPeriodoLectivo(SQLModel):
  id: int | None = None
  anio: int = Field(ge=2000)
  activo: bool = False
  cerrado: bool = False


class CrearPeriodoLectivo(SQLModel):
  anio: int = Field(ge=2000)
  activo: bool = False


class ActualizarPeriodoLectivo(SQLModel):
  activo: bool | None = None
  cerrado: bool | None = None


# ====
# Esquemas para Reportes
# ====
class CrearReporte(SQLModel):
  id_estudiante: int
  id_docente: int | None = None

  articulo: int = Field(ge=1)
  reglamento: en.Reglamentos
  incidencia: str = Field(min_length=1)
  defensa: str = Field(min_length=1)
  nivel_gravedad: en.NivelGravedad = en.NivelGravedad.leve
  categoria: en.CategoriaReportes
  fecha: datetime
  archivo_url: str | None = None

  @field_validator("archivo_url")
  @classmethod
  def validar_archivo_url(cls, valor: str | None) -> str | None:
    return _validar_ruta_relativa(valor)

  @field_validator("fecha")
  @classmethod
  def normalizar_fecha(cls, valor: datetime) -> datetime:
    return _normalizar_fecha_caracas(valor)


class ActualizarReporte(SQLModel):
  id_docente: int | None = None

  articulo: int | None = Field(default=None, ge=1)
  reglamento: en.Reglamentos | None = None
  incidencia: str | None = Field(default=None, min_length=1)
  defensa: str | None = Field(default=None, min_length=1)
  nivel_gravedad: en.NivelGravedad | None = None
  categoria: en.CategoriaReportes | None = None
  fecha: datetime | None = None
  archivo_url: str | None = None

  @field_validator("archivo_url")
  @classmethod
  def validar_archivo_url(cls, valor: str | None) -> str | None:
    return _validar_ruta_relativa(valor)

  @field_validator("fecha")
  @classmethod
  def normalizar_fecha(cls, valor: datetime | None) -> datetime | None:
    return _normalizar_fecha_caracas(valor) if valor is not None else None


class PeticionReporte(SQLModel):
  id: int
  id_estudiante: int
  id_usuario: int
  id_docente: int | None = None

  articulo: int
  reglamento: en.Reglamentos
  incidencia: str
  defensa: str
  nivel_gravedad: en.NivelGravedad
  categoria: en.CategoriaReportes
  fecha: datetime
  periodo_lectivo: int | None = None
  archivo_url: str | None = None
  archivo_nombre: str | None = None
  archivo_mime: str | None = None
  archivo_tamano: int | None = None
  archivo_hash: str | None = None
  archivo_subido_por: int | None = None
  archivo_fecha: datetime | None = None

  # Datos de apoyo para listados y filtros por nivel.
  estudiante: str | None = None
  cedula_estudiantil: str | None = None
  nivel: en.NivelEducativo | None = None
  usuario: str | None = None
  docente: str | None = None


# ====
# Esquemas para Listados (PDFs generados por tipo)
# ====
class SolicitudListado(SQLModel):
  """Filtros para generar un listado PDF.

  Una sección define grado/periodo; sin sección, se genera "general" por
  nivel. `id_grado` solo admite grados de liceo (horarios).
  """

  periodo_lectivo: int | None = None
  nivel: en.NivelEducativo | None = None
  id_grado: int | None = None
  id_seccion: int | None = None


class PeticionDocumentoGenerado(SQLModel):
  id: int | None = None
  tipo: en.TipoDocumento
  periodo_lectivo: int | None = None
  nivel: en.NivelEducativo | None = None
  id_grado: int | None = None
  id_seccion: int | None = None

  nombre_archivo: str
  ruta_relativa: str
  hash: str
  tamano: int
  mime: str
  fecha_generacion: datetime
  generado_por: int | None = None

  # Datos de apoyo para filtros y desplegables
  grado_numero: int | None = None
  grado_nombre: str | None = None


# ====
# Esquema para el resumen de gestión académica
# ====
class PeticionResumenGestion(SQLModel):
  nivel: en.NivelEducativo | None = None
  representantes: int
  estudiantes: int
  secciones: int
  docentes: int
  asignaturas: int
  horarios: int
  pases: int
  reportes: int


# ====
# Esquema para Auditoría
# ====
class PeticionAuditoria(SQLModel):
  id: int | None
  usuario_id: int | None
  usuario: str | None = None
  modulo: str
  accion: str
  descripcion: str
  fecha_creacion: datetime

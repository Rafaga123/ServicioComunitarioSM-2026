"""Declara los contratos de entrada y salida de los endpoints."""

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


class CrearUsuario(SQLModel):
  """Datos necesarios para crear una cuenta de usuario."""
  nombre: str = Field(min_length=1, max_length=100)
  clave: str = Field(min_length=8, max_length=72)
  rol: en.RolesAsignables
  # Coordinador y secretaria siempre pertenecen a un nivel. El
  # administrador se crea por script o se obtiene al transferir el rol.
  nivel: en.NivelEducativo


class PeticionUsuario(SQLModel):
  """Datos visibles de una cuenta de usuario."""
  id: int | None
  nombre: str
  rol: en.RolesUsuario
  nivel: en.NivelEducativo | None = None


class ActualizarUsuario(SQLModel):
  """Campos editables de una cuenta por parte del administrador."""
  nombre: str | None = Field(default=None, min_length=1, max_length=100)
  rol: en.RolesAsignables | None = None
  nivel: en.NivelEducativo | None = None
  # Reset de clave por parte del administrador. Opcional: si no viene,
  # el PUT sigue actualizando solo nombre/rol/nivel como siempre.
  clave: str | None = Field(default=None, min_length=8, max_length=72)


class CambiarClave(SQLModel):
  """Clave actual y nueva para el cambio propio de clave."""
  clave_actual: str
  clave_nueva: str = Field(min_length=8, max_length=72)


class PeticionGrado(SQLModel):
  """Grado del catálogo expuesto al frontend."""
  id: int
  numero: int
  nombre: str
  nivel: en.NivelEducativo


class CrearSeccion(SQLModel):
  """Datos para crear una sección de un grado."""
  id_grado: int
  letra: str
  periodo_lectivo: int = Field(ge=2000)
  id_docente_titular: int | None = None

  @field_validator("letra")
  @classmethod
  def validar_letra(cls, valor: str) -> str:
    return _normalizar_letra(valor)


class ActualizarSeccion(SQLModel):
  """Campos editables de una sección."""
  letra: str | None = None
  periodo_lectivo: int | None = Field(default=None, ge=2000)
  id_docente_titular: int | None = None

  @field_validator("letra")
  @classmethod
  def validar_letra(cls, valor: str | None) -> str | None:
    return _normalizar_letra(valor) if valor is not None else None


class PeticionSeccion(SQLModel):
  """Datos visibles de una sección."""
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


class CrearRepresentante(SQLModel):
  """Datos para registrar un representante."""
  primer_nombre: str = Field(min_length=1)
  segundo_nombre: str | None = None
  primer_apellido: str = Field(min_length=1)
  segundo_apellido: str | None = None

  telefono: str = Field(min_length=1)


class ActualizarRepresentante(SQLModel):
  """Campos editables de un representante."""
  primer_nombre: str | None = Field(default=None, min_length=1)
  segundo_nombre: str | None = None
  primer_apellido: str | None = Field(default=None, min_length=1)
  segundo_apellido: str | None = None
  telefono: str | None = Field(default=None, min_length=1)


class PeticionRepresentante(SQLModel):
  """Datos visibles de un representante."""
  id: int
  primer_nombre: str
  segundo_nombre: str | None = None
  primer_apellido: str
  segundo_apellido: str | None = None
  telefono: str


class CrearDocente(SQLModel):
  """Datos para registrar un docente."""
  primer_nombre: str = Field(min_length=1)
  segundo_nombre: str | None = None
  primer_apellido: str = Field(min_length=1)
  segundo_apellido: str | None = None

  cedula: str = Field(min_length=1)
  nivel: en.NivelEducativo


class ActualizarDocente(SQLModel):
  """Campos editables de un docente."""
  primer_nombre: str | None = Field(default=None, min_length=1)
  segundo_nombre: str | None = None
  primer_apellido: str | None = Field(default=None, min_length=1)
  segundo_apellido: str | None = None
  cedula: str | None = Field(default=None, min_length=1)
  nivel: en.NivelEducativo | None = None


class PeticionDocente(SQLModel):
  """Datos visibles de un docente."""
  id: int
  primer_nombre: str
  segundo_nombre: str | None = None
  primer_apellido: str
  segundo_apellido: str | None = None
  cedula: str
  nivel: en.NivelEducativo


class CrearEstudiante(SQLModel):
  """Datos para inscribir un estudiante."""
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
  """Campos editables de un estudiante."""
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
  """Datos visibles de un estudiante con su ubicación académica."""
  id: int
  id_seccion: int
  id_representante: int | None = None

  cedula_estudiantil: str

  primer_nombre: str
  segundo_nombre: str | None = None
  primer_apellido: str
  segundo_apellido: str | None = None

  fecha_nacimiento: datetime
  # Asignado por el cierre de año; solo se expone en lectura (no acepta PUT).
  fecha_egreso: datetime | None = None

  # Datos de apoyo para listados y filtros por nivel.
  nivel: en.NivelEducativo | None = None
  id_grado: int | None = None
  grado_numero: int | None = None
  grado_nombre: str | None = None
  seccion_letra: str | None = None
  periodo_lectivo: int | None = None
  representante: str | None = None


class CrearAsignatura(SQLModel):
  """Datos para crear una asignatura."""
  id_grado: int
  nombre: str = Field(min_length=1)
  # Opcional: si no se envía, se usa el periodo lectivo activo.
  periodo_lectivo: int | None = Field(default=None, ge=2000)


class ActualizarAsignatura(SQLModel):
  """Campos editables de una asignatura."""
  id_grado: int | None = None
  nombre: str | None = Field(default=None, min_length=1)
  # El periodo lectivo se asigna en el registro; el cliente no puede cambiarlo.
  periodo_lectivo: int | None = None


class PeticionAsignatura(SQLModel):
  """Datos visibles de una asignatura y sus docentes."""
  id: int
  id_grado: int
  periodo_lectivo: int
  nombre: str

  grado_numero: int | None = None
  grado_nombre: str | None = None
  nivel: en.NivelEducativo | None = None
  docentes: list[PeticionDocente] = Field(default_factory=list)


class VincularDocente(SQLModel):
  """Identificador del docente a vincular a una asignatura."""
  id_docente: int


class CrearBloqueHorario(SQLModel):
  """Datos para crear un bloque de la jornada."""
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
  """Campos editables de un bloque horario."""
  orden: int | None = Field(default=None, ge=1, le=10)
  numero: int | None = Field(default=None, ge=1, le=8)
  nombre: str | None = Field(default=None, min_length=1)
  tipo: en.TipoBloqueHorario | None = None
  hora_inicio: time | None = None
  hora_fin: time | None = None


class PeticionBloqueHorario(SQLModel):
  """Datos visibles de un bloque horario."""
  id: int
  orden: int
  numero: int | None = None
  nombre: str
  tipo: en.TipoBloqueHorario
  hora_inicio: time
  hora_fin: time


class CrearHorario(SQLModel):
  """Datos para asignar un horario a una sección."""
  id_seccion: int
  id_bloque: int
  id_asignatura: int
  id_docente: int
  periodo_lectivo: int = Field(ge=2000)
  dia_semana: int = Field(ge=1, le=5)


class ActualizarHorario(SQLModel):
  """Campos editables de un horario."""
  id_seccion: int | None = None
  id_bloque: int | None = None
  id_asignatura: int | None = None
  id_docente: int | None = None
  periodo_lectivo: int | None = Field(default=None, ge=2000)
  dia_semana: int | None = Field(default=None, ge=1, le=5)


class PeticionHorario(SQLModel):
  """Datos visibles de una celda del horario."""
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
  """Respuesta del autocompletado de horario por estudiante y bloque."""
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


class CrearPase(SQLModel):
  """Datos para registrar un pase disciplinario."""
  id_estudiante: int
  id_docente: int | None = None
  id_asignatura: int | None = None
  tipo: en.TipoPase = en.TipoPase.entrada
  motivo: str = Field(min_length=1)
  fecha: datetime
  autorizador: str | None = None

  @field_validator("fecha")
  @classmethod
  def normalizar_fecha(cls, valor: datetime) -> datetime:
    return _normalizar_fecha_caracas(valor)


class ActualizacionPase(SQLModel):
  """Campos editables de un pase."""
  id_docente: int | None = None
  id_asignatura: int | None = None
  tipo: en.TipoPase | None = None
  motivo: str | None = Field(default=None, min_length=1)
  fecha: datetime | None = None
  autorizador: str | None = None

  @field_validator("fecha")
  @classmethod
  def normalizar_fecha(cls, valor: datetime | None) -> datetime | None:
    return _normalizar_fecha_caracas(valor) if valor is not None else None


class PeticionPase(SQLModel):
  """Datos visibles de un pase."""
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
  """Datos visibles de un periodo lectivo."""
  id: int | None = None
  anio: int = Field(ge=2000)
  activo: bool = False
  cerrado: bool = False


class CrearPeriodoLectivo(SQLModel):
  """Datos para crear un periodo lectivo."""
  anio: int = Field(ge=2000)
  activo: bool = False


class ActualizarPeriodoLectivo(SQLModel):
  """Campos editables de un periodo lectivo."""
  activo: bool | None = None
  cerrado: bool | None = None


class CrearReporte(SQLModel):
  """Datos para registrar un reporte disciplinario."""
  id_estudiante: int
  id_docente: int | None = None

  articulo: int = Field(ge=1)
  reglamento: en.Reglamentos
  incidencia: str = Field(min_length=1)
  defensa: str = Field(min_length=1)
  nivel_gravedad: en.NivelGravedad = en.NivelGravedad.leve
  categoria: en.CategoriaReportes
  fecha: datetime

  @field_validator("fecha")
  @classmethod
  def normalizar_fecha(cls, valor: datetime) -> datetime:
    return _normalizar_fecha_caracas(valor)


class ActualizarReporte(SQLModel):
  """Campos editables de un reporte."""
  id_docente: int | None = None

  articulo: int | None = Field(default=None, ge=1)
  reglamento: en.Reglamentos | None = None
  incidencia: str | None = Field(default=None, min_length=1)
  defensa: str | None = Field(default=None, min_length=1)
  nivel_gravedad: en.NivelGravedad | None = None
  categoria: en.CategoriaReportes | None = None
  fecha: datetime | None = None

  @field_validator("fecha")
  @classmethod
  def normalizar_fecha(cls, valor: datetime | None) -> datetime | None:
    return _normalizar_fecha_caracas(valor) if valor is not None else None


class PeticionReporte(SQLModel):
  """Datos visibles de un reporte."""
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


class SolicitudCierreAnio(SQLModel):
  """Parámetros solicitados para ejecutar el cierre de año."""
  periodo_actual: int = Field(ge=2000)
  periodo_siguiente: int = Field(ge=2000)


class PeticionCierreAnio(SQLModel):
  """Resultado del cierre de año ejecutado."""
  periodo_cerrado: int
  periodo_activado: int
  documentos_generados: int
  estudiantes_promovidos: int
  egresados: int
  secciones_creadas: int
  asignaturas_creadas: int


class SolicitudListado(SQLModel):
  """Filtros para generar un listado PDF.

  Una sección define grado/periodo. Sin sección, `nivel` genera el listado
  general de todo el nivel y `id_grado` genera el general de un solo grado
  para nóminas y representantes. `id_grado` e `id_seccion` no se combinan.
  """

  periodo_lectivo: int | None = None
  nivel: en.NivelEducativo | None = None
  id_grado: int | None = None
  id_seccion: int | None = None


class PeticionDocumentoGenerado(SQLModel):
  """Datos visibles de un PDF generado y su ruta de descarga."""
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


class PeticionResumenGestion(SQLModel):
  """Resumen agregado de gestión académica por nivel."""
  nivel: en.NivelEducativo | None = None
  periodo_lectivo: int | None = None
  representantes: int
  estudiantes: int
  secciones: int
  docentes: int
  asignaturas: int
  horarios: int
  pases: int
  reportes: int


class PeticionAuditoria(SQLModel):
  """Registro de auditoría expuesto al frontend."""
  id: int | None
  usuario_id: int | None
  usuario: str | None = None
  modulo: str
  accion: str
  descripcion: str
  fecha_creacion: datetime

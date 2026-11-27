"""Enumera los valores controlados utilizados por la API."""

from enum import Enum


# Enum para los roles de usuarios
class RolesUsuario(str, Enum):
  """Roles permitidos para una cuenta de usuario."""
  administrador = "ADMINISTRADOR"
  coordinador = "COORDINADOR"
  secretaria = "SECRETARIA"


# Roles que el administrador puede asignar desde la API
class RolesAsignables(str, Enum):
  """Roles que el administrador puede asignar desde la API."""
  coordinador = "COORDINADOR"
  secretaria = "SECRETARIA"


# Nivel educativo al que pertenece un grado, docente o cuenta de usuario
class NivelEducativo(str, Enum):
  """Nivel educativo al que pertenecen grados, docentes y cuentas."""
  escuela = "ESCUELA"
  liceo = "LICEO"


# Tipo de tramo dentro de la jornada institucional del liceo
class TipoBloqueHorario(str, Enum):
  """Tipo de tramo de la jornada: académico o receso."""
  academico = "ACADEMICO"
  receso = "RECESO"


class ModuloAuditoria(str, Enum):
  """Módulos del sistema susceptibles de auditoría."""
  usuarios = "USUARIOS"
  estudiantes = "ESTUDIANTES"
  grados = "GRADOS"
  secciones = "SECCIONES"
  representantes = "REPRESENTANTES"
  docentes = "DOCENTES"
  asignaturas = "ASIGNATURAS"
  bloques_horarios = "BLOQUES HORARIOS"
  horarios = "HORARIOS"
  pases = "PASES"
  reportes = "REPORTES"
  auditorias = "AUDITORIAS"
  periodos_lectivos = "PERIODOS LECTIVOS"
  documentos = "DOCUMENTOS"
  cierre_anio = "CIERRE AÑO"


# Tipos de documentos generados como PDFs de listados institucionales
class TipoDocumento(str, Enum):
  """Tipos de PDF generados por los listados institucionales."""
  nominas = "nominas"
  representantes = "representantes"
  horarios = "horarios"
  docentes = "docentes"


# Enum para los tipos de reglamento
class Reglamentos(str, Enum):
  """Tipos de reglamento asociados a un pase."""
  lopnna = "LOPNNA"  # Ley Orgánica para la protección de niños, niñas y adolescentes
  loe = "LOE"  # Ley Orgánica de Educación
  cbv = "CBV"  # Constitución de la República Bolivariana de Venezuela
  nc = "NC"  # Nuestra Carta


# Enum para la gravedad de un reporte
class NivelGravedad(str, Enum):
  """Niveles de gravedad de un reporte."""
  leve = "LEVE"
  grave = "GRAVE"


# Enum para la categoría de los reportes
class CategoriaReportes(str, Enum):
  """Categorías disponibles para los reportes."""
  conducta = "CONDUCTUAL"
  academico = "ACADEMICO"


# Enum para tipo de pase
class TipoPase(str, Enum):
  """Tipos de pase disciplinario emitidos a un estudiante."""
  salida = "SALIDA"
  entrada = "ENTRADA"

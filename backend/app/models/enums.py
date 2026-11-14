from enum import Enum


# Enum para los roles de usuarios
class RolesUsuario(str, Enum):
  administrador = "ADMINISTRADOR"
  coordinador = "COORDINADOR"
  secretaria = "SECRETARIA"


# Enum para los tipos de reglamento
class Reglamentos(str, Enum):
  lopnna = "LOPNNA" # Ley Orgánica para la protección de niños, niñas y adolescentes
  loe = "LOE"       # Ley Orgánica de Educación
  cbv = "CBV"       # Constitución de la República Bolivariana de Venezuela
  nc = "NC"         # Nuestra Carta


# Enum para la gravedad de un reporte
class NivelGravedad(str, Enum):
  leve = "LEVE"
  grave = "GRAVE"


# Enum para la categoría de los reportes
class CategoriaReportes(str, Enum):
  conducta = "CONDUCTUAL"
  academico = "ACADEMICO"


# Enum para tipo de pase
class TipoPase(str, Enum):
  salida = "SALIDA"
  entrada = "ENTRADA"
  


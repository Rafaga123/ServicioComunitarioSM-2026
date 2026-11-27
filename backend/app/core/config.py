"""Lee y valida la configuración de entorno, JWT, almacenamiento y límites de acceso."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Carga las variables de entorno del archivo .env.
load_dotenv()

# Configuración de la Base de Datos
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Nombre de la institución que encabeza los PDFs de listados.
INSTITUCION_NOMBRE = os.getenv(
  "INSTITUCION_NOMBRE", "UNIDAD EDUCATIVA PRIVADA SANTA MARTA"
)

# Logo institucional dibujado arriba a la izquierda en todos los PDFs.
# Se puede sobreescribir con LOGO_SANTA_MARTA_PATH si el archivo vive fuera del proyecto.
LOGO_PATH = Path(
  os.getenv("LOGO_SANTA_MARTA_PATH")
  or Path(__file__).resolve().parents[1] / "assets" / "logo_santa_marta_grande.png"
)

# Directorio raíz del almacenamiento físico de archivos adjuntos de pases y reportes.
STORAGE_ROOT = os.getenv("STORAGE_ROOT", r"C:\sistema")

# Tamaño máximo de un archivo adjunto subido (imágenes: jpg/jpeg/png/webp).
ARCHIVOS_MAX_BYTES = 5 * 1024 * 1024

# Reutilizar un PDF existente cuando la firma de sus datos no cambió.
# Desactivado por defecto: requiere aprobación explícita en el entorno.
REUTILIZAR_DOCUMENTOS_IGUALES = (
  os.getenv("REUTILIZAR_DOCUMENTOS_IGUALES", "False").lower() == "true"
)

# Configuración de los tokens JWT
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "360")

# Validaciones de la configuración JWT
if not SECRET_KEY:
  raise RuntimeError(
    "SECRET_KEY no está definida. Agrégala al archivo .env antes de iniciar la API."
  )

if len(SECRET_KEY.encode("utf-8")) < 32:
  raise RuntimeError(
    "SECRET_KEY es demasiado corta: usa al menos 32 bytes "
    "(por ejemplo, secrets.token_urlsafe(48))."
  )

try:
  ACCESS_TOKEN_EXPIRE_MINUTES = int(ACCESS_TOKEN_EXPIRE_MINUTES)
except ValueError as error:
  raise RuntimeError(
    "ACCESS_TOKEN_EXPIRE_MINUTES debe ser un número entero."
  ) from error

if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
  raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES debe ser mayor que cero.")

# Límite de intentos de inicio de sesión (anti fuerza bruta / flood).
LIMITE_LOGIN_INTENTOS = os.getenv("LIMITE_LOGIN_INTENTOS", "5")
LIMITE_LOGIN_IP = os.getenv("LIMITE_LOGIN_IP", "20")
LIMITE_LOGIN_VENTANA_SEGUNDOS = os.getenv("LIMITE_LOGIN_VENTANA_SEGUNDOS", "60")

# Horas que se conserva un jti revocado después de vencido el token.
TOKENS_REVOCADOS_RETENCION_HORAS = os.getenv(
  "TOKENS_REVOCADOS_RETENCION_HORAS", "24"
)

def _entero_positivo(nombre: str, valor: str) -> int:
  """Convierte y valida una variable entera positiva de entorno."""

  try:
    numero = int(valor)
  except ValueError as error:
    raise RuntimeError(f"{nombre} debe ser un número entero.") from error

  if numero <= 0:
    raise RuntimeError(f"{nombre} debe ser mayor que cero.")

  return numero


LIMITE_LOGIN_INTENTOS = _entero_positivo(
  "LIMITE_LOGIN_INTENTOS", LIMITE_LOGIN_INTENTOS
)
LIMITE_LOGIN_IP = _entero_positivo("LIMITE_LOGIN_IP", LIMITE_LOGIN_IP)
LIMITE_LOGIN_VENTANA_SEGUNDOS = _entero_positivo(
  "LIMITE_LOGIN_VENTANA_SEGUNDOS", LIMITE_LOGIN_VENTANA_SEGUNDOS
)
TOKENS_REVOCADOS_RETENCION_HORAS = _entero_positivo(
  "TOKENS_REVOCADOS_RETENCION_HORAS", TOKENS_REVOCADOS_RETENCION_HORAS
)

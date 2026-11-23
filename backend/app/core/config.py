import os

from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
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

# Directorio raíz del almacenamiento físico de archivos adjuntos de pases y reportes.
STORAGE_ROOT = os.getenv("STORAGE_ROOT", r"C:\sistema")

# Tamaño máximo de un archivo adjunto subido (imágenes: jpg/jpeg/png/webp).
ARCHIVOS_MAX_BYTES = 5 * 1024 * 1024

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

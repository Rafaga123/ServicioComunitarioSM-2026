import os

from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

# Configuración de los tokens JWT
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "360"))

# Evita arrancar la API firmando tokens con una clave vacía
if not SECRET_KEY:
  raise RuntimeError(
    "SECRET_KEY no está definida. Agrégala al archivo .env antes de iniciar la API."
  )

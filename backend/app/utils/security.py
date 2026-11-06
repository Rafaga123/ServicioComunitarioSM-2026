from datetime import UTC, datetime, timedelta

import jwt

# Configurador del encriptador
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecate="auto")

SECRET_KEY = "ELONEPICEESCLAVE" # Cambiar luego, lol
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 # 1 hora


# Obtiene el texto simple de la clave y lo encripta en hash
def obtener_hash_clave(clave: str) -> str:
    
    return pwd_context.hash(clave)

# Compara la clave en texto plano con un hash para verificar si son la misma
def verificar_clave(clave: str, clave_hash) -> bool:
    return pwd_context.verify(clave, clave_hash)


# Crea y firma el JWT
def crear_token_acceso(data: dict) -> str:
    to_encode = data.copy()
    
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) # Tiempo de expiracion del token
    
    to_encode.update({"exp": expire}) # Actualizacion del tiempo de expiracion
    
    token_codificado = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM) # Firma del token codificado
    
    return token_codificado

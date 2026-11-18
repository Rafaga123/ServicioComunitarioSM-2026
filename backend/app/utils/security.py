from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlmodel import Session

from app.models.db import Usuarios
from app.models.session import get_session

SECRET_KEY = "ELONEPICEESCLAVE"  # Cambiar luego, lol
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 360  # 6 horas


# Obtiene el texto simple de la clave y lo encripta en hash
def obtener_hash_clave(clave: str) -> str:
  """Recibe una contraseña en texto plano y devuelve su hash irreversible."""

  clave_bytes = clave.encode("utf-8")
  salt = bcrypt.gensalt()
  hash_bytes = bcrypt.hashpw(clave_bytes, salt)

  return hash_bytes.decode("utf-8")


# Compara la clave en texto plano con un hash para verificar si son la misma
def verificar_clave(clave: str, clave_hash: str) -> bool:
  """Compara una contraseña ingresada en texto plano con un hash para verificar su concordancia."""

  clave_bytes = clave.encode("utf-8")
  hash_bytes = clave_hash.encode("utf-8")

  return bcrypt.checkpw(clave_bytes, hash_bytes)


# Crea y firma el JWT
def crear_token_acceso(data: dict) -> str:
  """Crea y firma  el JWT"""

  to_encode = data.copy()

  expire = datetime.now(UTC) + timedelta(
    minutes=ACCESS_TOKEN_EXPIRE_MINUTES
  )  # Tiempo de expiracion del token

  to_encode.update({"exp": expire})  # Actualizacion del tiempo de expiracion

  token_codificado = jwt.encode(
    to_encode, SECRET_KEY, algorithm=ALGORITHM
  )  # Firma del token codificado

  return token_codificado


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def obtener_usuario_actual(
  token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
) -> Usuarios:
  excepcion_credenciales = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudieron validar las credenciales (Token inválido o expirado)",
    headers={"WWW-Authenticate": "Bearer"},
  )

  try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    usuario_id: str = payload.get("sub")

    if usuario_id is None:
      raise excepcion_credenciales

  except InvalidTokenError:
    raise excepcion_credenciales

  usuario = session.get(Usuarios, int(usuario_id))

  if usuario is None:
    raise excepcion_credenciales

  return usuario

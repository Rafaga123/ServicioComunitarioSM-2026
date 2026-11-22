from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlmodel import Session

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from app.models.db import Usuarios
from app.models.enums import NivelEducativo, RolesUsuario
from app.models.session import get_session


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


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


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

    usuario_id = payload.get("sub")

    if usuario_id is None:
      raise excepcion_credenciales

    usuario = session.get(Usuarios, int(usuario_id))

  except (InvalidTokenError, TypeError, ValueError):
    raise excepcion_credenciales

  if usuario is None or usuario.fecha_eliminacion is not None:
    raise excepcion_credenciales

  return usuario


# Dependencia reutilizable para restringir endpoints según el rol del usuario
def requerir_roles(*roles: RolesUsuario):
  def dependencia(
    usuario_actual: Usuarios = Depends(obtener_usuario_actual),
  ) -> Usuarios:
    if usuario_actual.rol not in roles:
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos para realizar esta acción",
      )

    return usuario_actual

  return dependencia


# Nivel que debe aplicarse como filtro en las consultas.
# El administrador no se limita a un nivel (None = ambos).
def nivel_efectivo(usuario: Usuarios) -> NivelEducativo | None:
  if usuario.rol == RolesUsuario.administrador:
    return None

  return usuario.nivel


# Solo el administrador gestiona catálogos y operaciones estructurales
def requerir_admin(
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
) -> Usuarios:
  if usuario_actual.rol != RolesUsuario.administrador:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Solo el administrador puede realizar esta acción",
    )

  return usuario_actual


# Coordinador y secretaria operan únicamente dentro de su nivel
def requerir_operador(
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
) -> Usuarios:
  if usuario_actual.rol not in (
    RolesUsuario.coordinador,
    RolesUsuario.secretaria,
  ):
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="No tienes permisos para realizar esta acción",
    )

  if usuario_actual.nivel is None:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="La cuenta no tiene un nivel educativo asignado",
    )

  return usuario_actual


# Verifica que un operador solo acceda a registros de su nivel.
# El administrador siempre tiene acceso.
def validar_acceso_nivel(
  usuario: Usuarios, nivel: NivelEducativo | None
) -> None:
  if usuario.rol == RolesUsuario.administrador:
    return

  if nivel is None or usuario.nivel != nivel:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="No tienes acceso a registros de otro nivel educativo",
    )

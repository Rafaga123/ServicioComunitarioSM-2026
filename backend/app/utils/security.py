"""Valida JWT, resuelve roles y niveles, y aplica el control de acceso."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlmodel import Session

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from app.models.db import Usuarios
from app.models.enums import NivelEducativo, RolesUsuario
from app.models.session import get_session
from app.utils.tokens_revocados import esta_revocado


def obtener_hash_clave(clave: str) -> str:
  """Devuelve el hash bcrypt de una clave en texto plano."""

  clave_bytes = clave.encode("utf-8")
  salt = bcrypt.gensalt()
  hash_bytes = bcrypt.hashpw(clave_bytes, salt)

  return hash_bytes.decode("utf-8")


def verificar_clave(clave: str, clave_hash: str) -> bool:
  """Devuelve True si la clave en texto plano coincide con el hash."""

  clave_bytes = clave.encode("utf-8")
  hash_bytes = clave_hash.encode("utf-8")

  return bcrypt.checkpw(clave_bytes, hash_bytes)


def crear_token_acceso(data: dict, version_tokens: int) -> str:
  """Crea y firma el JWT con identificador único y versión del usuario."""

  to_encode = data.copy()

  expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

  to_encode.update(
    {
      "exp": expire,
      "jti": str(uuid4()),
      "ver": version_tokens,
    }
  )

  return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def validar_token(
  token: str,
  session: Session,
  *,
  exigir_no_revocado: bool = True,
) -> tuple[Usuarios, dict]:
  """Valida firma, expiración, usuario, versión y denylist.

  `exigir_no_revocado=False` se usa solo en logout: así un segundo cierre
  con el mismo token sigue devolviendo 204 en vez de 401.
  """

  excepcion_credenciales = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudieron validar las credenciales (token inválido)",
    headers={"WWW-Authenticate": "Bearer"},
  )
  excepcion_expirado = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="La sesión ha expirado. Inicia sesión nuevamente.",
    headers={
      "WWW-Authenticate": 'Bearer error="invalid_token", error_description="token expirado"'
    },
  )
  excepcion_revocado = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="La sesión fue cerrada. Inicia sesión nuevamente.",
    headers={
      "WWW-Authenticate": 'Bearer error="invalid_token", error_description="sesion cerrada"'
    },
  )
  excepcion_version = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="La clave o los permisos del usuario cambiaron. Inicia sesión nuevamente.",
    headers={
      "WWW-Authenticate": 'Bearer error="invalid_token", error_description="token obsoleto"'
    },
  )

  try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    usuario_id = payload.get("sub")
    jti = payload.get("jti")
    ver = payload.get("ver")

    if usuario_id is None or jti is None or ver is None:
      raise excepcion_credenciales

    usuario = session.get(Usuarios, int(usuario_id))

  except ExpiredSignatureError:
    raise excepcion_expirado
  except (InvalidTokenError, TypeError, ValueError):
    raise excepcion_credenciales

  if usuario is None or usuario.fecha_eliminacion is not None:
    raise excepcion_credenciales

  if ver != usuario.version_tokens:
    raise excepcion_version

  if exigir_no_revocado and esta_revocado(session, jti):
    raise excepcion_revocado

  return usuario, payload


def obtener_usuario_actual(
  token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
) -> Usuarios:
  """Devuelve el usuario autenticado a partir del token."""
  usuario, _ = validar_token(token, session)
  return usuario


def obtener_sesion_actual(
  token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
) -> tuple[Usuarios, dict]:
  """Igual que obtener_usuario_actual pero permite logout idempotente."""

  return validar_token(token, session, exigir_no_revocado=False)


def requerir_roles(*roles: RolesUsuario):
  """Devuelve una dependencia que exige uno de los roles indicados."""
  def dependencia(
    usuario_actual: Usuarios = Depends(obtener_usuario_actual),
  ) -> Usuarios:
    """Comprueba el rol del usuario antes de continuar."""
    if usuario_actual.rol not in roles:
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos para realizar esta acción",
      )

    return usuario_actual

  return dependencia


def nivel_efectivo(usuario: Usuarios) -> NivelEducativo | None:
  """Devuelve el nivel de filtro del usuario; None para el administrador."""
  if usuario.rol == RolesUsuario.administrador:
    return None

  return usuario.nivel


def resolver_nivel(
  usuario: Usuarios, nivel_solicitado: NivelEducativo | None
) -> NivelEducativo | None:
  """Devuelve el nivel solicitado por el administrador o el propio del operador."""
  if usuario.rol == RolesUsuario.administrador:
    return nivel_solicitado

  if usuario.nivel is None:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="La cuenta no tiene un nivel educativo asignado",
    )

  if nivel_solicitado is not None:
    validar_acceso_nivel(usuario, nivel_solicitado)

  return usuario.nivel


def requerir_admin(
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
) -> Usuarios:
  """Exige que el usuario autenticado sea administrador."""
  if usuario_actual.rol != RolesUsuario.administrador:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Solo el administrador puede realizar esta acción",
    )

  return usuario_actual


def requerir_operador(
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
) -> Usuarios:
  """Exige un operador con nivel educativo asignado."""
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


def validar_acceso_nivel(usuario: Usuarios, nivel: NivelEducativo | None) -> None:
  """Comprueba que el usuario pueda acceder al nivel indicado."""
  if usuario.rol == RolesUsuario.administrador:
    return

  if nivel is None or usuario.nivel != nivel:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="No tienes acceso a registros de otro nivel educativo",
    )

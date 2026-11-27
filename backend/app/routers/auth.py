from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.models.db import Usuarios
from app.models.enums import ModuloAuditoria
from app.models.schemas import PeticionUsuario
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.limite_login import (
  ip_cliente,
  registrar_exito,
  registrar_fallo,
  verificar_limite,
)
from app.utils.security import (
  crear_token_acceso,
  obtener_hash_clave,
  obtener_sesion_actual,
  obtener_usuario_actual,
  verificar_clave,
)
from app.utils.tokens_revocados import limpiar_si_toca, revocar_token

router = APIRouter(prefix="/auth", tags=["Validaciones"])


# Se verifica contra este hash cuando el usuario no existe, para que
# "usuario inexistente" y "clave incorrecta" tarden lo mismo y no filtren
# qué cuentas están registradas.
_CLAVE_FANTASMA = "usuario-inexistente-no-usar-1234"
_HASH_FANTASMA: str | None = None


def _hash_para_usuario_inexistente() -> str:
  global _HASH_FANTASMA
  if _HASH_FANTASMA is None:
    _HASH_FANTASMA = obtener_hash_clave(_CLAVE_FANTASMA)
  return _HASH_FANTASMA


# Endpoint para iniciar sesión
@router.post("/login")
def iniciar_sesion(
  request: Request,
  form_data: OAuth2PasswordRequestForm = Depends(),
  session: Session = Depends(get_session),
):
  ip = ip_cliente(request)
  usuario = form_data.username

  verificar_limite(ip, usuario)
  limpiar_si_toca(session)

  statement = select(Usuarios).where(Usuarios.nombre == usuario)
  usuario_db = session.exec(statement).first()

  hash_comparar = (
    usuario_db.clave
    if usuario_db is not None
    else _hash_para_usuario_inexistente()
  )

  if (
    usuario_db is None
    or usuario_db.fecha_eliminacion is not None
    or not verificar_clave(form_data.password, hash_comparar)
  ):
    registrar_fallo(ip, usuario)
    # Guarda el DELETE perezoso de la limpieza aunque no haya auditoría.
    session.commit()
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Usuario o contraseña incorrectos",
      headers={"WWW-Authenticate": "Bearer"},
    )

  datos_token = {
    "sub": str(usuario_db.id),
    "rol": usuario_db.rol.value,
    "nivel": usuario_db.nivel.value if usuario_db.nivel else None,
  }

  token_jwt = crear_token_acceso(datos_token, usuario_db.version_tokens)

  registrar_auditoria(
    session,
    usuario_db.id,
    ModuloAuditoria.usuarios,
    "INICIO DE SESIÓN",
    f"Inicio de sesión del usuario '{usuario_db.nombre}'.",
  )
  registrar_exito(ip, usuario)
  session.commit()

  return {"access_token": token_jwt, "token_type": "bearer"}


@router.get("/me", response_model=PeticionUsuario)
def perfil_usuario_actual(usuario_actual: Usuarios = Depends(obtener_usuario_actual)):
  return usuario_actual


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def cerrar_sesion(
  session: Session = Depends(get_session),
  sesion: tuple[Usuarios, dict] = Depends(obtener_sesion_actual),
):
  """Registra el cierre y revoca el JWT usado en la petición.

  La revocación es por `jti`: otros tokens del mismo usuario siguen válidos.
  """

  usuario_actual, payload = sesion

  limpiar_si_toca(session)

  revocar_token(
    session,
    jti=payload["jti"],
    usuario_id=usuario_actual.id,
    exp=payload["exp"],
    motivo="CIERRE DE SESIÓN",
  )

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.usuarios,
    "CIERRE DE SESIÓN",
    f"Cierre de sesión del usuario '{usuario_actual.nombre}'.",
  )
  session.commit()

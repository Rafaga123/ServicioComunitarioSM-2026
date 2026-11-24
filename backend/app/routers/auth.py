from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.models.db import Usuarios
from app.models.enums import ModuloAuditoria
from app.models.schemas import PeticionUsuario
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.security import (
  crear_token_acceso,
  obtener_usuario_actual,
  verificar_clave,
)

router = APIRouter(prefix="/auth", tags=["Validaciones"])


# Endpoint para iniciar sesión
@router.post("/login")
def iniciar_sesion(
  form_data: OAuth2PasswordRequestForm = Depends(),
  session: Session = Depends(get_session),
):
  statement = select(Usuarios).where(Usuarios.nombre == form_data.username)
  usuario_db = session.exec(statement).first()

  if (
    not usuario_db
    or usuario_db.fecha_eliminacion is not None
    or not verificar_clave(form_data.password, usuario_db.clave)
  ):
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

  token_jwt = crear_token_acceso(datos_token)

  registrar_auditoria(
    session,
    usuario_db.id,
    ModuloAuditoria.usuarios,
    "LOGIN",
    f"Inicio de sesión del usuario '{usuario_db.nombre}'.",
  )
  session.commit()

  return {"access_token": token_jwt, "token_type": "bearer"}


@router.get("/me", response_model=PeticionUsuario)
def perfil_usuario_actual(usuario_actual: Usuarios = Depends(obtener_usuario_actual)):
  return usuario_actual

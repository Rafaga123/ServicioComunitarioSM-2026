from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.models.db import Usuarios
from app.models.schemas import CrearUsuario, PeticionUsuario
from app.models.session import get_session
from app.utils.security import (
  crear_token_acceso,
  obtener_hash_clave,
  obtener_usuario_actual,
  verificar_clave,
)

router = APIRouter(prefix="/auth", tags=["Validaciones"])


# Endpoint para registros de usuarios
@router.post(
  "/registro", response_model=PeticionUsuario, status_code=status.HTTP_201_CREATED
)
def registrar_usuario(
  usuario_in: CrearUsuario, session: Session = Depends(get_session)
):
  # Verificar si el usuario ya existe
  statement = select(Usuarios).where(Usuarios.nombre == usuario_in.nombre)

  usuario_existe = session.exec(statement).first()

  # En caso de existencia del usuario se devuelve una excepción
  if usuario_existe:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Usuario ya existente en la Base de Datos",
    )

  # Se hashea la contraseña enviada por el usuario
  hash_clave = obtener_hash_clave(usuario_in.clave)

  nuevo_usuario = Usuarios(
    nombre=usuario_in.nombre, clave=hash_clave, rol=usuario_in.rol
  )

  # Insertar nuevo usuario a la Base de Datos
  session.add(nuevo_usuario)

  session.commit()  # Confirmar la consulta

  # Refrescar al usuario nuevo extrayendolo de la Base de Datos
  session.refresh(nuevo_usuario)

  # Retornar el Usuario en base al esquema realizado en schemas.py
  return nuevo_usuario


# Endpoint para iniciar sesión
@router.post("/login")
def iniciar_sesion(
  form_data: OAuth2PasswordRequestForm = Depends(),
  session: Session = Depends(get_session),
):
  statement = select(Usuarios).where(Usuarios.nombre == form_data.username)
  usuario_db = session.exec(statement).first()

  if not usuario_db or not verificar_clave(form_data.password, usuario_db.clave):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Usuario o contraseña incorrectos",
      headers={"WWW-Authenticate": "Bearer"},
    )

  datos_token = {"sub": str(usuario_db.id), "rol": usuario_db.rol.value}

  token_jwt = crear_token_acceso(datos_token)

  return {"access_token": token_jwt, "token_type": "bearer"}


@router.get("/me", response_model=PeticionUsuario)
def perfil_usuario_actual(usuario_actual: Usuarios = Depends(obtener_usuario_actual)):
  return usuario_actual

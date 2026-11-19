from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  filtro_activos,
  paginar,
)
from app.models.db import Usuarios
from app.models.enums import ModuloAuditoria, RolesUsuario
from app.models.schemas import (
  ActualizarUsuario,
  CambiarClave,
  CrearUsuario,
  PeticionUsuario,
)
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.security import (
  obtener_hash_clave,
  obtener_usuario_actual,
  requerir_roles,
  verificar_clave,
)
from app.utils.soft_delete import marcar_eliminado

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
requerir_admin = requerir_roles(RolesUsuario.administrador)


def _obtener_usuario_activo(session: Session, usuario_id: int) -> Usuarios:
  usuario = session.get(Usuarios, usuario_id)

  if not usuario or usuario.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
    )

  return usuario


@router.get("/", response_model=RespuestaPaginada[PeticionUsuario])
def listar_usuarios(
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  consulta = filtro_activos(select(Usuarios), Usuarios)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(items, total, paginacion)


@router.post(
  "/", response_model=PeticionUsuario, status_code=status.HTTP_201_CREATED
)
def registrar_usuario(
  usuario_in: CrearUsuario,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  statement = select(Usuarios).where(Usuarios.nombre == usuario_in.nombre)

  if session.exec(statement).first():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Ya existe un usuario con ese nombre",
    )

  nuevo_usuario = Usuarios(
    nombre=usuario_in.nombre,
    clave=obtener_hash_clave(usuario_in.clave),
    rol=RolesUsuario(usuario_in.rol.value),
  )

  session.add(nuevo_usuario)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.usuarios,
    "CREAR",
    (
      f"Se creó la cuenta del usuario '{nuevo_usuario.nombre}' "
      f"con el rol {nuevo_usuario.rol.value}."
    ),
  )

  session.commit()
  session.refresh(nuevo_usuario)

  return nuevo_usuario


@router.put("/me/clave", status_code=status.HTTP_204_NO_CONTENT)
def cambiar_clave(
  clave_in: CambiarClave,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
) -> None:
  if not verificar_clave(clave_in.clave_actual, usuario_actual.clave):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="La clave actual no es correcta",
    )

  usuario_actual.clave = obtener_hash_clave(clave_in.clave_nueva)

  session.add(usuario_actual)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.usuarios,
    "CAMBIAR_CLAVE",
    f"El usuario '{usuario_actual.nombre}' cambió su clave.",
  )

  session.commit()


@router.get("/{usuario_id}", response_model=PeticionUsuario)
def obtener_usuario(
  usuario_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  return _obtener_usuario_activo(session, usuario_id)


@router.put("/{usuario_id}", response_model=PeticionUsuario)
def actualizar_usuario(
  usuario_id: int,
  usuario_in: ActualizarUsuario,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  usuario_db = _obtener_usuario_activo(session, usuario_id)

  if usuario_db.rol == RolesUsuario.administrador:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=(
        "El administrador se gestiona mediante la transferencia de rol"
      ),
    )

  datos_actualizar = usuario_in.model_dump(exclude_unset=True, exclude_none=True)

  if "rol" in datos_actualizar:
    datos_actualizar["rol"] = RolesUsuario(datos_actualizar["rol"].value)

  if (
    "nombre" in datos_actualizar
    and datos_actualizar["nombre"] != usuario_db.nombre
  ):
    statement = select(Usuarios).where(
      Usuarios.nombre == datos_actualizar["nombre"],
      Usuarios.id != usuario_id,
    )

    if session.exec(statement).first():
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Ya existe un usuario con ese nombre",
      )

  cambios = {
    campo: valor
    for campo, valor in datos_actualizar.items()
    if getattr(usuario_db, campo) != valor
  }

  if not cambios:
    return usuario_db

  for campo, valor in cambios.items():
    setattr(usuario_db, campo, valor)

  session.add(usuario_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.usuarios,
    "ACTUALIZAR",
    (
      f"Se actualizaron los datos del usuario '{usuario_db.nombre}' "
      f"con el rol {usuario_db.rol.value}."
    ),
  )

  session.commit()
  session.refresh(usuario_db)

  return usuario_db


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(
  usuario_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  usuario_db = _obtener_usuario_activo(session, usuario_id)

  if usuario_db.rol == RolesUsuario.administrador:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=(
        "El administrador no puede darse de baja; "
        "transfiere el rol primero"
      ),
    )

  marcar_eliminado(session, usuario_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.usuarios,
    "ELIMINAR",
    f"Se dio de baja al usuario '{usuario_db.nombre}'.",
  )

  session.commit()


@router.post("/{usuario_id}/transferir-admin", response_model=PeticionUsuario)
def transferir_admin(
  usuario_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  nuevo_admin = _obtener_usuario_activo(session, usuario_id)

  if nuevo_admin.rol == RolesUsuario.administrador:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El usuario ya es administrador",
    )

  nuevo_admin.rol = RolesUsuario.administrador

  session.add(nuevo_admin)
  marcar_eliminado(session, usuario_actual)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.usuarios,
    "TRANSFERIR_ADMIN",
    (
      f"El administrador '{usuario_actual.nombre}' transfirió el rol "
      f"a '{nuevo_admin.nombre}'."
    ),
  )

  session.commit()
  session.refresh(nuevo_admin)

  return nuevo_admin

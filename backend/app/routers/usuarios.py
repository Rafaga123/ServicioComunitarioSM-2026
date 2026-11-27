"""Gestiona cuentas, claves, roles y revocación de sesiones."""

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
from app.models.enums import (
  ModuloAuditoria,
  NivelEducativo,
  RolesAsignables,
  RolesUsuario,
)
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
  resolver_nivel,
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


def _validar_combinacion_rol_nivel(
  rol: RolesAsignables | RolesUsuario | None,
  nivel: NivelEducativo | None,
) -> None:
  if rol is None:
    return

  if rol in (RolesUsuario.coordinador, RolesUsuario.secretaria) and nivel is None:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Los roles de coordinador y secretaria requieren un nivel educativo",
    )


@router.get("/", response_model=RespuestaPaginada[PeticionUsuario])
def listar_usuarios(
  paginacion: Paginacion = Depends(),
  nivel: NivelEducativo | None = None,
  rol: RolesUsuario | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  """Devuelve una página de usuarios activos."""
  consulta = filtro_activos(select(Usuarios), Usuarios)

  nivel = resolver_nivel(usuario_actual, nivel)
  if nivel is not None:
    consulta = consulta.where(Usuarios.nivel == nivel)
  if rol is not None:
    consulta = consulta.where(Usuarios.rol == rol)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(items, total, paginacion)


@router.post("/", response_model=PeticionUsuario, status_code=status.HTTP_201_CREATED)
def registrar_usuario(
  usuario_in: CrearUsuario,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  """Registra una cuenta de usuario."""
  statement = select(Usuarios).where(Usuarios.nombre == usuario_in.nombre)

  if session.exec(statement).first():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Ya existe un usuario con ese nombre",
    )

  _validar_combinacion_rol_nivel(usuario_in.rol, usuario_in.nivel)

  nuevo_usuario = Usuarios(
    nombre=usuario_in.nombre,
    clave=obtener_hash_clave(usuario_in.clave),
    rol=RolesUsuario(usuario_in.rol.value),
    nivel=usuario_in.nivel,
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
  """Cambia la clave del usuario autenticado y cierra sus sesiones."""
  if not verificar_clave(clave_in.clave_actual, usuario_actual.clave):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="La clave actual no es correcta",
    )

  usuario_actual.clave = obtener_hash_clave(clave_in.clave_nueva)
  # La sesión usada para cambiar la clave también queda revocada.
  usuario_actual.version_tokens += 1

  session.add(usuario_actual)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.usuarios,
    "CAMBIAR CLAVE",
    f"El usuario '{usuario_actual.nombre}' cambió su clave.",
  )

  session.commit()


@router.get("/{usuario_id}", response_model=PeticionUsuario)
def obtener_usuario(
  usuario_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  """Devuelve un usuario activo por su identificador."""
  return _obtener_usuario_activo(session, usuario_id)


@router.put("/{usuario_id}", response_model=PeticionUsuario)
def actualizar_usuario(
  usuario_id: int,
  usuario_in: ActualizarUsuario,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  """Actualiza un usuario y revoca sus sesiones si cambia la autenticación."""
  usuario_db = _obtener_usuario_activo(session, usuario_id)

  if usuario_db.rol == RolesUsuario.administrador:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=("El administrador se gestiona mediante la transferencia de rol"),
    )

  datos_actualizar = usuario_in.model_dump(exclude_unset=True, exclude_none=True)

  # La clave se hashea y se trata aparte: nunca se asigna tal cual como
  # los demás campos con el bucle genérico de setattr.
  clave_nueva = datos_actualizar.pop("clave", None)

  _validar_combinacion_rol_nivel(
    datos_actualizar.get("rol", usuario_db.rol),
    datos_actualizar.get("nivel", usuario_db.nivel),
  )

  if "rol" in datos_actualizar:
    datos_actualizar["rol"] = RolesUsuario(datos_actualizar["rol"].value)

  if "nombre" in datos_actualizar and datos_actualizar["nombre"] != usuario_db.nombre:
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

  # Reset de clave por el admin: se hashea y se trata aparte del bucle genérico.
  if clave_nueva is not None:
    cambios["clave"] = obtener_hash_clave(clave_nueva)

  # Clave, rol y nivel afectan a la autenticación: sube la versión y revoca
  # TODAS las sesiones abiertas del usuario. El nombre solo cambia la etiqueta
  # visible y no cierra sesiones.
  if any(campo in cambios for campo in ("clave", "rol", "nivel")):
    cambios["version_tokens"] = usuario_db.version_tokens + 1

  if not cambios:
    return usuario_db

  for campo, valor in cambios.items():
    setattr(usuario_db, campo, valor)

  session.add(usuario_db)
  session.flush()

  descripcion = (
    f"Se actualizaron los datos del usuario '{usuario_db.nombre}' "
    f"con el rol {usuario_db.rol.value}."
  )
  if clave_nueva is not None:
    descripcion += " Se restableció su clave y se cerraron sus sesiones."
  elif "version_tokens" in cambios:
    descripcion += " Se cerraron sus sesiones por el cambio de rol o nivel."

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.usuarios,
    "ACTUALIZAR",
    descripcion,
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
  """Da de baja un usuario y revoca sus sesiones."""
  usuario_db = _obtener_usuario_activo(session, usuario_id)

  if usuario_db.rol == RolesUsuario.administrador:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=("El administrador no puede darse de baja; transfiere el rol primero"),
    )

  marcar_eliminado(session, usuario_db)
  # La baja ya bloqueaba en validar_token; el +1 la hace explícita e
  # irreversible aunque luego se reactive la cuenta.
  usuario_db.version_tokens += 1
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
  """Transfiere el rol de administrador a otro usuario."""
  nuevo_admin = _obtener_usuario_activo(session, usuario_id)

  if nuevo_admin.rol == RolesUsuario.administrador:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El usuario ya es administrador",
    )

  nuevo_admin.rol = RolesUsuario.administrador
  nuevo_admin.nivel = None

  # Cambió el privilegio: nadie debe seguir operando con el token que
  # decía el rol anterior. Aplica al entrante y al saliente.
  nuevo_admin.version_tokens += 1
  usuario_actual.version_tokens += 1

  session.add(nuevo_admin)
  marcar_eliminado(session, usuario_actual)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.usuarios,
    "TRANSFERIR ADMIN",
    (
      f"El administrador '{usuario_actual.nombre}' transfirió el rol "
      f"a '{nuevo_admin.nombre}'."
    ),
  )

  session.commit()
  session.refresh(nuevo_admin)

  return nuevo_admin

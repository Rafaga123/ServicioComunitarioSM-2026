#imports
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, col, select

#imports de la app
from app.models.db import Auditorias, Usuarios
from app.models.enums import RolesUsuario
from app.models.schemas import PeticionAuditoria
from app.models.session import get_session
from app.utils.security import obtener_usuario_actual

router = APIRouter(prefix="/auditorias", tags=["Auditorías"])


# Funcion para listar las auditorias
@router.get("/", response_model=list[PeticionAuditoria])
def listar_auditorias(
  usuario: str | None = None,
  modulo: str | None = None,
  accion: str | None = None,
  fecha: date | None = None,
  offset: int = 0,
  limit: int = 20,
  sesion: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):

  """
  Este apartado es opcional, en dado caso se puede obviar la restricción a solo
  administradores o coordinadores, o en dado caso, se pudiera quitar esta parte
  """
  if usuario_actual.rol == RolesUsuario.secretaria:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="No tienes permisos para consultar las auditorias",
    )
 
  # ====
  # Consulta el historial de auditorias del sistema con soporte de paginación 
  # Se hace un inner join para evitar consultas adicionales desde el frontend
  # ====
  consulta = select(Auditorias, Usuarios.nombre).join(
    Usuarios, col(Auditorias.usuario_id) == col(Usuarios.id),)
 
  
  if usuario is not None:
    consulta = consulta.where(col(Usuarios.nombre).ilike(f"%{usuario}%"))
  if modulo is not None:
    consulta = consulta.where(col(Auditorias.modulo).ilike(f"%{modulo}%"))
  if accion is not None:
    consulta = consulta.where(col(Auditorias.accion).ilike(f"%{accion}%"))
  if fecha is not None:
    consulta = consulta.where(func.date(Auditorias.fecha_creacion) == fecha)
    
    
  #ordenamos de mayor a menor (la mas reciente, a la mas antigua)
  consulta = (
    consulta.order_by(col(Auditorias.fecha_creacion).desc())
    .offset(offset)
    .limit(limit)
  )
  
  # retornamos todas las auditorias
  return [
    PeticionAuditoria(**auditoria.model_dump(), usuario=nombre_usuario)
    for auditoria, nombre_usuario in sesion.exec(consulta).all()
  ]



# Funcion para obtener una auditoria en especifico por su id
@router.get("/{auditoria_id}", response_model=PeticionAuditoria)
def obtener_auditoria(
  auditoria_id: int,
  sesion: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual)
):

  if usuario_actual.rol == RolesUsuario.secretaria:
    raise HTTPException(
      status_code = status.HTTP_403_FORBIDDEN,
      detail="No tienes permisos para consultar las auditorias.",
    )
  
    
  auditoria = sesion.get(Auditorias, auditoria_id)
  
  
  if not auditoria:
    raise HTTPException(
      status_code = status.HTTP_404_NOT_FOUND,
      detail="Registro de auditoria no encontrado"
    )
  
  usuario = sesion.get(Usuarios, auditoria.usuario_id)
  
  
  if not usuario:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Usuario asociado a la auditoría no encontrado",
    )
  
  return PeticionAuditoria(
    **auditoria.model_dump(),
    usuario=usuario.nombre,
  )

#imports
from fastapi import APIRouter, Depends, HTTPException, status
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
  usuario_id: int | None = None,
  modulo_afectado: str | None = None,
  accion: str | None = None,
  offset: int = 0,
  limit: int = 20,
  session: Session = Depends(get_session),
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
 
  statement = select(Auditorias)
  
  if usuario_id is not None:
    statement = statement.where(Auditorias.usuario_id == usuario_id)
  if modulo_afectado is not None:
    statement = statement.where(col(Auditorias.modulo_afectado).ilike(f"%{modulo_afectado}%"))
  if accion is not None:
    statement = statement.where(col(Auditorias.accion).ilike(f"%{accion}%"))
    
  #ordenamos de mayor a menor (la mas reciente, a la mas antigua)
  statement = (
    statement.order_by(col(Auditorias.fecha_creacion).desc())
    .offset(offset)
    .limit(limit)
  )
  
  #retornamos todas las auditorias
  return session.exec(statement).all()


# Funcion para obtener una auditoria en especifico por su id
@router.get("/{auditoria_id}", response_model=PeticionAuditoria)
def obtener_auditoria(
  auditoria_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual)
):

  if usuario_actual.rol == RolesUsuario.secretaria:
    raise HTTPException(
      status_code = status.HTTP_403_FORBIDDEN,
      detail="No tienes permisos para consultar las auditorias.",
    )
  auditoria = session.get(Auditorias, auditoria_id)
  if not auditoria:
    raise HTTPException(
      status_code = status.HTTP_404_NOT_FOUND,
      detail="Registro de auditoria no encontrado"
    )
    
  return auditoria

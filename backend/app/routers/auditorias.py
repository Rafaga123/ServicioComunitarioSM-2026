"""Consulta el historial de auditorías del sistema."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  paginar,
)
from app.models.db import Auditorias, Usuarios
from app.models.enums import RolesUsuario
from app.models.schemas import PeticionAuditoria
from app.models.session import get_session
from app.utils.security import requerir_roles

router = APIRouter(prefix="/auditorias", tags=["Auditorías"])


@router.get("/", response_model=RespuestaPaginada[PeticionAuditoria])
def listar_auditorias(
  usuario: str | None = None,
  modulo: str | None = None,
  accion: str | None = None,
  fecha: date | None = None,
  paginacion: Paginacion = Depends(),
  sesion: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_roles(RolesUsuario.administrador)),
):
  # El join evita una consulta adicional por fila desde el frontend.
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

  consulta = consulta.order_by(col(Auditorias.fecha_creacion).desc())

  filas, total = paginar(sesion, consulta, paginacion)

  items = [
    PeticionAuditoria(**auditoria.model_dump(), usuario=nombre_usuario)
    for auditoria, nombre_usuario in filas
  ]

  return construir_pagina(items, total, paginacion)


@router.get("/{auditoria_id}", response_model=PeticionAuditoria)
def obtener_auditoria(
  auditoria_id: int,
  sesion: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_roles(RolesUsuario.administrador)),
):
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

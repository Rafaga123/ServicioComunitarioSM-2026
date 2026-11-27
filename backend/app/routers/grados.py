"""Expone el catálogo de grados como solo lectura."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  filtro_activos,
  paginar,
)
from app.models.db import Grados, Usuarios
from app.models.enums import NivelEducativo
from app.models.schemas import PeticionGrado
from app.models.session import get_session
from app.utils.security import (
  obtener_usuario_actual,
  resolver_nivel,
  validar_acceso_nivel,
)

router = APIRouter(prefix="/grados", tags=["Grados"])


def _obtener_grado_activo(session: Session, grado_id: int) -> Grados:
  grado = session.get(Grados, grado_id)

  if not grado or grado.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Grado no encontrado"
    )

  return grado


@router.get("/", response_model=RespuestaPaginada[PeticionGrado])
def listar_grados(
  paginacion: Paginacion = Depends(),
  nivel: NivelEducativo | None = None,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  consulta = filtro_activos(select(Grados), Grados)

  nivel = resolver_nivel(usuario_actual, nivel)
  if nivel is not None:
    consulta = consulta.where(Grados.nivel == nivel)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(items, total, paginacion)


@router.get("/{grado_id}", response_model=PeticionGrado)
def obtener_grado(
  grado_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  grado = _obtener_grado_activo(session, grado_id)
  validar_acceso_nivel(usuario_actual, grado.nivel)

  return grado

from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  paginar,
)
from app.models.db import Grados, Usuarios
from app.models.schemas import CrearGrado, PeticionGrado
from app.models.session import get_session
from app.utils.security import obtener_usuario_actual

router = APIRouter(prefix="/grados", tags=["Catálogos: Grados"])


@router.post("/", response_model=PeticionGrado, status_code=status.HTTP_201_CREATED)
def registrar_grado(
  grado_in: CrearGrado,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  nuevo_grado = Grados(grado=grado_in.grado, seccion=grado_in.seccion)
  session.add(nuevo_grado)
  session.commit()
  session.refresh(nuevo_grado)

  return nuevo_grado


@router.get("/", response_model=RespuestaPaginada[PeticionGrado])
def listar_grados(
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  # Traemos todos los grados activos
  consulta = select(Grados).where(Grados.fecha_eliminacion == None)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(items, total, paginacion)

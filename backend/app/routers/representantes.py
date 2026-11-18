from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  paginar,
)
from app.models.db import Estudiantes, Representantes, Usuarios
from app.models.schemas import CrearRepresentante, PeticionRepresentante
from app.models.session import get_session
from app.utils.security import obtener_usuario_actual

router = APIRouter(prefix="/representantes", tags=["Representantes"])


# 1. Crear un Representante (Independiente)
@router.post(
  "/", response_model=PeticionRepresentante, status_code=status.HTTP_201_CREATED
)
def registrar_representante(
  rep_in: CrearRepresentante,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  nuevo_rep = Representantes(
    nombre=rep_in.nombre, apellido=rep_in.apellido, telefono=rep_in.telefono
  )
  session.add(nuevo_rep)
  session.commit()
  session.refresh(nuevo_rep)
  return nuevo_rep


# 2. Listar Representantes
@router.get("/", response_model=RespuestaPaginada[PeticionRepresentante])
def listar_representantes(
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  # Traemos solo los que no están eliminados lógicamente
  consulta = select(Representantes).where(Representantes.fecha_eliminacion == None)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(items, total, paginacion)


# 3. EL ENDPOINT MÁGICO: Vincular Representante con Estudiante
@router.post(
  "/{representante_id}/vincular_estudiante/{estudiante_id}",
  status_code=status.HTTP_200_OK,
)
def vincular_estudiante_representante(
  representante_id: int,
  estudiante_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  # Buscamos a ambos en la base de datos
  representante = session.get(Representantes, representante_id)
  estudiante = session.get(Estudiantes, estudiante_id)

  # Validamos que ambos existan y no estén eliminados
  if not representante or representante.fecha_eliminacion:
    raise HTTPException(status_code=404, detail="Representante no encontrado")
  if not estudiante or estudiante.fecha_eliminacion:
    raise HTTPException(status_code=404, detail="Estudiante no encontrado")

  # Verificamos si ya están vinculados para no duplicar datos
  if representante in estudiante.representantes:
    raise HTTPException(
      status_code=400, detail="El representante ya está vinculado a este estudiante"
    )

  # SQLModel hace la magia relacional aquí:
  estudiante.representantes.append(representante)

  session.add(estudiante)
  session.commit()

  return {
    "mensaje": f"Representante {representante.nombre} vinculado exitosamente al estudiante {estudiante.primer_nombre}"
  }

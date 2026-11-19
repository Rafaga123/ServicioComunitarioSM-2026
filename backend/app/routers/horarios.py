from datetime import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.models.db import Estudiantes, Horarios
from app.models.schemas import PeticionBloque
from app.models.session import get_session

router = APIRouter(prefix="/horarios", tags=["Horarios"])

@router.get("/", response_model=PeticionBloque, status_code=status.HTTP_200_OK)
def solicitar_asignatura(
    id_estudiante: int,
    dia_semana: int,
    hora: time,
    session: Session = Depends(get_session)
):
    estudiante = session.get(Estudiantes, id_estudiante)
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    statement_horario = select(Horarios).where(
        Horarios.id_grado == estudiante.grado_id,
        Horarios.hora == hora,
        Horarios.dia_semana == dia_semana,
    )

    horario = session.exec(statement_horario).first()
    if not horario:
        raise HTTPException(status_code=404, detail="No hay asignatura asignada en este horario para el grado ingresado.")

    return PeticionBloque(
        id=horario.id,
        asignatura=horario.asignatura.nombre,
        docente=horario.docente.nombre
    )
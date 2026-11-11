from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.db import Estudiantes, Usuarios
from app.models.schemas import ActualizarEstudiante, CrearEstudiante, PeticionEstudiante
from app.models.session import get_session
from app.utils.security import obtener_usuario_actual

router = APIRouter(prefix="/estudiantes", tags=["Estudiantes"])


# Registrar a un Estudiante nuevo
@router.post(
  "/", response_model=PeticionEstudiante, status_code=status.HTTP_201_CREATED
)
def registrar_estudiante(
  estudiante_in: CrearEstudiante,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  statement = select(Estudiantes).where(
    Estudiantes.cedula_estudiantil == estudiante_in.cedula_estudiantil
  )

  if session.exec(statement).first():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Ya existe un estudiante con está cédula",
    )

  nuevo_estudiante = Estudiantes(
    grado_id=estudiante_in.grado_id,
    cedula_estudiantil=estudiante_in.cedula_estudiantil,
    primer_nombre=estudiante_in.primer_nombre,
    segundo_nombre=estudiante_in.segundo_nombre,
    primer_apellido=estudiante_in.primer_apellido,
    segundo_apellido=estudiante_in.segundo_apellido,
    fecha_nacimiento=estudiante_in.fecha_nacimiento,
  )

  session.add(nuevo_estudiante)
  session.commit()
  session.refresh(nuevo_estudiante)

  return nuevo_estudiante


# Pedir un listado de Estudiantes
@router.get("/", response_model=list[PeticionEstudiante])
def listar_estudiantes(
  offset: int = 0,  # Desde qué registro empezar
  limit: int = 15,  # Cuántos registros traer máximo
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  statement = (
    select(Estudiantes)
    .where(  # Solo traer los registros de estudiantes que no esten eliminados
      Estudiantes.fecha_eliminacion == None
    )
    .offset(offset)
    .limit(limit)
  )

  estudiantes_db = session.exec(statement).all()

  return estudiantes_db


# Buscar Estudiantes listado
@router.get("/buscar/", response_model=list[PeticionEstudiante])
def buscar_estudiantes(
  termino: str,  # Lo que el usuario escribe en el buscador (cédula, nombre, etc.)
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  termino_limpio = f"%{termino}"

  statement = (
    select(Estudiantes)
    .where(
      (Estudiantes.fecha_eliminacion == None)
      & (
        (Estudiantes.cedula_estudiantil.contains(termino))
        | (
          func.unaccent(Estudiantes.primer_nombre.ilike(func.unaccent(termino_limpio)))
        )
        | (
          func.unaccent(
            Estudiantes.primer_apellido.ilike(func.unaccent(termino_limpio))
          )
        )
      )
    )
    .limit(10)
  )  # Limitamos a 10 para respuestas ultrarrápidas

  resultados = session.exec(statement).all()

  return resultados


# Solicitar a un Estudiante especifico por ID
@router.get("/{estudiante_id}", response_model=PeticionEstudiante)
def obtener_estudiante(
  estudiante_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  # session.get es la forma más rápida de buscar por Primary Key (ID)
  estudiante = session.get(Estudiantes, estudiante_id)

  # Verificamos que exista y que no esté eliminado lógicamente
  if not estudiante or estudiante.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Estudiante no encontrado"
    )

  return estudiante


# Actualizar a un Estudiante
@router.put("/{estudiante_id}", response_model=PeticionEstudiante)
def actualizar_estudiante(
  estudiante_id: int,
  estudiante_in: ActualizarEstudiante,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  estudiante_db = session.get(Estudiantes, estudiante_id)

  if not estudiante_db or estudiante_db.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Estudiante no encontrado"
    )

  # Si se intenta cambiar la cédula, verificamos que no choque con otro estudiante
  if (
    estudiante_in.cedula_estudiantil
    and estudiante_in.cedula_estudiantil != estudiante_db.cedula_estudiantil
  ):
    statement = select(Estudiantes).where(
      Estudiantes.cedula_estudiantil == estudiante_in.cedula_estudiantil
    )
    if session.exec(statement).first():
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="La nueva cédula ya está registrada en otro estudiante",
      )

  # Extraemos solo los campos que el frontend realmente envió (ignora los nulos)
  datos_actualizar = estudiante_in.model_dump(exclude_unset=True)

  # Aplicamos los cambios al objeto de la base de datos
  for key, value in datos_actualizar.items():
    setattr(estudiante_db, key, value)

  session.add(estudiante_db)
  session.commit()
  session.refresh(estudiante_db)

  return estudiante_db


# "Eliminar" a un Estudiante por ID (Soft Delete aplicado)
@router.delete("/{estudiante_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_estudiante(
  estudiante_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
) -> None:
  estudiante_db = session.get(Estudiantes, estudiante_id)

  if not estudiante_db or estudiante_db.fecha_eliminacion is not None:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND, detail="Estudiante no encontrado"
    )

  # SOFT DELETE: No borramos la fila, solo le ponemos fecha de eliminación.
  # Así preservamos el historial para auditorías y reportes antiguos.
  estudiante_db.fecha_eliminacion = datetime.now(UTC)

  session.add(estudiante_db)
  session.commit()

  # Un status 204 significa que la operación fue un éxito pero no hay contenido que devolver
  return None

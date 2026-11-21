from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.paginacion import (
  Paginacion,
  RespuestaPaginada,
  construir_pagina,
  filtro_activos,
  paginar,
)
from app.models.db import (
  Asignaturas,
  Docentes,
  Estudiantes,
  Grados,
  Horarios,
  Usuarios,
)
from app.models.enums import ModuloAuditoria, RolesUsuario
from app.models.schemas import (
  ActualizarHorario,
  CrearHorario,
  PeticionBloque,
  PeticionHorario,
)
from app.models.session import get_session
from app.utils.auditoria import registrar_auditoria
from app.utils.nombres import nombre_completo
from app.utils.security import obtener_usuario_actual, requerir_roles
from app.utils.soft_delete import marcar_eliminado

router = APIRouter(prefix="/horarios", tags=["Horarios"])
requerir_admin = requerir_roles(RolesUsuario.administrador)


def _obtener_registro_activo(session: Session, modelo, registro_id: int, mensaje: str):
  registro = session.get(modelo, registro_id)

  if not registro or registro.fecha_eliminacion is not None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=mensaje)

  return registro


def _validar_referencias(
  session: Session, id_grado: int, id_asignatura: int, id_docente: int
) -> tuple[Grados, Asignaturas, Docentes]:
  grado = _obtener_registro_activo(
    session, Grados, id_grado, "Grado no encontrado"
  )
  asignatura = _obtener_registro_activo(
    session, Asignaturas, id_asignatura, "Asignatura no encontrada"
  )
  docente = _obtener_registro_activo(
    session, Docentes, id_docente, "Docente no encontrado"
  )

  return grado, asignatura, docente


def _validar_solape(
  session: Session,
  id_grado: int,
  periodo_lectivo: int,
  dia_semana: int,
  hora: time,
  excluir_id: int | None = None,
) -> None:
  # La franja se identifica por grado, período, día y hora. Solo se comparan
  # horarios activos para permitir reutilizar una franja después de una baja.
  statement = select(Horarios).where(
    Horarios.id_grado == id_grado,
    Horarios.periodo_lectivo == periodo_lectivo,
    Horarios.dia_semana == dia_semana,
    Horarios.hora == hora,
    Horarios.fecha_eliminacion.is_(None),
  )

  if excluir_id is not None:
    statement = statement.where(Horarios.id != excluir_id)

  if session.exec(statement).first():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=(
        "Ya existe un horario activo para ese grado, período, día y hora"
      ),
    )


def _descripcion_horario(
  horario: Horarios,
  grado: Grados,
  asignatura: Asignaturas,
  docente: Docentes,
) -> str:
  return (
    f"para el grado {grado.grado} \"{grado.seccion}\" "
    f"con la asignatura '{asignatura.nombre}' y el docente "
    f"'{nombre_completo(docente)}', el día {horario.dia_semana} "
    f"a las {horario.hora.strftime('%H:%M')} del período "
    f"{horario.periodo_lectivo}"
  )


def _a_peticion_horario(
  horario: Horarios,
  grado: Grados,
  asignatura: Asignaturas,
  docente: Docentes,
) -> PeticionHorario:
  return PeticionHorario(
    id=horario.id,
    id_grado=horario.id_grado,
    id_asignatura=horario.id_asignatura,
    id_docente=horario.id_docente,
    periodo_lectivo=horario.periodo_lectivo,
    dia_semana=horario.dia_semana,
    hora=horario.hora,
    grado=grado.grado,
    seccion=grado.seccion,
    asignatura=asignatura.nombre,
    docente=nombre_completo(docente),
  )


@router.get("/", response_model=PeticionBloque, status_code=status.HTTP_200_OK)
def solicitar_asignatura(
  id_estudiante: int,
  fecha: date,
  hora: time,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(obtener_usuario_actual),
):
  # La fecha es la fuente única para el día y el período lectivo. Así el
  # frontend no tiene que calcular ni enviar el número de día por separado.
  estudiante = _obtener_registro_activo(
    session, Estudiantes, id_estudiante, "Estudiante no encontrado"
  )

  if estudiante.grado_id is None:
    return PeticionBloque(encontrado=False)

  dia_semana = fecha.isoweekday()

  # Sábado y domingo no tienen bloques en el horario escolar.
  if dia_semana > 5:
    return PeticionBloque(encontrado=False)

  statement = select(Horarios).where(
    Horarios.id_grado == estudiante.grado_id,
    Horarios.periodo_lectivo == fecha.year,
    Horarios.dia_semana == dia_semana,
    Horarios.hora == hora,
    Horarios.fecha_eliminacion.is_(None),
  )

  horario = session.exec(statement).first()

  if not horario:
    return PeticionBloque(encontrado=False)

  return PeticionBloque(
    encontrado=True,
    id_horario=horario.id,
    id_asignatura=horario.id_asignatura,
    id_docente=horario.id_docente,
    asignatura=horario.asignatura.nombre,
    docente=nombre_completo(horario.docente),
  )


@router.get(
  "/registros/", response_model=RespuestaPaginada[PeticionHorario]
)
def listar_horarios(
  id_grado: int | None = None,
  id_asignatura: int | None = None,
  id_docente: int | None = None,
  periodo_lectivo: int | None = None,
  dia_semana: int | None = None,
  paginacion: Paginacion = Depends(),
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  consulta = filtro_activos(select(Horarios), Horarios)

  if id_grado is not None:
    consulta = consulta.where(Horarios.id_grado == id_grado)
  if id_asignatura is not None:
    consulta = consulta.where(Horarios.id_asignatura == id_asignatura)
  if id_docente is not None:
    consulta = consulta.where(Horarios.id_docente == id_docente)
  if periodo_lectivo is not None:
    consulta = consulta.where(Horarios.periodo_lectivo == periodo_lectivo)
  if dia_semana is not None:
    consulta = consulta.where(Horarios.dia_semana == dia_semana)

  consulta = consulta.order_by(Horarios.dia_semana, Horarios.hora)

  items, total = paginar(session, consulta, paginacion)

  return construir_pagina(
    [
      _a_peticion_horario(
        horario,
        horario.grado,
        horario.asignatura,
        horario.docente,
      )
      for horario in items
    ],
    total,
    paginacion,
  )


@router.get("/registros/{horario_id}", response_model=PeticionHorario)
def obtener_horario(
  horario_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  horario = _obtener_registro_activo(
    session, Horarios, horario_id, "Horario no encontrado"
  )

  return _a_peticion_horario(
    horario, horario.grado, horario.asignatura, horario.docente
  )


@router.post(
  "/registros/",
  response_model=PeticionHorario,
  status_code=status.HTTP_201_CREATED,
)
def registrar_horario(
  horario_in: CrearHorario,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  grado, asignatura, docente = _validar_referencias(
    session,
    horario_in.id_grado,
    horario_in.id_asignatura,
    horario_in.id_docente,
  )

  _validar_solape(
    session,
    horario_in.id_grado,
    horario_in.periodo_lectivo,
    horario_in.dia_semana,
    horario_in.hora,
  )

  nuevo_horario = Horarios(
    id_grado=horario_in.id_grado,
    id_asignatura=horario_in.id_asignatura,
    id_docente=horario_in.id_docente,
    periodo_lectivo=horario_in.periodo_lectivo,
    dia_semana=horario_in.dia_semana,
    hora=horario_in.hora,
  )

  session.add(nuevo_horario)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.horarios,
    "CREAR",
    (
      "Se registró un horario "
      f"{_descripcion_horario(nuevo_horario, grado, asignatura, docente)}."
    ),
  )

  session.commit()
  session.refresh(nuevo_horario)

  return _a_peticion_horario(
    nuevo_horario, grado, asignatura, docente
  )


@router.put("/registros/{horario_id}", response_model=PeticionHorario)
def actualizar_horario(
  horario_id: int,
  horario_in: ActualizarHorario,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
):
  horario_db = _obtener_registro_activo(
    session, Horarios, horario_id, "Horario no encontrado"
  )
  datos_actualizar = horario_in.model_dump(
    exclude_unset=True, exclude_none=True
  )

  if not datos_actualizar:
    return _a_peticion_horario(
      horario_db,
      horario_db.grado,
      horario_db.asignatura,
      horario_db.docente,
    )

  valores_finales = {
    "id_grado": datos_actualizar.get("id_grado", horario_db.id_grado),
    "id_asignatura": datos_actualizar.get(
      "id_asignatura", horario_db.id_asignatura
    ),
    "id_docente": datos_actualizar.get(
      "id_docente", horario_db.id_docente
    ),
    "periodo_lectivo": datos_actualizar.get(
      "periodo_lectivo", horario_db.periodo_lectivo
    ),
    "dia_semana": datos_actualizar.get(
      "dia_semana", horario_db.dia_semana
    ),
    "hora": datos_actualizar.get("hora", horario_db.hora),
  }

  grado, asignatura, docente = _validar_referencias(
    session,
    valores_finales["id_grado"],
    valores_finales["id_asignatura"],
    valores_finales["id_docente"],
  )

  _validar_solape(
    session,
    valores_finales["id_grado"],
    valores_finales["periodo_lectivo"],
    valores_finales["dia_semana"],
    valores_finales["hora"],
    excluir_id=horario_id,
  )

  cambios = {
    campo: valor
    for campo, valor in valores_finales.items()
    if getattr(horario_db, campo) != valor
  }

  if not cambios:
    return _a_peticion_horario(
      horario_db, grado, asignatura, docente
    )

  for campo, valor in cambios.items():
    setattr(horario_db, campo, valor)

  session.add(horario_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.horarios,
    "ACTUALIZAR",
    (
      "Se actualizó el horario "
      f"{_descripcion_horario(horario_db, grado, asignatura, docente)}."
    ),
  )

  session.commit()
  session.refresh(horario_db)

  return _a_peticion_horario(horario_db, grado, asignatura, docente)


@router.delete(
  "/registros/{horario_id}", status_code=status.HTTP_204_NO_CONTENT
)
def eliminar_horario(
  horario_id: int,
  session: Session = Depends(get_session),
  usuario_actual: Usuarios = Depends(requerir_admin),
) -> None:
  horario_db = _obtener_registro_activo(
    session, Horarios, horario_id, "Horario no encontrado"
  )

  descripcion = _descripcion_horario(
    horario_db,
    horario_db.grado,
    horario_db.asignatura,
    horario_db.docente,
  )

  marcar_eliminado(session, horario_db)
  session.flush()

  registrar_auditoria(
    session,
    usuario_actual.id,
    ModuloAuditoria.horarios,
    "ELIMINAR",
    f"Se dio de baja el horario {descripcion}.",
  )

  session.commit()

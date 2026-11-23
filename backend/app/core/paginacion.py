from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlmodel import Session, func, select

T = TypeVar("T")


# Parámetros de paginación que el cliente envía por query string.
# Ejemplo: GET /estudiantes/?offset=0&size=15
class Paginacion(BaseModel):
  # Registro desde el que se empieza a contar (0 = primera página)
  offset: int = Query(0, ge=0)
  # Cantidad máxima de registros a devolver (máximo 100)
  size: int = Query(15, ge=1, le=100)


# Variante usada por los buscadores: conserva el tope de 10 resultados.
class PaginacionBusqueda(Paginacion):
  size: int = Query(10, ge=1, le=100)


# Forma estándar de toda respuesta paginada.
class RespuestaPaginada(BaseModel, Generic[T]):
  # Registros que pertenecen a la página solicitada
  items: list[T]
  # Total de registros que cumplen los filtros, sin aplicar offset/size
  total: int
  # Offset que se aplicó
  offset: int
  # Tamaño de página que se aplicó
  size: int


def filtro_activos(consulta, modelo):
  return consulta.where(modelo.fecha_eliminacion.is_(None))


def filtro_texto(consulta, termino: str, *campos):
  termino = termino.strip()

  if not termino or not campos:
    return consulta

  patron = f"%{termino}%"
  condiciones = [func.unaccent(campo).ilike(func.unaccent(patron)) for campo in campos]

  return consulta.where(or_(*condiciones))


# Ejecuta una consulta paginada y devuelve (items de la página, total de registros).
# La consulta recibida debe incluir sus filtros y su orden, pero NO offset/limit.
def paginar(session: Session, consulta, paginacion: Paginacion) -> tuple[list, int]:
  # Para el conteo se quita el orden: no cambia el total y evita ordenar
  # una subconsulta que solo se usa para contar filas.
  consulta_sin_orden = consulta.order_by(None)
  total = session.exec(
    select(func.count()).select_from(consulta_sin_orden.subquery())
  ).one()

  # La consulta original conserva su orden y se recorta a la página pedida.
  items = session.exec(consulta.offset(paginacion.offset).limit(paginacion.size)).all()
  return list(items), total


# Arma el envelope final combinando los items (ya mapeados al schema de
# respuesta) con el total y los parámetros de paginación utilizados.
def construir_pagina(
  items: list[T], total: int, paginacion: Paginacion
) -> RespuestaPaginada[T]:
  return RespuestaPaginada[T](
    items=items,
    total=total,
    offset=paginacion.offset,
    size=paginacion.size,
  )

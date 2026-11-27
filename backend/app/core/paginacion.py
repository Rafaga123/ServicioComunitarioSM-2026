"""Define el envelope paginado y las utilidades de consulta compartidas por los routers."""

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
  """Parámetros de paginación enviados por el cliente en la query string."""
  offset: int = Query(0, ge=0)
  # Cantidad máxima de registros a devolver (máximo 100)
  size: int = Query(15, ge=1, le=100)


# Variante usada por los buscadores: conserva el tope de 10 resultados.
class PaginacionBusqueda(Paginacion):
  """Variante de paginación con tope de diez resultados para buscadores."""
  size: int = Query(10, ge=1, le=100)


# Forma estándar de toda respuesta paginada.
class RespuestaPaginada(BaseModel, Generic[T]):
  # Registros que pertenecen a la página solicitada
  """Envelope estándar con items, total, offset y size."""
  items: list[T]
  # Total de registros que cumplen los filtros, sin aplicar offset/size
  total: int
  # Offset que se aplicó
  offset: int
  # Tamaño de página que se aplicó
  size: int


def filtro_activos(consulta, modelo):
  """Devuelve la consulta restringida a registros no eliminados."""
  return consulta.where(modelo.fecha_eliminacion.is_(None))


def filtro_texto(consulta, termino: str, *campos):
  """Devuelve la consulta filtrada por texto en los campos indicados."""
  termino = termino.strip()

  if not termino or not campos:
    return consulta

  patron = f"%{termino}%"
  condiciones = [func.unaccent(campo).ilike(func.unaccent(patron)) for campo in campos]

  return consulta.where(or_(*condiciones))


def paginar(session: Session, consulta, paginacion: Paginacion) -> tuple[list, int]:
  """Devuelve los items de la página y el total de registros."""
  # Para el conteo se quita el orden: no cambia el total y evita ordenar
  # una subconsulta que solo se usa para contar filas.
  consulta_sin_orden = consulta.order_by(None)
  total = session.exec(
    select(func.count()).select_from(consulta_sin_orden.subquery())
  ).one()

  # La consulta original conserva su orden y se recorta a la página pedida.
  items = session.exec(consulta.offset(paginacion.offset).limit(paginacion.size)).all()
  return list(items), total


def construir_pagina(
  items: list[T], total: int, paginacion: Paginacion
) -> RespuestaPaginada[T]:
  """Devuelve el envelope con items, total y parámetros de paginación."""
  return RespuestaPaginada[T](
    items=items,
    total=total,
    offset=paginacion.offset,
    size=paginacion.size,
  )

"""Define el envelope paginado y las utilidades de consulta compartidas por los routers."""

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlmodel import Session, func, select

T = TypeVar("T")


class Paginacion(BaseModel):
  """Parámetros de paginación enviados por el cliente en la query string."""
  offset: int = Query(0, ge=0)
  size: int = Query(15, ge=1, le=100)


class PaginacionBusqueda(Paginacion):
  """Variante de paginación con diez resultados por defecto en buscadores."""
  size: int = Query(10, ge=1, le=100)


class RespuestaPaginada(BaseModel, Generic[T]):
  """Envelope estándar con items, total, offset y size."""
  items: list[T]
  # Total sin aplicar la ventana de la página solicitada.
  total: int
  offset: int
  size: int


def filtro_activos(consulta, modelo):
  """Devuelve la consulta restringida a registros no eliminados."""
  return consulta.where(modelo.fecha_eliminacion.is_(None))


def filtro_vigentes(consulta, modelo):
  """Restringe a registros no eliminados y, si aplica, no egresados.

  `Estudiantes` es el único modelo con `fecha_egreso`: un graduado conserva
  su ficha histórica pero deja de ser parte de la nómina vigente.
  """
  consulta = filtro_activos(consulta, modelo)
  if hasattr(modelo, "fecha_egreso"):
    consulta = consulta.where(modelo.fecha_egreso.is_(None))
  return consulta


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

"""Compone nombres completos a partir de los campos personales."""

from typing import Protocol


class ConNombreCompleto(Protocol):
  """Protocolo de objetos que exponen los cuatro campos del nombre completo."""
  primer_nombre: str
  segundo_nombre: str
  primer_apellido: str
  segundo_apellido: str


def nombre_completo(persona: ConNombreCompleto) -> str:
  """Une los cuatro campos del nombre omitiendo los que estén vacíos."""
  partes = (
    persona.primer_nombre,
    persona.segundo_nombre,
    persona.primer_apellido,
    persona.segundo_apellido,
  )
  return " ".join(parte for parte in partes if parte).strip()

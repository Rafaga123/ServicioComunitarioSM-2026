"""Normalización de textos visibles enviados al frontend."""

import re


def texto_legible(valor: object) -> str:
  """Convierte texto técnico a texto legible.

  Reglas: `_` → espacio y `ano`/`anio` → `año` (respetando mayúsculas).
  Se aplica a cualquier texto recibido, incluidas rutas y claves.
  """
  texto = str(valor or "").replace("_", " ")

  def reemplazar_año(conincidencia: re.Match[str]) -> str:
    """Devuelve el texto con tilde y capitalización acordes a la palabra."""
    palabra = conincidencia.group(0)
    if palabra.isupper():
      return "AÑO"
    if palabra[:1].isupper():
      return "Año"
    return "año"

  texto = re.sub(r"\b(?:ano|anio)\b", reemplazar_año, texto, flags=re.IGNORECASE)
  return re.sub(r"\s+", " ", texto).strip()

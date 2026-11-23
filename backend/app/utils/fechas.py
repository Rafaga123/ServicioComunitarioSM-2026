from datetime import datetime
from zoneinfo import ZoneInfo

# Zona horaria institucional. Todas las fechas del sistema se guardan
# como datetime naive en esta zona, sin conversiones a UTC.
ZONA_CARACAS = ZoneInfo("America/Caracas")


def ahora_caracas() -> datetime:
  """Devuelve la fecha y hora actual de Caracas, sin tzinfo.

  Las columnas de la base son TIMESTAMP WITHOUT TIME ZONE. Al quitar
  el tzinfo guardamos exactamente la hora local que ve el usuario.
  """

  return datetime.now(ZONA_CARACAS).replace(tzinfo=None)


def normalizar_fecha(fecha: datetime) -> datetime:
  """Convierte una fecha con zona horaria a hora local de Caracas.

  Si la fecha ya viene sin tzinfo se asume que está en hora de Caracas
  y se devuelve tal cual.
  """
  if fecha.tzinfo is None:
    return fecha

  return fecha.astimezone(ZONA_CARACAS).replace(tzinfo=None)

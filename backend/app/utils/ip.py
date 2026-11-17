import socket


def obtener_ip_local() -> str:
  """Obtiene la IP local real simulando una conexión (sin enviar datos)"""
  try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
      s.connect(("8.8.8.8", 80))
      return s.getsockname()[0]
  except OSError:
    return "127.0.0.1"

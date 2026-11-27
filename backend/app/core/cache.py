"""Cabeceras de caché explícitas para respuestas dependientes de la sesión."""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SinCacheMiddleware:
  """Fuerza `Cache-Control: private, no-store` en toda respuesta HTTP.

  Cada respuesta depende del rol/nivel del token y las descargas escriben
  auditoría, así que ningún caché compartido debe guardarla. Se aplica a JSON,
  PDF, errores y a los archivos estáticos de la documentación.
  """

  def __init__(self, app: ASGIApp) -> None:
    self.app = app

  async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] != "http":
      await self.app(scope, receive, send)
      return

    async def enviar_con_cache(mensaje: Message) -> None:
      if mensaje["type"] == "http.response.start":
        cabeceras = MutableHeaders(scope=mensaje)
        cabeceras["cache-control"] = "private, no-store"
      await send(mensaje)

    await self.app(scope, receive, enviar_con_cache)

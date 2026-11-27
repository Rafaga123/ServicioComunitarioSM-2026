from collections import deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status

from app.core.config import (
    LIMITE_LOGIN_INTENTOS,
    LIMITE_LOGIN_IP,
    LIMITE_LOGIN_VENTANA_SEGUNDOS,
)

_ventanas: dict[tuple[str, str], deque[float]] = {}
_bloqueo = Lock()

# Las claves de usuarios/IPs que dejan de usarse nunca se limpiarían solas:
# se podan como máximo una vez por hora para evitar crecimiento infinito.
_ultima_poda: float = monotonic()
_INTERVALO_PODA_SEGUNDOS = 3600


def ip_cliente(request: Request) -> str:
    """IP del cliente. No confiamos en X-Forwarded-For por defecto."""

    return request.client.host if request.client else "desconocida"


def _clave_usuario(ip: str, usuario: str) -> tuple[str, str]:
    return (ip, usuario.strip().lower())


def _clave_ip(ip: str) -> tuple[str, str]:
    return (ip, "*")


def _limpiar(clave: tuple[str, str], ahora: float) -> deque[float]:
    cola = _ventanas.setdefault(clave, deque())
    corte = ahora - LIMITE_LOGIN_VENTANA_SEGUNDOS

    while cola and cola[0] <= corte:
        cola.popleft()

    return cola


def _podar_ventanas(ahora: float) -> None:
    """Elimina claves sin intentos recientes. Requiere `_bloqueo` tomado."""

    global _ultima_poda

    if ahora - _ultima_poda < _INTERVALO_PODA_SEGUNDOS:
        return

    corte = ahora - LIMITE_LOGIN_VENTANA_SEGUNDOS

    for clave in list(_ventanas):
        cola = _ventanas[clave]
        while cola and cola[0] <= corte:
            cola.popleft()
        if not cola:
            del _ventanas[clave]

    _ultima_poda = ahora


def _segundos_restantes(clave: tuple[str, str], ahora: float) -> int:
    cola = _ventanas.get(clave)
    if not cola:
        return 1

    return max(1, int(cola[0] + LIMITE_LOGIN_VENTANA_SEGUNDOS - ahora) + 1)


def verificar_limite(ip: str, usuario: str) -> None:
    """Se llama ANTES de buscar el usuario y antes de bcrypt."""

    ahora = monotonic()

    with _bloqueo:
        _podar_ventanas(ahora)

        clave_usuario = _clave_usuario(ip, usuario)
        clave_ip = _clave_ip(ip)

        cola_usuario = _limpiar(clave_usuario, ahora)
        cola_ip = _limpiar(clave_ip, ahora)

        if len(cola_usuario) >= LIMITE_LOGIN_INTENTOS:
            segundos = _segundos_restantes(clave_usuario, ahora)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Demasiados intentos fallidos. "
                    f"Intenta nuevamente en {segundos} segundos."
                ),
                headers={"Retry-After": str(segundos)},
            )

        if len(cola_ip) >= LIMITE_LOGIN_IP:
            segundos = _segundos_restantes(clave_ip, ahora)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Demasiadas peticiones de inicio de sesión. "
                    f"Intenta nuevamente en {segundos} segundos."
                ),
                headers={"Retry-After": str(segundos)},
            )


def registrar_fallo(ip: str, usuario: str) -> None:
    ahora = monotonic()

    with _bloqueo:
        _limpiar(_clave_usuario(ip, usuario), ahora).append(ahora)
        _limpiar(_clave_ip(ip), ahora).append(ahora)


def registrar_exito(ip: str, usuario: str) -> None:
    """Limpia el contador de fallos del usuario; el de IP sigue hasta expirar."""

    ahora = monotonic()

    with _bloqueo:
        _limpiar(_clave_ip(ip), ahora).append(ahora)
        _ventanas.pop(_clave_usuario(ip, usuario), None)

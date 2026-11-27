"""Administra la denylist de JWT revocados por logout o cierre forzado."""

from datetime import UTC, datetime, timedelta
from threading import Lock
from time import monotonic

from pydantic import NaiveDatetime
from sqlalchemy import delete as delete_sql
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import TOKENS_REVOCADOS_RETENCION_HORAS
from app.models.db import TokensRevocados
from app.utils.fechas import ZONA_CARACAS, ahora_caracas


def expira_en_desde_payload(exp: int) -> NaiveDatetime:
    """Convierte el claim `exp` (epoch UTC) a datetime naive de Caracas."""

    return (
        datetime.fromtimestamp(exp, tz=UTC)
        .astimezone(ZONA_CARACAS)
        .replace(tzinfo=None)
    )


def revocar_token(
    session: Session,
    jti: str,
    usuario_id: int,
    exp: int,
    motivo: str = "CIERRE DE SESIÓN",
) -> None:
    """Anota un jti como revocado. Idempotente: no duplica filas."""

    existe = session.exec(
        select(TokensRevocados).where(TokensRevocados.jti == jti)
    ).first()

    if existe is not None:
        return

    session.add(
        TokensRevocados(
            jti=jti,
            usuario_id=usuario_id,
            expira_en=expira_en_desde_payload(exp),
            motivo=motivo,
        )
    )

    try:
        session.flush()
    except IntegrityError:
        # Otro logout concurrente insertó el mismo jti. La fila ya existe;
        # hacemos rollback para dejar la sesión limpia antes de auditar.
        session.rollback()


def esta_revocado(session: Session, jti: str) -> bool:
    """Devuelve True si el jti está en la denylist."""

    return (
        session.exec(
            select(TokensRevocados.id).where(TokensRevocados.jti == jti)
        ).first()
        is not None
    )


def limpiar_tokens_revocados(session: Session) -> int:
    """Borra filas ya vencidas + retención. NO hace commit: lo hace el caller."""

    corte = ahora_caracas() - timedelta(hours=TOKENS_REVOCADOS_RETENCION_HORAS)

    resultado = session.execute(
        delete_sql(TokensRevocados).where(TokensRevocados.expira_en < corte)
    )

    return max(resultado.rowcount or 0, 0)

_ultima_limpieza: float = monotonic()
_bloqueo_limpieza = Lock()


def limpiar_si_toca(session: Session) -> None:
    """Ejecuta la limpieza como máximo una vez por hora. No hace commit."""

    global _ultima_limpieza
    ahora = monotonic()

    with _bloqueo_limpieza:
        if ahora - _ultima_limpieza < 3600:
            return
        limpiar_tokens_revocados(session)
        _ultima_limpieza = ahora

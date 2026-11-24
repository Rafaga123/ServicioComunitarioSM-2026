"""Normaliza los textos visibles de las auditorías ya registradas.

Uso (desde `backend/`):
  python -m scripts.normalizar_textos_auditoria

Reemplaza `_` por espacios y `ano`/`anio` por `año` en módulo, acción y
descripción. Es idempotente: solo actualiza las filas que cambian.
"""

from sqlmodel import Session

from app.models.session import engine
from app.utils.auditoria import normalizar_auditorias_existentes


def main() -> None:
  with Session(engine) as session:
    cambiadas = normalizar_auditorias_existentes(session)
  print(f"Auditorías normalizadas: {cambiadas}")


if __name__ == "__main__":
  main()

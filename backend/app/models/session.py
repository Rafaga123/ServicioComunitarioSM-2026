"""Configura el engine PostgreSQL, el esquema y la sesión de SQLModel."""

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER, DEBUG
from app.core.migraciones import aplicar_migraciones, preparar_extensiones
from app.core.semilla import sembrar_datos
from app.utils.tokens_revocados import limpiar_tokens_revocados

# Construye la URL de conexión para PostgreSQL.
sql_url = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(sql_url, echo=DEBUG)


def create_db_tables():
  """Crea las tablas y delega las migraciones en `app.core.migraciones`."""
  preparar_extensiones(engine)
  SQLModel.metadata.create_all(engine)
  aplicar_migraciones(engine)


def inicializar_base_datos() -> tuple[int, int]:
  """Crea el esquema, solicita la limpieza de revocaciones y carga la semilla."""

  create_db_tables()

  with Session(engine) as session:
    # El DELETE no se confirma aquí: se aprovecha el commit de `sembrar_datos`.
    limpiar_tokens_revocados(session)
    return sembrar_datos(session)


def get_session():
  """Entrega una sesión de base de datos por petición."""
  with Session(engine) as session:
    yield session

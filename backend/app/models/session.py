import os

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine, text

# Cargar variables de entorno del archivo .env
load_dotenv()

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")


# Construcción de la URL corregida para PostgreSQL
sql_url = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{DB_PORT}/{DB_NAME}"

engine = create_engine(sql_url, echo=True)


def create_db_tables():
  with engine.begin() as conn:
    # Instalando las extensiones en lab base de datos
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

  SQLModel.metadata.create_all(engine)


def get_session():
  with Session(engine) as session:
    yield session

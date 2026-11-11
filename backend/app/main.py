from contextlib import asynccontextmanager

from fastapi import FastAPI

# ruff: noqa: F401 # Evita el error por importación sin uso para el Litner Ruff
from app.models import db
from app.models.session import create_db_tables
from app.routers import auth, estudiantes


@asynccontextmanager
async def lifespan(app: FastAPI):
  print("API Encendida")
  create_db_tables()
  yield
  print("API Apagada")


app = FastAPI(title="API Servicio Comunitario", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(estudiantes.router)


@app.get("/")
def get_root():
  return {"status": "Ok"}

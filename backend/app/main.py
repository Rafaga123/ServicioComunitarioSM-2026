from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ruff: noqa: F401 # Evita el error por importación sin uso para el Litner Ruff
from app.models import db
from app.models.session import create_db_tables
from app.routers import auditorias, auth, estudiantes, horarios
from app.utils.ip import obtener_ip_local


@asynccontextmanager
async def lifespan(app: FastAPI):
  ip_local = obtener_ip_local()
  print("=" * 50)
  print("🚀 API Encendida y lista para la acción")
  print(f"📡 Disponible en red local: http://{ip_local}:8000")
  print(f"📖 Documentación Swagger:  http://{ip_local}:8000/docs")
  print("=" * 50)

  create_db_tables()
  yield
  print("🛑 API Apagada")


app = FastAPI(title="API Servicio Comunitario", lifespan=lifespan, version="v1.0")

app.include_router(auth.router)
app.include_router(estudiantes.router)
app.include_router(auditorias.router)
app.include_router(horarios.router)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# fastapi dev app/main.py --host 0.0.0.0 --port 8000


@app.get("/")
def get_root():
  return {"status": "Ok"}

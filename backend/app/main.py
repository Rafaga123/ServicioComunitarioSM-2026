from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ruff: noqa: F401 # Evita el error por importación sin uso para el Litner Ruff
from app.models import db
from app.models.session import inicializar_base_datos
from app.routers import (
  asignaturas,
  auditorias,
  auth,
  docentes,
  estudiantes,
  grados,
  horarios,
  representantes,
  usuarios,
)
from app.utils.ip import obtener_ip_local


@asynccontextmanager
async def lifespan(app: FastAPI):
  ip_local = obtener_ip_local()
  print("=" * 50)
  print("🚀 API Encendida y lista para la acción")
  print(f"📡 Disponible en red local: http://{ip_local}:8000")
  print(f"📖 Documentación Swagger:  http://{ip_local}:8000/docs")
  print("=" * 50)

  grados, bloques = inicializar_base_datos()
  print(f"🌱 Semilla: {grados} grados y {bloques} bloques nuevos")
  yield
  print("🛑 API Apagada")


app = FastAPI(title="API Servicio Comunitario", lifespan=lifespan, version="v1.0")

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(estudiantes.router)
api_router.include_router(auditorias.router)
api_router.include_router(grados.router)
api_router.include_router(representantes.router)
api_router.include_router(docentes.router)
api_router.include_router(asignaturas.router)
api_router.include_router(horarios.router)
api_router.include_router(usuarios.router)

app.include_router(api_router)

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

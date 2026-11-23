from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# ruff: noqa: F401 # Evita el error por importación sin uso para el Litner Ruff
from app.models import db
from app.models.session import engine, inicializar_base_datos
from app.routers import (
  asignaturas,
  auditorias,
  auth,
  bloques_horarios,
  docentes,
  estudiantes,
  gestion,
  grados,
  horarios,
  pases,
  reportes,
  representantes,
  secciones,
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
api_router.include_router(secciones.router)
api_router.include_router(bloques_horarios.router)
api_router.include_router(pases.router)
api_router.include_router(reportes.router)
api_router.include_router(gestion.router)

app.include_router(api_router)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  # El auth viaja como Bearer en el header, no en cookies. Con el
  # frontend servido desde el mismo backend tampoco hay cross-origin.
  allow_credentials=False,
  allow_methods=["*"],
  allow_headers=["*"],
)


@app.get("/")
def get_root():
  return {"status": "Ok"}


@app.get("/health", tags=["Salud"])
def health_check():
  try:
    with engine.connect() as conexion:
      conexion.execute(text("SELECT 1"))
  except SQLAlchemyError:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail="Base de datos no disponible",
    )

  return {"status": "ok", "database": "ok"}

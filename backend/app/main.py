"""Registra los routers, el middleware CORS y los endpoints de salud de la API."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# ruff: noqa: F401  # db registra los modelos en SQLModel.
from app.core.cache import SinCacheMiddleware
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
  listados,
  pases,
  reportes,
  representantes,
  secciones,
  usuarios,
)
from app.utils.ip import obtener_ip_local


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Inicializa la base de datos y muestra las URLs de acceso."""
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
api_router.include_router(listados.router)
api_router.include_router(gestion.router)

app.include_router(api_router)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  # La autenticación viaja como Bearer en el header, no en cookies; por eso
  # no se requieren credenciales aunque se admitan todos los orígenes.
  allow_credentials=False,
  allow_methods=["*"],
  allow_headers=["*"],
  # `Retry-After` no es cabecera CORS-safelisted: sin exponerla el navegador
  # la oculta cuando el frontend apunta directo al backend (Tailscale).
  expose_headers=["Retry-After"],
)
# Se agrega después de CORS para envolver también las respuestas de preflight.
app.add_middleware(SinCacheMiddleware)


@app.get("/")
def get_root():
  """Devuelve el estado básico del servicio."""
  return {"status": "Ok"}


@app.get("/health", tags=["Salud"])
def health_check():
  """Comprueba la conexión con la base de datos."""
  try:
    with engine.connect() as conexion:
      conexion.execute(text("SELECT 1"))
  except SQLAlchemyError:
    raise HTTPException(
      status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
      detail="Base de datos no disponible",
    )

  return {"status": "ok", "database": "ok"}

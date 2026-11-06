# ServicioComunitarioSM-

### Inicio de Servidor 
cd backend/

Creación del entorno virtual
python -m venv .venv

Activación del entorno virtual
./.venv/Scripts/Activate.ps1 

Instalación de dependencias
pip install -r requirements.txt

---
Conexión con PostgreSQL para la creación de la Base de Datos
psql -U postgres
create database database;
exit
---

Creación de archivo '.env' para las variables de entorno
.env.example > .env

Prueba del Servidor
fastapi dev
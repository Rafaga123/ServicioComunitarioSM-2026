from sqlmodel import SQLModel

import app.models.enums as en


# ====
# Esquemas para Usuarios
# ====
class CrearUsuario(SQLModel):
  nombre: str
  clave: str
  rol: en.RolesUsuario


class PeticionUsuario(SQLModel):
  id: int | None
  nombre: str
  rol: en.RolesUsuario

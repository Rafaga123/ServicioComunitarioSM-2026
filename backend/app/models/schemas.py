from sqlmodel import SQLModel

import app.models.enums as en


# ====
# Esquemas para Usuarios
# ====
class CrearUsuario(SQLModel):
  name: str
  password: str
  rol: en.RolesUsuario


class PeticionUsuario(SQLModel):
  id: int | None
  name: str
  rol: en.RolesUsuario

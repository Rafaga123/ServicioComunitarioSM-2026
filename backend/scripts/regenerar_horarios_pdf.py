"""Regenera los PDFs de horarios activos conservando su nombre.

Uso (desde `backend/`):
  python -m scripts.regenerar_horarios_pdf
  python -m scripts.regenerar_horarios_pdf --periodo 2026 --usuario-id 1

Los registros anteriores se dan de baja lógicamente y se crean otros nuevos
apuntando a la misma ruta. No genera sufijos `_v2` y no toca otros listados.
"""

import argparse

from sqlmodel import Session, select

from app.models.db import DocumentosGenerados, Secciones, Usuarios
from app.models.enums import ModuloAuditoria, RolesUsuario, TipoDocumento
from app.models.session import engine
from app.services import listados as servicio_listados
from app.utils.auditoria import registrar_auditoria
from app.utils.fechas import ahora_caracas
from app.utils.pdf import construir_pdf_horarios
from app.utils.periodos import periodo_lectivo_efectivo
from app.utils.storage import (
  guardar_archivo,
  hash_contenido,
  ruta_absoluta,
)


def _usuario_generador(session: Session, usuario_id: int | None) -> Usuarios:
  if usuario_id is not None:
    usuario = session.get(Usuarios, usuario_id)
    if usuario is None or usuario.fecha_eliminacion is not None:
      raise SystemExit(f"No existe el usuario activo #{usuario_id}")
    return usuario
  usuario = session.exec(
    select(Usuarios)
    .where(
      Usuarios.rol == RolesUsuario.administrador,
      Usuarios.fecha_eliminacion.is_(None),
    )
    .order_by(Usuarios.id)
  ).first()
  if usuario is None:
    raise SystemExit("No hay un administrador activo para registrar la generación")
  return usuario


def regenerar(periodo: int | None = None, usuario_id: int | None = None) -> int:
  with Session(engine) as session:
    periodo = periodo or periodo_lectivo_efectivo(session, None)
    if periodo is None:
      raise SystemExit("No hay periodo lectivo activo; indica --periodo")

    usuario = _usuario_generador(session, usuario_id)
    documentos = session.exec(
      select(DocumentosGenerados)
      .where(
        DocumentosGenerados.tipo == TipoDocumento.horarios,
        DocumentosGenerados.periodo_lectivo == periodo,
        DocumentosGenerados.fecha_eliminacion.is_(None),
      )
      .order_by(DocumentosGenerados.id)
    ).all()

    regenerados = 0
    for anterior in documentos:
      if anterior.id_seccion is None:
        continue
      seccion = session.get(Secciones, anterior.id_seccion)
      if seccion is None or seccion.fecha_eliminacion is not None:
        continue

      grado = seccion.grado
      documento = servicio_listados.construir_documento(
        TipoDocumento.horarios,
        periodo,
        grado.nivel,
        grado,
        seccion,
        session,
      )
      assert documento.horario_cabecera is not None
      assert documento.horario_filas is not None
      assert documento.horario_docentes is not None

      pdf = construir_pdf_horarios(
        documento.horario_cabecera,
        documento.horario_filas,
        documento.horario_docentes,
      )
      ruta_relativa = servicio_listados.ruta_relativa_listado(
        TipoDocumento.horarios,
        periodo,
        grado.nivel,
        grado,
        seccion,
        documento.nombre_archivo,
      )
      guardar_archivo(ruta_relativa, pdf)
      if not ruta_absoluta(ruta_relativa).is_file():
        raise SystemExit(f"No se pudo guardar {ruta_relativa}")

      session.add(
        DocumentosGenerados(
          tipo=TipoDocumento.horarios,
          periodo_lectivo=periodo,
          nivel=grado.nivel,
          id_grado=documento.grado_id,
          id_seccion=documento.seccion_id,
          nombre_archivo=documento.nombre_archivo,
          ruta_relativa=ruta_relativa,
          hash=hash_contenido(pdf),
          tamano=len(pdf),
          mime="application/pdf",
          fecha_generacion=ahora_caracas(),
          generado_por=usuario.id,
        )
      )
      anterior.fecha_eliminacion = ahora_caracas()

      registrar_auditoria(
        session,
        usuario.id,
        ModuloAuditoria.documentos,
        "GENERAR",
        f"Regeneró el PDF {documento.nombre_archivo} (horarios).",
      )
      regenerados += 1

    session.commit()
  return regenerados


def main() -> None:
  analizador = argparse.ArgumentParser(description=__doc__)
  analizador.add_argument("--periodo", type=int, help="Año del periodo (ej. 2026)")
  analizador.add_argument(
    "--usuario-id", type=int, help="Usuario que registra la auditoría"
  )
  argumentos = analizador.parse_args()
  total = regenerar(argumentos.periodo, argumentos.usuario_id)
  print(f"Horarios regenerados: {total}")


if __name__ == "__main__":
  main()

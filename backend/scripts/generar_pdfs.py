"""
Genera todos los PDFs de listados (generales por nivel, por sección y por grado).

Con `REUTILIZAR_DOCUMENTOS_IGUALES=True`, omite los PDFs cuya firma de datos
ya esté registrada y los cuenta como reutilizados.

Uso (desde backend/):

  python -m scripts.generar_pdfs
  python -m scripts.generar_pdfs --periodo 2026 --usuario-id 1
  
"""

import argparse

from sqlmodel import Session, select

from app.models.db import DocumentosGenerados, Grados, Secciones, Usuarios
from app.models.enums import (
  ModuloAuditoria,
  NivelEducativo,
  RolesUsuario,
  TipoDocumento,
)
from app.models.session import engine
from app.services import firmas as servicio_firmas
from app.services import listados as servicio_listados
from app.utils.auditoria import registrar_auditoria
from app.utils.fechas import ahora_caracas
from app.utils.pdf import construir_pdf, construir_pdf_horarios
from app.utils.periodos import etiqueta_periodo, periodo_lectivo_efectivo
from app.utils.storage import (
  guardar_archivo,
  hash_contenido,
  nombre_unico,
  ruta_con_nombre,
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


def _emitir_pdf(
  session: Session,
  usuario: Usuarios,
  tipo: TipoDocumento,
  periodo: int,
  nivel: NivelEducativo,
  grado: Grados | None,
  seccion: Secciones | None,
) -> tuple[str, bool]:
  """Emite un PDF y devuelve `(ruta_relativa, reutilizado)`."""
  documento = servicio_listados.construir_documento(
    tipo, periodo, nivel, grado, seccion, session
  )
  firma = servicio_firmas.firma_si_activa(tipo, periodo, nivel, documento)
  if firma is not None:
    existente = servicio_firmas.documento_reutilizable(session, firma)
    if existente is not None:
      return existente.ruta_relativa, True

  if tipo == TipoDocumento.horarios:
    assert documento.horario_cabecera is not None
    assert documento.horario_filas is not None
    assert documento.horario_docentes is not None
    pdf = construir_pdf_horarios(
      documento.horario_cabecera,
      documento.horario_filas,
      documento.horario_docentes,
    )
  else:
    pdf = construir_pdf(
      documento.titulo,
      documento.encabezados,
      documento.filas,
      col_anchos=documento.col_anchos,
      nivel=nivel.value if nivel else None,
      grado=None,
      seccion=documento.seccion_descripcion,
      periodo_lectivo=etiqueta_periodo(periodo),
    )

  ruta_relativa = servicio_listados.ruta_relativa_listado(
    tipo, periodo, nivel, documento.grado, seccion, documento.nombre_archivo
  )
  nombre_archivo = nombre_unico(ruta_relativa, documento.nombre_archivo)
  ruta_relativa = ruta_con_nombre(ruta_relativa, nombre_archivo)
  guardar_archivo(ruta_relativa, pdf)

  registro = DocumentosGenerados(
    tipo=tipo,
    periodo_lectivo=periodo,
    nivel=nivel,
    id_grado=documento.grado_id,
    id_seccion=documento.seccion_id,
    nombre_archivo=nombre_archivo,
    ruta_relativa=ruta_relativa,
    hash=hash_contenido(pdf),
    tamano=len(pdf),
    mime="application/pdf",
    fecha_generacion=ahora_caracas(),
    generado_por=usuario.id,
  )
  session.add(registro)
  session.flush()
  if firma is not None:
    servicio_firmas.registrar_firma(session, firma, registro.id)

  registrar_auditoria(
    session,
    usuario.id,
    ModuloAuditoria.documentos,
    "GENERAR",
    f"Generó el documento {registro.nombre_archivo} ({tipo.value}).",
  )
  return ruta_relativa, False


def generar_todos(
  periodo: int | None = None, usuario_id: int | None = None
) -> tuple[list[str], int]:
  """Devuelve `(rutas, cantidad_reutilizada)`."""
  rutas: list[str] = []
  reutilizados = 0

  def registrar_resultado(resultado: tuple[str, bool]) -> None:
    nonlocal reutilizados
    ruta, reutilizado = resultado
    rutas.append(ruta)
    reutilizados += int(reutilizado)

  with Session(engine) as session:
    periodo = periodo or periodo_lectivo_efectivo(session, None)
    if periodo is None:
      raise SystemExit("No hay periodo lectivo activo; indica --periodo")

    usuario = _usuario_generador(session, usuario_id)

    # 1. Generales por nivel (ESCUELA y LICEO): nominas, representantes y docentes
    for nivel in (NivelEducativo.escuela, NivelEducativo.liceo):
      for tipo in (
        TipoDocumento.nominas,
        TipoDocumento.representantes,
        TipoDocumento.docentes,
      ):
        registrar_resultado(
          _emitir_pdf(session, usuario, tipo, periodo, nivel, None, None)
        )

    # 2. Generales por grado (sin sección): nominas y representantes
    grados = session.exec(
      select(Grados)
      .where(Grados.fecha_eliminacion.is_(None))
      .order_by(Grados.numero)
    ).all()
    for grado in grados:
      for tipo in (TipoDocumento.nominas, TipoDocumento.representantes):
        registrar_resultado(
          _emitir_pdf(session, usuario, tipo, periodo, grado.nivel, grado, None)
        )

    # 3. Por sección: nominas y representantes en ambos niveles; horarios solo en LICEO
    secciones = session.exec(
      select(Secciones)
      .where(
        Secciones.periodo_lectivo == periodo,
        Secciones.fecha_eliminacion.is_(None),
      )
      .order_by(Secciones.id_grado, Secciones.letra)
    ).all()
    for seccion in secciones:
      grado = seccion.grado
      tipos_seccion = [TipoDocumento.nominas, TipoDocumento.representantes]
      if grado.nivel == NivelEducativo.liceo:
        tipos_seccion.append(TipoDocumento.horarios)

      for tipo in tipos_seccion:
        registrar_resultado(
          _emitir_pdf(session, usuario, tipo, periodo, grado.nivel, grado, seccion)
        )

    session.commit()
  return rutas, reutilizados


def main() -> None:
  analizador = argparse.ArgumentParser(description=__doc__)
  analizador.add_argument("--periodo", type=int, help="Año del periodo (ej. 2026)")
  analizador.add_argument(
    "--usuario-id", type=int, help="Usuario que registra la auditoría"
  )
  argumentos = analizador.parse_args()

  rutas, reutilizados = generar_todos(argumentos.periodo, argumentos.usuario_id)
  for ruta in rutas:
    print(f"[OK] {ruta}")
  print(f"\nTotal PDFs: {len(rutas)} (reutilizados por firma idéntica: {reutilizados})")


if __name__ == "__main__":
  main()
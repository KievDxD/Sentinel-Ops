"""
Fase 6 (Enterprise V2.0): Módulo de Exportación Contable (Prenómina Laboral Colombiana
Ley 2101 de 42h semanales + Descuento por Ausentismos en CSV/Excel para Siigo/Novasoft)
y Generación del Libro Foliado Oficial de Minuta Digital con Sello Criptográfico SHA-256.
"""

import csv
import hashlib
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos.modelos_bd import (
    ModeloRegistroMinuta,
    ModeloTurno,
    ModeloUsuario,
    RolUsuario,
    TipoTurno,
    VisibilidadMinuta,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.configuracion import configuracion
from app.nucleo.seguridad import requerir_roles

enrutador_reportes = APIRouter(
    prefix="/api/reportes",
    tags=["Fase 6 - Exportación de Prenómina Excel/CSV y Minuta Foliada Oficial"],
)


@enrutador_reportes.get(
    "/prenomina-colombia-csv",
    summary="Descargar Prenómina Laboral Colombiana Ley 2101 (Exclusivo ADMINISTRADOR y RRHH)",
)
async def exportar_prenomina_colombia_csv(
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.RRHH)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> StreamingResponse:
    """
    Genera un archivo CSV con codificación UTF-8 con BOM para apertura directa en
    Microsoft Excel / Siigo / Novasoft, discriminando tope semanal Ley 2101 (42h),
    horas ordinarias, recargo nocturno (35%), extras (+25% / +75%), dominicales (+75%),
    descuentos por ausentismos (EPS/ARL/Licencia/Falta) y neto liquidado COP.
    """
    consulta = (
        select(ModeloTurno)
        .options(
            selectinload(ModeloTurno.operador),
            selectinload(ModeloTurno.puesto_vigilancia),
        )
        .order_by(ModeloTurno.operador_id.asc(), ModeloTurno.fecha_inicio.asc())
    )
    turnos = list((await sesion_bd.execute(consulta)).scalars().all())

    flujo_memoria = io.StringIO()
    flujo_memoria.write("\ufeff")
    escritor = csv.writer(flujo_memoria, delimiter=";")

    escritor.writerow(
        [
            "ID_TURNO",
            "DOCUMENTO_GUARDIA",
            "NOMBRE_OPERADOR",
            "CODIGO_PLACA",
            "CREDENCIAL_SUPERVIGILANCIA",
            "CODIGO_PUESTO",
            "NOMBRE_PUESTO",
            "TIPO_TURNO_2X2",
            "ESTADO_TURNO",
            "FECHA_INICIO",
            "FECHA_FIN",
            "TOPE_SEMANAL_LEY_2101",
            "HORAS_TOTALES",
            "HORAS_ORDINARIAS_BASE",
            "RECARGO_NOCTURNO_35_PCT",
            "EXTRA_DIURNA_125_PCT",
            "EXTRA_NOCTURNA_175_PCT",
            "DOMINICAL_FESTIVO_75_PCT",
            "HORAS_DESCUENTO_AUSENTISMO",
            "MOTIVO_AUSENTISMO",
            "COSTO_LIQUIDADO_COP",
        ]
    )

    for t in turnos:
        if t.tipo_turno == TipoTurno.DESCANSO or t.operador is None or t.puesto_vigilancia is None:
            continue
        op = t.operador
        pv = t.puesto_vigilancia
        escritor.writerow(
            [
                t.turno_id,
                op.documento_identidad,
                op.nombre_completo,
                op.codigo_placa,
                op.numero_credencial_sv or "SIN_CREDENCIAL",
                pv.codigo_puesto,
                pv.nombre_puesto,
                t.tipo_turno.value,
                t.estado_turno.value,
                t.fecha_inicio.strftime("%Y-%m-%d %H:%M"),
                t.fecha_fin.strftime("%Y-%m-%d %H:%M"),
                f"{configuracion.tope_horas_semanales}H",
                f"{t.horas_totales:.2f}",
                f"{t.horas_ordinarias:.2f}",
                f"{t.horas_recargo_nocturno:.2f}",
                f"{t.horas_extras_diurnas:.2f}",
                f"{t.horas_extras_nocturnas:.2f}",
                f"{t.horas_dominicales_festivas:.2f}",
                f"{t.horas_descuento_ausentismo:.2f}",
                t.motivo_ausentismo or "NINGUNO",
                f"{t.costo_estimado_cop:.0f}",
            ]
        )

    contenido_bytes = flujo_memoria.getvalue().encode("utf-8")
    nombre_archivo = (
        f"prenomina_sentinel_ops_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    )

    return StreamingResponse(
        io.BytesIO(contenido_bytes),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre_archivo}"'
        },
    )


@enrutador_reportes.get(
    "/minuta-foliada-oficial",
    response_class=HTMLResponse,
    summary="Generar Libro Foliado Oficial de Minuta Digital con Sello SHA-256 (ADMINISTRADOR, SUPERVISOR y CLIENTE)",
)
async def generar_libro_foliado_minuta_oficial(
    usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR, RolUsuario.CLIENTE
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> HTMLResponse:
    """
    Genera un documento oficial foliado y firmado criptográficamente con SHA-256
    para auditorías de la Superintendencia de Vigilancia y Seguridad Privada.
    Si el usuario es CLIENTE, filtra exclusivamente a su puesto contratado y visibilidad PUBLICA_CLIENTE.
    """
    consulta = (
        select(ModeloRegistroMinuta)
        .options(
            selectinload(ModeloRegistroMinuta.operador),
            selectinload(ModeloRegistroMinuta.puesto_vigilancia),
        )
        .order_by(ModeloRegistroMinuta.fecha_registro.asc())
    )

    if usuario_actual.rol == RolUsuario.CLIENTE:
        consulta = consulta.where(
            ModeloRegistroMinuta.visibilidad == VisibilidadMinuta.PUBLICA_CLIENTE
        )
        if usuario_actual.puesto_base_id is not None:
            consulta = consulta.where(
                ModeloRegistroMinuta.puesto_id == usuario_actual.puesto_base_id
            )

    registros = list((await sesion_bd.execute(consulta)).scalars().all())

    filas_html: list[str] = []
    hash_acumulado = hashlib.sha256(b"SENTINEL_OPS_GENESIS_2026").hexdigest()

    for indice, reg in enumerate(registros, start=1):
        doc_operador = reg.operador.documento_identidad if reg.operador else "N/A"
        nom_operador = reg.operador.nombre_completo if reg.operador else "Operador"
        placa_operador = reg.operador.codigo_placa if reg.operador else "OPR"
        cred_operador = (reg.operador.numero_credencial_sv or "SV-N/A") if reg.operador else "SV-N/A"
        cod_puesto = reg.puesto_vigilancia.codigo_puesto if reg.puesto_vigilancia else "PST"
        nom_puesto = reg.puesto_vigilancia.nombre_puesto if reg.puesto_vigilancia else "Puesto"

        cadena_folio = (
            f"{indice}|{reg.registro_id}|{reg.fecha_registro.isoformat()}|"
            f"{doc_operador}|{reg.titulo_evento}|{hash_acumulado}"
        )
        hash_acumulado = hashlib.sha256(cadena_folio.encode("utf-8")).hexdigest()
        sello_corto = hash_acumulado[:16].upper()

        filas_html.append(
            f"""
            <tr>
              <td class="mono">FOLIO-{indice:04d}</td>
              <td class="mono">{reg.fecha_registro.strftime('%Y-%m-%d %H:%M:%S')}</td>
              <td><strong>{cod_puesto}</strong><br/>{nom_puesto}</td>
              <td>{reg.tipo_registro.value}<br/><strong>Prioridad: {reg.nivel_prioridad.value}</strong><br/><span class="mono">{reg.visibilidad.value}</span></td>
              <td><strong>{reg.titulo_evento}</strong><br/>{reg.descripcion_detallada}</td>
              <td>{nom_operador}<br/><span class="mono">{placa_operador} • {cred_operador}</span></td>
              <td class="mono">{sello_corto}</td>
            </tr>
            """
        )

    fecha_expedicion = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    alcance_texto = (
        "CONSOLA CORPORATIVA DE CLIENTE (FILTRADO PÚBLICO)"
        if usuario_actual.rol == RolUsuario.CLIENTE
        else "AUDITORÍA INTEGRAL DE OPERACIONES Y SUPERVIGILANCIA"
    )
    documento_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Libro Oficial Foliado de Minuta Digital - SENTINEL // OPS</title>
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #0f172a; margin: 32px; }}
    .encabezado {{ border-bottom: 3px solid #059669; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }}
    h1 {{ margin: 0; font-size: 22px; letter-spacing: 0.05em; }}
    .subtitulo {{ font-size: 12px; color: #475569; margin-top: 4px; }}
    .sello-maestro {{ background: #f1f5f9; border: 1px solid #cbd5e1; padding: 10px 14px; font-size: 11px; border-radius: 6px; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #0f172a; color: #f8fafc; text-transform: uppercase; font-size: 10px; }}
    .mono {{ font-family: Consolas, monospace; font-size: 10px; }}
    .boton-imprimir {{ background: #059669; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; }}
    @media print {{ .boton-imprimir {{ display: none; }} }}
  </style>
</head>
<body>
  <div class="encabezado">
    <div>
      <h1>SENTINEL // OPS — LIBRO FOLIADO OFICIAL DE MINUTA DIGITAL</h1>
      <div class="subtitulo">Alcance: {alcance_texto} • SuperVigilancia Colombia • Fecha: {fecha_expedicion}</div>
    </div>
    <button class="boton-imprimir" onclick="window.print()">Imprimir / Guardar PDF Oficial</button>
  </div>
  <div class="sello-maestro">
    <strong>Sello Criptográfico de Cadena de Custodia (SHA-256):</strong>
    <span class="mono">{hash_acumulado.upper()}</span> • Total Folios Auditados: {len(registros)}
  </div>
  <table>
    <thead>
      <tr>
        <th>N° Folio</th>
        <th>Fecha y Hora</th>
        <th>Puesto Vigilancia</th>
        <th>Categoría / Nivel</th>
        <th>Detalle de la Anotación</th>
        <th>Operador Responsable</th>
        <th>Firma SHA-256</th>
      </tr>
    </thead>
    <tbody>
      {"".join(filas_html)}
    </tbody>
  </table>
</body>
</html>"""
    return HTMLResponse(content=documento_html)


@enrutador_reportes.get(
    "/respaldo-forense-cifrado",
    summary="Descargar Respaldo Forense Criptográfico (Fase 12 - Exclusivo ADMINISTRADOR)",
)
async def descargar_respaldo_forense(
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> dict:
    """Retorna volcado forense JSON estructurado con firma digital SHA-256."""
    from app.servicios.respaldo_forense import generar_paquete_respaldo_forense

    return await generar_paquete_respaldo_forense(sesion_bd)


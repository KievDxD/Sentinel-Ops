"""
Fase 8 (Enterprise V3.0): Módulo de Tarificación Legal SuperVigilancia y Facturación B2B.
Cálculo estricto de tarifas mínimas legales, cotizaciones en tiempo real y emisión
de prefacturas B2B con firma digital criptográfica SHA-256.
"""

from datetime import date, datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.esquemas.esquemas_pydantic import (
    RespuestaDesgloseCotizacion,
    RespuestaPrefactura,
    SolicitudCotizacionTarifa,
    SolicitudGenerarPrefactura,
)
from app.modelos.modelos_bd import (
    EstadoFactura,
    ModeloPuestoVigilancia,
    ModeloPrefactura,
    ModeloUsuario,
    RolUsuario,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.seguridad import requerir_roles
from app.servicios.motor_tarificacion import (
    calcular_tarifa_supervigilancia,
    generar_firma_digital_prefactura,
)

enrutador_facturacion = APIRouter(
    prefix="/api/facturacion",
    tags=["Fase 8 - Tarificación Legal SuperVigilancia y Facturación B2B"],
)


@enrutador_facturacion.post(
    "/cotizar",
    response_model=RespuestaDesgloseCotizacion,
    summary="Simular Cotización Legal según SuperVigilancia",
)
async def simular_cotizacion_puesto(
    solicitud: SolicitudCotizacionTarifa,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.RRHH,
            RolUsuario.CLIENTE,
        )
    ),
) -> RespuestaDesgloseCotizacion:
    """Calcula la tarifa regulada mínima legal en tiempo real."""
    liquidacion = calcular_tarifa_supervigilancia(
        modalidad=solicitud.modalidad_servicio,
        cantidad_puestos=solicitud.cantidad_puestos,
        porcentaje_administracion=solicitud.porcentaje_administracion,
        smlmv=solicitud.smlmv,
        auxilio_transporte=solicitud.auxilio_transporte,
    )

    return RespuestaDesgloseCotizacion(
        modalidad_servicio=liquidacion.modalidad_servicio,
        cantidad_puestos=liquidacion.cantidad_puestos,
        guardas_por_puesto=liquidacion.guardas_por_puesto,
        total_guardas_requeridos=liquidacion.total_guardas_requeridos,
        costo_laboral_unitario_guarda=liquidacion.costo_laboral_unitario_guarda,
        costo_mano_obra_total=liquidacion.costo_mano_obra_total,
        costo_armamento_y_equipos=liquidacion.costo_armamento_y_equipos,
        costo_administracion_aiu=liquidacion.costo_administracion_aiu,
        subtotal_antes_iva=liquidacion.subtotal_antes_iva,
        iva_dian=liquidacion.iva_dian,
        tarifa_total_factura_cop=liquidacion.tarifa_total_factura_cop,
        tarifa_minima_supervigilancia=liquidacion.tarifa_minima_supervigilancia,
    )


@enrutador_facturacion.get(
    "/prefacturas",
    response_model=list[RespuestaPrefactura],
    summary="Listar Prefacturas B2B Emitidas",
)
async def listar_prefacturas(
    usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.RRHH,
            RolUsuario.CLIENTE,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaPrefactura]:
    """Lista las prefacturas emitidas con filtro por cliente si aplica."""
    consulta = (
        select(ModeloPrefactura)
        .options(
            selectinload(ModeloPrefactura.cliente),
            selectinload(ModeloPrefactura.puesto_vigilancia),
        )
        .order_by(ModeloPrefactura.prefactura_id.desc())
    )

    if usuario_actual.rol == RolUsuario.CLIENTE:
        consulta = consulta.where(ModeloPrefactura.cliente_id == usuario_actual.usuario_id)

    resultado = await sesion_bd.execute(consulta)
    prefacturas = resultado.scalars().all()

    respuesta: list[RespuestaPrefactura] = []
    for pf in prefacturas:
        nombre_cliente = pf.cliente.nombre_completo if pf.cliente else f"Cliente #{pf.cliente_id}"
        nombre_puesto = pf.puesto_vigilancia.nombre_puesto if pf.puesto_vigilancia else None

        respuesta.append(
            RespuestaPrefactura(
                prefactura_id=pf.prefactura_id,
                codigo_factura=pf.codigo_factura,
                cliente_id=pf.cliente_id,
                nombre_cliente=nombre_cliente,
                puesto_id=pf.puesto_id,
                nombre_puesto=nombre_puesto,
                mes_servicio=pf.mes_servicio,
                modalidad_servicio=pf.modalidad_servicio,
                cantidad_puestos=pf.cantidad_puestos,
                cantidad_guardas_requeridos=pf.cantidad_guardas_requeridos,
                costo_mano_obra_cop=pf.costo_mano_obra_cop,
                costo_armamento_cop=pf.costo_armamento_cop,
                costo_administracion_cop=pf.costo_administracion_cop,
                subtotal_cop=pf.subtotal_cop,
                iva_cop=pf.iva_cop,
                total_factura_cop=pf.total_factura_cop,
                estado_factura=pf.estado_factura,
                notas_comerciales=pf.notas_comerciales,
                firma_digital_sha256=pf.firma_digital_sha256,
                fecha_emision=pf.fecha_emision,
                fecha_vencimiento=pf.fecha_vencimiento,
            )
        )

    return respuesta


@enrutador_facturacion.post(
    "/prefacturas",
    response_model=RespuestaPrefactura,
    status_code=status.HTTP_201_CREATED,
    summary="Generar Nueva Prefactura Legal B2B",
)
async def generar_nueva_prefactura(
    solicitud: SolicitudGenerarPrefactura,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.RRHH)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaPrefactura:
    """Genera y almacena una prefactura oficial con sello de integridad."""
    # Verificar existencia del cliente
    consulta_cliente = select(ModeloUsuario).where(
        ModeloUsuario.usuario_id == solicitud.cliente_id,
        ModeloUsuario.rol == RolUsuario.CLIENTE,
    )
    resultado_cliente = await sesion_bd.execute(consulta_cliente)
    cliente = resultado_cliente.scalar_one_or_none()

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró un cliente activo con ID {solicitud.cliente_id}.",
        )

    nombre_puesto: str | None = None
    if solicitud.puesto_id is not None:
        consulta_puesto = select(ModeloPuestoVigilancia).where(
            ModeloPuestoVigilancia.puesto_id == solicitud.puesto_id
        )
        resultado_puesto = await sesion_bd.execute(consulta_puesto)
        puesto = resultado_puesto.scalar_one_or_none()
        if not puesto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Puesto de vigilancia #{solicitud.puesto_id} no encontrado.",
            )
        nombre_puesto = puesto.nombre_puesto

    liquidacion = calcular_tarifa_supervigilancia(
        modalidad=solicitud.modalidad_servicio,
        cantidad_puestos=solicitud.cantidad_puestos,
        porcentaje_administracion=solicitud.porcentaje_administracion,
    )

    fecha_ahora = datetime.now(timezone.utc)
    codigo_factura = f"FAC-{solicitud.mes_servicio.replace('-', '')}-{uuid.uuid4().hex[:6].upper()}"
    fecha_vencimiento = date.today() + timedelta(days=30)

    firma_hash = generar_firma_digital_prefactura(
        codigo_factura=codigo_factura,
        cliente_id=cliente.usuario_id,
        mes_servicio=solicitud.mes_servicio,
        total_cop=liquidacion.tarifa_total_factura_cop,
        fecha_emision=fecha_ahora,
    )

    nueva_prefactura = ModeloPrefactura(
        codigo_factura=codigo_factura,
        cliente_id=cliente.usuario_id,
        puesto_id=solicitud.puesto_id,
        mes_servicio=solicitud.mes_servicio,
        modalidad_servicio=solicitud.modalidad_servicio,
        cantidad_puestos=solicitud.cantidad_puestos,
        cantidad_guardas_requeridos=liquidacion.total_guardas_requeridos,
        costo_mano_obra_cop=liquidacion.costo_mano_obra_total,
        costo_armamento_cop=liquidacion.costo_armamento_y_equipos,
        costo_administracion_cop=liquidacion.costo_administracion_aiu,
        subtotal_cop=liquidacion.subtotal_antes_iva,
        iva_cop=liquidacion.iva_dian,
        total_factura_cop=liquidacion.tarifa_total_factura_cop,
        estado_factura=EstadoFactura.EMITIDA,
        notas_comerciales=solicitud.notas_comerciales,
        firma_digital_sha256=firma_hash,
        fecha_emision=fecha_ahora,
        fecha_vencimiento=fecha_vencimiento,
    )

    sesion_bd.add(nueva_prefactura)
    await sesion_bd.commit()
    await sesion_bd.refresh(nueva_prefactura)

    return RespuestaPrefactura(
        prefactura_id=nueva_prefactura.prefactura_id,
        codigo_factura=nueva_prefactura.codigo_factura,
        cliente_id=nueva_prefactura.cliente_id,
        nombre_cliente=cliente.nombre_completo,
        puesto_id=nueva_prefactura.puesto_id,
        nombre_puesto=nombre_puesto,
        mes_servicio=nueva_prefactura.mes_servicio,
        modalidad_servicio=nueva_prefactura.modalidad_servicio,
        cantidad_puestos=nueva_prefactura.cantidad_puestos,
        cantidad_guardas_requeridos=nueva_prefactura.cantidad_guardas_requeridos,
        costo_mano_obra_cop=nueva_prefactura.costo_mano_obra_cop,
        costo_armamento_cop=nueva_prefactura.costo_armamento_cop,
        costo_administracion_cop=nueva_prefactura.costo_administracion_cop,
        subtotal_cop=nueva_prefactura.subtotal_cop,
        iva_cop=nueva_prefactura.iva_cop,
        total_factura_cop=nueva_prefactura.total_factura_cop,
        estado_factura=nueva_prefactura.estado_factura,
        notas_comerciales=nueva_prefactura.notas_comerciales,
        firma_digital_sha256=nueva_prefactura.firma_digital_sha256,
        fecha_emision=nueva_prefactura.fecha_emision,
        fecha_vencimiento=nueva_prefactura.fecha_vencimiento,
    )


@enrutador_facturacion.get(
    "/prefacturas/{prefactura_id}/html",
    response_class=HTMLResponse,
    summary="Ver Prefactura Legal Foliada en HTML/PDF",
)
async def ver_prefactura_foliada_html(
    prefactura_id: int,
    usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.RRHH,
            RolUsuario.CLIENTE,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> HTMLResponse:
    """Genera la factura foliada B2B con sello de firma digital."""
    consulta = (
        select(ModeloPrefactura)
        .options(
            selectinload(ModeloPrefactura.cliente),
            selectinload(ModeloPrefactura.puesto_vigilancia),
        )
        .where(ModeloPrefactura.prefactura_id == prefactura_id)
    )
    resultado = await sesion_bd.execute(consulta)
    pf = resultado.scalar_one_or_none()

    if not pf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prefactura #{prefactura_id} no encontrada.",
        )

    if usuario_actual.rol == RolUsuario.CLIENTE and pf.cliente_id != usuario_actual.usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: no autorizado para visualizar esta prefactura.",
        )

    nombre_cliente = pf.cliente.nombre_completo if pf.cliente else f"Cliente #{pf.cliente_id}"
    doc_cliente = pf.cliente.documento_identidad if pf.cliente else "NIT/CC No Registrado"
    nombre_puesto = pf.puesto_vigilancia.nombre_puesto if pf.puesto_vigilancia else "General / Consolidado"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Prefactura Legal {pf.codigo_factura} — SENTINEL // OPS</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 30px;
        }}
        .factura-box {{
            max-width: 850px;
            margin: auto;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }}
        .encabezado {{
            display: flex;
            justify-content: space-between;
            border-bottom: 2px solid #38bdf8;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }}
        .logo {{
            font-size: 24px;
            font-weight: 900;
            letter-spacing: 2px;
            color: #38bdf8;
        }}
        .sublogo {{
            font-size: 11px;
            color: #94a3b8;
            letter-spacing: 1px;
        }}
        .info-factura {{
            text-align: right;
            font-size: 13px;
            color: #cbd5e1;
        }}
        .info-factura strong {{
            color: #38bdf8;
            font-size: 15px;
        }}
        .seccion-cliente {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            background: #0f172a;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #38bdf8;
            margin-bottom: 25px;
            font-size: 13px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 25px;
            font-size: 13px;
        }}
        th {{
            background: #334155;
            color: #38bdf8;
            padding: 10px;
            text-align: left;
            border-bottom: 2px solid #475569;
        }}
        td {{
            padding: 12px 10px;
            border-bottom: 1px solid #334155;
        }}
        .total-box {{
            float: right;
            width: 320px;
            background: #0f172a;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #334155;
            font-size: 13px;
        }}
        .total-box div {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        .total-box .gran-total {{
            font-size: 17px;
            font-weight: bold;
            color: #10b981;
            border-top: 1px solid #475569;
            padding-top: 8px;
        }}
        .pie-pagina {{
            clear: both;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #334155;
            font-size: 10px;
            color: #64748b;
            text-align: center;
        }}
        .hash-code {{
            font-family: monospace;
            background: #0f172a;
            padding: 6px;
            border-radius: 4px;
            color: #38bdf8;
            word-break: break-all;
            margin-top: 5px;
        }}
        .btn-imprimir {{
            background: #0284c7;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            margin-bottom: 15px;
        }}
        @media print {{
            .btn-imprimir {{ display: none; }}
            body {{ background: white; color: black; padding: 0; }}
            .factura-box {{ border: none; box-shadow: none; background: white; color: black; }}
            .seccion-cliente, .total-box, .hash-code {{ background: #f1f5f9; color: black; }}
            th {{ background: #e2e8f0; color: black; }}
            td {{ border-bottom: 1px solid #cbd5e1; }}
        }}
    </style>
</head>
<body>
    <div style="max-width: 850px; margin: auto;">
        <button class="btn-imprimir" onclick="window.print()">🖨️ Imprimir / Guardar en PDF</button>
    </div>
    <div class="factura-box">
        <div class="encabezado">
            <div>
                <div class="logo">SENTINEL // OPS</div>
                <div class="sublogo">SISTEMA INTEGRAL DE SEGURIDAD PRIVADA & GESTIÓN TÁCTICA</div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">Vigilado por la Superintendencia de Vigilancia y Seguridad Privada</div>
            </div>
            <div class="info-factura">
                <div>ESTADO: <strong>{pf.estado_factura.value}</strong></div>
                <div>PREFACTURA N°: <strong>{pf.codigo_factura}</strong></div>
                <div>Fecha Emisión: {pf.fecha_emision.strftime('%d/%m/%Y')}</div>
                <div>Fecha Vencimiento: {pf.fecha_vencimiento.strftime('%d/%m/%Y')}</div>
            </div>
        </div>

        <div class="seccion-cliente">
            <div>
                <span style="color: #94a3b8;">DATOS DEL CLIENTE CONTRATANTE:</span><br>
                <strong style="color: #f8fafc; font-size: 14px;">{nombre_cliente}</strong><br>
                NIT / C.C.: {doc_cliente}<br>
                Puesto Asignado: {nombre_puesto}
            </div>
            <div>
                <span style="color: #94a3b8;">PERÍODO Y MODALIDAD:</span><br>
                Mes de Facturación: <strong>{pf.mes_servicio}</strong><br>
                Modalidad: <strong>{pf.modalidad_servicio.value.replace('_', ' ')}</strong><br>
                Puestos Operativos: <strong>{pf.cantidad_puestos}</strong> ({pf.cantidad_guardas_requeridos} guardas en cobertura)
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Concepto Regulado (SuperVigilancia / Ley 1920)</th>
                    <th style="text-align: center;">Cantidad</th>
                    <th style="text-align: right;">Tarifa COP</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>
                        <strong>Mano de Obra Operativa y Factor Prestacional</strong><br>
                        <small style="color: #94a3b8;">SMLMV, Auxilio de Transporte, Cesantías, Prima, ARL Riesgo V, Caja, Dotación y Seguro de Vida</small>
                    </td>
                    <td style="text-align: center;">{pf.cantidad_guardas_requeridos} Guardas</td>
                    <td style="text-align: right;">${pf.costo_mano_obra_cop:,.2f}</td>
                </tr>
                <tr>
                    <td>
                        <strong>Costo Operativo de Armamento, Comunicaciones y Equipos</strong><br>
                        <small style="color: #94a3b8;">Permisos DCCA Indumil, Munición, Radios y Mantenimiento Balístico</small>
                    </td>
                    <td style="text-align: center;">{pf.cantidad_puestos} Puesto(s)</td>
                    <td style="text-align: right;">${pf.costo_armamento_cop:,.2f}</td>
                </tr>
                <tr>
                    <td>
                        <strong>Gastos de Administración e Intermediación (AIU)</strong><br>
                        <small style="color: #94a3b8;">Mínimo regulado por SuperVigilancia (Supervisión motorizada, centro de control 24/7)</small>
                    </td>
                    <td style="text-align: center;">10% Reg.</td>
                    <td style="text-align: right;">${pf.costo_administracion_cop:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="total-box">
            <div>
                <span>Subtotal Operativo:</span>
                <span>${pf.subtotal_cop:,.2f}</span>
            </div>
            <div>
                <span>IVA DIAN (19% sobre AIU):</span>
                <span>${pf.iva_cop:,.2f}</span>
            </div>
            <div class="gran-total">
                <span>TOTAL A PAGAR:</span>
                <span>${pf.total_factura_cop:,.2f} COP</span>
            </div>
        </div>

        <div class="pie-pagina">
            <div>Esta prefactura cumple con las tarifas mínimas obligatorias expedidas por la Superintendencia de Vigilancia y Seguridad Privada de Colombia.</div>
            <div style="margin-top: 6px;">FIRMA DIGITAL Y SELLO CRIPTOGRÁFICO DE AUTENTICIDAD:</div>
            <div class="hash-code">{pf.firma_digital_sha256}</div>
        </div>
    </div>
</body>
</html>"""

    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)


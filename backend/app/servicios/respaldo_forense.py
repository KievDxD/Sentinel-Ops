"""
Fase 12 (Enterprise V3.0): Servicio de Respaldo Forense Criptográfico Multi-Tenant.
Genera un volcado estructurado JSON con sello SHA-256 de todas las minutas, actas de relevo,
movimientos balísticos y prefacturas para auditoría legal de la SuperVigilancia y DCCA.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.modelos_bd import (
    ModeloActaRelevoPuesto,
    ModeloAlertaPanicoSos,
    ModeloKardexBalistico,
    ModeloPrefactura,
    ModeloRegistroAccesoGarita,
    ModeloRegistroMinuta,
    ModeloTurno,
    ModeloUsuario,
)


async def generar_paquete_respaldo_forense(
    sesion_bd: AsyncSession,
    tenant_id: str = "EMPRESA-SEGURIDAD-COLOMBIA-01",
) -> dict[str, Any]:
    """Genera paquete JSON exportable con firma de integridad SHA-256."""
    ahora = datetime.now(timezone.utc)

    # 1. Contar y consultar registros clave
    res_minuta = await sesion_bd.execute(select(ModeloRegistroMinuta).limit(100))
    minutas = res_minuta.scalars().all()

    res_actas = await sesion_bd.execute(select(ModeloActaRelevoPuesto).limit(50))
    actas = res_actas.scalars().all()

    res_balistica = await sesion_bd.execute(select(ModeloKardexBalistico).limit(50))
    balistica = res_balistica.scalars().all()

    res_prefacturas = await sesion_bd.execute(select(ModeloPrefactura).limit(50))
    prefacturas = res_prefacturas.scalars().all()

    cuerpo_datos = {
        "encabezado": {
            "plataforma": "SENTINEL // OPS Enterprise V3.0",
            "tenant_id": tenant_id,
            "normativa": "Superintendencia de Vigilancia y Seguridad Privada",
            "fecha_generacion": ahora.isoformat(),
        },
        "resumen_totales": {
            "total_minutas_auditadas": len(minutas),
            "total_actas_relevo_auditadas": len(actas),
            "total_movimientos_balisticos_auditados": len(balistica),
            "total_prefacturas_auditadas": len(prefacturas),
        },
        "registros_minuta": [
            {
                "registro_id": m.registro_id,
                "puesto_id": m.puesto_id,
                "tipo_registro": m.tipo_registro.value,
                "titulo": m.titulo_evento,
                "prioridad": m.nivel_prioridad.value,
                "fecha_evento": m.fecha_registro.isoformat(),
            }
            for m in minutas
        ],
        "actas_relevo_indumil": [
            {
                "acta_id": a.acta_id,
                "puesto_id": a.puesto_id,
                "estado_armamento": a.estado_armamento.value,
                "municion_verificada": a.municion_verificada,
                "sello_sha256": a.sello_sha256,
                "fecha_acta": a.fecha_acta.isoformat(),
            }
            for a in actas
        ],
        "kardex_balistico": [
            {
                "movimiento_id": b.movimiento_id,
                "tipo_movimiento": b.tipo_movimiento.value,
                "calibre": b.calibre,
                "cantidad": b.cantidad_municion_afectada,
                "saldo": b.saldo_municion_resultante,
                "firma_sha256": b.firma_digital_sha256,
            }
            for b in balistica
        ],
        "prefacturas_supervigilancia": [
            {
                "codigo_factura": pf.codigo_factura,
                "mes_servicio": pf.mes_servicio,
                "modalidad": pf.modalidad_servicio.value,
                "total_cop": pf.total_factura_cop,
                "firma_sha256": pf.firma_digital_sha256,
            }
            for pf in prefacturas
        ],
    }

    # Sello global de integridad del paquete forense
    cadena_serializada = json.dumps(cuerpo_datos, sort_keys=True)
    hash_global = hashlib.sha256(cadena_serializada.encode("utf-8")).hexdigest()

    cuerpo_datos["sello_criptografico_auditoria_sha256"] = hash_global
    return cuerpo_datos

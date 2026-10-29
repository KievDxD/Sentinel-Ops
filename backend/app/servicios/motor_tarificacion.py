"""
Motor de Cálculo de Tarifas Mínimas Legales de Vigilancia Privada y Facturación B2B.
Regulado según circulares anuales de la Superintendencia de Vigilancia y Seguridad Privada,
Ley 1920 de 2018 (Ley del Vigilante), Ley 2101 de 2021 (Jornada Máxima) y Art. 462-1 E.T. (DIAN).
"""

import hashlib
from datetime import date, datetime, timezone
from typing import Any
from dataclasses import dataclass

from app.modelos.modelos_bd import ModalidadServicioTarifa


# Parámetros base de Ley Colombia (Vigencia 2026)
SMLMV_BASE_COLOMBIA: float = 1_423_500.0  # Salario Mínimo Legal Mensual Vigente
AUXILIO_TRANSPORTE_BASE: float = 200_000.0  # Auxilio de transporte legal mensual
PORCENTAJE_PRESTACIONES: float = 0.2183  # Cesantías, Intereses, Prima, Vacaciones (21.83%)
PORCENTAJE_SEGURIDAD_SOCIAL: float = 0.2885  # Salud 8.5%, Pensión 12%, ARL Riesgo V 4.35%, CCF 4% (28.85%)
PORCENTAJE_DOTACION_SEGURO_VIDA: float = 0.040  # Dotación y seguro obligatorio Ley 1920 (4.0%)
PORCENTAJE_AIU_MINIMO_LEGAL: float = 0.10  # Margen obligatorio de Administración e Intermediación (10%)
TARIFA_IVA_SOBRE_AIU: float = 0.19  # IVA del 19% sobre la base de Administración (Art. 462-1 E.T.)


@dataclass
class DesgloseCostoGuarda:
    """Estructura de costos laborales mensuales por cada operador/guarda."""

    salario_base: float
    auxilio_transporte: float
    recargo_nocturno_dominical: float
    prestaciones_sociales: float
    seguridad_social_parafiscales: float
    dotacion_y_seguro_vida: float
    costo_laboral_total: float


@dataclass
class LiquidacionTarifariaPuesto:
    """Liquidación consolidada mensual del puesto de vigilancia ante el cliente B2B."""

    modalidad_servicio: ModalidadServicioTarifa
    cantidad_puestos: int
    guardas_por_puesto: int
    total_guardas_requeridos: int
    costo_laboral_unitario_guarda: float
    costo_mano_obra_total: float
    costo_armamento_y_equipos: float
    costo_administracion_aiu: float
    subtotal_antes_iva: float
    iva_dian: float
    tarifa_total_factura_cop: float
    tarifa_minima_supervigilancia: float


def calcular_costo_laboral_guarda(
    modalidad: ModalidadServicioTarifa,
    smlmv: float = SMLMV_BASE_COLOMBIA,
    auxilio_transporte: float = AUXILIO_TRANSPORTE_BASE,
) -> DesgloseCostoGuarda:
    """Calcula el costo real patronal de un guarda mensual según jornada y recargos."""
    # Factor de recargos nocturnos y dominicales según la modalidad
    if modalidad in (ModalidadServicioTarifa.VIGILANCIA_24H_ARMADA, ModalidadServicioTarifa.VIGILANCIA_24H_SIN_ARMA):
        # En ciclo 2x2 rotativo 24/7, el recargo promedio legal ronda el 36% del SMLMV
        recargo = smlmv * 0.36
    elif modalidad == ModalidadServicioTarifa.VIGILANCIA_12H_NOCTURNA:
        # 12 horas nocturnas permanentes: 35% recargo nocturno + dominicales
        recargo = smlmv * 0.45
    elif modalidad == ModalidadServicioTarifa.SUPERVISION_MOTORIZADA:
        # Supervisores con bonificación táctica de rodamiento y nocturno
        recargo = smlmv * 0.40
    else:
        # 12 horas diurnas (recargos dominicales y festivos promedio)
        recargo = smlmv * 0.15

    base_prestacional = smlmv + recargo
    prestaciones = base_prestacional * PORCENTAJE_PRESTACIONES
    seguridad_social = base_prestacional * PORCENTAJE_SEGURIDAD_SOCIAL
    dotacion_seguro = smlmv * PORCENTAJE_DOTACION_SEGURO_VIDA

    costo_total = (
        smlmv
        + auxilio_transporte
        + recargo
        + prestaciones
        + seguridad_social
        + dotacion_seguro
    )

    return DesgloseCostoGuarda(
        salario_base=round(smlmv, 2),
        auxilio_transporte=round(auxilio_transporte, 2),
        recargo_nocturno_dominical=round(recargo, 2),
        prestaciones_sociales=round(prestaciones, 2),
        seguridad_social_parafiscales=round(seguridad_social, 2),
        dotacion_y_seguro_vida=round(dotacion_seguro, 2),
        costo_laboral_total=round(costo_total, 2),
    )


def calcular_tarifa_supervigilancia(
    modalidad: ModalidadServicioTarifa,
    cantidad_puestos: int = 1,
    porcentaje_administracion: float = PORCENTAJE_AIU_MINIMO_LEGAL,
    smlmv: float = SMLMV_BASE_COLOMBIA,
    auxilio_transporte: float = AUXILIO_TRANSPORTE_BASE,
) -> LiquidacionTarifariaPuesto:
    """
    Calcula la tarifa mínima legal y estructura de facturación según SuperVigilancia.
    """
    if cantidad_puestos < 1:
        cantidad_puestos = 1

    # Definir dotación de personal por puesto
    if modalidad in (ModalidadServicioTarifa.VIGILANCIA_24H_ARMADA, ModalidadServicioTarifa.VIGILANCIA_24H_SIN_ARMA):
        guardas_por_puesto = 4  # 4 guardas rotativos para 24/7 sin exceder jornada
    elif modalidad in (ModalidadServicioTarifa.VIGILANCIA_12H_DIURNA, ModalidadServicioTarifa.VIGILANCIA_12H_NOCTURNA):
        guardas_por_puesto = 2
    else:
        guardas_por_puesto = 1

    total_guardas = guardas_por_puesto * cantidad_puestos
    costo_guarda = calcular_costo_laboral_guarda(modalidad, smlmv, auxilio_transporte)
    costo_mano_obra = costo_guarda.costo_laboral_total * total_guardas

    # Recargo de armamento y municiones (10% sobre mano de obra si es armada)
    if modalidad == ModalidadServicioTarifa.VIGILANCIA_24H_ARMADA:
        costo_armamento = round(costo_mano_obra * 0.10, 2)
    else:
        costo_armamento = 0.0

    # Margen de Administración e Intermediación (AIU)
    pct_admin = max(porcentaje_administracion, PORCENTAJE_AIU_MINIMO_LEGAL)
    costo_administracion = round((costo_mano_obra + costo_armamento) * pct_admin, 2)

    subtotal = round(costo_mano_obra + costo_armamento + costo_administracion, 2)

    # IVA DIAN Art. 462-1 (19% sobre la base de administración AIU)
    iva = round(costo_administracion * TARIFA_IVA_SOBRE_AIU, 2)
    total_factura = round(subtotal + iva, 2)

    # Tarifa piso mínima legal SuperVigilancia (no permite cotizar por debajo)
    tarifa_minima = total_factura

    return LiquidacionTarifariaPuesto(
        modalidad_servicio=modalidad,
        cantidad_puestos=cantidad_puestos,
        guardas_por_puesto=guardas_por_puesto,
        total_guardas_requeridos=total_guardas,
        costo_laboral_unitario_guarda=costo_guarda.costo_laboral_total,
        costo_mano_obra_total=costo_mano_obra,
        costo_armamento_y_equipos=costo_armamento,
        costo_administracion_aiu=costo_administracion,
        subtotal_antes_iva=subtotal,
        iva_dian=iva,
        tarifa_total_factura_cop=total_factura,
        tarifa_minima_supervigilancia=tarifa_minima,
    )


def generar_firma_digital_prefactura(
    codigo_factura: str,
    cliente_id: int,
    mes_servicio: str,
    total_cop: float,
    fecha_emision: datetime,
) -> str:
    """Genera huella SHA-256 de integridad para la prefactura legal B2B."""
    cadena = f"{codigo_factura}:{cliente_id}:{mes_servicio}:{total_cop:.2f}:{fecha_emision.isoformat()}"
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest()


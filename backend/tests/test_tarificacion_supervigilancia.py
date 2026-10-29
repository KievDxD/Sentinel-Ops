"""
Tests unitarios y de integración para el Motor de Tarificación Legal SuperVigilancia (V3.0).
Valida cálculos de piso tarifario, dotación de guardas 24/7 y firma criptográfica SHA-256.
"""

from datetime import datetime, timezone
import pytest

from app.modelos.modelos_bd import ModalidadServicioTarifa
from app.servicios.motor_tarificacion import (
    calcular_costo_laboral_guarda,
    calcular_tarifa_supervigilancia,
    generar_firma_digital_prefactura,
)


def test_calculo_costo_guarda_incluye_prestaciones_y_seguridad_social():
    """Verifica que el costo del guarda compute salario, auxilio, recargos y aportes."""
    smlmv = 1_423_500.0
    auxilio = 200_000.0
    desglose = calcular_costo_laboral_guarda(
        modalidad=ModalidadServicioTarifa.VIGILANCIA_24H_ARMADA,
        smlmv=smlmv,
        auxilio_transporte=auxilio,
    )

    assert desglose.salario_base == smlmv
    assert desglose.auxilio_transporte == auxilio
    assert desglose.recargo_nocturno_dominical > 0
    assert desglose.prestaciones_sociales > 0
    assert desglose.seguridad_social_parafiscales > 0
    assert desglose.costo_laboral_total > (smlmv * 1.8)


def test_puesto_24h_requiere_4_guardas_y_recargo_armas():
    """Un puesto 24/7 armado debe calcular 4 guardas y 10% adicional por armamento."""
    liquidacion = calcular_tarifa_supervigilancia(
        modalidad=ModalidadServicioTarifa.VIGILANCIA_24H_ARMADA,
        cantidad_puestos=1,
    )

    assert liquidacion.guardas_por_puesto == 4
    assert liquidacion.total_guardas_requeridos == 4
    assert liquidacion.costo_armamento_y_equipos > 0
    assert liquidacion.costo_administracion_aiu > 0
    assert liquidacion.tarifa_total_factura_cop > liquidacion.subtotal_antes_iva


def test_puesto_sin_arma_costo_armamento_cero():
    """Un puesto sin arma no debe incluir costo de armamento."""
    liquidacion = calcular_tarifa_supervigilancia(
        modalidad=ModalidadServicioTarifa.VIGILANCIA_24H_SIN_ARMA,
        cantidad_puestos=2,
    )

    assert liquidacion.guardas_por_puesto == 4
    assert liquidacion.total_guardas_requeridos == 8
    assert liquidacion.costo_armamento_y_equipos == 0.0


def test_firma_digital_prefactura_sha256_consistente():
    """La firma digital SHA-256 debe ser determinista e inmutable."""
    ahora = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)
    hash_1 = generar_firma_digital_prefactura("FAC-202610-001", 5, "2026-10", 15_000_000.0, ahora)
    hash_2 = generar_firma_digital_prefactura("FAC-202610-001", 5, "2026-10", 15_000_000.0, ahora)

    assert len(hash_1) == 64
    assert hash_1 == hash_2


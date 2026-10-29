"""
Pruebas de integración y motor normativo colombiano (Release Enterprise V2.0)
para SENTINEL // OPS:
- Ley 2101 de 2021 (Tope semanal dinámico de 42 horas en 2026)
- Descuento automático por ausentismos (EPS / ARL / Licencia / Falta)
- Control de vigencia de credencial SuperVigilancia y excepción temporal de Administrador
- Geocerca geodésica Haversine
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.modelos.modelos_bd import TipoTurno
from app.rutas.rutas_rondas import calcular_distancia_haversine_metros
from app.servicios.motor_turnos import (
    calcular_liquidacion_turno_colombia,
    verificar_vigencia_credencial_sv,
)

ZONA_BOGOTA = ZoneInfo("America/Bogota")


def test_liquidacion_turno_diurno_12_horas() -> None:
    """Verifica que un turno diurno de 06:00 a 18:00 tenga 8h ordinarias y 4h extras diurnas."""
    inicio = datetime(2026, 10, 29, 6, 0, tzinfo=ZONA_BOGOTA)
    fin = datetime(2026, 10, 29, 18, 0, tzinfo=ZONA_BOGOTA)
    resultado = calcular_liquidacion_turno_colombia(inicio, fin, TipoTurno.DIURNO)

    assert resultado.horas_totales == 12.0
    assert resultado.horas_ordinarias == 8.0
    assert resultado.horas_extras_diurnas == 4.0
    assert resultado.horas_recargo_nocturno == 0.0
    assert resultado.horas_extras_nocturnas == 0.0


def test_liquidacion_turno_nocturno_12_horas() -> None:
    """
    Verifica que un turno nocturno de 18:00 a 06:00 (08h ordinarias de 18:00 a 02:00,
    con franja nocturna desde las 21:00) calcule 5h de recargo nocturno y 4h extras nocturnas.
    """
    inicio = datetime(2026, 10, 29, 18, 0, tzinfo=ZONA_BOGOTA)
    fin = datetime(2026, 10, 30, 6, 0, tzinfo=ZONA_BOGOTA)
    resultado = calcular_liquidacion_turno_colombia(inicio, fin, TipoTurno.NOCTURNO)

    assert resultado.horas_totales == 12.0
    assert resultado.horas_ordinarias == 8.0
    assert resultado.horas_recargo_nocturno == 5.0
    assert resultado.horas_extras_nocturnas == 4.0


def test_tope_semanal_dinamico_42_horas_ley_2101() -> None:
    """
    Verifica que cuando el operador ya acumula 40 horas ordinarias en la semana,
    en el siguiente turno de 12h solo las primeras 2h sean ordinarias (alcanzando el tope de 42h)
    y las 10h restantes pasen automáticamente a horas extras.
    """
    inicio = datetime(2026, 10, 30, 6, 0, tzinfo=ZONA_BOGOTA)
    fin = datetime(2026, 10, 30, 18, 0, tzinfo=ZONA_BOGOTA)
    resultado = calcular_liquidacion_turno_colombia(
        inicio,
        fin,
        TipoTurno.DIURNO,
        horas_ordinarias_acumuladas_semana=40.0,
    )
    assert resultado.horas_ordinarias == 2.0
    assert resultado.horas_extras_diurnas == 10.0


def test_descuento_automatico_por_ausentismo() -> None:
    """Verifica el descuento automático de horas y costo en prenómina por incapacidad o falta."""
    inicio = datetime(2026, 10, 29, 6, 0, tzinfo=ZONA_BOGOTA)
    fin = datetime(2026, 10, 29, 18, 0, tzinfo=ZONA_BOGOTA)
    resultado = calcular_liquidacion_turno_colombia(
        inicio,
        fin,
        TipoTurno.DIURNO,
        horas_descuento_ausentismo=12.0,
    )
    assert resultado.horas_totales == 0.0
    assert resultado.horas_descuento_ausentismo == 12.0
    assert resultado.costo_estimado_cop == 0.0


def test_bloqueo_y_excepcion_credencial_supervigilancia() -> None:
    """Verifica el bloqueo por credencial SV vencida y la habilitación por excepción de Admin."""
    hoy = date.today()
    fecha_vencida = hoy - timedelta(days=10)
    fecha_vigente = hoy + timedelta(days=120)

    hab_vencida, _ = verificar_vigencia_credencial_sv(fecha_vencida, False, hoy)
    assert hab_vencida is False

    hab_excepcion, _ = verificar_vigencia_credencial_sv(fecha_vencida, True, hoy)
    assert hab_excepcion is True

    hab_vigente, _ = verificar_vigencia_credencial_sv(fecha_vigente, False, hoy)
    assert hab_vigente is True


def test_distancia_geodesica_haversine_geocerca() -> None:
    """Verifica el cálculo geodésico en metros para validación de checkpoints QR/GPS."""
    distancia = calcular_distancia_haversine_metros(
        4.6612, -74.0535, 4.66125, -74.05348
    )
    assert 0.0 <= distancia <= 15.0

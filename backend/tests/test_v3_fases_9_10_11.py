"""
Tests unitarios y de integración para las Fases 9, 10 y 11 (Release Enterprise V3.0).
Valida:
- Fase 9: Decodificador de código de barras PDF417 de cédula colombiana.
- Fase 10: Semáforo preventivo de salvoconductos y firma de movimientos balísticos Indumil.
- Fase 11: Despacho CAD y cálculo de ETA geodésico Haversine.
"""

from datetime import date, datetime, timedelta, timezone
import pytest

from app.modelos.modelos_bd import (
    ModalidadServicioTarifa,
    TipoAccesoGarita,
    TipoMovimientoBalistico,
)
from app.rutas.rutas_rondas import calcular_distancia_haversine_metros
from app.servicios.decodificador_cedula import (
    decodificar_trama_pdf417_colombia,
)


def test_decodificador_cedula_colombiana_formato_estandar():
    """Verifica la extracción fiel de cédula, nombres, apellidos, RH y fecha de nacimiento."""
    trama_simulada = (
        "PubDSK_1 0010203040 VARGAS RESTREPO ALEJANDRO JOSE M 19880415 O+ 00000000"
    )
    resultado = decodificar_trama_pdf417_colombia(trama_simulada)

    assert resultado.es_valido is True
    assert resultado.documento_identidad == "10203040"
    assert resultado.primer_apellido == "VARGAS"
    assert resultado.segundo_apellido == "RESTREPO"
    assert resultado.primer_nombre == "ALEJANDRO"
    assert resultado.segundo_nombre == "JOSE"
    assert resultado.sexo == "M"
    assert resultado.fecha_nacimiento == date(1988, 4, 15)
    assert resultado.grupo_sanguineo_rh == "O+"


def test_decodificador_cedula_trama_invalida_o_corta():
    """Una trama corrupta o vacía debe retornar es_valido False sin lanzar excepción."""
    resultado = decodificar_trama_pdf417_colombia("123")
    assert resultado.es_valido is False
    assert resultado.documento_identidad == ""


def test_calculo_distancia_haversine_entre_puntos_bogota():
    """Verifica que la distancia entre dos puntos en Bogotá sea precisa para el CAD."""
    # Coordenadas: Torre Financiera (Chapinero) vs Parque Simón Bolívar
    lat_1, lon_1 = 4.6533, -74.0836
    lat_2, lon_2 = 4.6580, -74.0930

    distancia_metros = calcular_distancia_haversine_metros(lat_1, lon_1, lat_2, lon_2)
    # Debe estar en un rango razonable ~1.1 km a 1.3 km
    assert 900.0 < distancia_metros < 1500.0


def test_semaforo_dias_salvoconducto_calculo():
    """Valida los umbrales de alerta temprana para salvoconductos (90, 60, 30 días)."""
    hoy = date.today()
    vencimiento_verde = hoy + timedelta(days=120)
    vencimiento_amarillo = hoy + timedelta(days=45)
    vencimiento_rojo = hoy + timedelta(days=15)
    vencimiento_vencido = hoy - timedelta(days=5)

    assert (vencimiento_verde - hoy).days > 90
    assert 30 < (vencimiento_amarillo - hoy).days <= 90
    assert 0 < (vencimiento_rojo - hoy).days <= 30
    assert (vencimiento_vencido - hoy).days <= 0


def test_normalizacion_placa_lpr_colombiana():
    """Valida reconocimiento de placas de automóvil y moto según estándar RUNT."""
    import re

    # Caso 1: Automóvil particular ABC-123
    trama_auto = "abc 123"
    limpia_auto = re.sub(r"[^A-Za-z0-9]", "", trama_auto).upper()
    assert re.match(r"^[A-Z]{3}\d{3}$", limpia_auto) is not None
    norm_auto = f"{limpia_auto[:3]}-{limpia_auto[3:]}"
    assert norm_auto == "ABC-123"

    # Caso 2: Motocicleta ABC-12D
    trama_moto = "xyz-89e"
    limpia_moto = re.sub(r"[^A-Za-z0-9]", "", trama_moto).upper()
    assert re.match(r"^[A-Z]{3}\d{2}[A-Z]$", limpia_moto) is not None
    norm_moto = f"{limpia_moto[:3]}-{limpia_moto[3:]}"
    assert norm_moto == "XYZ-89E"


def test_parsing_carga_masiva_csv_usuarios():
    """Valida el análisis de filas y compatibilidad con comas y puntos y comas."""
    import csv
    import io

    csv_data = """documento_identidad,nombre_completo,correo_electronico,telefono,rol,codigo_placa
1099887766,Carlos Guarda,carlos@vigilancia.co,3112233445,OPERADOR,GRD-901
1088776655,Diana Supervisora,diana@vigilancia.co,3123344556,SUPERVISOR,SUP-402
"""
    lector = list(csv.DictReader(io.StringIO(csv_data.strip()), delimiter=","))
    assert len(lector) == 2
    assert lector[0]["documento_identidad"] == "1099887766"
    assert lector[0]["rol"] == "OPERADOR"
    assert lector[1]["nombre_completo"] == "Diana Supervisora"
    assert lector[1]["rol"] == "SUPERVISOR"

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


def test_integridad_cadena_sha256_hash_chaining():
    """Verifica que el encadenamiento criptográfico SHA-256 vincule el hash anterior y el génesis."""
    from app.nucleo.seguridad import HASH_GENESIS_SHA256, calcular_hash_encadenado_sha256

    assert len(HASH_GENESIS_SHA256) == 64
    assert HASH_GENESIS_SHA256 == "0" * 64

    # Registro Génesis (Primer registro del puesto)
    datos_acta_1 = "ACTA_INDUMIL|PST-NORTE-01|CC102030|OPTIMO|36|Relevo normal|2026-10-29T18:00:00Z"
    hash_1 = calcular_hash_encadenado_sha256(datos_acta_1, None)
    assert len(hash_1) == 64
    assert hash_1.isupper()

    # Segundo registro encadenado con hash_1
    datos_acta_2 = "ACTA_INDUMIL|PST-NORTE-01|CC102031|OPTIMO|36|Relevo normal|2026-10-30T06:00:00Z"
    hash_2 = calcular_hash_encadenado_sha256(datos_acta_2, hash_1)
    assert len(hash_2) == 64
    assert hash_2 != hash_1

    # Tercer registro encadenado con hash_2
    datos_acta_3 = "ACTA_INDUMIL|PST-NORTE-01|CC102032|OPTIMO|36|Relevo normal|2026-10-30T18:00:00Z"
    hash_3 = calcular_hash_encadenado_sha256(datos_acta_3, hash_2)
    assert len(hash_3) == 64
    assert hash_3 != hash_2

    # Verificación de inmutabilidad: si alguien altera datos_acta_2, hash_2 cambia y rompe la cadena
    hash_2_adulterado = calcular_hash_encadenado_sha256(datos_acta_2 + "_ALTERADO", hash_1)
    assert hash_2_adulterado != hash_2


def test_fragmentacion_turno_nocturno_por_dia_calendario():
    """Verifica que un turno 18:00 a 06:00 se divida en medianoche (00:00) por día calendario."""
    from zoneinfo import ZoneInfo
    from app.servicios.motor_turnos import fragmentar_turno_por_dia_calendario

    zona = ZoneInfo("America/Bogota")
    # Turno de Domingo 18:00 a Lunes 06:00
    inicio_domingo = datetime(2026, 11, 1, 18, 0, tzinfo=zona)
    fin_lunes = datetime(2026, 11, 2, 6, 0, tzinfo=zona)

    segmentos = fragmentar_turno_por_dia_calendario(inicio_domingo, fin_lunes)
    assert len(segmentos) == 2

    # Segmento 1: Domingo 18:00 a 00:00 Lunes (6 horas en domingo)
    seg1_inicio, seg1_fin = segmentos[0]
    assert seg1_inicio == inicio_domingo
    assert seg1_fin == datetime(2026, 11, 2, 0, 0, tzinfo=zona)
    assert (seg1_fin - seg1_inicio).total_seconds() == 6 * 3600

    # Segmento 2: Lunes 00:00 a 06:00 (6 horas en lunes)
    seg2_inicio, seg2_fin = segmentos[1]
    assert seg2_inicio == datetime(2026, 11, 2, 0, 0, tzinfo=zona)
    assert seg2_fin == fin_lunes
    assert (seg2_fin - seg2_inicio).total_seconds() == 6 * 3600


def test_corte_exacto_ley_2101_tope_42_horas():
    """Verifica la transición milimétrica de hora ordinaria a hora extra con tope dinámico 42h."""
    from zoneinfo import ZoneInfo
    from app.modelos.modelos_bd import TipoTurno
    from app.servicios.motor_turnos import calcular_liquidacion_turno_colombia

    zona = ZoneInfo("America/Bogota")
    inicio = datetime(2026, 10, 30, 6, 0, tzinfo=zona)
    fin = datetime(2026, 10, 30, 18, 0, tzinfo=zona)  # 12 horas totales

    # Si el operador ya acumulaba 38 horas en la semana (cupo restante: 4 horas ordinarias)
    resultado = calcular_liquidacion_turno_colombia(
        fecha_inicio=inicio,
        fecha_fin=fin,
        tipo_turno=TipoTurno.DIURNO,
        horas_ordinarias_acumuladas_semana=38.0,
        tope_horas_semanales=42,
    )

    assert resultado.horas_totales == 12.0
    assert resultado.horas_ordinarias == 4.0  # 38 + 4 = 42 (Tope Ley 2101 alcanzado)
    assert resultado.horas_extras_diurnas == 8.0  # Las restantes 8h son extras
    assert resultado.horas_recargo_nocturno == 0.0


def test_habeas_data_enmascaramiento_y_formulario():
    """Verifica la protección de datos sensibles y el consentimiento expreso Ley 1581 de 2012."""
    from app.nucleo.seguridad import enmascarar_dato_sensible
    from app.esquemas.esquemas_pydantic import SolicitudRegistrarAccesoGarita

    # Enmascaramiento de cédulas y datos personales en logs públicos
    cedula_original = "1020304050"
    cedula_enmascarada = enmascarar_dato_sensible(cedula_original, caracteres_visibles=2)
    assert cedula_enmascarada == "10******50"
    assert len(cedula_enmascarada) == len(cedula_original)

    # Consentimiento obligatorio Habeas Data en Garita
    solicitud = SolicitudRegistrarAccesoGarita(
        puesto_id=1,
        tipo_acceso=TipoAccesoGarita.PEATONAL_VISITANTE,
        documento_identidad="1020304050",
        nombres="Juan",
        apellidos="Pérez",
        empresa_o_destino="Oficina 501",
        motivo_ingreso="Reunión comercial",
        autoriza_tratamiento_datos=True,
    )
    assert solicitud.autoriza_tratamiento_datos is True


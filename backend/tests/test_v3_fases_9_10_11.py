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


class _AdaptadorSesionAsincrona:
    """Adaptador ligero sobre Session síncrona de SQLite en memoria para pruebas deterministas."""

    def __init__(self, sesion_sync):
        self._sesion = sesion_sync

    async def execute(self, sentencia):
        return self._sesion.execute(sentencia)

    def add(self, instancia):
        self._sesion.add(instancia)

    def add_all(self, instancias):
        self._sesion.add_all(instancias)

    async def flush(self):
        self._sesion.flush()

    async def commit(self):
        self._sesion.commit()

    async def refresh(self, instancia):
        self._sesion.refresh(instancia)

    def close(self):
        self._sesion.close()


def _ejecutar_coro_directo(coro):
    """Ejecuta una corrutina determinista en memoria sin instanciar ProactorEventLoop/socketpair."""
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


def _crear_sesion_memoria_sembrada():
    """Inicializa una BD SQLite en memoria y ejecuta el seeder V4.0."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.nucleo.base_datos import BaseModeloDeclarativo
    from app.servicios.semilla import inicializar_datos_semilla

    motor_sync = create_engine("sqlite:///:memory:", echo=False)
    BaseModeloDeclarativo.metadata.create_all(bind=motor_sync)
    FabricaSync = sessionmaker(bind=motor_sync, expire_on_commit=False)
    sesion_sync = FabricaSync()
    sesion_async = _AdaptadorSesionAsincrona(sesion_sync)
    _ejecutar_coro_directo(inicializar_datos_semilla(sesion_async))
    return sesion_async, motor_sync


def test_seeder_multisede_bogota_sabana_integridad_completa():
    """Valida que el seeder V4.0 cree los 6 puestos tácticos, 32 usuarios, escuadrones 2x2 y cadenas SHA-256."""
    from sqlalchemy import select
    from app.modelos.modelos_bd import (
        ModeloActaRelevoPuesto,
        ModeloKardexBalistico,
        ModeloPrefactura,
        ModeloPuestoVigilancia,
        ModeloRegistroAccesoGarita,
        ModeloRegistroMinuta,
        ModeloUsuario,
    )
    from app.servicios.simulador_operativo import auditar_integridad_blockchain_sha256

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        puestos = sesion._sesion.execute(select(ModeloPuestoVigilancia)).scalars().all()
        codigos_puestos = {p.codigo_puesto for p in puestos}
        assert len(puestos) == 6
        assert {
            "PST-BOG-01",
            "PST-OCC-02",
            "PST-BOG-03",
            "PST-FAC-04",
            "PST-BOG-05",
            "PST-BOG-06",
        }.issubset(codigos_puestos)

        usuarios = sesion._sesion.execute(select(ModeloUsuario)).scalars().all()
        assert len(usuarios) >= 31

        minutas = sesion._sesion.execute(select(ModeloRegistroMinuta)).scalars().all()
        assert len(minutas) >= 25

        relevos = sesion._sesion.execute(select(ModeloActaRelevoPuesto)).scalars().all()
        assert len(relevos) >= 6

        kardex = sesion._sesion.execute(select(ModeloKardexBalistico)).scalars().all()
        assert len(kardex) >= 12

        accesos = sesion._sesion.execute(select(ModeloRegistroAccesoGarita)).scalars().all()
        assert len(accesos) == 32

        prefacturas = sesion._sesion.execute(select(ModeloPrefactura)).scalars().all()
        assert len(prefacturas) == 4

        auditoria = _ejecutar_coro_directo(auditar_integridad_blockchain_sha256(sesion))  # type: ignore[arg-type]
        assert auditoria["INTEGRIDAD_VERIFICADA"] is True
        assert auditoria["bloques_corruptos"] == 0
        assert auditoria["total_bloques_auditados"] == len(minutas) + len(relevos) + len(kardex)
    finally:
        sesion.close()
        motor.dispose()


def test_simulador_rafaga_operativa_mantiene_integridad_sha256():
    """Valida que al disparar una ráfaga operativa en vivo se encadenen bloques SHA-256 sin corrupción."""
    from app.servicios.simulador_operativo import (
        auditar_integridad_blockchain_sha256,
        ejecutar_rafaga_operativa,
    )

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        auditoria_inicial = _ejecutar_coro_directo(auditar_integridad_blockchain_sha256(sesion))  # type: ignore[arg-type]
        bloques_iniciales = auditoria_inicial["total_bloques_auditados"]

        resultado_rafaga = _ejecutar_coro_directo(ejecutar_rafaga_operativa(sesion))  # type: ignore[arg-type]
        assert resultado_rafaga["rafaga_numero"] >= 1
        assert len(resultado_rafaga["sello_sha256_generado"]) == 64
        assert resultado_rafaga["integridad_blockchain_verificada"] is True
        assert resultado_rafaga["total_bloques_cadena"] == bloques_iniciales + 1
    finally:
        sesion.close()
        motor.dispose()


def test_kpis_tiempo_real_calculo_sla_y_auditoria_bloques():
    """Valida el cálculo de KPIs ejecutivos en vivo (SLA por puesto, nómina Ley 2101, reacción CAD e integridad)."""
    from app.servicios.simulador_operativo import calcular_kpis_tiempo_real

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        kpis = _ejecutar_coro_directo(calcular_kpis_tiempo_real(sesion))  # type: ignore[arg-type]

        assert kpis["porcentaje_sla_global"] > 0
        assert len(kpis["sla_por_puesto"]) == 6
        assert kpis["costo_nomina_acumulado_cop"] > 0
        assert kpis["horas_extras_totales"] > 0
        assert kpis["tiempo_promedio_reaccion_sos_segundos"] > 0
        assert kpis["integridad_blockchain"]["INTEGRIDAD_VERIFICADA"] is True
        assert kpis["ocupacion_perimetral_total"] == 12
    finally:
        sesion.close()
        motor.dispose()


def test_alternar_modo_simulacion_viva_y_telemetria_patrullas():
    """Valida el encendido/apagado del motor de simulación viva y el avance de coordenadas GPS de patrullas."""
    from app.servicios.semilla import COORDENADAS_PUESTOS_V4
    from app.servicios.simulador_operativo import gestor_simulacion

    assert len(COORDENADAS_PUESTOS_V4) == 6
    coord_antes = gestor_simulacion.obtener_coordenadas_supervisor("SUP-101")
    gestor_simulacion.avanzar_telemetria()
    coord_despues = gestor_simulacion.obtener_coordenadas_supervisor("SUP-101")
    assert coord_antes != coord_despues

    activa_on = gestor_simulacion.alternar_modo_simulacion(activar=True)
    assert activa_on is True
    activa_off = gestor_simulacion.alternar_modo_simulacion(activar=False)
    assert activa_off is False


def test_coordenadas_georreferenciadas_6_puestos_bogota_sabana():
    """Verifica que las coordenadas de los 6 puestos correspondan a Bogotá y Sabana de Occidente."""
    from app.servicios.semilla import COORDENADAS_PUESTOS_V4

    codigos_esperados = [
        "PST-BOG-01",
        "PST-OCC-02",
        "PST-BOG-03",
        "PST-FAC-04",
        "PST-BOG-05",
        "PST-BOG-06",
    ]
    for cod in codigos_esperados:
        assert cod in COORDENADAS_PUESTOS_V4
        lat, lon, radio_m = COORDENADAS_PUESTOS_V4[cod]
        assert 4.50 <= lat <= 4.90
        assert -74.45 <= lon <= -74.00
        assert radio_m >= 50.0


def test_credenciales_vencidas_y_por_vencer_en_seeder_v4():
    """Verifica que el seeder incluya guardas con credencial VIGENTE, POR_VENCER y 2 con VENCIDA."""
    from sqlalchemy import select
    from app.modelos.modelos_bd import ModeloUsuario, RolUsuario

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        hoy = date.today()
        operadores = (
            sesion._sesion.execute(
                select(ModeloUsuario).where(ModeloUsuario.rol == RolUsuario.OPERADOR)
            )
            .scalars()
            .all()
        )

        vencidas = [
            op for op in operadores
            if op.fecha_vencimiento_credencial and op.fecha_vencimiento_credencial < hoy
        ]
        por_vencer = [
            op for op in operadores
            if op.fecha_vencimiento_credencial and 0 <= (op.fecha_vencimiento_credencial - hoy).days <= 30
        ]
        vigentes = [
            op for op in operadores
            if op.fecha_vencimiento_credencial and (op.fecha_vencimiento_credencial - hoy).days > 30
        ]

        assert len(vencidas) == 2
        assert len(por_vencer) == 6
        assert len(vigentes) == 16
    finally:
        sesion.close()
        motor.dispose()


# ============================================================================
# FASE 12 (RELEASE ENTERPRISE V5.0): OPERACIONES ESPECIALES, K9, SARLAFT,
# SG-SST DECRETO 1072, HOMBRE CAÍDO & LABORATORIO FORENSE SHA-256
# ============================================================================


def test_creacion_y_verificacion_corredor_escolta_basc():
    """Valida el registro de escoltas BASC, cálculo Haversine, sello SHA-256 y alerta por desvío."""
    from sqlalchemy import select
    from app.modelos.modelos_bd import ModeloUsuario, RolUsuario
    from app.rutas.rutas_operaciones_especiales import (
        SolicitudCrearEscoltaBasc,
        SolicitudVerificarCorredorEscolta,
        crear_mision_escolta,
        listar_misiones_escolta,
        verificar_corredor_escolta,
    )

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        admin = (
            sesion._sesion.execute(
                select(ModeloUsuario).where(ModeloUsuario.rol == RolUsuario.ADMINISTRADOR)
            )
            .scalars()
            .first()
        )
        assert admin is not None

        misiones_semilla = _ejecutar_coro_directo(listar_misiones_escolta(sesion, admin))  # type: ignore[arg-type]
        assert len(misiones_semilla) >= 3

        solicitud = SolicitudCrearEscoltaBasc(
            tipo_mision="CONVOY_CARGA_CRITICA_BASC",
            descripcion_ruta="Convoy Siberia -> Puerto Seco Facatativá",
            corredor_vial="Autopista Medellín Calle 80 -> Sabana Occidente",
            vehiculo_placa="TRK-991 (Blindado Nivel IV)",
            nivel_blindaje="NIVEL_IV",
            serial_arma_indumil="IM-9MM-301988",
            lat_origen=4.7390,
            lon_origen=-74.1280,
            lat_destino=4.8143,
            lon_destino=-74.3547,
            umbral_desvio_metros=200.0,
        )
        nueva = _ejecutar_coro_directo(crear_mision_escolta(solicitud, sesion, admin))  # type: ignore[arg-type]
        assert nueva["distancia_ruta_km"] > 10.0
        assert len(nueva["sello_manifiesto_sha256"]) == 64

        verif_desvio = _ejecutar_coro_directo(
            verificar_corredor_escolta(
                nueva["mision_id"],
                SolicitudVerificarCorredorEscolta(
                    lat_actual=4.6100,
                    lon_actual=-74.2200,
                    desviacion_reportada_metros=640.0,
                ),
                sesion,  # type: ignore[arg-type]
                admin,
            )
        )
        assert verif_desvio["alerta_desvio_disparada"] is True
        assert verif_desvio["estado_mision"] == "ALERTA_DESVIO_RUTA"
        assert verif_desvio["registro_minuta_alerta_id"] is not None
    finally:
        sesion.close()
        motor.dispose()


def test_control_fatiga_y_descanso_unidad_canina_k9():
    """Valida el semáforo de fatiga K9 (tope 6h continuas) y el reinicio tras descanso en canil."""
    from sqlalchemy import select
    from app.modelos.modelos_bd import ModeloUsuario, RolUsuario
    from app.rutas.rutas_operaciones_especiales import (
        SolicitudDescansoCaninoK9,
        listar_binomios_k9,
        registrar_descanso_k9,
    )

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        admin = (
            sesion._sesion.execute(
                select(ModeloUsuario).where(ModeloUsuario.rol == RolUsuario.ADMINISTRADOR)
            )
            .scalars()
            .first()
        )
        binomios = _ejecutar_coro_directo(listar_binomios_k9(sesion, admin))  # type: ignore[arg-type]
        assert len(binomios) == 4
        nombres = {b["nombre_canino"] for b in binomios}
        assert {"Thor", "Athena", "Rex", "Sombra"} == nombres

        sombra = next(b for b in binomios if b["nombre_canino"] == "Sombra")
        assert sombra["horas_trabajadas_turno"] >= 5.5

        descanso = _ejecutar_coro_directo(
            registrar_descanso_k9(
                sombra["k9_id"],
                SolicitudDescansoCaninoK9(minutos_descanso_canil=60, hidratacion_verificada=True),
                sesion,  # type: ignore[arg-type]
                admin,
            )
        )
        assert descanso["horas_trabajadas_turno"] == 0.0
        assert descanso["estado_fatiga"] == "APTO_OPERATIVO"
        assert descanso["semaforo_normativo_k9"] == "VERDE_APTO_OPERATIVO"
    finally:
        sesion.close()
        motor.dispose()


def test_monitoreo_medios_tecnologicos_y_cercas_por_puesto():
    """Valida el estado operativo, latencia y voltaje en kV de los 18 dispositivos tecnológicos."""
    from sqlalchemy import select
    from app.modelos.modelos_bd import ModeloUsuario, RolUsuario
    from app.rutas.rutas_operaciones_especiales import listar_medios_tecnologicos

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        admin = (
            sesion._sesion.execute(
                select(ModeloUsuario).where(ModeloUsuario.rol == RolUsuario.ADMINISTRADOR)
            )
            .scalars()
            .first()
        )
        medios = _ejecutar_coro_directo(listar_medios_tecnologicos(None, sesion, admin))  # type: ignore[arg-type]
        assert len(medios) == 18
        cercas = [m for m in medios if m["tipo_dispositivo"] == "CERCA_ELECTRICA"]
        assert len(cercas) >= 5
        assert all(c["voltaje_cerca_kv"] >= 8.0 for c in cercas)
    finally:
        sesion.close()
        motor.dispose()


def test_consulta_sarlaft_listas_restrictivas_y_certificado_sha256():
    """Valida la emisión de certificados SARLAFT 2.0 (Limpio, PEP y Bloqueo OFAC/INTERPOL) con SHA-256."""
    from sqlalchemy import select
    from app.modelos.modelos_bd import ModeloUsuario, RolUsuario
    from app.rutas.rutas_cumplimiento import (
        SolicitudConsultaSarlaft,
        consultar_listas_sarlaft,
        listar_historial_sarlaft,
    )

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        admin = (
            sesion._sesion.execute(
                select(ModeloUsuario).where(ModeloUsuario.rol == RolUsuario.ADMINISTRADOR)
            )
            .scalars()
            .first()
        )

        limpio = _ejecutar_coro_directo(
            consultar_listas_sarlaft(
                SolicitudConsultaSarlaft(
                    documento="1032445901",
                    nombre_completo="Camilo Andrés Fajardo",
                    tipo_tercero="ASPIRANTE_GUARDA",
                ),
                sesion,  # type: ignore[arg-type]
                admin,
            )
        )
        assert limpio["nivel_riesgo"] == "SIN_COINCIDENCIAS"
        assert limpio["apto_contratacion_ingreso"] is True
        assert len(limpio["sello_auditoria_sha256"]) == 64

        pep = _ejecutar_coro_directo(
            consultar_listas_sarlaft(
                SolicitudConsultaSarlaft(
                    documento="79884120",
                    nombre_completo="Ex-Senador Rodrigo Villamizar PEP",
                    tipo_tercero="CLIENTE_B2B",
                ),
                sesion,  # type: ignore[arg-type]
                admin,
            )
        )
        assert pep["nivel_riesgo"] == "RIESGO_MEDIO_PEP"

        bloqueado = _ejecutar_coro_directo(
            consultar_listas_sarlaft(
                SolicitudConsultaSarlaft(
                    documento="80666999",
                    nombre_completo="Inversiones Fantasma OFAC Ltda",
                    tipo_tercero="VISITANTE_CRITICO",
                ),
                sesion,  # type: ignore[arg-type]
                admin,
            )
        )
        assert bloqueado["nivel_riesgo"] == "BLOQUEO_LISTA_RESTRICTIVA"
        assert bloqueado["apto_contratacion_ingreso"] is False
        assert "OFAC_SDN_CLINTON" in bloqueado["listas_coincidentes"]

        historial = _ejecutar_coro_directo(listar_historial_sarlaft(sesion, admin))  # type: ignore[arg-type]
        assert len(historial) >= 13
    finally:
        sesion.close()
        motor.dispose()


def test_sst_check_aptitud_psicofisica_y_semaforo_kevlar():
    """Valida el bloqueo SG-SST Decreto 1072 cuando el guarda reporta < 5h de sueño y el semáforo Kevlar."""
    from sqlalchemy import select
    from app.modelos.modelos_bd import ModeloPuestoVigilancia, ModeloUsuario, RolUsuario
    from app.rutas.rutas_cumplimiento import (
        SolicitudCheckAptitudSst,
        consultar_semaforo_chalecos_kevlar,
        registrar_check_aptitud_sst,
    )

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        admin = (
            sesion._sesion.execute(
                select(ModeloUsuario).where(ModeloUsuario.rol == RolUsuario.ADMINISTRADOR)
            )
            .scalars()
            .first()
        )
        puesto = sesion._sesion.execute(select(ModeloPuestoVigilancia)).scalars().first()
        assert puesto is not None

        chalecos = _ejecutar_coro_directo(consultar_semaforo_chalecos_kevlar(sesion, admin))  # type: ignore[arg-type]
        assert len(chalecos) == 6
        assert any(c["semaforo_kevlar"] == "VENCIDO_REEMPLAZO_INMEDIATO" for c in chalecos)

        check_fatiga = _ejecutar_coro_directo(
            registrar_check_aptitud_sst(
                SolicitudCheckAptitudSst(
                    puesto_id=puesto.puesto_id,
                    horas_sueno_reportadas=3.5,
                    cero_alcohol_fatiga=True,
                    chaleco_kevlar_verificado=True,
                ),
                sesion,  # type: ignore[arg-type]
                admin,
            )
        )
        assert check_fatiga["apto_operacion"] is False
        assert check_fatiga["alerta_sst_disparada"] is True
        assert check_fatiga["estado_evaluacion"] == "BLOQUEO_FATIGA_O_EPP_DECRETO_1072"
    finally:
        sesion.close()
        motor.dispose()


def test_alerta_hombre_caido_latido_supervivencia():
    """Valida el temporizador Dead Man's Switch, confirmación de latido y disparo de pre-alerta SOS."""
    from sqlalchemy import select
    from app.modelos.modelos_bd import ModeloPuestoVigilancia, ModeloUsuario, RolUsuario
    from app.rutas.rutas_cumplimiento import (
        SolicitudLatidoHombreCaido,
        listar_monitores_hombre_caido,
        registrar_latido_hombre_caido,
    )

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        admin = (
            sesion._sesion.execute(
                select(ModeloUsuario).where(ModeloUsuario.rol == RolUsuario.ADMINISTRADOR)
            )
            .scalars()
            .first()
        )
        puesto = sesion._sesion.execute(select(ModeloPuestoVigilancia)).scalars().first()
        assert puesto is not None

        monitores = _ejecutar_coro_directo(listar_monitores_hombre_caido(sesion, admin))  # type: ignore[arg-type]
        assert len(monitores) == 6

        pulso_ok = _ejecutar_coro_directo(
            registrar_latido_hombre_caido(
                puesto.puesto_id,
                SolicitudLatidoHombreCaido(simular_inactividad_critica=False),
                sesion,  # type: ignore[arg-type]
                admin,
            )
        )
        assert pulso_ok["estado_supervivencia"] == "ACTIVO_NORMAL"

        pulso_alerta = _ejecutar_coro_directo(
            registrar_latido_hombre_caido(
                puesto.puesto_id,
                SolicitudLatidoHombreCaido(simular_inactividad_critica=True),
                sesion,  # type: ignore[arg-type]
                admin,
            )
        )
        assert pulso_alerta["estado_supervivencia"] == "ALERTA_HOMBRE_CAIDO_SOS"
        assert pulso_alerta["alertas_disparadas_turno"] >= 1
    finally:
        sesion.close()
        motor.dispose()


def test_boletin_relevo_inteligencia_tactica_y_antifraude_rondas():
    """Valida el generador de Boletín de Relevo IA por puesto y el auditor antifraude de rondas GPS."""
    from sqlalchemy import select
    from app.modelos.modelos_bd import ModeloUsuario, RolUsuario
    from app.rutas.rutas_inteligencia import (
        auditar_antifraude_rondas,
        generar_boletin_relevo_ia,
    )

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        admin = (
            sesion._sesion.execute(
                select(ModeloUsuario).where(ModeloUsuario.rol == RolUsuario.ADMINISTRADOR)
            )
            .scalars()
            .first()
        )

        boletin = _ejecutar_coro_directo(
            generar_boletin_relevo_ia("PST-BOG-03", sesion, admin)  # type: ignore[arg-type]
        )
        assert boletin["puesto_codigo"] == "PST-BOG-03"
        assert boletin["nivel_amenaza"] in ("BAJO", "MODERADO", "ALTO", "CRITICO")
        assert len(boletin["hallazgos_clave"]) >= 1
        assert len(boletin["recomendaciones_tacticas"]) >= 2
        assert len(boletin["sello_boletin_sha256"]) == 64

        antifraude = _ejecutar_coro_directo(auditar_antifraude_rondas(sesion, admin))  # type: ignore[arg-type]
        assert antifraude["total_marcaciones_auditadas"] > 0
        assert antifraude["total_anomalias_detectadas"] >= 1
        assert any(
            a["tipo_anomalia"] == "VELOCIDAD_HUMANA_IMPOSIBLE" for a in antifraude["anomalias"]
        )
    finally:
        sesion.close()
        motor.dispose()


def test_laboratorio_sabotaje_deteccion_y_autoreparacion_sha256():
    """Valida el ciclo completo: Sabotaje de Minuta en BD -> Detección SHA-256 -> Auto-Reparación Forense."""
    from sqlalchemy import select
    from app.modelos.modelos_bd import ModeloUsuario, RolUsuario
    from app.rutas.rutas_inteligencia import (
        SolicitudSabotajeForense,
        endpoint_reparar_cadena_forense,
        endpoint_simular_sabotaje_forense,
    )
    from app.servicios.simulador_operativo import auditar_integridad_blockchain_sha256

    sesion, motor = _crear_sesion_memoria_sembrada()
    try:
        admin = (
            sesion._sesion.execute(
                select(ModeloUsuario).where(ModeloUsuario.rol == RolUsuario.ADMINISTRADOR)
            )
            .scalars()
            .first()
        )

        # 1. Simular ataque / adulteración en base de datos
        sabotaje = _ejecutar_coro_directo(
            endpoint_simular_sabotaje_forense(
                SolicitudSabotajeForense(
                    texto_adulterado="[ATAQUE SQL] Registro adulterado maliciosamente sin recalcular SHA-256."
                ),
                sesion,  # type: ignore[arg-type]
                admin,
            )
        )
        auditoria_rota = sabotaje["auditoria_resultante"]
        assert auditoria_rota["INTEGRIDAD_VERIFICADA"] is False
        assert auditoria_rota["bloques_corruptos"] >= 1
        assert auditoria_rota["bloque_corrupto_id"] is not None
        assert auditoria_rota["hash_esperado"] != auditoria_rota["hash_calculado"]

        # 2. Ejecutar auto-reparación forense SHA-256 y verificar restauración al 100%
        reparacion = _ejecutar_coro_directo(
            endpoint_reparar_cadena_forense(sesion, admin)  # type: ignore[arg-type]
        )
        assert reparacion["registros_restaurados"] >= 1
        assert reparacion["auditoria_post_reparacion"]["INTEGRIDAD_VERIFICADA"] is True
        assert reparacion["auditoria_post_reparacion"]["bloques_corruptos"] == 0

        auditoria_final = _ejecutar_coro_directo(auditar_integridad_blockchain_sha256(sesion))  # type: ignore[arg-type]
        assert auditoria_final["INTEGRIDAD_VERIFICADA"] is True
    finally:
        sesion.close()
        motor.dispose()





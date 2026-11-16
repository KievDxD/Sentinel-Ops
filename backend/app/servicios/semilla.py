"""
Servicio de inicialización de datos semilla (Seed Release Enterprise V4.0) para SENTINEL // OPS.
Puebla una operación hiperrealista y georreferenciada en Bogotá D.C. y el corredor industrial
de Sabana de Occidente (Madrid, Cota/Siberia, Facatativá - Cundinamarca) bajo el tenant
`EMPRESA-SEGURIDAD-COLOMBIA-01`.

Incluye:
- 6 Puestos de Vigilancia B2B reales con geocercas y dotación Indumil.
- 32 Usuarios en los 5 roles RBAC (5 cuentas maestras + 3 supervisores motorizados + 24 guardas en escuadrones 2x2).
- Malla histórica y futura de Turnos 2x2 (14 días) liquidada con Ley 2101 (42h semanales y corte a medianoche).
- 3 Ausentismos reales (EPS, ARL Nivel V, Licencia Remunerada) con descuentos aplicados.
- 6 Actas de Relevo y 26 Anotaciones de Minuta Digital encadenadas con SHA-256 desde el génesis ('0' * 64).
- Kardex Balístico DCCA Indumil encadenado con SHA-256 y Certificados Anuales de Polígono.
- Censo en Garita (12 activos DENTRO + 20 históricos SALIO) con placas RUNT y Habeas Data Ley 1581.
- 4 Prefacturas comerciales B2B emitidas bajo tarifa regulada SuperVigilancia y Art. 462-1 E.T. DIAN.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select

from app.modelos.modelos_bd import (
    EstadoAccesoGarita,
    EstadoAlertaSos,
    EstadoDespachoPatrulla,
    EstadoFactura,
    EstadoItemDotacion,
    EstadoSolicitudIntercambio,
    EstadoTurno,
    ModalidadServicioTarifa,
    ModeloActaRelevoPuesto,
    ModeloAlertaPanicoSos,
    ModeloAusentismo,
    ModeloBinomioCaninoK9,
    ModeloCertificadoPoligono,
    ModeloCertificadoSarlaft,
    ModeloCheckAptitudSst,
    ModeloDespachoPatrulla,
    ModeloDotacionPuesto,
    ModeloKardexBalistico,
    ModeloMarcacionRonda,
    ModeloMedioTecnologico,
    ModeloMisionEscoltaBasc,
    ModeloMonitoreoHombreCaido,
    ModeloPrefactura,
    ModeloPuestoVigilancia,
    ModeloPuntoControlRonda,
    ModeloRegistroAccesoGarita,
    ModeloRegistroMinuta,
    ModeloSolicitudIntercambio,
    ModeloTurno,
    ModeloUsuario,
    NivelCursoVigilancia,
    NivelPrioridad,
    RolUsuario,
    TipoAccesoGarita,
    TipoAusentismo,
    TipoMovimientoBalistico,
    TipoRegistroMinuta,
    TipoTurno,
    VisibilidadMinuta,
)
from app.nucleo.base_datos import Base, FabricaSesionesAsincronas, motor_bd
from app.nucleo.seguridad import (
    HASH_GENESIS_SHA256,
    calcular_hash_encadenado_sha256,
    encriptar_contrasena,
)
from app.rutas.rutas_rondas import calcular_distancia_haversine_metros
from app.servicios.motor_tarificacion import (
    calcular_tarifa_supervigilancia,
    generar_firma_digital_prefactura,
)
from app.servicios.motor_turnos import (
    generar_matriz_cobertura_puesto_2x2,
    validar_factibilidad_intercambio,
)

TENANT_PRINCIPAL = "EMPRESA-SEGURIDAD-COLOMBIA-01"
ZONA_BOGOTA = ZoneInfo("America/Bogota")

# Coordenadas georreferenciadas oficiales por código de puesto
COORDENADAS_PUESTOS_V4: dict[str, tuple[float, float, float]] = {
    "PST-BOG-01": (4.6533, -74.0560, 80.0),   # Chapinero - Torre Financiera
    "PST-OCC-02": (4.7820, -74.3210, 150.0),  # Madrid/Facatativá - Parque Logístico Sabana
    "PST-BOG-03": (4.7390, -74.1280, 120.0),  # Cota/Calle 80 - Zona Franca Siberia
    "PST-FAC-04": (4.8143, -74.3547, 100.0),  # Facatativá - Planta Agroindustrial Los Andes
    "PST-BOG-05": (4.6482, -74.0985, 60.0),   # Salitre - Reserva del Parque
    "PST-BOG-06": (4.6295, -74.1120, 50.0),   # Puente Aranda - Centro de Datos & Telecom
}


async def inicializar_datos_semilla(sesion_externa: object | None = None) -> None:
    """Garantiza la creación del esquema SQLAlchemy y puebla la base de datos si está vacía."""
    if sesion_externa is not None:
        sesion_interna = getattr(sesion_externa, "_sesion", None)
        bind_sincrono = getattr(sesion_interna, "bind", None) if sesion_interna is not None else None
        if bind_sincrono is not None:
            Base.metadata.create_all(bind=bind_sincrono)
        await _ejecutar_semilla_en_sesion(sesion_externa)  # type: ignore[arg-type]
        return
    async with motor_bd.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with FabricaSesionesAsincronas() as sesion:
        await _ejecutar_semilla_en_sesion(sesion)


async def _ejecutar_semilla_en_sesion(sesion: object) -> None:
    """Ejecuta la inserción completa del seeder V4.0 sobre la sesión provista."""
    if True:
        consulta_existente = select(ModeloUsuario).limit(1)
        resultado = await sesion.execute(consulta_existente)  # type: ignore[attr-defined]
        if resultado.scalar_one_or_none() is not None:
            return

        # Pre-cálculo único de hash bcrypt para no bloquear el Event Loop
        contrasena_demo: str = encriptar_contrasena("Sentinel2026*")
        hoy: date = date.today()
        ahora_utc: datetime = datetime.now(timezone.utc)

        # =====================================================================
        # 1. CREAR 6 PUESTOS DE VIGILANCIA REALES (BOGOTÁ & SABANA DE OCCIDENTE)
        # =====================================================================
        puesto_1 = ModeloPuestoVigilancia(
            codigo_puesto="PST-BOG-01",
            nombre_puesto="Centro Empresarial Torre Financiera (Bogotá - Chapinero)",
            empresa_cliente="Banca Corporativa de Colombia S.A.",
            direccion_ubicacion="Carrera 7 # 76-35, Chapinero Financiero",
            ciudad="Bogotá D.C.",
            requiere_armamento=True,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )
        puesto_2 = ModeloPuestoVigilancia(
            codigo_puesto="PST-OCC-02",
            nombre_puesto="Parque Logístico Industrial Sabana (Corredor Madrid - Facatativá)",
            empresa_cliente="Logística Andina S.A.S.",
            direccion_ubicacion="Km 19 Troncal de Occidente Vía Madrid - Facatativá",
            ciudad="Madrid (Cundinamarca)",
            requiere_armamento=True,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )
        puesto_3 = ModeloPuestoVigilancia(
            codigo_puesto="PST-BOG-03",
            nombre_puesto="Zona Franca Metropolitana Siberia (Cota / Calle 80)",
            empresa_cliente="Consorcio Aduanero Industrial Siberia S.A.",
            direccion_ubicacion="Autopista Medellín Km 7.5 Glorieta Siberia",
            ciudad="Cota (Cundinamarca)",
            requiere_armamento=True,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )
        puesto_4 = ModeloPuestoVigilancia(
            codigo_puesto="PST-FAC-04",
            nombre_puesto="Planta Agroindustrial Los Andes (Facatativá, Cundinamarca)",
            empresa_cliente="Agroexportadora de la Sabana S.A.",
            direccion_ubicacion="Sector Industrial El Corzo Km 32 Vía Facatativá",
            ciudad="Facatativá (Cundinamarca)",
            requiere_armamento=True,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )
        puesto_5 = ModeloPuestoVigilancia(
            codigo_puesto="PST-BOG-05",
            nombre_puesto="Complejo Residencial Reserva del Parque (Bogotá - Salitre)",
            empresa_cliente="Copropiedad Reserva del Salitre P.H.",
            direccion_ubicacion="Avenida La Esperanza # 68B-45, Ciudad Salitre",
            ciudad="Bogotá D.C.",
            requiere_armamento=False,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )
        puesto_6 = ModeloPuestoVigilancia(
            codigo_puesto="PST-BOG-06",
            nombre_puesto="Centro de Datos & Nodo Telecomunicaciones (Bogotá - Zona Industrial)",
            empresa_cliente="Red Nacional de Fibra & DataCenter Tier-IV S.A.S.",
            direccion_ubicacion="Avenida Calle 13 # 42-18, Puente Aranda Industrial",
            ciudad="Bogotá D.C.",
            requiere_armamento=True,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )

        puestos_lista = [puesto_1, puesto_2, puesto_3, puesto_4, puesto_5, puesto_6]
        sesion.add_all(puestos_lista)
        await sesion.flush()

        # =====================================================================
        # 2. DOTACIÓN Y ARMAMENTO INDUMIL DCCA PARA LOS 6 PUESTOS
        # =====================================================================
        dotaciones_lista = [
            ModeloDotacionPuesto(
                puesto_id=puesto_1.puesto_id,
                tipo_arma="Revólver Indumil Llama Martial Calibre .38L (x2) + Escopeta 12GA (x2)",
                serial_arma="IM-884920",
                numero_salvoconducto_indumil="DCCA-TEN-2026-884120",
                tipo_salvoconducto="TENENCIA",
                fecha_vencimiento_salvoconducto=hoy + timedelta(days=215),  # VERDE
                cantidad_municion_autorizada=24,
                serial_chaleco_balistico="CHB-IIIA-BOG01",
                serie_radio_comunicacion="MOT-DEP450-101",
                celular_corporativo_imei="358901234560001",
                tiene_linterna_tactica=True,
                llaves_y_minutas_fisicas=True,
            ),
            ModeloDotacionPuesto(
                puesto_id=puesto_2.puesto_id,
                tipo_arma="Escopeta Repetición Indumil Calibre 12 GA",
                serial_arma="IM-12G-773190",
                numero_salvoconducto_indumil="DCCA-TEN-2026-551902",
                tipo_salvoconducto="TENENCIA",
                fecha_vencimiento_salvoconducto=hoy + timedelta(days=52),   # AMARILLO (<60d)
                cantidad_municion_autorizada=30,
                serial_chaleco_balistico="CHB-IIIA-OCC02",
                serie_radio_comunicacion="MOT-DEP450-202",
                celular_corporativo_imei="358901234560002",
                tiene_linterna_tactica=True,
                llaves_y_minutas_fisicas=True,
            ),
            ModeloDotacionPuesto(
                puesto_id=puesto_3.puesto_id,
                tipo_arma="Revólver Indumil Llama Martial .38L (Escuadrón Triple)",
                serial_arma="IM-38L-662104",
                numero_salvoconducto_indumil="DCCA-TEN-2026-339011",
                tipo_salvoconducto="TENENCIA",
                fecha_vencimiento_salvoconducto=hoy + timedelta(days=18),   # ROJO CRÍTICO (<25d)
                cantidad_municion_autorizada=36,
                serial_chaleco_balistico="CHB-IIIA-SIB03",
                serie_radio_comunicacion="MOT-DEP450-303",
                celular_corporativo_imei="358901234560003",
                tiene_linterna_tactica=True,
                llaves_y_minutas_fisicas=True,
            ),
            ModeloDotacionPuesto(
                puesto_id=puesto_4.puesto_id,
                tipo_arma="Escopeta Mossberg 500 Calibre 12 GA + Revólver .38L",
                serial_arma="IM-12G-509218",
                numero_salvoconducto_indumil="DCCA-POR-2026-712045",
                tipo_salvoconducto="PORTE",
                fecha_vencimiento_salvoconducto=hoy + timedelta(days=145),  # VERDE
                cantidad_municion_autorizada=25,
                serial_chaleco_balistico="CHB-IIIA-FAC04",
                serie_radio_comunicacion="MOT-DEP450-404",
                celular_corporativo_imei="358901234560004",
                tiene_linterna_tactica=True,
                llaves_y_minutas_fisicas=True,
            ),
            ModeloDotacionPuesto(
                puesto_id=puesto_5.puesto_id,
                tipo_arma="Medios Tecnológicos + Binomio Canino / Bastón Tonfa Policarbonato",
                serial_arma="NL-CAN-90124",
                numero_salvoconducto_indumil="SV-MED-TEC-2026-901",
                tipo_salvoconducto="TENENCIA",
                fecha_vencimiento_salvoconducto=hoy + timedelta(days=290),  # VERDE
                cantidad_municion_autorizada=6,
                serial_chaleco_balistico="CHB-IIA-SAL05",
                serie_radio_comunicacion="MOT-DEP450-505",
                celular_corporativo_imei="358901234560005",
                tiene_linterna_tactica=True,
                llaves_y_minutas_fisicas=True,
            ),
            ModeloDotacionPuesto(
                puesto_id=puesto_6.puesto_id,
                tipo_arma="Pistola Córdova Indumil 9x19mm NATO + Revólver .38L",
                serial_arma="IM-9MM-301988",
                numero_salvoconducto_indumil="DCCA-TEN-2026-998123",
                tipo_salvoconducto="TENENCIA",
                fecha_vencimiento_salvoconducto=hoy + timedelta(days=44),   # AMARILLO (<60d)
                cantidad_municion_autorizada=45,
                serial_chaleco_balistico="CHB-IIIA-DAT06",
                serie_radio_comunicacion="MOT-DGP8550-606",
                celular_corporativo_imei="358901234560006",
                tiene_linterna_tactica=True,
                llaves_y_minutas_fisicas=True,
            ),
        ]
        sesion.add_all(dotaciones_lista)
        await sesion.flush()

        # =====================================================================
        # 3. USUARIOS: 5 CUENTAS MAESTRAS + 3 SUPERVISORES CAD + 24 GUARDAS 2X2
        # =====================================================================
        admin = ModeloUsuario(
            documento_identidad="CC-80123456",
            nombre_completo="Comandante Alejandro Vargas Restrepo",
            correo_electronico="admin@sentinelops.co",
            telefono="+57 310 450 1100",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.ADMINISTRADOR,
            codigo_placa="PL-001",
            puesto_base_id=puesto_1.puesto_id,
            numero_credencial_sv="SV-DIR-00192",
            fecha_vencimiento_credencial=hoy + timedelta(days=365),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=365),
            nivel_curso=NivelCursoVigilancia.ESPECIALIZACION,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )
        supervisor_1 = ModeloUsuario(
            documento_identidad="CC-79654321",
            nombre_completo="Capitán Valeria Mendoza Ospina",
            correo_electronico="supervisor@sentinelops.co",
            telefono="+57 315 890 2200",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.SUPERVISOR,
            codigo_placa="SUP-101",
            puesto_base_id=puesto_1.puesto_id,
            numero_credencial_sv="SV-SUP-44810",
            fecha_vencimiento_credencial=hoy + timedelta(days=280),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=250),
            nivel_curso=NivelCursoVigilancia.ESPECIALIZACION,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )
        supervisor_2 = ModeloUsuario(
            documento_identidad="CC-79881204",
            nombre_completo="Teniente Ricardo Andrés Bohórquez (Patrulla Calle 13 / Sabana)",
            correo_electronico="supervisor2@sentinelops.co",
            telefono="+57 316 512 3300",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.SUPERVISOR,
            codigo_placa="SUP-102",
            puesto_base_id=puesto_2.puesto_id,
            numero_credencial_sv="SV-SUP-44811",
            fecha_vencimiento_credencial=hoy + timedelta(days=210),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=190),
            nivel_curso=NivelCursoVigilancia.ESPECIALIZACION,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )
        supervisor_3 = ModeloUsuario(
            documento_identidad="CC-80334912",
            nombre_completo="Sargento Primero Mauricio Pinzón (Patrulla Autopista Medellín / Siberia)",
            correo_electronico="supervisor3@sentinelops.co",
            telefono="+57 317 623 4400",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.SUPERVISOR,
            codigo_placa="SUP-103",
            puesto_base_id=puesto_3.puesto_id,
            numero_credencial_sv="SV-SUP-44812",
            fecha_vencimiento_credencial=hoy + timedelta(days=175),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=165),
            nivel_curso=NivelCursoVigilancia.ESPECIALIZACION,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )
        supervisor_4 = ModeloUsuario(
            documento_identidad="CC-80992145",
            nombre_completo="Intendente Jefe Héctor Fabio Aristizábal (Patrulla Av. Boyacá / Salitre)",
            correo_electronico="supervisor4@sentinelops.co",
            telefono="+57 318 734 5500",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.SUPERVISOR,
            codigo_placa="SUP-104",
            puesto_base_id=puesto_6.puesto_id,
            numero_credencial_sv="SV-SUP-44813",
            fecha_vencimiento_credencial=hoy + timedelta(days=240),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=220),
            nivel_curso=NivelCursoVigilancia.ESPECIALIZACION,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )
        rrhh = ModeloUsuario(
            documento_identidad="CC-52981234",
            nombre_completo="Dra. Laura Sofía Cárdenas (Directora RRHH & Nómina)",
            correo_electronico="rrhh@sentinelops.co",
            telefono="+57 311 340 5500",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.RRHH,
            codigo_placa="RRH-201",
            puesto_base_id=puesto_1.puesto_id,
            numero_credencial_sv="SV-ADM-20100",
            fecha_vencimiento_credencial=hoy + timedelta(days=365),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=365),
            nivel_curso=NivelCursoVigilancia.FUNDAMENTACION,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )
        cliente = ModeloUsuario(
            documento_identidad="NIT-900456123",
            nombre_completo="Dr. Roberto Silva (Director Seguridad Torre Financiera)",
            correo_electronico="cliente@sentinelops.co",
            telefono="+57 314 220 9900",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.CLIENTE,
            codigo_placa="CLI-901",
            puesto_base_id=puesto_1.puesto_id,
            tenant_id=TENANT_PRINCIPAL,
            activo=True,
        )

        # Definición de los 24 Guardas (4 por cada uno de los 6 puestos 24/7)
        # Incluye credenciales VIGENTES (>30d), POR VENCER (5-25d) y 2 VENCIDAS (<0d)
        datos_guardas = [
            # Escuadrón 1: PST-BOG-01 (Torre Financiera Chapinero)
            ("CC-1020456789", "Guarda Carlos Andrés Ramírez", "operador1@sentinelops.co", "OPR-1001", puesto_1.puesto_id, "SV-OPR-88201", 190, NivelCursoVigilancia.ESPECIALIZACION),
            ("CC-1032987654", "Guarda Julián Esteban Pineda", "operador2@sentinelops.co", "OPR-1002", puesto_1.puesto_id, "SV-OPR-88202", 145, NivelCursoVigilancia.REENTRENAMIENTO),
            ("CC-1045123987", "Guarda Mateo Suárez Delgado", "operador3@sentinelops.co", "OPR-1003", puesto_1.puesto_id, "SV-OPR-88203", 14, NivelCursoVigilancia.REENTRENAMIENTO),   # POR VENCER (14d)
            ("CC-1018445901", "Guarda Jhon Jairo Castañeda", "operador4@sentinelops.co", "OPR-1004", puesto_1.puesto_id, "SV-OPR-88204", 210, NivelCursoVigilancia.ESPECIALIZACION),
            # Escuadrón 2: PST-OCC-02 (Parque Logístico Sabana - Madrid)
            ("CC-1052678123", "Guarda Diego Alejandro Morales", "operador5@sentinelops.co", "OPR-1005", puesto_2.puesto_id, "SV-OPR-88205", 205, NivelCursoVigilancia.ESPECIALIZACION),
            ("CC-1063789234", "Guarda Camilo Ernesto Herrera", "operador6@sentinelops.co", "OPR-1006", puesto_2.puesto_id, "SV-OPR-88206", 175, NivelCursoVigilancia.REENTRENAMIENTO),
            ("CC-1074890345", "Guarda Brayan Alexis Castro", "operador7@sentinelops.co", "OPR-1007", puesto_2.puesto_id, "SV-OPR-88207", 21, NivelCursoVigilancia.FUNDAMENTACION),    # POR VENCER (21d)
            ("CC-1070991234", "Guarda Wilmer Giovanny Roa", "operador8@sentinelops.co", "OPR-1008", puesto_2.puesto_id, "SV-OPR-88208", 130, NivelCursoVigilancia.REENTRENAMIENTO),
            # Escuadrón 3: PST-BOG-03 (Zona Franca Siberia - Cota)
            ("CC-1085901456", "Guarda Juan Sebastián Ríos", "operador9@sentinelops.co", "OPR-1009", puesto_3.puesto_id, "SV-OPR-88209", 230, NivelCursoVigilancia.ESPECIALIZACION),
            ("CC-1096012567", "Guarda Cristian Camilo Ortiz", "operador10@sentinelops.co", "OPR-1010", puesto_3.puesto_id, "SV-OPR-88210", 9, NivelCursoVigilancia.REENTRENAMIENTO),   # POR VENCER (9d)
            ("CC-1107123678", "Guarda Andrés Felipe Zapata", "operador11@sentinelops.co", "OPR-1011", puesto_3.puesto_id, "SV-OPR-88211", -6, NivelCursoVigilancia.FUNDAMENTACION),     # VENCIDA (-6d)
            ("CC-1014228901", "Guarda Édgar Leonardo Quintero", "operador12@sentinelops.co", "OPR-1012", puesto_3.puesto_id, "SV-OPR-88212", 180, NivelCursoVigilancia.ESPECIALIZACION),
            # Escuadrón 4: PST-FAC-04 (Planta Agroindustrial Los Andes - Facatativá)
            ("CC-1072665431", "Guarda Óscar Iván Velásquez", "operador13@sentinelops.co", "OPR-1013", puesto_4.puesto_id, "SV-OPR-88213", 160, NivelCursoVigilancia.REENTRENAMIENTO),
            ("CC-1073881920", "Guarda Edwin Ferney Garzón", "operador14@sentinelops.co", "OPR-1014", puesto_4.puesto_id, "SV-OPR-88214", 18, NivelCursoVigilancia.REENTRENAMIENTO),   # POR VENCER (18d)
            ("CC-1075112390", "Guarda Yeison Fabián Murcia", "operador15@sentinelops.co", "OPR-1015", puesto_4.puesto_id, "SV-OPR-88215", 250, NivelCursoVigilancia.ESPECIALIZACION),
            ("CC-1076334512", "Guarda Néstor Raúl Pachón", "operador16@sentinelops.co", "OPR-1016", puesto_4.puesto_id, "SV-OPR-88216", 110, NivelCursoVigilancia.FUNDAMENTACION),
            # Escuadrón 5: PST-BOG-05 (Complejo Residencial Reserva del Parque - Salitre)
            ("CC-1019887123", "Guarda Luisa Fernanda Téllez (Manejadora Canina)", "operador17@sentinelops.co", "OPR-1017", puesto_5.puesto_id, "SV-CAN-88217", 275, NivelCursoVigilancia.ESPECIALIZACION),
            ("CC-1022449811", "Guarda Miguel Ángel Pedraza", "operador18@sentinelops.co", "OPR-1018", puesto_5.puesto_id, "SV-OPR-88218", 140, NivelCursoVigilancia.REENTRENAMIENTO),
            ("CC-1023991045", "Guarda Paola Andrea Bermúdez", "operador19@sentinelops.co", "OPR-1019", puesto_5.puesto_id, "SV-OPR-88219", 11, NivelCursoVigilancia.FUNDAMENTACION),    # POR VENCER (11d)
            ("CC-1024776190", "Guarda Duván Stiven Alarcón", "operador20@sentinelops.co", "OPR-1020", puesto_5.puesto_id, "SV-OPR-88220", -12, NivelCursoVigilancia.FUNDAMENTACION),   # VENCIDA (-12d)
            # Escuadrón 6: PST-BOG-06 (Centro de Datos & Nodo Telecom - Puente Aranda)
            ("CC-1030554129", "Guarda Sergio Alejandro Chaparro", "operador21@sentinelops.co", "OPR-1021", puesto_6.puesto_id, "SV-ESP-88221", 310, NivelCursoVigilancia.ESPECIALIZACION),
            ("CC-1031667890", "Guarda Fabián DaríoForero", "operador22@sentinelops.co", "OPR-1022", puesto_6.puesto_id, "SV-ESP-88222", 240, NivelCursoVigilancia.ESPECIALIZACION),
            ("CC-1033778912", "Guarda Jhonatan David Laverde", "operador23@sentinelops.co", "OPR-1023", puesto_6.puesto_id, "SV-ESP-88223", 23, NivelCursoVigilancia.REENTRENAMIENTO), # POR VENCER (23d)
            ("CC-1034889023", "Guarda Víctor Manuel Salamanca", "operador24@sentinelops.co", "OPR-1024", puesto_6.puesto_id, "SV-ESP-88224", 195, NivelCursoVigilancia.ESPECIALIZACION),
        ]

        operadores: list[ModeloUsuario] = []
        for idx, (doc, nombre, correo, placa, p_id, cred_sv, dias_venc, nivel) in enumerate(datos_guardas, start=1):
            op = ModeloUsuario(
                documento_identidad=doc,
                nombre_completo=nombre,
                correo_electronico=correo,
                telefono=f"+57 320 771 {3300 + idx:04d}",
                contrasena_encriptada=contrasena_demo,
                rol=RolUsuario.OPERADOR,
                codigo_placa=placa,
                puesto_base_id=p_id,
                numero_credencial_sv=cred_sv,
                fecha_vencimiento_credencial=hoy + timedelta(days=dias_venc),
                fecha_vencimiento_psicofisico=hoy + timedelta(days=max(15, dias_venc + 30)),
                nivel_curso=nivel,
                excepcion_credencial_autorizada=False,
                tenant_id=TENANT_PRINCIPAL,
                activo=True,
            )
            operadores.append(op)

        sesion.add_all(
            [admin, supervisor_1, supervisor_2, supervisor_3, supervisor_4, rrhh, cliente, *operadores]
        )
        await sesion.flush()

        # =====================================================================
        # 4. MALLA DE TURNOS 2X2 (ÚLTIMOS 7 DÍAS + PRÓXIMOS 7 DÍAS = 14 DÍAS)
        # =====================================================================
        fecha_inicio_malla = hoy - timedelta(days=7)
        escuadras_puestos = [
            (puesto_1.puesto_id, [operadores[0].usuario_id, operadores[1].usuario_id, operadores[2].usuario_id, operadores[3].usuario_id]),
            (puesto_2.puesto_id, [operadores[4].usuario_id, operadores[5].usuario_id, operadores[6].usuario_id, operadores[7].usuario_id]),
            (puesto_3.puesto_id, [operadores[8].usuario_id, operadores[9].usuario_id, operadores[10].usuario_id, operadores[11].usuario_id]),
            (puesto_4.puesto_id, [operadores[12].usuario_id, operadores[13].usuario_id, operadores[14].usuario_id, operadores[15].usuario_id]),
            (puesto_5.puesto_id, [operadores[16].usuario_id, operadores[17].usuario_id, operadores[18].usuario_id, operadores[19].usuario_id]),
            (puesto_6.puesto_id, [operadores[20].usuario_id, operadores[21].usuario_id, operadores[22].usuario_id, operadores[23].usuario_id]),
        ]

        turnos_guardados: list[ModeloTurno] = []
        for p_id, ops_ids in escuadras_puestos:
            matriz = generar_matriz_cobertura_puesto_2x2(
                puesto_id=p_id,
                operadores_ids=ops_ids,
                fecha_inicio_ciclo=fecha_inicio_malla,
                cantidad_dias=14,
            )
            for datos_t in matriz:
                es_pasado = datos_t["fecha_fin"] < ahora_utc
                es_actual = datos_t["fecha_inicio"] <= ahora_utc <= datos_t["fecha_fin"]
                estado_t = (
                    EstadoTurno.COMPLETADO
                    if es_pasado
                    else (EstadoTurno.EN_CURSO if es_actual else EstadoTurno.PROGRAMADO)
                )
                turno_nuevo = ModeloTurno(
                    operador_id=datos_t["operador_id"],
                    puesto_id=datos_t["puesto_id"],
                    tipo_turno=datos_t["tipo_turno"],
                    estado_turno=estado_t,
                    fecha_inicio=datos_t["fecha_inicio"],
                    fecha_fin=datos_t["fecha_fin"],
                    horas_totales=datos_t["horas_totales"],
                    horas_ordinarias=datos_t["horas_ordinarias"],
                    horas_recargo_nocturno=datos_t["horas_recargo_nocturno"],
                    horas_extras_diurnas=datos_t["horas_extras_diurnas"],
                    horas_extras_nocturnas=datos_t["horas_extras_nocturnas"],
                    horas_dominicales_festivas=datos_t["horas_dominicales_festivas"],
                    costo_estimado_cop=datos_t["costo_estimado_cop"],
                    observaciones=datos_t["observaciones"],
                )
                sesion.add(turno_nuevo)
                turnos_guardados.append(turno_nuevo)

        await sesion.flush()

        # =====================================================================
        # 5. AUSENTISMOS REALES (3 CASOS: EPS, ARL NIVEL V, LICENCIA REMUNERADA)
        # =====================================================================
        turnos_operativos = [t for t in turnos_guardados if t.tipo_turno != TipoTurno.DESCANSO]
        if len(turnos_operativos) >= 15:
            t_eps = turnos_operativos[2]
            t_eps.horas_descuento_ausentismo = 12.0
            t_eps.motivo_ausentismo = "INCAPACIDAD_EPS"
            t_eps.estado_turno = EstadoTurno.DESCUBIERTO_PARCIAL

            t_arl = turnos_operativos[7]
            t_arl.horas_descuento_ausentismo = 12.0
            t_arl.motivo_ausentismo = "INCAPACIDAD_ARL"

            t_lic = turnos_operativos[12]
            t_lic.horas_descuento_ausentismo = 12.0
            t_lic.motivo_ausentismo = "LICENCIA_REMUNERADA"

            ausentismos_semilla = [
                ModeloAusentismo(
                    operador_id=t_eps.operador_id,
                    turno_afectado_id=t_eps.turno_id,
                    tipo_ausentismo=TipoAusentismo.INCAPACIDAD_EPS,
                    fecha_inicio=hoy - timedelta(days=3),
                    fecha_fin=hoy - timedelta(days=1),
                    horas_descontadas=36.0,
                    descripcion_soporte="Incapacidad médica EPS Sanitas #EPS-2026-99182 por cuadro viral respiratorio (3 días).",
                    registrado_por_id=rrhh.usuario_id,
                    reemplazo_asignado_id=operadores[3].usuario_id,
                ),
                ModeloAusentismo(
                    operador_id=t_arl.operador_id,
                    turno_afectado_id=t_arl.turno_id,
                    tipo_ausentismo=TipoAusentismo.INCAPACIDAD_ARL,
                    fecha_inicio=hoy - timedelta(days=5),
                    fecha_fin=hoy - timedelta(days=4),
                    horas_descontadas=24.0,
                    descripcion_soporte="Incapacidad ARL Sura Riesgo Nivel V #ARL-88412 por esguince en ronda perimetral nocturna.",
                    registrado_por_id=rrhh.usuario_id,
                    reemplazo_asignado_id=operadores[7].usuario_id,
                ),
                ModeloAusentismo(
                    operador_id=t_lic.operador_id,
                    turno_afectado_id=t_lic.turno_id,
                    tipo_ausentismo=TipoAusentismo.LICENCIA_REMUNERADA,
                    fecha_inicio=hoy - timedelta(days=2),
                    fecha_fin=hoy - timedelta(days=2),
                    horas_descontadas=12.0,
                    descripcion_soporte="Licencia remunerada por calamidad doméstica comprobada y autorizada por Talento Humano.",
                    registrado_por_id=rrhh.usuario_id,
                    reemplazo_asignado_id=operadores[11].usuario_id,
                ),
            ]
            sesion.add_all(ausentismos_semilla)

        # Solicitud de intercambio inicial validada por el motor
        turnos_op1 = [t for t in turnos_guardados if t.operador_id == operadores[0].usuario_id and t.tipo_turno != TipoTurno.DESCANSO and t.fecha_inicio > ahora_utc]
        turnos_op2 = [t for t in turnos_guardados if t.operador_id == operadores[1].usuario_id and t.tipo_turno != TipoTurno.DESCANSO and t.fecha_inicio > ahora_utc]
        if turnos_op1 and turnos_op2:
            t_orig = turnos_op1[0]
            t_dest = turnos_op2[-1]
            es_valido, descanso_min, detalle_val = validar_factibilidad_intercambio(
                t_orig,
                t_dest,
                [t for t in turnos_guardados if t.operador_id == operadores[0].usuario_id],
                [t for t in turnos_guardados if t.operador_id == operadores[1].usuario_id],
            )
            solicitud_demo = ModeloSolicitudIntercambio(
                operador_solicitante_id=operadores[0].usuario_id,
                operador_receptor_id=operadores[1].usuario_id,
                turno_origen_id=t_orig.turno_id,
                turno_destino_id=t_dest.turno_id,
                motivo_solicitud="Diligencia de renovación de examen psicofísico SuperVigilancia en IPS acreditada.",
                estado_solicitud=EstadoSolicitudIntercambio.PENDIENTE,
                validacion_sin_cruces=es_valido,
                horas_descanso_minimo_calculadas=max(12.0, descanso_min),
                detalle_validacion_motor=detalle_val,
            )
            sesion.add(solicitud_demo)

        # =====================================================================
        # 6. CADENA FORENSE DE ACTAS DE RELEVO Y MINUTAS (SHA-256 REAL DESDE GÉNESIS)
        # =====================================================================
        hashes_acta_por_puesto: dict[int, str] = {}
        hashes_minuta_por_puesto: dict[int, str] = {}

        # Crear 6 Actas de Relevo (1 en cada puesto) con hash encadenado real
        datos_actas_relevo = [
            (puesto_1, operadores[1], operadores[0], EstadoItemDotacion.OPTIMO, 24, False, "Relevo 06:00h conforme. Revólver Indumil Llama Martial .38L serie IM-884920 con 24 cartuchos y salvoconducto DCCA en cofre."),
            (puesto_2, operadores[5], operadores[4], EstadoItemDotacion.OPTIMO, 30, False, "Entrega de portería vehicular pesada Madrid-Facatativá. Escopeta 12GA serie IM-12G-773190 con 30 cartuchos y cámara LPR operativa."),
            (puesto_3, operadores[9], operadores[8], EstadoItemDotacion.NOVEDAD, 35, True, "Novedad en relevo Zona Franca Siberia: se verifica 1 cartucho .38L percutido en polígono pendiente de reposición DCCA (35/36)."),
            (puesto_4, operadores[13], operadores[12], EstadoItemDotacion.OPTIMO, 25, False, "Relevo Planta Los Andes Facatativá sin novedad. Armamento Mossberg 12GA, 25 cartuchos, radio VHF y linterna de largo alcance óptimos."),
            (puesto_5, operadores[17], operadores[16], EstadoItemDotacion.OPTIMO, 6, False, "Relevo Reserva del Parque Salitre. Binomio canino (K9 Thor), medios tecnológicos CCTV y 6 cargas no letales verificadas."),
            (puesto_6, operadores[21], operadores[20], EstadoItemDotacion.OPTIMO, 45, False, "Entrega blindada Centro de Datos Puente Aranda. Pistola Córdova 9mm serie IM-9MM-301988 con 3 proveedores (45 cartuchos) y biometría activa."),
        ]

        for idx_a, (puesto_obj, op_sal, op_ent, est_arma, municion, alerta_flag, obs) in enumerate(datos_actas_relevo):
            instante_acta = ahora_utc - timedelta(hours=12 - idx_a)
            hash_prev_acta = hashes_acta_por_puesto.get(puesto_obj.puesto_id, HASH_GENESIS_SHA256)
            payload_acta = (
                f"ACTA_INDUMIL|{puesto_obj.codigo_puesto}|{op_sal.documento_identidad}|"
                f"{est_arma.value}|{municion}|{obs}|{instante_acta.isoformat()}"
            )
            sello_acta = calcular_hash_encadenado_sha256(payload_acta, hash_prev_acta)
            hashes_acta_por_puesto[puesto_obj.puesto_id] = sello_acta

            sesion.add(
                ModeloActaRelevoPuesto(
                    puesto_id=puesto_obj.puesto_id,
                    operador_saliente_id=op_sal.usuario_id,
                    operador_entrante_id=op_ent.usuario_id,
                    estado_armamento=est_arma,
                    municion_verificada=municion,
                    estado_chaleco=EstadoItemDotacion.OPTIMO,
                    estado_radio=EstadoItemDotacion.OPTIMO,
                    estado_linterna_y_llaves=EstadoItemDotacion.OPTIMO,
                    observaciones_relevo=obs,
                    sello_sha256=sello_acta,
                    hash_anterior_sha256=hash_prev_acta,
                    tenant_id=TENANT_PRINCIPAL,
                    alerta_disparada=alerta_flag,
                    fecha_acta=instante_acta,
                )
            )

        # Crear 26 Anotaciones de Minuta Digital con visibilidad dual y cadena SHA-256 por puesto
        eventos_minuta_semilla = [
            # PST-BOG-01 (Torre Financiera Chapinero) - 6 eventos
            (puesto_1, operadores[0], TipoRegistroMinuta.ENTREGA_RECIBO_PUESTO, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Apertura y recibo de puesto Torre Financiera sin novedad", "Se recibe puesto PST-BOG-01 con armamento Indumil Llama Martial .38L serie IM-884920 (24 cartuchos), radio Motorola y CCTV operativo.", None, None, None, 48),
            (puesto_1, operadores[0], TipoRegistroMinuta.INGRESO_VEHICULO, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.MEDIA, "Ingreso de blindado transportador de valores Brinks", "Ingresa camión de valores placa KMV-842 a bóveda principal del sótano 2 con escolta acreditada. Sellos verificados.", "Hernán Darío Gómez", "71882910", "KMV-842", 42),
            (puesto_1, operadores[1], TipoRegistroMinuta.RONDA_CONTROL, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Ronda técnica en helipuerto, terraza piso 28 y subestación", "Se verifican puertas cortafuego, planta eléctrica Cummins en modo automático y sensores perimetrales sin novedad.", None, None, None, 36),
            (puesto_1, supervisor_1, TipoRegistroMinuta.NOVEDAD_INCIDENTE, VisibilidadMinuta.INTERNA_OPERATIVA, NivelPrioridad.ALTA, "[DIRECTIVA INTERNA] Reentrenamiento obligatorio operador OPR-1003", "Se notifica al guarda Mateo Suárez (OPR-1003) asistir a polígono antes de 14 días por próximo vencimiento de credencial SV.", None, None, None, 28),
            (puesto_1, operadores[0], TipoRegistroMinuta.INGRESO_VISITANTE, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Ingreso de comisión de auditoría externa Superintendencia Financiera", "Se registra ingreso con escáner PDF417 y autorización de Presidencia en Piso 18.", "Dra. Marcela Patiño Restrepo", "52441980", None, 14),
            (puesto_1, operadores[1], TipoRegistroMinuta.RONDA_CONTROL, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.MEDIA, "Verificación de cierre de oficinas bancarias y activación de bóveda temporizada", "Cierre hermético verificado a las 19:00h en coordinación con central de monitoreo.", None, None, None, 4),

            # PST-OCC-02 (Parque Logístico Sabana - Madrid) - 5 eventos
            (puesto_2, operadores[4], TipoRegistroMinuta.ENTREGA_RECIBO_PUESTO, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Recibo de Portería Vehicular Pesada Parque Logístico Sabana", "Se recibe puesto PST-OCC-02 con escopeta Indumil 12GA serie IM-12G-773190, barreras hidráulicas y lector OCR de placas.", None, None, None, 46),
            (puesto_2, operadores[4], TipoRegistroMinuta.INGRESO_VEHICULO, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.MEDIA, "Ingreso de tractomula Kenworth con contenedor refrigerado", "Se valida manifiesto de carga DIAN, precinto ISO #99412 y placa TGL-910 hacia Muelle Logístico 4.", "Segundo Ramiro Mateus", "79445120", "TGL-910", 38),
            (puesto_2, operadores[5], TipoRegistroMinuta.NOVEDAD_INCIDENTE, VisibilidadMinuta.INTERNA_OPERATIVA, NivelPrioridad.ALTA, "[INTERNA] Fluctuación de fluido eléctrico en garita occidente", "Se presentó corte de energía de ENEL Codensa por 8 minutos en el corredor Madrid-Facatativá. Respaldo UPS y planta operaron al 100%.", None, None, None, 22),
            (puesto_2, operadores[6], TipoRegistroMinuta.RONDA_CONTROL, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Ronda perimetral en patio de contenedores y báscula camionera", "Marcación QR/GPS completada dentro de geocerca (radio 150m). Iluminación LED perimetral completa.", None, None, None, 11),
            (puesto_2, supervisor_2, TipoRegistroMinuta.RONDA_CONTROL, VisibilidadMinuta.INTERNA_OPERATIVA, NivelPrioridad.MEDIA, "Revista motorizada de supervisión en corredor Sabana de Occidente", "Supervisor SUP-102 pasa revista de armamento, libro físico y presentación personal del escuadrón.", None, None, None, 3),

            # PST-BOG-03 (Zona Franca Siberia - Cota) - 4 eventos
            (puesto_3, operadores[8], TipoRegistroMinuta.ENTREGA_RECIBO_PUESTO, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Entrega de puesto Zona Franca Metropolitana Siberia", "Dotación verificada en báscula aduanera y bodega fiscal. 3 revólveres .38L Indumil en custodia.", None, None, None, 44),
            (puesto_3, operadores[9], TipoRegistroMinuta.INGRESO_VEHICULO, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.MEDIA, "Inspección antinarcóticos BASC a furgón de exportación", "Se realiza inspección física con espejo convexo y registro fotográfico a vehículo WXY-942 sin anomalías.", "Jorge Eliécer Buitrago", "80119432", "WXY-942", 30),
            (puesto_3, supervisor_3, TipoRegistroMinuta.NOVEDAD_INCIDENTE, VisibilidadMinuta.INTERNA_OPERATIVA, NivelPrioridad.CRITICA, "[BLOQUEO SV] Relevo inmediato de operador OPR-1011 por credencial vencida", "El sistema bloqueó automáticamente la programación del guarda Andrés Zapata (OPR-1011). Se asignó relevante acreditado OPR-1012.", None, None, None, 16),
            (puesto_3, operadores[8], TipoRegistroMinuta.RONDA_CONTROL, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Verificación de precintos aduaneros en Bodegas 12 a 18", "Todos los candados satelitales y sellos de alta seguridad BASC permanecen intactos.", None, None, None, 5),

            # PST-FAC-04 (Planta Agroindustrial Los Andes - Facatativá) - 4 eventos
            (puesto_4, operadores[12], TipoRegistroMinuta.ENTREGA_RECIBO_PUESTO, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Recibo de puesto Planta Agroindustrial Los Andes", "Armamento Indumil 12GA serie IM-12G-509218 verificado con 25 cartuchos y concertina perimetral electrificada activa.", None, None, None, 40),
            (puesto_4, operadores[13], TipoRegistroMinuta.NOVEDAD_INCIDENTE, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.ALTA, "Hallazgo de malla eslabonada destemplada en lindero norte (Sector El Corzo)", "Durante ronda nocturna se detecta poste inclinado por fuertes lluvias. Se instala iluminación táctica provisional y se refuerza vigilancia.", None, None, None, 25),
            (puesto_4, operadores[14], TipoRegistroMinuta.INGRESO_VEHICULO, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Despacho de mulas con carga de flores de exportación hacia El Dorado", "Salen 3 camiones refrigerados escoltados con precinto verificado hacia terminal de carga aérea.", "Fabián Murcia", "1075112390", "SJK-512", 12),
            (puesto_4, operadores[12], TipoRegistroMinuta.RONDA_CONTROL, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Ronda de control en reservorio de agua y cuarto de calderas", "Niveles de presión normales. Checkpoint QR verificado con GPS a 8.2m del punto central.", None, None, None, 2),

            # PST-BOG-05 (Complejo Residencial Reserva del Parque - Salitre) - 3 eventos
            (puesto_5, operadores[16], TipoRegistroMinuta.ENTREGA_RECIBO_PUESTO, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Recibo de portería principal y binomio canino en Reserva del Parque", "Se recibe ejemplar canino detector (K9 Thor) en óptimas condiciones veterinarias, tonfa y radio Motorola.", None, None, None, 35),
            (puesto_5, operadores[17], TipoRegistroMinuta.INGRESO_VISITANTE, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Ingreso de cuadrilla técnica de ascensores Otis", "Se autoriza por administración el ingreso de 2 técnicos identificados por lector PDF417 hacia Torre B.", "César Augusto Méndez", "79554310", "XRP-45F", 19),
            (puesto_5, operadores[16], TipoRegistroMinuta.RONDA_CONTROL, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Ronda preventiva canina en parqueaderos subterráneos N1 y N2", "Sin vehículos con puertas abiertas ni personas ajenas en zonas comunes.", None, None, None, 6),

            # PST-BOG-06 (Centro de Datos & Nodo Telecom - Puente Aranda) - 4 eventos
            (puesto_6, operadores[20], TipoRegistroMinuta.ENTREGA_RECIBO_PUESTO, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Recibo de Esclusa Biométrica Centro de Datos Tier-IV", "Pistola Indumil Córdova 9mm serie IM-9MM-301988 verificada con 45 cartuchos. Esclusa mantrap y rayos X activos.", None, None, None, 41),
            (puesto_6, operadores[21], TipoRegistroMinuta.INGRESO_VISITANTE, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.MEDIA, "Ingreso de ingenieros de fibra óptica a Sala Blanca de Servidores #3", "Se retienen dispositivos móviles en casillero Faraday y se entrega tarjeta RFID temporal nivel 3.", "Ing. Nicolás Sabogal", "1015443210", "BGT-901", 27),
            (puesto_6, supervisor_4, TipoRegistroMinuta.NOVEDAD_INCIDENTE, VisibilidadMinuta.INTERNA_OPERATIVA, NivelPrioridad.MEDIA, "[AUDITORÍA ISO 27001 / 28000] Verificación de cadena SHA-256 de accesos", "Se comprueba integridad del 100% de los bloques de control de acceso y minuta en el nodo de telecomunicaciones.", None, None, None, 15),
            (puesto_6, operadores[20], TipoRegistroMinuta.RONDA_CONTROL, VisibilidadMinuta.PUBLICA_CLIENTE, NivelPrioridad.BAJA, "Inspección de bancos de baterías y tanques de ACPM de emergencia", "Autonomía de 72 horas verificada. Temperatura de sala de servidores estable en 18.4°C.", None, None, None, 1),
        ]

        for puesto_obj, op_obj, tipo_reg, visib, prio, titulo, desc, nom_vis, doc_vis, placa_v, horas_atras in eventos_minuta_semilla:
            instante_min = ahora_utc - timedelta(hours=horas_atras)
            hash_prev_min = hashes_minuta_por_puesto.get(puesto_obj.puesto_id, HASH_GENESIS_SHA256)
            datos_min = (
                f"MINUTA|{puesto_obj.codigo_puesto}|{op_obj.documento_identidad}|"
                f"{tipo_reg.value}|{visib.value}|{titulo}|{desc}|{instante_min.isoformat()}"
            )
            sello_min = calcular_hash_encadenado_sha256(datos_min, hash_prev_min)
            hashes_minuta_por_puesto[puesto_obj.puesto_id] = sello_min

            sesion.add(
                ModeloRegistroMinuta(
                    operador_id=op_obj.usuario_id,
                    puesto_id=puesto_obj.puesto_id,
                    tipo_registro=tipo_reg,
                    visibilidad=visib,
                    nivel_prioridad=prio,
                    titulo_evento=titulo,
                    descripcion_detallada=desc,
                    nombre_visitante=nom_vis,
                    documento_visitante=doc_vis,
                    placa_vehiculo=placa_v,
                    sello_sha256=sello_min,
                    hash_anterior_sha256=hash_prev_min,
                    tenant_id=TENANT_PRINCIPAL,
                    fecha_registro=instante_min,
                )
            )

        # =====================================================================
        # 7. KARDEX BALÍSTICO DCCA INDUMIL (SHA-256) Y CERTIFICADOS DE POLÍGONO
        # =====================================================================
        hashes_kardex_por_puesto: dict[int, str] = {}
        movimientos_balisticos_semilla = [
            (puesto_1, dotaciones_lista[0], supervisor_1, TipoMovimientoBalistico.DOTACION_INICIAL, ".38 Especial Indumil", 24, 24, "Asignación inicial de carga reglamentaria DCCA Indumil para 2 revólveres Llama Martial.", "DCCA-OF-2026-1001", 120),
            (puesto_1, dotaciones_lista[0], supervisor_1, TipoMovimientoBalistico.PRACTICA_POLIGONO, ".38 Especial Indumil", 6, 18, "Rotación de munición antigua en polígono anual Academia Colombiana de Seguridad.", "DCCA-POL-2026-1045", 60),
            (puesto_1, dotaciones_lista[0], admin, TipoMovimientoBalistico.REPOSICION_INDUMIL, ".38 Especial Indumil", 6, 24, "Reposición de lote nuevo Indumil 2026 para completar carga autorizada de 24 cartuchos.", "DCCA-REP-2026-1102", 18),
            (puesto_2, dotaciones_lista[1], supervisor_2, TipoMovimientoBalistico.DOTACION_INICIAL, "12 GA Doble Cero Indumil", 30, 30, "Dotación inicial para portería logística Sabana de Occidente.", "DCCA-OF-2026-2001", 110),
            (puesto_2, dotaciones_lista[1], supervisor_2, TipoMovimientoBalistico.MANTENIMIENTO_ARMERIA, "12 GA Doble Cero Indumil", 5, 30, "Inspección y limpieza preventiva por armero certificado sin afectación de saldo.", "DCCA-ARM-2026-2089", 24),
            (puesto_3, dotaciones_lista[2], supervisor_3, TipoMovimientoBalistico.DOTACION_INICIAL, ".38 Especial Indumil", 36, 36, "Dotación para escuadrón triple en Zona Franca Siberia (3 revólveres x 12 cartuchos).", "DCCA-OF-2026-3001", 95),
            (puesto_3, dotaciones_lista[2], supervisor_3, TipoMovimientoBalistico.PRACTICA_POLIGONO, ".38 Especial Indumil", 6, 30, "Consumo en prueba de idoneidad balística de relevo.", "DCCA-POL-2026-3050", 40),
            (puesto_3, dotaciones_lista[2], admin, TipoMovimientoBalistico.REPOSICION_INDUMIL, ".38 Especial Indumil", 6, 36, "Reintegro de munición desde bóveda central de armería.", "DCCA-REP-2026-3099", 10),
            (puesto_4, dotaciones_lista[3], supervisor_2, TipoMovimientoBalistico.DOTACION_INICIAL, "12 GA Indumil", 25, 25, "Dotación asignada a Planta Agroindustrial Facatativá.", "DCCA-OF-2026-4001", 80),
            (puesto_5, dotaciones_lista[4], supervisor_4, TipoMovimientoBalistico.DOTACION_INICIAL, "Cartucho Impulso No Letal", 6, 6, "Dotación preventiva no letal para complejo residencial Salitre.", "SV-NL-2026-5001", 75),
            (puesto_6, dotaciones_lista[5], supervisor_4, TipoMovimientoBalistico.DOTACION_INICIAL, "9x19mm NATO Indumil", 45, 45, "Carga de alta seguridad para Pistola Córdova en Centro de Datos Tier-IV.", "DCCA-OF-2026-6001", 90),
            (puesto_6, dotaciones_lista[5], admin, TipoMovimientoBalistico.MANTENIMIENTO_ARMERIA, "9x19mm NATO Indumil", 15, 45, "Certificación trimestral de mecanismos de disparo y agujas percutoras.", "DCCA-ARM-2026-6040", 12),
        ]

        for puesto_obj, dot_obj, resp_obj, tipo_mov, cal, cant_afect, saldo_res, justif, oficio, horas_atras in movimientos_balisticos_semilla:
            fecha_mov = ahora_utc - timedelta(hours=horas_atras)
            hash_prev_kar = hashes_kardex_por_puesto.get(puesto_obj.puesto_id, HASH_GENESIS_SHA256)
            cadena_kar = f"{dot_obj.dotacion_id}:{tipo_mov.value}:{cant_afect}:{saldo_res}:{fecha_mov.isoformat()}"
            firma_kar = calcular_hash_encadenado_sha256(cadena_kar, hash_prev_kar)
            hashes_kardex_por_puesto[puesto_obj.puesto_id] = firma_kar

            sesion.add(
                ModeloKardexBalistico(
                    puesto_id=puesto_obj.puesto_id,
                    dotacion_id=dot_obj.dotacion_id,
                    operador_responsable_id=resp_obj.usuario_id,
                    tipo_movimiento=tipo_mov,
                    calibre=cal,
                    cantidad_municion_afectada=cant_afect,
                    saldo_municion_resultante=saldo_res,
                    justificacion_novedad=justif,
                    numero_oficio_dcca=oficio,
                    firma_digital_sha256=firma_kar,
                    hash_anterior_sha256=hash_prev_kar,
                    tenant_id=TENANT_PRINCIPAL,
                    fecha_movimiento=fecha_mov,
                )
            )

        # Certificados de Polígono (8 operadores certificados)
        certificados_semilla = [
            (operadores[0], "Academia Nacional de Vigilancia El Cóndor", "Revólver Llama Martial .38L", 96.5, True, hoy - timedelta(days=45)),
            (operadores[1], "Academia Nacional de Vigilancia El Cóndor", "Revólver Llama Martial .38L", 91.0, True, hoy - timedelta(days=60)),
            (operadores[4], "Centro de Entrenamiento Táctico Sabana", "Escopeta Indumil 12 GA", 94.2, True, hoy - timedelta(days=30)),
            (operadores[5], "Centro de Entrenamiento Táctico Sabana", "Escopeta Indumil 12 GA", 89.5, True, hoy - timedelta(days=80)),
            (operadores[8], "Escuela Colombiana de Seguridad Privada", "Revólver Llama Martial .38L", 92.8, True, hoy - timedelta(days=50)),
            (operadores[12], "Centro de Entrenamiento Táctico Sabana", "Escopeta Mossberg 12 GA", 95.0, True, hoy - timedelta(days=25)),
            (operadores[20], "Polígono Indumil Soacha - Nivel Especialización", "Pistola Córdova 9x19mm", 98.4, True, hoy - timedelta(days=15)),
            (operadores[21], "Polígono Indumil Soacha - Nivel Especialización", "Pistola Córdova 9x19mm", 94.7, True, hoy - timedelta(days=20)),
        ]
        for op_cert, acad, arma_cal, puntaje, aprob, f_prac in certificados_semilla:
            sesion.add(
                ModeloCertificadoPoligono(
                    operador_id=op_cert.usuario_id,
                    academia_seguridad=acad,
                    tipo_arma_calificada=arma_cal,
                    puntaje_precision=puntaje,
                    aprobado=aprob,
                    fecha_practica=f_prac,
                    fecha_vencimiento_anual=f_prac + timedelta(days=365),
                )
            )

        # =====================================================================
        # 8. TRÁFICO EN GARITA: 12 ACTIVOS (DENTRO) + 20 HISTÓRICOS (SALIO)
        # =====================================================================
        accesos_activos_datos = [
            (puesto_1, operadores[0], TipoAccesoGarita.VEHICULAR, "71882910", "HERNÁN DARÍO", "GÓMEZ RESTREPO", "O+", "KMV-842", "Bóveda Central Piso S2 - Brinks", "Recolección y aprovisionamiento de remesa bancaria", 45),
            (puesto_1, operadores[0], TipoAccesoGarita.PEATONAL_VISITANTE, "52441980", "MARCELA", "PATIÑO RESTREPO", "A+", None, "Presidencia Ejecutiva Piso 18", "Comisión de inspección Superintendencia Financiera", 80),
            (puesto_2, operadores[4], TipoAccesoGarita.VEHICULAR, "79445120", "SEGUNDO RAMIRO", "MATEUS CAMARGO", "O+", "TGL-910", "Muelle de Carga Pesada #4", "Descargue de contenedor refrigerado 40 pies", 65),
            (puesto_2, operadores[4], TipoAccesoGarita.CONTRATISTA, "1070984120", "JAIRO ALONSO", "PULIDO", "B+", "XRP-45F", "Subestación Eléctrica Bodega 2", "Mantenimiento preventivo de transformadores Siemens", 110),
            (puesto_3, operadores[8], TipoAccesoGarita.VEHICULAR, "80119432", "JORGE ELIÉCER", "BUITRAGO", "O-", "WXY-942", "Zona Aduanera Bodega Fiscal 14", "Inspección pre-embarque de mercancía en tránsito", 50),
            (puesto_3, operadores[8], TipoAccesoGarita.EMPLEADO, "1018412990", "CATALINA", "LONDOÑO VÉLEZ", "A+", "FGH-319", "Agencia de Aduanas Nivel 3", "Coordinación de levante de importación DIAN", 150),
            (puesto_4, operadores[12], TipoAccesoGarita.VEHICULAR, "1075119823", "WILSON FERNEY", "CHITIVA", "O+", "SJK-512", "Cuarto Frío PosCosecha #1", "Cargue de pallets de exportación hacia Aeropuerto El Dorado", 35),
            (puesto_4, operadores[12], TipoAccesoGarita.CONTRATISTA, "79331098", "ÁLVARO JAVIER", "MONROY", "AB+", None, "Planta de Tratamiento de Aguas", "Calibración de bombas dosificadoras", 95),
            (puesto_5, operadores[16], TipoAccesoGarita.CONTRATISTA, "79554310", "CÉSAR AUGUSTO", "MÉNDEZ", "O+", "MNT-18D", "Torre B - Cuarto de Máquinas", "Mantenimiento certificado de ascensores Otis", 70),
            (puesto_5, operadores[16], TipoAccesoGarita.PEATONAL_VISITANTE, "51990234", "CLARA INÉS", "VALDERRAMA", "A-", None, "Apartamento 1104 - Torre A", "Visita familiar autorizada por citofonía digital", 40),
            (puesto_6, operadores[20], TipoAccesoGarita.CONTRATISTA, "1015443210", "NICOLÁS", "SABOGAL", "O+", "BGT-901", "Sala Blanca de Servidores #3", "Fusión de hilo de fibra óptica en rack principal", 55),
            (puesto_6, operadores[20], TipoAccesoGarita.EMPLEADO, "80776543", "ESTEBAN", "CORREDOR", "B+", "DFR-774", "NOC - Centro de Operaciones de Red", "Turno de ingeniería de ciberseguridad e infraestructura", 180),
        ]

        for p_obj, op_obj, t_acc, doc_v, nom_v, ape_v, rh_v, placa_v, dest_v, mot_v, min_atras in accesos_activos_datos:
            sesion.add(
                ModeloRegistroAccesoGarita(
                    puesto_id=p_obj.puesto_id,
                    operador_id=op_obj.usuario_id,
                    tipo_acceso=t_acc,
                    documento_identidad=doc_v,
                    nombres=nom_v,
                    apellidos=ape_v,
                    tipo_sangre_rh=rh_v,
                    placa_vehiculo=placa_v,
                    empresa_o_destino=dest_v,
                    motivo_ingreso=mot_v,
                    autoriza_tratamiento_datos=True,
                    es_sospechoso_alerta=False,
                    estado_acceso=EstadoAccesoGarita.DENTRO,
                    tenant_id=TENANT_PRINCIPAL,
                    fecha_ingreso=ahora_utc - timedelta(minutes=min_atras),
                    observaciones="Identidad verificada con lector PDF417 y consentimiento Ley 1581 firmado.",
                )
            )

        # 20 registros históricos de garita con salida completada
        for i in range(1, 21):
            p_hist = puestos_lista[(i - 1) % len(puestos_lista)]
            op_hist = operadores[((i - 1) % len(puestos_lista)) * 4]
            f_ing = ahora_utc - timedelta(hours=i * 3 + 2)
            f_sal = f_ing + timedelta(minutes=45 + (i * 5))
            placa_h = f"COL-{100 + i}" if i % 2 == 0 else None
            sesion.add(
                ModeloRegistroAccesoGarita(
                    puesto_id=p_hist.puesto_id,
                    operador_id=op_hist.usuario_id,
                    tipo_acceso=TipoAccesoGarita.VEHICULAR if placa_h else TipoAccesoGarita.PEATONAL_VISITANTE,
                    documento_identidad=f"102030{4000 + i}",
                    nombres=f"VISITANTE CORPORATIVO {i}",
                    apellidos="REGISTRADO PDF417",
                    tipo_sangre_rh="O+" if i % 3 != 0 else "A+",
                    placa_vehiculo=placa_h,
                    empresa_o_destino=f"Área Operativa / Oficina {200 + i}",
                    motivo_ingreso="Gestión comercial y entrega de documentación auditada",
                    autoriza_tratamiento_datos=True,
                    es_sospechoso_alerta=False,
                    estado_acceso=EstadoAccesoGarita.SALIO,
                    tenant_id=TENANT_PRINCIPAL,
                    fecha_ingreso=f_ing,
                    fecha_salida=f_sal,
                    observaciones="Ciclo de ingreso y salida completado sin novedades.",
                )
            )

        # =====================================================================
        # 9. PUNTOS DE CONTROL QR/GPS (12 PUNTOS EN LOS 6 PUESTOS) + MARCACIONES
        # =====================================================================
        definicion_puntos_qr = [
            (puesto_1, "QR-SNT-BOG01-SOTANO2", "Bóveda Principal y Generadores Sótano 2", 4.6533, -74.0560, 80.0, 1),
            (puesto_1, "QR-SNT-BOG01-HELIPUERTO", "Acceso Helipuerto y Terraza Técnica Piso 28", 4.6535, -74.0558, 80.0, 2),
            (puesto_2, "QR-SNT-OCC02-MUELLE4", "Patio de Tractomulas y Muelle Refrigerado #4", 4.7820, -74.3210, 150.0, 1),
            (puesto_2, "QR-SNT-OCC02-BASCULA", "Báscula Camionera y Esclusa LPR Occidente", 4.7824, -74.3206, 150.0, 2),
            (puesto_3, "QR-SNT-BOG03-ADUANA", "Recinto Fiscal Aduanero DIAN Bodega 14", 4.7390, -74.1280, 120.0, 1),
            (puesto_3, "QR-SNT-BOG03-PERIMETRO", "Malla Perimetral Norte Glorieta Siberia", 4.7394, -74.1277, 120.0, 2),
            (puesto_4, "QR-SNT-FAC04-POSCOSECHA", "Cuarto Frío de Exportación y Calderas", 4.8143, -74.3547, 100.0, 1),
            (puesto_4, "QR-SNT-FAC04-LINDERO", "Lindero Norte Sector El Corzo y Reservorio", 4.8146, -74.3544, 100.0, 2),
            (puesto_5, "QR-SNT-BOG05-CANIL", "Zona Canina K9 y Parqueadero Subterráneo N2", 4.6482, -74.0985, 60.0, 1),
            (puesto_5, "QR-SNT-BOG05-LOBBY", "Portería Peatonal y Esclusa Salitre", 4.6484, -74.0983, 60.0, 2),
            (puesto_6, "QR-SNT-BOG06-SALABLANCA", "Esclusa Biométrica Sala Blanca Servidores Tier-IV", 4.6295, -74.1120, 50.0, 1),
            (puesto_6, "QR-SNT-BOG06-SUBESTACION", "Banco de Baterías UPS y Tanques ACPM", 4.6297, -74.1118, 50.0, 2),
        ]

        puntos_creados: list[ModeloPuntoControlRonda] = []
        for p_obj, qr_code, nom_p, lat_p, lon_p, rad_p, ord_p in definicion_puntos_qr:
            pt = ModeloPuntoControlRonda(
                puesto_id=p_obj.puesto_id,
                codigo_qr_hash=qr_code,
                nombre_punto=nom_p,
                latitud_gps=lat_p,
                longitud_gps=lon_p,
                radio_tolerancia_metros=rad_p,
                orden_secuencia=ord_p,
                activo=True,
            )
            sesion.add(pt)
            puntos_creados.append(pt)

        await sesion.flush()

        # Crear marcaciones de ronda en todos los puntos para reflejar alto cumplimiento SLA
        for idx_pt, pt_obj in enumerate(puntos_creados):
            op_ronda = operadores[(idx_pt // 2) * 4]
            lat_cap = pt_obj.latitud_gps + 0.00004
            lon_cap = pt_obj.longitud_gps - 0.00003
            dist = calcular_distancia_haversine_metros(pt_obj.latitud_gps, pt_obj.longitud_gps, lat_cap, lon_cap)
            sesion.add(
                ModeloMarcacionRonda(
                    punto_id=pt_obj.punto_id,
                    operador_id=op_ronda.usuario_id,
                    latitud_capturada=lat_cap,
                    longitud_capturada=lon_cap,
                    distancia_calculada_metros=dist,
                    dentro_de_geocerca=dist <= pt_obj.radio_tolerancia_metros,
                    sincronizado_desde_offline=(idx_pt % 4 == 0),
                    observacion_ronda=f"Ronda verificada en {pt_obj.nombre_punto}. Perímetro sin novedad.",
                    fecha_marcacion=ahora_utc - timedelta(minutes=25 + idx_pt * 12),
                )
            )

        # =====================================================================
        # 10. FACTURACIÓN B2B (4 PREFACTURAS EMITIDAS CON CÁLCULO LEGAL EXACTO)
        # =====================================================================
        datos_prefacturas = [
            ("FAC-B2B-2026-001", puesto_1, "2026-10", ModalidadServicioTarifa.VIGILANCIA_24H_ARMADA, 2, 0.10, "Servicio de vigilancia 24/7 armada con 2 puestos (8 guardas) en Centro Empresarial Torre Financiera Chapinero."),
            ("FAC-B2B-2026-002", puesto_2, "2026-10", ModalidadServicioTarifa.VIGILANCIA_24H_ARMADA, 3, 0.11, "Cobertura integral 24/7 armada + control LPR en Parque Logístico Industrial Sabana (Logística Andina S.A.S.)."),
            ("FAC-B2B-2026-003", puesto_4, "2026-10", ModalidadServicioTarifa.VIGILANCIA_24H_ARMADA, 2, 0.10, "Protección perimetral armada 24/7 en Planta Agroindustrial Los Andes Facatativá (Agroexportadora de la Sabana S.A.)."),
            ("FAC-B2B-2026-004", puesto_5, "2026-10", ModalidadServicioTarifa.VIGILANCIA_24H_SIN_ARMA, 2, 0.10, "Vigilancia preventiva 24/7 con binomio canino y medios tecnológicos en Complejo Reserva del Parque Salitre."),
        ]

        for cod_fac, p_fac, mes_s, mod_s, cant_p, pct_aiu, notas_c in datos_prefacturas:
            liq = calcular_tarifa_supervigilancia(
                modalidad=mod_s,
                cantidad_puestos=cant_p,
                porcentaje_administracion=pct_aiu,
            )
            f_emi = ahora_utc - timedelta(days=5)
            firma_fac = generar_firma_digital_prefactura(
                codigo_factura=cod_fac,
                cliente_id=cliente.usuario_id,
                mes_servicio=mes_s,
                total_cop=liq.tarifa_total_factura_cop,
                fecha_emision=f_emi,
            )
            sesion.add(
                ModeloPrefactura(
                    codigo_factura=cod_fac,
                    cliente_id=cliente.usuario_id,
                    puesto_id=p_fac.puesto_id,
                    mes_servicio=mes_s,
                    modalidad_servicio=mod_s,
                    cantidad_puestos=cant_p,
                    cantidad_guardas_requeridos=liq.total_guardas_requeridos,
                    costo_mano_obra_cop=liq.costo_mano_obra_total,
                    costo_armamento_cop=liq.costo_armamento_y_equipos,
                    costo_administracion_cop=liq.costo_administracion_aiu,
                    subtotal_cop=liq.subtotal_antes_iva,
                    iva_cop=liq.iva_dian,
                    total_factura_cop=liq.tarifa_total_factura_cop,
                    estado_factura=EstadoFactura.EMITIDA,
                    notas_comerciales=notas_c,
                    firma_digital_sha256=firma_fac,
                    fecha_emision=f_emi,
                    fecha_vencimiento=hoy + timedelta(days=25),
                )
            )

        # =====================================================================
        # 11. HISTORIAL DE REACCIÓN SOS Y DESPACHO CAD PARA KPIs DE TIEMPO REAL
        # =====================================================================
        alerta_hist_1 = ModeloAlertaPanicoSos(
            operador_id=operadores[4].usuario_id,
            puesto_id=puesto_2.puesto_id,
            latitud_gps=4.7820,
            longitud_gps=-74.3210,
            estado_alerta=EstadoAlertaSos.ATENDIDA,
            fecha_activacion=ahora_utc - timedelta(hours=18),
            atendida_por_id=supervisor_2.usuario_id,
            fecha_atencion=ahora_utc - timedelta(hours=18) + timedelta(seconds=165),
            tiempo_reaccion_segundos=165,
            nota_reaccion="Reacción motorizada SUP-102 en 2m 45s por intento de intrusión vehicular en báscula Madrid.",
        )
        alerta_hist_2 = ModeloAlertaPanicoSos(
            operador_id=operadores[8].usuario_id,
            puesto_id=puesto_3.puesto_id,
            latitud_gps=4.7390,
            longitud_gps=-74.1280,
            estado_alerta=EstadoAlertaSos.ATENDIDA,
            fecha_activacion=ahora_utc - timedelta(hours=8),
            atendida_por_id=supervisor_3.usuario_id,
            fecha_atencion=ahora_utc - timedelta(hours=8) + timedelta(seconds=140),
            tiempo_reaccion_segundos=140,
            nota_reaccion="Apoyo táctico SUP-103 y enlace con CAI Siberia en 2m 20s. Situación controlada.",
        )
        sesion.add_all([alerta_hist_1, alerta_hist_2])
        await sesion.flush()

        despacho_hist_1 = ModeloDespachoPatrulla(
            alerta_sos_id=alerta_hist_1.alerta_id,
            supervisor_id=supervisor_2.usuario_id,
            puesto_id=puesto_2.puesto_id,
            distancia_km_calculada=1.8,
            eta_minutos_estimado=2.7,
            estado_despacho=EstadoDespachoPatrulla.FINALIZADO,
            fecha_despacho=alerta_hist_1.fecha_activacion,
            fecha_llegada_sitio=alerta_hist_1.fecha_atencion,
            tiempo_arribo_segundos=165,
            informe_tactico_cierre="Se verificó perímetro de Parque Logístico Sabana con apoyo del cuadrante PONAL Madrid.",
        )
        sesion.add(despacho_hist_1)

        # =====================================================================
        # 12. OPERACIONES ESPECIALES V5.0: ESCOLTAS BASC/VIP, UNIDAD K9 Y MEDIOS TECNOLÓGICOS
        # =====================================================================
        datos_escoltas_basc = [
            (
                "BASC-CONV-2026-001",
                "CONVOY_CARGA_CRITICA_BASC",
                "Convoy Aeropuerto El Dorado (Terminal Carga) -> Zona Franca Siberia -> Parque Logístico Facatativá",
                "Calle 26 -> Devisab -> Autopista Medellín (Calle 80) -> Corredor Sabana Occidente",
                "GKV-912 (Kenworth T800 + Escolta Blindada BMW-551)",
                "NIVEL_IV",
                supervisor_2.usuario_id,
                "IM-9MM-301988",
                4.6960, -74.1415,
                4.7820, -74.3210,
                4.7495, -74.2180,
                22.4,
                0.0,
                250.0,
                "EN_RUTA_ACTIVA",
            ),
            (
                "BASC-VIP-2026-002",
                "PROTECCION_EJECUTIVA_VIP",
                "Desplazamiento Blindado Presidencia Corporativa: Torre Financiera Chapinero -> Centro de Datos Puente Aranda",
                "Carrera 7 -> Calle 63 -> Av. NQS (Carrera 30) -> Calle 13 (Zona Industrial)",
                "JRP-884 (Toyota Land Cruiser 300 Blindada)",
                "NIVEL_V",
                supervisor_1.usuario_id,
                "IM-884920",
                4.6533, -74.0560,
                4.6295, -74.1120,
                4.6410, -74.0840,
                7.2,
                0.0,
                180.0,
                "EN_RUTA_ACTIVA",
            ),
            (
                "BASC-CONV-2026-003",
                "CONVOY_AGROEXPORTACION_BASC",
                "Convoy Refrigerado de Exportación: Planta Los Andes Facatativá -> Muelle Carga El Dorado",
                "Carretera de Occidente (Calle 13) -> Peaje Corso -> Fontibón -> Aeropuerto El Dorado",
                "SJK-512 (Tractomula + Patrulla Escolta SUP-104)",
                "NIVEL_IIIA",
                supervisor_4.usuario_id,
                "IM-12G-509218",
                4.8143, -74.3547,
                4.6960, -74.1415,
                4.6960, -74.1415,
                28.6,
                0.0,
                250.0,
                "COMPLETADA",
            ),
        ]

        hash_prev_escolta = HASH_GENESIS_SHA256
        for (
            cod_mision, tipo_m, desc_ruta, corr_vial, placa_v, niv_blindaje,
            esc_id, serial_arma, lat_o, lon_o, lat_d, lon_d, lat_a, lon_a,
            dist_km, desv_m, umbral_m, est_mision
        ) in datos_escoltas_basc:
            instante_esc = ahora_utc - timedelta(hours=3)
            payload_esc = (
                f"ESCOLTA_BASC|{cod_mision}|{tipo_m}|{placa_v}|{niv_blindaje}|"
                f"{serial_arma}|{dist_km}|{instante_esc.isoformat()}"
            )
            sello_esc = calcular_hash_encadenado_sha256(payload_esc, hash_prev_escolta)
            sesion.add(
                ModeloMisionEscoltaBasc(
                    codigo_mision=cod_mision,
                    tipo_mision=tipo_m,
                    descripcion_ruta=desc_ruta,
                    corredor_vial=corr_vial,
                    vehiculo_placa=placa_v,
                    nivel_blindaje=niv_blindaje,
                    escolta_id=esc_id,
                    serial_arma_indumil=serial_arma,
                    lat_origen=lat_o,
                    lon_origen=lon_o,
                    lat_destino=lat_d,
                    lon_destino=lon_d,
                    lat_actual=lat_a,
                    lon_actual=lon_a,
                    distancia_ruta_km=dist_km,
                    desviacion_metros=desv_m,
                    umbral_desvio_metros=umbral_m,
                    estado_mision=est_mision,
                    sello_manifiesto_sha256=sello_esc,
                    hash_anterior_sha256=hash_prev_escolta,
                    tenant_id=TENANT_PRINCIPAL,
                    fecha_despacho=instante_esc,
                )
            )
            hash_prev_escolta = sello_esc

        # 4 Unidades Caninas Biodetectoras K9 (Resolución SuperVigilancia - tope 6h continuas)
        datos_binomios_k9 = [
            ("K9-BOG-001", "Thor", "Pastor Belga Malinois", "EXPLOSIVOS", "900182004910231", operadores[0].usuario_id, puesto_1.puesto_id, True, hoy + timedelta(days=190), 3.5, 6.0, "APTO_OPERATIVO"),
            ("K9-SIB-002", "Athena", "Labrador Retriever", "NARCOTICOS", "900182004910884", operadores[8].usuario_id, puesto_3.puesto_id, True, hoy + timedelta(days=145), 4.2, 6.0, "APTO_OPERATIVO"),
            ("K9-SAL-003", "Rex", "Pastor Alemán", "DEFENSA_CONTROLADA", "900182004911092", operadores[16].usuario_id, puesto_5.puesto_id, True, hoy + timedelta(days=210), 2.0, 6.0, "APTO_OPERATIVO"),
            ("K9-FAC-004", "Sombra", "Pastor Belga Malinois", "EXPLOSIVOS", "900182004911740", operadores[12].usuario_id, puesto_4.puesto_id, True, hoy + timedelta(days=95), 5.8, 6.0, "FATIGA_PREVENTIVA"),
        ]

        for cod_k9, nom_k9, raza_k9, esp_k9, chip_k9, guia_id, p_k9_id, vac_ok, f_vac, h_trab, h_max, est_fat in datos_binomios_k9:
            sesion.add(
                ModeloBinomioCaninoK9(
                    codigo_unidad_k9=cod_k9,
                    nombre_canino=nom_k9,
                    raza=raza_k9,
                    especialidad=esp_k9,
                    codigo_microchip=chip_k9,
                    guia_operador_id=guia_id,
                    puesto_id=p_k9_id,
                    vacunacion_vigente=vac_ok,
                    fecha_vencimiento_vacunas=f_vac,
                    horas_trabajadas_turno=h_trab,
                    max_horas_continuas_norma=h_max,
                    estado_fatiga=est_fat,
                    ultimo_descanso_canil=ahora_utc - timedelta(hours=int(h_trab)),
                    observaciones_veterinarias=f"Certificación ICA y registro SuperVigilancia activo. Chip ISO {chip_k9} verificado.",
                    tenant_id=TENANT_PRINCIPAL,
                )
            )

        # 18 Dispositivos de Seguridad Electrónica y Cercas Perimetrales (3 por cada uno de los 6 puestos)
        dispositivos_tecnologicos = [
            # PST-BOG-01
            ("TEC-BOG01-LPR", puesto_1.puesto_id, "CAMARA_IP_LPR", "Cámara LPR Sótano Bóveda Bancaria #1", "ONLINE", 12, 0.0),
            ("TEC-BOG01-NVR", puesto_1.puesto_id, "NVR_GRABADOR", "Servidor NVR 64CH redundante RAID-6", "ONLINE", 8, 0.0),
            ("TEC-BOG01-RAD", puesto_1.puesto_id, "RADAR_PERIMETRAL", "Sensor Microondas Helipuerto Piso 28", "ONLINE", 15, 0.0),
            # PST-OCC-02
            ("TEC-OCC02-LPR", puesto_2.puesto_id, "CAMARA_IP_LPR", "Arco LPR Lectura Placas Báscula Camionera", "ONLINE", 18, 0.0),
            ("TEC-OCC02-CER", puesto_2.puesto_id, "CERCA_ELECTRICA", "Cerca Perimetral Electrificada 1.8km Sabana", "ONLINE", 14, 10.8),
            ("TEC-OCC02-DRN", puesto_2.puesto_id, "DRON_AUTONOMO", "Dron Térmico Autónomo DJI Enterprise Dock", "ONLINE", 24, 0.0),
            # PST-BOG-03
            ("TEC-BOG03-LPR", puesto_3.puesto_id, "CAMARA_IP_LPR", "Cámara LPR Aduanera Zona Franca Siberia", "ONLINE", 16, 0.0),
            ("TEC-BOG03-CER", puesto_3.puesto_id, "CERCA_ELECTRICA", "Cerca Perimetral Patio Contenedores Bodega 14", "ONLINE", 11, 11.2),
            ("TEC-BOG03-NVR", puesto_3.puesto_id, "NVR_GRABADOR", "Clúster Video Analítica IA Fiscal", "ONLINE", 9, 0.0),
            # PST-FAC-04
            ("TEC-FAC04-CER", puesto_4.puesto_id, "CERCA_ELECTRICA", "Cerca Electrificada Sector El Corzo (Norte)", "BATERIA_RESPALDO", 48, 8.4),
            ("TEC-FAC04-RAD", puesto_4.puesto_id, "RADAR_PERIMETRAL", "Barrera Infrarroja Reservorio Agroindustrial", "ONLINE", 22, 0.0),
            ("TEC-FAC04-DRN", puesto_4.puesto_id, "DRON_AUTONOMO", "Patrulla Aérea Nocturna Sabana Occidente", "ONLINE", 29, 0.0),
            # PST-BOG-05
            ("TEC-BOG05-LPR", puesto_5.puesto_id, "CAMARA_IP_LPR", "Lector Vehicular Portería Salitre", "ONLINE", 10, 0.0),
            ("TEC-BOG05-CER", puesto_5.puesto_id, "CERCA_ELECTRICA", "Cerca Perimetral Sendero Peatonal Oriental", "ONLINE", 13, 10.2),
            ("TEC-BOG05-NVR", puesto_5.puesto_id, "NVR_GRABADOR", "Central CCTV Recepción Reserva del Parque", "ONLINE", 7, 0.0),
            # PST-BOG-06
            ("TEC-BOG06-LPR", puesto_6.puesto_id, "CAMARA_IP_LPR", "Esclusa Biométrica & Reconocimiento Facial Tier-IV", "ONLINE", 6, 0.0),
            ("TEC-BOG06-CER", puesto_6.puesto_id, "CERCA_ELECTRICA", "Muro Electrificado Alta Seguridad Subestación", "ONLINE", 9, 12.0),
            ("TEC-BOG06-NVR", puesto_6.puesto_id, "NVR_GRABADOR", "Bóveda Criptográfica de Video ISO-27001", "ONLINE", 5, 0.0),
        ]

        for cod_disp, p_tec_id, tipo_d, ub_det, est_op, lat_ms, volt_kv in dispositivos_tecnologicos:
            sesion.add(
                ModeloMedioTecnologico(
                    codigo_dispositivo=cod_disp,
                    puesto_id=p_tec_id,
                    tipo_dispositivo=tipo_d,
                    ubicacion_detalle=ub_det,
                    estado_operativo=est_op,
                    latencia_ms=lat_ms,
                    voltaje_cerca_kv=volt_kv,
                    bateria_respaldo_pct=88 if est_op == "BATERIA_RESPALDO" else 100,
                    ultima_telemetria=ahora_utc - timedelta(minutes=2),
                    tenant_id=TENANT_PRINCIPAL,
                )
            )

        # =====================================================================
        # 13. CUMPLIMIENTO SARLAFT 2.0 & SG-SST DECRETO 1072 / HOMBRE CAÍDO
        # =====================================================================
        datos_sarlaft_semilla = [
            ("SARL-2026-0001", "1020771001", "Brayan Stiven Castañeda", "ASPIRANTE_GUARDA", "SIN_COINCIDENCIAS", "NINGUNA", True, "Validación de antecedentes judiciales PONAL, Procuraduría, Contraloría y OFAC sin registros adversos."),
            ("SARL-2026-0002", "900481920-1", "Banco Corporativo de los Andes S.A.", "CLIENTE_B2B", "SIN_COINCIDENCIAS", "NINGUNA", True, "Debida diligencia B2B conforme a Circular Externa SuperVigilancia SARLAFT 2.0."),
            ("SARL-2026-0003", "901223890-4", "Logística Andina Zona Franca S.A.S.", "CLIENTE_B2B", "SIN_COINCIDENCIAS", "NINGUNA", True, "Beneficiarios finales validados sin alertas en listas ONU / OFAC."),
            ("SARL-2026-0004", "79884120", "Dr. Gustavo Adolfo Mendoza Pardo (Ex-Viceministro)", "VISITANTE_CRITICO", "RIESGO_MEDIO_PEP", "PEP_NACIONAL_FUNCIONARIO_PUBLICO", True, "Persona Expuesta Políticamente (PEP). Requiere aprobación de Oficial de Cumplimiento para contratos B2B."),
            ("SARL-2026-0005", "80666999", "Alias 'El Zar' / Inversiones Fantasma del Caribe Ltda.", "VISITANTE_CRITICO", "BLOQUEO_LISTA_RESTRICTIVA", "OFAC_SDN_CLINTON,INTERPOL_CIRCULAR_ROJA,PONAL_CAPTURA", False, "BLOQUEO INMEDIATO SARLAFT: Coincidencia exacta en Lista OFAC SDN y Circular Roja INTERPOL. Reporte ROS generado a UIAF."),
            ("SARL-2026-0006", "1020771005", "Jhon Fredy Ospina", "ASPIRANTE_GUARDA", "SIN_COINCIDENCIAS", "NINGUNA", True, "Verificación de ingreso personal operativo Sabana de Occidente aprobada."),
            ("SARL-2026-0007", "900774112-8", "Agroexportadora de la Sabana S.A.", "CLIENTE_B2B", "SIN_COINCIDENCIAS", "NINGUNA", True, "Certificado BASC y validación SARLAFT vigente sin hallazgos."),
            ("SARL-2026-0008", "1020771009", "Yerson David Mosquera", "ASPIRANTE_GUARDA", "SIN_COINCIDENCIAS", "NINGUNA", True, "Consulta anual ordinaria de personal armado en Zona Franca Siberia."),
            ("SARL-2026-0009", "830091234-5", "DataCenter Colombia Tier-IV S.A.S.", "CLIENTE_B2B", "SIN_COINCIDENCIAS", "NINGUNA", True, "Debida diligencia ampliada para cliente de infraestructura crítica nacional."),
            ("SARL-2026-0010", "52441980", "Dra. Marcela Patiño Restrepo", "VISITANTE_CRITICO", "SIN_COINCIDENCIAS", "NINGUNA", True, "Validación instantánea en portería para ingreso a presidencia financiera."),
        ]

        hash_prev_sarlaft = HASH_GENESIS_SHA256
        for idx_s, (cod_cert, doc_s, nom_s, tipo_t, niv_r, listas_pos, apto_s, det_s) in enumerate(datos_sarlaft_semilla):
            f_sarl = ahora_utc - timedelta(hours=30 - idx_s * 2)
            payload_sarl = f"SARLAFT_2_0|{cod_cert}|{doc_s}|{nom_s}|{tipo_t}|{niv_r}|{listas_pos}|{f_sarl.isoformat()}"
            sello_sarl = calcular_hash_encadenado_sha256(payload_sarl, hash_prev_sarlaft)
            sesion.add(
                ModeloCertificadoSarlaft(
                    codigo_certificado=cod_cert,
                    documento_consultado=doc_s,
                    nombre_consultado=nom_s,
                    tipo_tercero=tipo_t,
                    nivel_riesgo=niv_r,
                    listas_coincidentes=listas_pos,
                    listas_evaluadas="OFAC_CLINTON,ONU_CONSEJO_SEGURIDAD,INTERPOL,PONAL_ANTECEDENTES,PROCURADURIA_SIRI,CONTRALORIA_SIBOR",
                    apto_contratacion_ingreso=apto_s,
                    detalle_validacion=det_s,
                    consultado_por_id=admin.usuario_id,
                    sello_auditoria_sha256=sello_sarl,
                    hash_anterior_sha256=hash_prev_sarlaft,
                    tenant_id=TENANT_PRINCIPAL,
                    fecha_consulta=f_sarl,
                )
            )
            hash_prev_sarlaft = sello_sarl

        # 6 Controles de Aptitud Psicofísica SG-SST Pre-Turno y 6 Monitores de Hombre Caído (1 por Puesto)
        for idx_p, p_sst in enumerate([puesto_1, puesto_2, puesto_3, puesto_4, puesto_5, puesto_6]):
            op_sst = operadores[idx_p * 4]
            f_check = ahora_utc - timedelta(hours=4)
            sello_sst = calcular_hash_encadenado_sha256(
                f"SST_1072|{p_sst.codigo_puesto}|{op_sst.documento_identidad}|7.5|APTO_OPERATIVO|{f_check.isoformat()}",
                HASH_GENESIS_SHA256,
            )
            sesion.add(
                ModeloCheckAptitudSst(
                    operador_id=op_sst.usuario_id,
                    puesto_id=p_sst.puesto_id,
                    horas_sueno_reportadas=7.5 if idx_p != 3 else 6.5,
                    cero_alcohol_fatiga=True,
                    chaleco_kevlar_verificado=True,
                    serial_chaleco_asignado=f"KEV-IIIA-{2022 + (idx_p % 3)}-0{idx_p + 1}",
                    fecha_fabricacion_chaleco=hoy - timedelta(days=365 * (2 + (idx_p % 3))),
                    apto_operacion=True,
                    estado_evaluacion="APTO_OPERATIVO",
                    observaciones_sst=f"Check-in psicofísico Decreto 1072 verificado en {p_sst.codigo_puesto}. Panel balístico Kevlar Nivel IIIA vigente.",
                    sello_sst_sha256=sello_sst,
                    tenant_id=TENANT_PRINCIPAL,
                    fecha_check=f_check,
                )
            )

            minutos_sin_pulso = 2 if idx_p != 3 else 11
            estado_hc = "ACTIVO_NORMAL" if idx_p != 3 else "PRE_ALERTA_INACTIVIDAD"
            sesion.add(
                ModeloMonitoreoHombreCaido(
                    puesto_id=p_sst.puesto_id,
                    operador_id=op_sst.usuario_id,
                    intervalo_esperado_min=15,
                    ultimo_latido_utc=ahora_utc - timedelta(minutes=minutos_sin_pulso),
                    estado_supervivencia=estado_hc,
                    latidos_consecutivos_exitosos=28 + idx_p * 5,
                    alertas_disparadas_turno=0 if idx_p != 3 else 1,
                    tenant_id=TENANT_PRINCIPAL,
                )
            )

        await sesion.commit()

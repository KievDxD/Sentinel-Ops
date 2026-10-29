"""
Servicio de inicialización de datos semilla (Seed Release Enterprise V2.0) para SENTINEL // OPS.
Crea usuarios para los 5 roles RBAC (ADMINISTRADOR, SUPERVISOR, RRHH, OPERADOR, CLIENTE),
credenciales SuperVigilancia, puestos de vigilancia, dotación/armamento Indumil,
programación 2x2 de 12 horas (Ley 2101 - 42h), minuta con visibilidad dual y acta SHA-256.
"""

import hashlib
from datetime import date, timedelta
from sqlalchemy import select

from app.modelos.modelos_bd import (
    EstadoItemDotacion,
    EstadoSolicitudIntercambio,
    EstadoTurno,
    ModeloActaRelevoPuesto,
    ModeloDotacionPuesto,
    ModeloMarcacionRonda,
    ModeloPuestoVigilancia,
    ModeloPuntoControlRonda,
    ModeloRegistroMinuta,
    ModeloSolicitudIntercambio,
    ModeloTurno,
    ModeloUsuario,
    NivelCursoVigilancia,
    NivelPrioridad,
    RolUsuario,
    TipoRegistroMinuta,
    TipoTurno,
    VisibilidadMinuta,
)
from app.nucleo.base_datos import FabricaSesionesAsincronas
from app.nucleo.seguridad import encriptar_contrasena
from app.servicios.motor_turnos import (
    generar_matriz_cobertura_puesto_2x2,
    validar_factibilidad_intercambio,
)


async def inicializar_datos_semilla() -> None:
    """Puebla la base de datos con registros operativos iniciales V2.0 si está vacía."""
    async with FabricaSesionesAsincronas() as sesion:
        consulta_existente = select(ModeloUsuario).limit(1)
        resultado = await sesion.execute(consulta_existente)
        if resultado.scalar_one_or_none() is not None:
            return

        contrasena_demo: str = encriptar_contrasena("Sentinel2026*")
        hoy: date = date.today()

        # 1. Crear Puestos de Vigilancia B2B
        puesto_torre = ModeloPuestoVigilancia(
            codigo_puesto="PST-BOG-01",
            nombre_puesto="Torre Financiera Nogal - Lobby Principal",
            empresa_cliente="Grupo Bancario Andino S.A.",
            direccion_ubicacion="Carrera 7 # 76-35, Chapinero",
            ciudad="Bogotá D.C.",
            requiere_armamento=True,
            activo=True,
        )
        puesto_logistico = ModeloPuestoVigilancia(
            codigo_puesto="PST-BOG-02",
            nombre_puesto="Centro Logístico Zona Franca - Portería Vehicular",
            empresa_cliente="Almacenes Industriales del Caribe",
            direccion_ubicacion="Avenida Centenario # 131-10, Fontibón",
            ciudad="Bogotá D.C.",
            requiere_armamento=True,
            activo=True,
        )
        puesto_corporativo = ModeloPuestoVigilancia(
            codigo_puesto="PST-MED-03",
            nombre_puesto="Campus Tecnológico El Poblado",
            empresa_cliente="DataCloud Colombia SAS",
            direccion_ubicacion="Avenida El Poblado # 10-45",
            ciudad="Medellín",
            requiere_armamento=False,
            activo=True,
        )

        sesion.add_all([puesto_torre, puesto_logistico, puesto_corporativo])
        await sesion.flush()

        # 2. Crear Inventario de Dotación y Armamento Indumil por Puesto (V2.0)
        dotacion_1 = ModeloDotacionPuesto(
            puesto_id=puesto_torre.puesto_id,
            tipo_arma="Revólver Llama Martial Calibre .38L",
            serial_arma="IND-38L-994812",
            numero_salvoconducto_indumil="SLV-2026-884120",
            tipo_salvoconducto="TENENCIA",
            fecha_vencimiento_salvoconducto=hoy + timedelta(days=240),
            cantidad_municion_autorizada=18,
            serial_chaleco_balistico="CHB-IIIA-4410",
            serie_radio_comunicacion="MOT-DEP450-101",
            celular_corporativo_imei="358901234567890",
            tiene_linterna_tactica=True,
            llaves_y_minutas_fisicas=True,
        )
        dotacion_2 = ModeloDotacionPuesto(
            puesto_id=puesto_logistico.puesto_id,
            tipo_arma="Escopeta Remington 870 Calibre 12",
            serial_arma="IND-12G-773190",
            numero_salvoconducto_indumil="SLV-2026-551902",
            tipo_salvoconducto="TENENCIA",
            fecha_vencimiento_salvoconducto=hoy + timedelta(days=180),
            cantidad_municion_autorizada=15,
            serial_chaleco_balistico="CHB-IIIA-4415",
            serie_radio_comunicacion="MOT-DEP450-202",
            celular_corporativo_imei="358901234567891",
            tiene_linterna_tactica=True,
            llaves_y_minutas_fisicas=True,
        )
        dotacion_3 = ModeloDotacionPuesto(
            puesto_id=puesto_corporativo.puesto_id,
            tipo_arma="Dispositivo No Letal Taser X2 / Bastón Tonfa",
            serial_arma="NL-TSR-110294",
            numero_salvoconducto_indumil="REG-SV-NL-3091",
            tipo_salvoconducto="PORTE",
            fecha_vencimiento_salvoconducto=hoy + timedelta(days=320),
            cantidad_municion_autorizada=4,
            serial_chaleco_balistico="CHB-IIA-5501",
            serie_radio_comunicacion="MOT-DEP450-303",
            celular_corporativo_imei="358901234567892",
            tiene_linterna_tactica=True,
            llaves_y_minutas_fisicas=True,
        )
        sesion.add_all([dotacion_1, dotacion_2, dotacion_3])
        await sesion.flush()

        # 3. Crear usuarios para los 5 roles RBAC (incluyendo RRHH y CLIENTE)
        admin = ModeloUsuario(
            documento_identidad="CC-80123456",
            nombre_completo="Comandante Alejandro Vargas",
            correo_electronico="admin@sentinelops.co",
            telefono="+57 310 450 1100",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.ADMINISTRADOR,
            codigo_placa="ADM-001",
            puesto_base_id=puesto_torre.puesto_id,
            numero_credencial_sv="SV-DIR-00192",
            fecha_vencimiento_credencial=hoy + timedelta(days=365),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=365),
            nivel_curso=NivelCursoVigilancia.ESPECIALIZACION,
            activo=True,
        )
        supervisor = ModeloUsuario(
            documento_identidad="CC-79654321",
            nombre_completo="Capitán Valeria Mendoza",
            correo_electronico="supervisor@sentinelops.co",
            telefono="+57 315 890 2200",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.SUPERVISOR,
            codigo_placa="SUP-104",
            puesto_base_id=puesto_torre.puesto_id,
            numero_credencial_sv="SV-SUP-44810",
            fecha_vencimiento_credencial=hoy + timedelta(days=280),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=250),
            nivel_curso=NivelCursoVigilancia.ESPECIALIZACION,
            activo=True,
        )
        rrhh = ModeloUsuario(
            documento_identidad="CC-52981234",
            nombre_completo="Directora RRHH Laura Sofía Cárdenas",
            correo_electronico="rrhh@sentinelops.co",
            telefono="+57 311 340 5500",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.RRHH,
            codigo_placa="RRH-201",
            puesto_base_id=puesto_torre.puesto_id,
            numero_credencial_sv="SV-ADM-20100",
            fecha_vencimiento_credencial=hoy + timedelta(days=365),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=365),
            nivel_curso=NivelCursoVigilancia.FUNDAMENTACION,
            activo=True,
        )
        cliente = ModeloUsuario(
            documento_identidad="NIT-900456123",
            nombre_completo="Director de Seguridad Banco Andino (Dr. Roberto Silva)",
            correo_electronico="cliente@sentinelops.co",
            telefono="+57 314 220 9900",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.CLIENTE,
            codigo_placa="CLI-901",
            puesto_base_id=puesto_torre.puesto_id,
            activo=True,
        )

        # Escuadra 1: Puesto Torre Financiera Nogal (PST-BOG-01)
        op1 = ModeloUsuario(
            documento_identidad="CC-1020456789",
            nombre_completo="Guardia Carlos Andrés Ramírez",
            correo_electronico="operador1@sentinelops.co",
            telefono="+57 320 771 3301",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.OPERADOR,
            codigo_placa="OPR-401",
            puesto_base_id=puesto_torre.puesto_id,
            numero_credencial_sv="SV-OPR-88201",
            fecha_vencimiento_credencial=hoy + timedelta(days=190),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=160),
            nivel_curso=NivelCursoVigilancia.ESPECIALIZACION,
            activo=True,
        )
        op2 = ModeloUsuario(
            documento_identidad="CC-1032987654",
            nombre_completo="Guardia Julián Esteban Pineda",
            correo_electronico="operador2@sentinelops.co",
            telefono="+57 311 662 4402",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.OPERADOR,
            codigo_placa="OPR-402",
            puesto_base_id=puesto_torre.puesto_id,
            numero_credencial_sv="SV-OPR-88202",
            fecha_vencimiento_credencial=hoy + timedelta(days=145),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=120),
            nivel_curso=NivelCursoVigilancia.REENTRENAMIENTO,
            activo=True,
        )
        op3 = ModeloUsuario(
            documento_identidad="CC-1045123987",
            nombre_completo="Guardia Mateo Suárez Delgado",
            correo_electronico="operador3@sentinelops.co",
            telefono="+57 318 903 5503",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.OPERADOR,
            codigo_placa="OPR-403",
            puesto_base_id=puesto_torre.puesto_id,
            numero_credencial_sv="SV-OPR-88203",
            # Por vencer (<= 30 días) para activar semáforo ámbar preventivo
            fecha_vencimiento_credencial=hoy + timedelta(days=14),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=20),
            nivel_curso=NivelCursoVigilancia.REENTRENAMIENTO,
            activo=True,
        )

        # Escuadra 2: Puesto Centro Logístico Zona Franca (PST-BOG-02)
        op4 = ModeloUsuario(
            documento_identidad="CC-1052678123",
            nombre_completo="Guardia Diego Alejandro Morales",
            correo_electronico="operador4@sentinelops.co",
            telefono="+57 312 445 6604",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.OPERADOR,
            codigo_placa="OPR-404",
            puesto_base_id=puesto_logistico.puesto_id,
            numero_credencial_sv="SV-OPR-88204",
            fecha_vencimiento_credencial=hoy + timedelta(days=210),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=200),
            nivel_curso=NivelCursoVigilancia.ESPECIALIZACION,
            activo=True,
        )
        op5 = ModeloUsuario(
            documento_identidad="CC-1063789234",
            nombre_completo="Guardia Camilo Ernesto Herrera",
            correo_electronico="operador5@sentinelops.co",
            telefono="+57 314 556 7705",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.OPERADOR,
            codigo_placa="OPR-405",
            puesto_base_id=puesto_logistico.puesto_id,
            numero_credencial_sv="SV-OPR-88205",
            fecha_vencimiento_credencial=hoy + timedelta(days=175),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=150),
            nivel_curso=NivelCursoVigilancia.REENTRENAMIENTO,
            activo=True,
        )
        op6 = ModeloUsuario(
            documento_identidad="CC-1074890345",
            nombre_completo="Guardia Brayan Alexis Castro",
            correo_electronico="operador6@sentinelops.co",
            telefono="+57 316 667 8806",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.OPERADOR,
            codigo_placa="OPR-406",
            puesto_base_id=puesto_logistico.puesto_id,
            numero_credencial_sv="SV-OPR-88206",
            fecha_vencimiento_credencial=hoy + timedelta(days=95),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=90),
            nivel_curso=NivelCursoVigilancia.FUNDAMENTACION,
            activo=True,
        )

        # Escuadra 3: Puesto Campus Tecnológico El Poblado (PST-MED-03)
        op7 = ModeloUsuario(
            documento_identidad="CC-1085901456",
            nombre_completo="Guardia Juan Sebastián Ríos",
            correo_electronico="operador7@sentinelops.co",
            telefono="+57 317 778 9907",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.OPERADOR,
            codigo_placa="OPR-407",
            puesto_base_id=puesto_corporativo.puesto_id,
            numero_credencial_sv="SV-OPR-88207",
            fecha_vencimiento_credencial=hoy + timedelta(days=230),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=210),
            nivel_curso=NivelCursoVigilancia.FUNDAMENTACION,
            activo=True,
        )
        op8 = ModeloUsuario(
            documento_identidad="CC-1096012567",
            nombre_completo="Guardia Cristian Camilo Ortiz",
            correo_electronico="operador8@sentinelops.co",
            telefono="+57 319 889 0008",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.OPERADOR,
            codigo_placa="OPR-408",
            puesto_base_id=puesto_corporativo.puesto_id,
            numero_credencial_sv="SV-OPR-88208",
            fecha_vencimiento_credencial=hoy + timedelta(days=19),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=45),
            nivel_curso=NivelCursoVigilancia.REENTRENAMIENTO,
            activo=True,
        )
        op9 = ModeloUsuario(
            documento_identidad="CC-1107123678",
            nombre_completo="Guardia Andrés Felipe Zapata",
            correo_electronico="operador9@sentinelops.co",
            telefono="+57 313 990 1109",
            contrasena_encriptada=contrasena_demo,
            rol=RolUsuario.OPERADOR,
            codigo_placa="OPR-409",
            puesto_base_id=puesto_corporativo.puesto_id,
            numero_credencial_sv="SV-OPR-88209",
            # Credencial vencida hace 4 días para demostrar alerta roja de bloqueo SuperVigilancia
            fecha_vencimiento_credencial=hoy - timedelta(days=4),
            fecha_vencimiento_psicofisico=hoy + timedelta(days=60),
            nivel_curso=NivelCursoVigilancia.FUNDAMENTACION,
            excepcion_credencial_autorizada=False,
            activo=True,
        )

        sesion.add_all(
            [
                admin,
                supervisor,
                rrhh,
                cliente,
                op1,
                op2,
                op3,
                op4,
                op5,
                op6,
                op7,
                op8,
                op9,
            ]
        )
        await sesion.flush()

        # 4. Generar programación continua 24/7 (30 días) para los 3 puestos de vigilancia
        escuadras_puestos = [
            (puesto_torre.puesto_id, [op1.usuario_id, op2.usuario_id, op3.usuario_id]),
            (
                puesto_logistico.puesto_id,
                [op4.usuario_id, op5.usuario_id, op6.usuario_id],
            ),
            (
                puesto_corporativo.puesto_id,
                [op7.usuario_id, op8.usuario_id, op9.usuario_id],
            ),
        ]

        turnos_guardados: list[ModeloTurno] = []
        for p_id, ops_ids in escuadras_puestos:
            matriz = generar_matriz_cobertura_puesto_2x2(
                puesto_id=p_id,
                operadores_ids=ops_ids,
                fecha_inicio_ciclo=hoy,
                cantidad_dias=30,
            )
            for datos_t in matriz:
                turno_nuevo = ModeloTurno(
                    operador_id=datos_t["operador_id"],
                    puesto_id=datos_t["puesto_id"],
                    tipo_turno=datos_t["tipo_turno"],
                    estado_turno=EstadoTurno.PROGRAMADO,
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

        # 5. Crear Acta Inicial de Entrega y Recibo de Puesto con Armamento Indumil (V2.0)
        sello_acta_1 = hashlib.sha256(
            f"ACTA_RELEVO|{puesto_torre.puesto_id}|{op1.usuario_id}|IND-38L-994812|18".encode(
                "utf-8"
            )
        ).hexdigest()
        acta_inicial = ModeloActaRelevoPuesto(
            puesto_id=puesto_torre.puesto_id,
            operador_saliente_id=op2.usuario_id,
            operador_entrante_id=op1.usuario_id,
            estado_armamento=EstadoItemDotacion.OPTIMO,
            municion_verificada=18,
            estado_chaleco=EstadoItemDotacion.OPTIMO,
            estado_radio=EstadoItemDotacion.OPTIMO,
            estado_linterna_y_llaves=EstadoItemDotacion.OPTIMO,
            observaciones_relevo=(
                "Relevo 06:00h verificado. Revólver .38L serial IND-38L-994812 con 18 cartuchos, "
                "salvoconducto Indumil vigente en cofre y radio Motorola operativo."
            ),
            sello_sha256=sello_acta_1,
            alerta_disparada=False,
        )
        sesion.add(acta_inicial)

        # 6. Crear Registros Iniciales de Minuta Digital con Visibilidad Dual
        minuta_1 = ModeloRegistroMinuta(
            operador_id=op1.usuario_id,
            puesto_id=puesto_torre.puesto_id,
            tipo_registro=TipoRegistroMinuta.ENTREGA_RECIBO_PUESTO,
            visibilidad=VisibilidadMinuta.PUBLICA_CLIENTE,
            nivel_prioridad=NivelPrioridad.BAJA,
            titulo_evento=f"[ACTA SHA-256: {sello_acta_1[:12].upper()}] Entrega de puesto y armamento Indumil conforme",
            descripcion_detallada=(
                "Se recibe puesto PST-BOG-01 con Revólver .38L (18 cartuchos), radio Motorola encriptado, "
                "chaleco balístico nivel IIIA y libro electrónico sincronizado."
            ),
        )
        minuta_2 = ModeloRegistroMinuta(
            operador_id=op4.usuario_id,
            puesto_id=puesto_logistico.puesto_id,
            tipo_registro=TipoRegistroMinuta.INGRESO_VEHICULO,
            visibilidad=VisibilidadMinuta.PUBLICA_CLIENTE,
            nivel_prioridad=NivelPrioridad.MEDIA,
            titulo_evento="Ingreso de tractomula de valores autorizada",
            descripcion_detallada=(
                "Se verifica manifiesto de carga y sellos de seguridad en muelles 3 y 4."
            ),
            nombre_visitante="Hernán Darío Gómez",
            documento_visitante="CC-71882910",
            placa_vehiculo="WXY-942",
        )
        minuta_3 = ModeloRegistroMinuta(
            operador_id=op1.usuario_id,
            puesto_id=puesto_torre.puesto_id,
            tipo_registro=TipoRegistroMinuta.RONDA_CONTROL,
            visibilidad=VisibilidadMinuta.PUBLICA_CLIENTE,
            nivel_prioridad=NivelPrioridad.ALTA,
            titulo_evento="Ronda perimetral en sótano 2 y cuarto de generadores",
            descripcion_detallada=(
                "Se detectó puerta de emergencia con sensor magnético desajustado. "
                "Se aseguró manualmente y se notificó a mantenimiento locativo."
            ),
        )
        minuta_4_interna = ModeloRegistroMinuta(
            operador_id=supervisor.usuario_id,
            puesto_id=puesto_torre.puesto_id,
            tipo_registro=TipoRegistroMinuta.NOVEDAD_INCIDENTE,
            visibilidad=VisibilidadMinuta.INTERNA_OPERATIVA,
            nivel_prioridad=NivelPrioridad.MEDIA,
            titulo_evento="[NOTA INTERNA SUPERVISIÓN] Revisión de protocolo de relevo nocturno",
            descripcion_detallada=(
                "Directiva interna para escoltas y guardias: programar reentrenamiento de polígono "
                "para el operador OPR-403 antes del vencimiento de su credencial SV."
            ),
        )
        sesion.add_all([minuta_1, minuta_2, minuta_3, minuta_4_interna])
        await sesion.flush()

        # 7. Crear una solicitud de intercambio inicial validada por el motor
        turnos_op1 = [
            t
            for t in turnos_guardados
            if t.operador_id == op1.usuario_id and t.tipo_turno != TipoTurno.DESCANSO
        ]
        turnos_op2 = [
            t
            for t in turnos_guardados
            if t.operador_id == op2.usuario_id and t.tipo_turno != TipoTurno.DESCANSO
        ]
        if len(turnos_op1) >= 2 and len(turnos_op2) >= 2:
            turno_origen_demo = turnos_op1[0]
            turno_destino_demo = turnos_op2[1]
            es_valido, descanso_min, detalle_val = validar_factibilidad_intercambio(
                turno_origen_demo,
                turno_destino_demo,
                [t for t in turnos_guardados if t.operador_id == op1.usuario_id],
                [t for t in turnos_guardados if t.operador_id == op2.usuario_id],
            )
            if es_valido:
                solicitud_demo = ModeloSolicitudIntercambio(
                    operador_solicitante_id=op1.usuario_id,
                    operador_receptor_id=op2.usuario_id,
                    turno_origen_id=turno_origen_demo.turno_id,
                    turno_destino_id=turno_destino_demo.turno_id,
                    motivo_solicitud="Cita médica prioritaria de control ocupacional.",
                    estado_solicitud=EstadoSolicitudIntercambio.PENDIENTE,
                    validacion_sin_cruces=True,
                    horas_descanso_minimo_calculadas=descanso_min,
                    detalle_validacion_motor=detalle_val,
                )
                sesion.add(solicitud_demo)

        # 8. Crear Puntos de Control QR/GPS (Fase 5)
        punto_1 = ModeloPuntoControlRonda(
            puesto_id=puesto_torre.puesto_id,
            codigo_qr_hash="QR-SNT-BOG01-SOTANO2",
            nombre_punto="Bóveda y Cuarto de Generadores Sótano 2",
            latitud_gps=4.6612,
            longitud_gps=-74.0535,
            radio_tolerancia_metros=45.0,
            orden_secuencia=1,
            activo=True,
        )
        punto_2 = ModeloPuntoControlRonda(
            puesto_id=puesto_torre.puesto_id,
            codigo_qr_hash="QR-SNT-BOG01-HELIPUERTO",
            nombre_punto="Acceso Helipuerto y Terraza Técnica Piso 28",
            latitud_gps=4.6614,
            longitud_gps=-74.0533,
            radio_tolerancia_metros=40.0,
            orden_secuencia=2,
            activo=True,
        )
        punto_3 = ModeloPuntoControlRonda(
            puesto_id=puesto_logistico.puesto_id,
            codigo_qr_hash="QR-SNT-BOG02-MUELLE4",
            nombre_punto="Muelle de Carga Pesada #4 y Patio de Contenedores",
            latitud_gps=4.6785,
            longitud_gps=-74.1412,
            radio_tolerancia_metros=60.0,
            orden_secuencia=1,
            activo=True,
        )
        sesion.add_all([punto_1, punto_2, punto_3])
        await sesion.flush()

        marcacion_inicial = ModeloMarcacionRonda(
            punto_id=punto_1.punto_id,
            operador_id=op1.usuario_id,
            latitud_capturada=4.66125,
            longitud_capturada=-74.05348,
            distancia_calculada_metros=5.9,
            dentro_de_geocerca=True,
            sincronizado_desde_offline=False,
            observacion_ronda="Verificación QR/GPS sin novedad. Generador auxiliar en modo automático.",
        )
        sesion.add(marcacion_inicial)

        await sesion.commit()

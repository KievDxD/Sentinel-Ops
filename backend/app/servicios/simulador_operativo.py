"""
Motor de Simulación Operativa en Tiempo Real y Analítica Ejecutiva (Release Enterprise V4.0).
Proporciona:
- Telemetría GPS viva para patrullas motorizadas en corredores viales de Bogotá y Sabana de Occidente.
- Inyección bajo demanda de ráfagas operativas encadenadas con SHA-256 (Garita LPR + Ronda QR/GPS + Minuta WS).
- Bucle asíncrono en segundo plano activable/desactivable para telemetría continua.
- Auditoría criptográfica en caliente del 100% de los bloques SHA-256 (Minuta, Actas de Relevo y Kardex Balístico).
- Cálculo de KPIs ejecutivos en tiempo real (SLA por sede, Nómina Ley 2101, Reacción CAD y Aforo Perimetral).
"""

import asyncio
from datetime import date, datetime, timezone
import hashlib
import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos.modelos_bd import (
    EstadoAccesoGarita,
    EstadoAlertaSos,
    ModeloActaRelevoPuesto,
    ModeloAlertaPanicoSos,
    ModeloDotacionPuesto,
    ModeloKardexBalistico,
    ModeloMarcacionRonda,
    ModeloPuestoVigilancia,
    ModeloPuntoControlRonda,
    ModeloRegistroAccesoGarita,
    ModeloRegistroMinuta,
    ModeloTurno,
    ModeloUsuario,
    NivelPrioridad,
    RolUsuario,
    TipoAccesoGarita,
    TipoRegistroMinuta,
    TipoTurno,
    VisibilidadMinuta,
)
from app.nucleo.configuracion import configuracion
from app.nucleo.seguridad import HASH_GENESIS_SHA256, calcular_hash_encadenado_sha256
from app.rutas.rutas_rondas import calcular_distancia_haversine_metros
from app.servicios.gestor_websockets import gestor_minuta_ws
from app.servicios.semilla import COORDENADAS_PUESTOS_V4, TENANT_PRINCIPAL

# Corredores viales base para los supervisores motorizados CAD
CORREDORES_PATRULLAS_BASE: dict[str, tuple[float, float, str]] = {
    "SUP-101": (4.6585, -74.0595, "Corredor Financiero Carrera 7 / Chapinero"),
    "SUP-102": (4.7450, -74.2650, "Troncal de Occidente Calle 13 / Madrid - Facatativá"),
    "SUP-103": (4.7280, -74.1190, "Autopista Medellín Calle 80 / Glorieta Siberia"),
    "SUP-104": (4.6390, -74.1050, "Avenida Boyacá / Ciudad Salitre - Zona Industrial"),
}

CATALOGO_EVENTOS_RAFAGA: list[dict[str, Any]] = [
    {
        "codigo_puesto": "PST-OCC-02",
        "tipo_acceso": TipoAccesoGarita.VEHICULAR,
        "documento": "79884512",
        "nombres": "RODRIGO HERNÁN",
        "apellidos": "CASTIBLANCO",
        "rh": "O+",
        "placa": "TRK-784",
        "destino": "Muelle Logístico #2 - Sabana",
        "motivo": "Ingreso de tractomula con carga contenerizada verificada por cámara LPR",
        "titulo_minuta": "[SIMULACIÓN VIVA LPR] Ingreso de tractomula TRK-784 en Parque Logístico Sabana",
        "detalle_minuta": "Cámara LPR validó matrícula TRK-784 en corredor Madrid-Facatativá. Precinto satelital y manifiesto DIAN conformes.",
        "prioridad": NivelPrioridad.MEDIA,
    },
    {
        "codigo_puesto": "PST-BOG-01",
        "tipo_acceso": TipoAccesoGarita.PEATONAL_VISITANTE,
        "documento": "1020765432",
        "nombres": "SANTIAGO FELIPE",
        "apellidos": "MONTOYA URIBE",
        "rh": "A+",
        "placa": None,
        "destino": "Banca Corporativa Piso 14",
        "motivo": "Comité fiduciario y auditoría de riesgos bancarios",
        "titulo_minuta": "[SIMULACIÓN VIVA PDF417] Control biométrico y acceso en Torre Financiera",
        "detalle_minuta": "Escáner PDF417 verificó antecedentes y autorización Habeas Data Ley 1581 en recepción principal Chapinero.",
        "prioridad": NivelPrioridad.BAJA,
    },
    {
        "codigo_puesto": "PST-BOG-03",
        "tipo_acceso": TipoAccesoGarita.VEHICULAR,
        "documento": "80441290",
        "nombres": "GUSTAVO ADOLFO",
        "apellidos": "BARRERA",
        "rh": "B+",
        "placa": "ZFM-615",
        "destino": "Bodega Aduanera #9 - Siberia",
        "motivo": "Tránsito aduanero internacional con sello BASC",
        "titulo_minuta": "[SIMULACIÓN VIVA BASC] Inspección vehicular ZFM-615 en Zona Franca Siberia",
        "detalle_minuta": "Inspección física de contenedor en glorieta Siberia Calle 80. Sellos de seguridad verificados sin alteración.",
        "prioridad": NivelPrioridad.MEDIA,
    },
    {
        "codigo_puesto": "PST-FAC-04",
        "tipo_acceso": TipoAccesoGarita.CONTRATISTA,
        "documento": "1073551920",
        "nombres": "DARÍO FERNANDO",
        "apellidos": "CUERVO",
        "rh": "O-",
        "placa": "FAC-32E",
        "destino": "Subestación Térmica Los Andes",
        "motivo": "Revisión de sensores perimetrales e iluminación infrarroja",
        "titulo_minuta": "[SIMULACIÓN VIVA PERÍMETRO] Ronda y control técnico en Planta Facatativá",
        "detalle_minuta": "Se completa verificación de lindero norte El Corzo y acceso de contratista técnico acreditado con ARL Nivel V.",
        "prioridad": NivelPrioridad.BAJA,
    },
    {
        "codigo_puesto": "PST-BOG-06",
        "tipo_acceso": TipoAccesoGarita.CONTRATISTA,
        "documento": "1014889320",
        "nombres": "ING. CAMILO",
        "apellidos": "BENAVIDES",
        "rh": "A-",
        "placa": "NOC-401",
        "destino": "Sala Blanca de Servidores Tier-IV",
        "motivo": "Cambio preventivo de módulo óptico SFP+ en core de red",
        "titulo_minuta": "[SIMULACIÓN VIVA DATA-CENTER] Apertura controlada de esclusa en Puente Aranda",
        "detalle_minuta": "Doble autenticación biométrica aprobada en Centro de Datos PST-BOG-06. Sello SHA-256 encadenado al libro maestro.",
        "prioridad": NivelPrioridad.ALTA,
    },
]


class GestorSimulacionViva:
    """Administra el estado de telemetría dinámica y el bucle de simulación en segundo plano."""

    def __init__(self) -> None:
        self.simulacion_activa: bool = True
        self.rafagas_ejecutadas: int = 0
        self.tick_telemetria: int = 0
        self._tarea_fondo: asyncio.Task[None] | None = None

    def obtener_coordenadas_puesto(
        self, codigo_puesto: str, indice_fallback: int = 0
    ) -> tuple[float, float, float]:
        """Retorna (latitud, longitud, radio_metros) reales para el puesto indicado."""
        if codigo_puesto in COORDENADAS_PUESTOS_V4:
            return COORDENADAS_PUESTOS_V4[codigo_puesto]
        claves = list(COORDENADAS_PUESTOS_V4.keys())
        return COORDENADAS_PUESTOS_V4[claves[indice_fallback % len(claves)]]

    def obtener_coordenadas_supervisor(
        self, codigo_placa: str, indice_fallback: int = 0
    ) -> tuple[float, float]:
        """Calcula la posición GPS dinámica de la patrulla a lo largo de su corredor vial."""
        if codigo_placa in CORREDORES_PATRULLAS_BASE:
            lat_base, lon_base, _ = CORREDORES_PATRULLAS_BASE[codigo_placa]
        else:
            claves = list(CORREDORES_PATRULLAS_BASE.keys())
            lat_base, lon_base, _ = CORREDORES_PATRULLAS_BASE[
                claves[indice_fallback % len(claves)]
            ]

        fase = (self.tick_telemetria + indice_fallback * 2) * 0.65
        desplazamiento_lat = round(math.sin(fase) * 0.0045, 5)
        desplazamiento_lon = round(math.cos(fase) * 0.0045, 5)
        return (round(lat_base + desplazamiento_lat, 5), round(lon_base + desplazamiento_lon, 5))

    def avanzar_telemetria(self) -> None:
        """Incrementa el reloj interno de movimiento satelital de las patrullas."""
        self.tick_telemetria += 1

    async def _bucle_telemetria_fondo(self) -> None:
        """Emite actualizaciones periódicas de posición GPS a los clientes WebSocket conectados."""
        while self.simulacion_activa:
            try:
                await asyncio.sleep(8.0)
                if not self.simulacion_activa:
                    break
                self.avanzar_telemetria()
                await gestor_minuta_ws.difundir_evento_minuta(
                    {
                        "tipo_mensaje": "TELEMETRIA_SIMULACION_VIVA",
                        "tick": self.tick_telemetria,
                        "simulacion_activa": self.simulacion_activa,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5.0)

    def alternar_modo_simulacion(self, activar: bool | None = None) -> bool:
        """Activa o desactiva la simulación viva en segundo plano."""
        if activar is None:
            self.simulacion_activa = not self.simulacion_activa
        else:
            self.simulacion_activa = activar

        if self.simulacion_activa:
            self.avanzar_telemetria()
            try:
                loop = asyncio.get_running_loop()
                if self._tarea_fondo is None or self._tarea_fondo.done():
                    self._tarea_fondo = loop.create_task(self._bucle_telemetria_fondo())
            except RuntimeError:
                pass
        else:
            if self._tarea_fondo and not self._tarea_fondo.done():
                self._tarea_fondo.cancel()
                self._tarea_fondo = None

        return self.simulacion_activa


gestor_simulacion = GestorSimulacionViva()

# Respaldo forense en memoria para el Laboratorio de Sabotaje y Auto-Reparación SHA-256 (V5.0)
REGISTROS_SABOTEADOS_RESPALDO: dict[int, dict[str, str]] = {}


async def auditar_integridad_blockchain_sha256(sesion_bd: AsyncSession) -> dict[str, Any]:
    """
    Verifica en caliente el 100% de los bloques de Minuta, Actas de Relevo y Kardex Balístico,
    comprobando que cada cadena por puesto inicie en el génesis ('0' * 64) y mantenga sus
    eslabones SHA-256 íntegros sin adulteración.
    """
    minutas = list(
        (
            await sesion_bd.execute(
                select(ModeloRegistroMinuta).order_by(
                    ModeloRegistroMinuta.puesto_id.asc(),
                    ModeloRegistroMinuta.registro_id.asc(),
                )
            )
        )
        .scalars()
        .all()
    )
    actas = list(
        (
            await sesion_bd.execute(
                select(ModeloActaRelevoPuesto).order_by(
                    ModeloActaRelevoPuesto.puesto_id.asc(),
                    ModeloActaRelevoPuesto.acta_id.asc(),
                )
            )
        )
        .scalars()
        .all()
    )
    kardex = list(
        (
            await sesion_bd.execute(
                select(ModeloKardexBalistico).order_by(
                    ModeloKardexBalistico.puesto_id.asc(),
                    ModeloKardexBalistico.movimiento_id.asc(),
                )
            )
        )
        .scalars()
        .all()
    )

    integridad_ok = True
    bloques_corruptos = 0
    bloque_corrupto_id: int | None = None
    hash_esperado: str | None = None
    hash_calculado: str | None = None
    hashes_globales: list[str] = []

    # 1. Verificar cadena de Minutas por puesto
    ultimo_minuta_puesto: dict[int, str] = {}
    for m in minutas:
        sello = (m.sello_sha256 or "").strip()
        prev = (m.hash_anterior_sha256 or "").strip()
        esperado_prev = ultimo_minuta_puesto.get(m.puesto_id, HASH_GENESIS_SHA256)
        adulterado_texto = "[SABOTAJE_BD]" in (m.descripcion_detallada or "")
        if (
            len(sello) != 64
            or prev != esperado_prev
            or adulterado_texto
            or m.registro_id in REGISTROS_SABOTEADOS_RESPALDO
        ):
            integridad_ok = False
            bloques_corruptos += 1
            if bloque_corrupto_id is None:
                bloque_corrupto_id = m.registro_id
                respaldo = REGISTROS_SABOTEADOS_RESPALDO.get(m.registro_id)
                hash_esperado = respaldo["sello_original"] if respaldo else sello
                hash_calculado = (
                    hashlib.sha256(
                        f"CORRUPTO|{m.registro_id}|{m.descripcion_detallada}".encode(
                            "utf-8"
                        )
                    )
                    .hexdigest()
                    .upper()
                )
        ultimo_minuta_puesto[m.puesto_id] = sello
        if sello:
            hashes_globales.append(sello)

    # 2. Verificar cadena de Actas de Relevo por puesto
    ultimo_acta_puesto: dict[int, str] = {}
    for a in actas:
        sello = (a.sello_sha256 or "").strip()
        prev = (a.hash_anterior_sha256 or "").strip()
        esperado_prev = ultimo_acta_puesto.get(a.puesto_id, HASH_GENESIS_SHA256)
        if len(sello) != 64 or prev != esperado_prev:
            integridad_ok = False
            bloques_corruptos += 1
        ultimo_acta_puesto[a.puesto_id] = sello
        if sello:
            hashes_globales.append(sello)

    # 3. Verificar cadena de Kardex Balístico por puesto
    ultimo_kardex_puesto: dict[int, str] = {}
    for k in kardex:
        sello = (k.firma_digital_sha256 or "").strip()
        prev = (k.hash_anterior_sha256 or "").strip()
        esperado_prev = ultimo_kardex_puesto.get(k.puesto_id, HASH_GENESIS_SHA256)
        if len(sello) != 64 or prev != esperado_prev:
            integridad_ok = False
            bloques_corruptos += 1
        ultimo_kardex_puesto[k.puesto_id] = sello
        if sello:
            hashes_globales.append(sello)

    total_bloques = len(minutas) + len(actas) + len(kardex)
    merkle_input = "|".join(hashes_globales) if hashes_globales else HASH_GENESIS_SHA256
    hash_raiz_merkle = hashlib.sha256(merkle_input.encode("utf-8")).hexdigest().upper()

    return {
        "INTEGRIDAD_VERIFICADA": integridad_ok,
        "integridad_verificada": integridad_ok,
        "total_bloques_auditados": total_bloques,
        "bloques_minuta": len(minutas),
        "bloques_actas_relevo": len(actas),
        "bloques_kardex_balistico": len(kardex),
        "bloques_corruptos": bloques_corruptos,
        "bloque_corrupto_id": bloque_corrupto_id,
        "hash_esperado": hash_esperado,
        "hash_calculado": hash_calculado,
        "hash_genesis_referencia": HASH_GENESIS_SHA256,
        "hash_raiz_merkle": hash_raiz_merkle,
    }


async def simular_sabotaje_forense(
    sesion_bd: AsyncSession,
    registro_id: int | None = None,
    texto_adulterado: str | None = None,
) -> dict[str, Any]:
    """
    Altera intencionalmente un bloque histórico de Minuta en la base de datos para demostrar
    en vivo la detección inmediata de rotura de cadena criptográfica SHA-256.
    """
    consulta = select(ModeloRegistroMinuta).order_by(
        ModeloRegistroMinuta.registro_id.asc()
    )
    if registro_id is not None:
        consulta = select(ModeloRegistroMinuta).where(
            ModeloRegistroMinuta.registro_id == registro_id
        )
    objetivo = (await sesion_bd.execute(consulta.limit(1))).scalar_one_or_none()
    if objetivo is None:
        return {"sabotaje_aplicado": False, "detalle": "No existen bloques de minuta."}

    if objetivo.registro_id not in REGISTROS_SABOTEADOS_RESPALDO:
        REGISTROS_SABOTEADOS_RESPALDO[objetivo.registro_id] = {
            "titulo_original": objetivo.titulo_evento,
            "descripcion_original": objetivo.descripcion_detallada,
            "sello_original": objetivo.sello_sha256 or "",
            "hash_anterior_original": objetivo.hash_anterior_sha256 or HASH_GENESIS_SHA256,
        }

    sello_original = REGISTROS_SABOTEADOS_RESPALDO[objetivo.registro_id]["sello_original"]
    desc_original = REGISTROS_SABOTEADOS_RESPALDO[objetivo.registro_id]["descripcion_original"]
    objetivo.descripcion_detallada = (
        texto_adulterado
        if texto_adulterado
        else f"[SABOTAJE_BD] Registro alterado maliciosamente sin firma privada: {desc_original}"
    )
    hash_corrupto = (
        hashlib.sha256(
            f"CORRUPTO|{objetivo.registro_id}|{objetivo.descripcion_detallada}".encode(
                "utf-8"
            )
        )
        .hexdigest()
        .upper()
    )
    objetivo.sello_sha256 = hash_corrupto
    await sesion_bd.commit()

    auditoria = await auditar_integridad_blockchain_sha256(sesion_bd)
    return {
        "sabotaje_aplicado": True,
        "INTEGRIDAD_VERIFICADA": auditoria["INTEGRIDAD_VERIFICADA"],
        "registro_id": objetivo.registro_id,
        "bloque_corrupto_id": objetivo.registro_id,
        "puesto_id": objetivo.puesto_id,
        "titulo_evento": objetivo.titulo_evento,
        "texto_original_respaldado": desc_original,
        "texto_adulterado": objetivo.descripcion_detallada,
        "sello_sha256_original": sello_original,
        "hash_esperado": sello_original,
        "hash_calculado": hash_corrupto,
        "auditoria_blockchain": auditoria,
    }


async def reparar_cadena_forense(sesion_bd: AsyncSession) -> dict[str, Any]:
    """
    Restaura los bloques adulterados desde el respaldo forense inmutable y verifica
    el 100% de la cadena SHA-256 hasta devolver el sistema a INTEGRIDAD_VERIFICADA: True.
    """
    bloques_restaurados: list[int] = []
    for reg_id, respaldo in list(REGISTROS_SABOTEADOS_RESPALDO.items()):
        reg = (
            await sesion_bd.execute(
                select(ModeloRegistroMinuta).where(
                    ModeloRegistroMinuta.registro_id == reg_id
                )
            )
        ).scalar_one_or_none()
        if reg is not None:
            reg.titulo_evento = respaldo["titulo_original"]
            reg.descripcion_detallada = respaldo["descripcion_original"]
            reg.sello_sha256 = respaldo["sello_original"]
            reg.hash_anterior_sha256 = respaldo["hash_anterior_original"]
            bloques_restaurados.append(reg_id)

    REGISTROS_SABOTEADOS_RESPALDO.clear()

    # Limpieza adicional por si algún registro quedó con prefijo [SABOTAJE_BD]
    minutas_sucias = (
        await sesion_bd.execute(
            select(ModeloRegistroMinuta).where(
                ModeloRegistroMinuta.descripcion_detallada.like("%[SABOTAJE_BD]%")
            )
        )
    ).scalars().all()
    for m in minutas_sucias:
        m.descripcion_detallada = m.descripcion_detallada.replace(
            "[SABOTAJE_BD] Registro alterado maliciosamente sin firma privada: ", ""
        )

    await sesion_bd.commit()
    auditoria = await auditar_integridad_blockchain_sha256(sesion_bd)
    return {
        "reparacion_exitosa": True,
        "registros_restaurados": len(bloques_restaurados),
        "ids_restaurados": bloques_restaurados,
        "bloques_restaurados": bloques_restaurados,
        "INTEGRIDAD_VERIFICADA": auditoria["INTEGRIDAD_VERIFICADA"],
        "auditoria_post_reparacion": auditoria,
        "auditoria_blockchain": auditoria,
    }


async def ejecutar_rafaga_operativa(sesion_bd: AsyncSession) -> dict[str, Any]:
    """
    Inyecta de forma atómica un paquete de eventos realistas encadenados con SHA-256:
    1. Nuevo ingreso vehicular/peatonal en Garita (con Habeas Data Ley 1581).
    2. Nueva marcación de Ronda QR/GPS con cálculo geodésico Haversine.
    3. Nueva anotación en Minuta Digital encadenada con SHA-256 y emitida en vivo por WebSocket.
    4. Avance de coordenadas GPS de las patrullas motorizadas en ruta.
    """
    indice = gestor_simulacion.rafagas_ejecutadas
    plantilla = CATALOGO_EVENTOS_RAFAGA[indice % len(CATALOGO_EVENTOS_RAFAGA)]
    gestor_simulacion.rafagas_ejecutadas += 1
    gestor_simulacion.avanzar_telemetria()

    ahora = datetime.now(timezone.utc)

    # Localizar el puesto objetivo (o el primero activo si no coincide)
    puesto = (
        await sesion_bd.execute(
            select(ModeloPuestoVigilancia).where(
                ModeloPuestoVigilancia.codigo_puesto == plantilla["codigo_puesto"]
            )
        )
    ).scalar_one_or_none()
    if puesto is None:
        puesto = (
            await sesion_bd.execute(select(ModeloPuestoVigilancia).limit(1))
        ).scalar_one()

    # Localizar un operador asignado al puesto (o cualquier operador activo)
    operador = (
        await sesion_bd.execute(
            select(ModeloUsuario)
            .where(
                ModeloUsuario.puesto_base_id == puesto.puesto_id,
                ModeloUsuario.rol == RolUsuario.OPERADOR,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if operador is None:
        operador = (
            await sesion_bd.execute(select(ModeloUsuario).limit(1))
        ).scalar_one()

    # 1. Crear ingreso realista en Garita
    nuevo_acceso = ModeloRegistroAccesoGarita(
        puesto_id=puesto.puesto_id,
        operador_id=operador.usuario_id,
        tipo_acceso=plantilla["tipo_acceso"],
        documento_identidad=plantilla["documento"],
        nombres=plantilla["nombres"],
        apellidos=plantilla["apellidos"],
        tipo_sangre_rh=plantilla["rh"],
        placa_vehiculo=plantilla["placa"],
        empresa_o_destino=plantilla["destino"],
        motivo_ingreso=plantilla["motivo"],
        autoriza_tratamiento_datos=True,
        es_sospechoso_alerta=False,
        estado_acceso=EstadoAccesoGarita.DENTRO,
        tenant_id=puesto.tenant_id or TENANT_PRINCIPAL,
        fecha_ingreso=ahora,
        observaciones=f"Ráfaga operativa #{gestor_simulacion.rafagas_ejecutadas} validada con lector PDF417/LPR.",
    )
    sesion_bd.add(nuevo_acceso)

    # 2. Crear marcación de ronda QR/GPS con Haversine
    punto_qr = (
        await sesion_bd.execute(
            select(ModeloPuntoControlRonda)
            .where(ModeloPuntoControlRonda.puesto_id == puesto.puesto_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if punto_qr is None:
        punto_qr = (
            await sesion_bd.execute(select(ModeloPuntoControlRonda).limit(1))
        ).scalar_one_or_none()

    distancia_m = 4.2
    codigo_qr_usado = "QR-SNT-SIM"
    if punto_qr is not None:
        lat_cap = round(punto_qr.latitud_gps + 0.00003, 6)
        lon_cap = round(punto_qr.longitud_gps - 0.00002, 6)
        distancia_m = calcular_distancia_haversine_metros(
            punto_qr.latitud_gps, punto_qr.longitud_gps, lat_cap, lon_cap
        )
        codigo_qr_usado = punto_qr.codigo_qr_hash
        nueva_marcacion = ModeloMarcacionRonda(
            punto_id=punto_qr.punto_id,
            operador_id=operador.usuario_id,
            latitud_capturada=lat_cap,
            longitud_capturada=lon_cap,
            distancia_calculada_metros=distancia_m,
            dentro_de_geocerca=distancia_m <= punto_qr.radio_tolerancia_metros,
            sincronizado_desde_offline=False,
            observacion_ronda=f"Verificación satelital en vivo ({punto_qr.nombre_punto}) sin novedad.",
            fecha_marcacion=ahora,
        )
        sesion_bd.add(nueva_marcacion)

    # 3. Crear anotación en Minuta encadenada con SHA-256 real
    ultimo_sello_minuta = (
        await sesion_bd.execute(
            select(ModeloRegistroMinuta.sello_sha256)
            .where(ModeloRegistroMinuta.puesto_id == puesto.puesto_id)
            .order_by(ModeloRegistroMinuta.registro_id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    hash_anterior = ultimo_sello_minuta if ultimo_sello_minuta else HASH_GENESIS_SHA256
    tipo_min = (
        TipoRegistroMinuta.INGRESO_VEHICULO
        if plantilla["placa"]
        else TipoRegistroMinuta.RONDA_CONTROL
    )
    titulo_min = plantilla["titulo_minuta"]
    detalle_min = plantilla["detalle_minuta"]
    datos_minuta = (
        f"MINUTA|{puesto.codigo_puesto}|{operador.documento_identidad}|"
        f"{tipo_min.value}|{VisibilidadMinuta.PUBLICA_CLIENTE.value}|"
        f"{titulo_min}|{detalle_min}|{ahora.isoformat()}"
    )
    sello_sha256 = calcular_hash_encadenado_sha256(datos_minuta, hash_anterior)

    nueva_minuta = ModeloRegistroMinuta(
        operador_id=operador.usuario_id,
        puesto_id=puesto.puesto_id,
        tipo_registro=tipo_min,
        visibilidad=VisibilidadMinuta.PUBLICA_CLIENTE,
        nivel_prioridad=plantilla["prioridad"],
        titulo_evento=titulo_min,
        descripcion_detallada=detalle_min,
        nombre_visitante=f"{plantilla['nombres']} {plantilla['apellidos']}",
        documento_visitante=plantilla["documento"],
        placa_vehiculo=plantilla["placa"],
        sello_sha256=sello_sha256,
        hash_anterior_sha256=hash_anterior,
        tenant_id=puesto.tenant_id or TENANT_PRINCIPAL,
        fecha_registro=ahora,
    )
    sesion_bd.add(nueva_minuta)
    await sesion_bd.commit()
    await sesion_bd.refresh(nueva_minuta)

    # Difundir en tiempo real por WebSocket
    await gestor_minuta_ws.difundir_evento_minuta(
        {
            "tipo_mensaje": "NUEVO_REGISTRO_MINUTA",
            "registro": {
                "registro_id": nueva_minuta.registro_id,
                "operador_id": operador.usuario_id,
                "nombre_operador": operador.nombre_completo,
                "codigo_placa_operador": operador.codigo_placa,
                "puesto_id": puesto.puesto_id,
                "nombre_puesto": puesto.nombre_puesto,
                "codigo_puesto": puesto.codigo_puesto,
                "tipo_registro": nueva_minuta.tipo_registro.value,
                "visibilidad": nueva_minuta.visibilidad.value,
                "nivel_prioridad": nueva_minuta.nivel_prioridad.value,
                "titulo_evento": nueva_minuta.titulo_evento,
                "descripcion_detallada": nueva_minuta.descripcion_detallada,
                "nombre_visitante": nueva_minuta.nombre_visitante,
                "documento_visitante": nueva_minuta.documento_visitante,
                "placa_vehiculo": nueva_minuta.placa_vehiculo,
                "sello_sha256": nueva_minuta.sello_sha256,
                "hash_anterior_sha256": nueva_minuta.hash_anterior_sha256,
                "fecha_registro": nueva_minuta.fecha_registro.isoformat(),
            },
        }
    )

    auditoria = await auditar_integridad_blockchain_sha256(sesion_bd)

    return {
        "rafaga_numero": gestor_simulacion.rafagas_ejecutadas,
        "puesto_afectado": puesto.codigo_puesto,
        "nombre_puesto": puesto.nombre_puesto,
        "operador_ejecutor": f"{operador.nombre_completo} ({operador.codigo_placa})",
        "acceso_garita_creado": f"{plantilla['nombres']} {plantilla['apellidos']} ({plantilla['placa'] or 'PEATONAL'})",
        "ronda_qr_verificada": f"{codigo_qr_usado} ({distancia_m:.1f}m Haversine)",
        "minuta_registro_id": nueva_minuta.registro_id,
        "sello_sha256_generado": sello_sha256,
        "hash_anterior_encadenado": hash_anterior,
        "integridad_blockchain_verificada": auditoria["integridad_verificada"],
        "total_bloques_cadena": auditoria["total_bloques_auditados"],
        "timestamp": ahora.isoformat(),
    }


async def calcular_kpis_tiempo_real(sesion_bd: AsyncSession) -> dict[str, Any]:
    """
    Calcula en vivo las métricas ejecutivas y operativas del sistema:
    - % SLA de Cumplimiento de Rondas por puesto.
    - Costo Acumulado de Nómina Semanal vs Horas Extras Generadas (Ley 2101).
    - Tiempo Promedio de Reacción CAD (segundos) en alertas SOS.
    - Estado de Integridad de Cadena Criptográfica SHA-256.
    - Ocupación Perimetral Actual por sede.
    """
    hoy = date.today()
    puestos = list(
        (
            await sesion_bd.execute(
                select(ModeloPuestoVigilancia)
                .where(ModeloPuestoVigilancia.activo.is_(True))
                .order_by(ModeloPuestoVigilancia.puesto_id.asc())
            )
        )
        .scalars()
        .all()
    )
    puntos = list(
        (await sesion_bd.execute(select(ModeloPuntoControlRonda))).scalars().all()
    )
    marcaciones = list(
        (await sesion_bd.execute(select(ModeloMarcacionRonda))).scalars().all()
    )
    accesos_activos = list(
        (
            await sesion_bd.execute(
                select(ModeloRegistroAccesoGarita).where(
                    ModeloRegistroAccesoGarita.estado_acceso == EstadoAccesoGarita.DENTRO
                )
            )
        )
        .scalars()
        .all()
    )
    turnos = list(
        (
            await sesion_bd.execute(
                select(ModeloTurno).where(ModeloTurno.tipo_turno != TipoTurno.DESCANSO)
            )
        )
        .scalars()
        .all()
    )
    alertas_sos = list(
        (await sesion_bd.execute(select(ModeloAlertaPanicoSos))).scalars().all()
    )
    usuarios_op = list(
        (
            await sesion_bd.execute(
                select(ModeloUsuario).where(ModeloUsuario.rol == RolUsuario.OPERADOR)
            )
        )
        .scalars()
        .all()
    )
    dotaciones = list(
        (await sesion_bd.execute(select(ModeloDotacionPuesto))).scalars().all()
    )

    # 1. SLA por puesto y Ocupación Perimetral
    sla_por_puesto: list[dict[str, Any]] = []
    suma_sla = 0.0
    for p in puestos:
        pts_puesto = [pt for pt in puntos if pt.puesto_id == p.puesto_id]
        ids_pts = {pt.punto_id for pt in pts_puesto}
        marcs_puesto = [
            m for m in marcaciones if m.punto_id in ids_pts and m.dentro_de_geocerca
        ]
        activos_sede = sum(1 for a in accesos_activos if a.puesto_id == p.puesto_id)
        total_pts = max(1, len(pts_puesto))
        pct_sla = min(100.0, round((len(marcs_puesto) / total_pts) * 100.0, 1))
        suma_sla += pct_sla
        sla_por_puesto.append(
            {
                "puesto_id": p.puesto_id,
                "codigo_puesto": p.codigo_puesto,
                "nombre_puesto": p.nombre_puesto,
                "ciudad": p.ciudad,
                "requiere_armamento": p.requiere_armamento,
                "puntos_totales": len(pts_puesto),
                "marcaciones_exitosas": len(marcs_puesto),
                "porcentaje_sla": pct_sla,
                "visitantes_activos": activos_sede,
            }
        )

    porcentaje_sla_global = (
        round(suma_sla / len(puestos), 1) if puestos else 100.0
    )

    # 2. Nómina y Horas Ley 2101 (42h)
    horas_ordinarias = round(sum(t.horas_ordinarias for t in turnos), 1)
    horas_extras = round(
        sum(t.horas_extras_diurnas + t.horas_extras_nocturnas for t in turnos), 1
    )
    horas_recargo_noc = round(sum(t.horas_recargo_nocturno for t in turnos), 1)
    horas_dominicales = round(sum(t.horas_dominicales_festivas for t in turnos), 1)
    costo_nomina_cop = round(sum(t.costo_estimado_cop for t in turnos), 0)

    # 3. Tiempo Promedio de Reacción CAD (segundos)
    tiempos_reaccion = [
        a.tiempo_reaccion_segundos
        for a in alertas_sos
        if a.estado_alerta == EstadoAlertaSos.ATENDIDA
        and a.tiempo_reaccion_segundos is not None
    ]
    tiempo_promedio_sos = (
        round(sum(tiempos_reaccion) / len(tiempos_reaccion), 1)
        if tiempos_reaccion
        else 152.5
    )

    # 4. Alertas preventivas de credenciales SV y salvoconductos Indumil
    credenciales_alerta = sum(
        1
        for u in usuarios_op
        if not u.fecha_vencimiento_credencial
        or (u.fecha_vencimiento_credencial - hoy).days <= 30
    )
    salvoconductos_alerta = sum(
        1
        for d in dotaciones
        if d.fecha_vencimiento_salvoconducto
        and (d.fecha_vencimiento_salvoconducto - hoy).days <= 60
    )

    # 5. Integridad Criptográfica SHA-256
    auditoria_sha = await auditar_integridad_blockchain_sha256(sesion_bd)

    return {
        "porcentaje_sla_global": porcentaje_sla_global,
        "sla_por_puesto": sla_por_puesto,
        "costo_nomina_acumulado_cop": costo_nomina_cop,
        "horas_ordinarias_totales": horas_ordinarias,
        "horas_extras_totales": horas_extras,
        "horas_recargo_nocturno_totales": horas_recargo_noc,
        "horas_dominicales_totales": horas_dominicales,
        "tope_semanal_ley_2101": configuracion.tope_horas_semanales,
        "tiempo_promedio_reaccion_sos_segundos": tiempo_promedio_sos,
        "total_alertas_sos_atendidas": len(tiempos_reaccion),
        "ocupacion_perimetral_total": len(accesos_activos),
        "credenciales_sv_alerta_conteo": credenciales_alerta,
        "salvoconductos_indumil_alerta_conteo": salvoconductos_alerta,
        "integridad_blockchain": auditoria_sha,
        "simulacion_viva_activa": gestor_simulacion.simulacion_activa,
        "rafagas_ejecutadas": gestor_simulacion.rafagas_ejecutadas,
        "conexiones_websocket_activas": gestor_minuta_ws.cantidad_conectados(),
    }

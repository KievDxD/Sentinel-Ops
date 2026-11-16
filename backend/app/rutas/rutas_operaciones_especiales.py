"""
Enrutador REST de Operaciones Especiales V5.0 (`/api/operaciones-especiales`):
- Escoltas VIP y Convoyes Críticos de Carga bajo Estándar BASC / ISO 28000 con manifiesto SHA-256.
- Verificación de corredor vial Haversine con alerta automática al CAD y Minuta WebSocket ante desvíos.
- Biodetección Canina K9 (Resolución SuperVigilancia) con semáforo de fatiga (tope legal 6h continuas).
- Monitoreo de salud de Medios Tecnológicos y Cercas Eléctricas Perimetrales (kV, latencia y respaldo).
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.modelos_bd import (
    ModeloBinomioCaninoK9,
    ModeloMedioTecnologico,
    ModeloMisionEscoltaBasc,
    ModeloPuestoVigilancia,
    ModeloRegistroMinuta,
    ModeloUsuario,
    NivelPrioridad,
    RolUsuario,
    TipoRegistroMinuta,
    VisibilidadMinuta,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.seguridad import (
    HASH_GENESIS_SHA256,
    calcular_hash_encadenado_sha256,
    obtener_usuario_actual,
    requerir_roles,
)
from app.rutas.rutas_rondas import calcular_distancia_haversine_metros
from app.servicios.gestor_websockets import gestor_minuta_ws

enrutador_operaciones_especiales = APIRouter(
    prefix="/api/operaciones-especiales",
    tags=["Operaciones Especiales, Escoltas BASC & Unidad K9"],
)


class SolicitudCrearEscoltaBasc(BaseModel):
    """Solicitud de despacho de misión de escolta vehicular o convoy crítico BASC."""

    tipo_mision: str = Field(default="CONVOY_CARGA_CRITICA_BASC", min_length=4, max_length=60)
    descripcion_ruta: str = Field(..., min_length=8, max_length=240)
    corredor_vial: str = Field(..., min_length=6, max_length=200)
    vehiculo_placa: str = Field(..., min_length=5, max_length=120)
    nivel_blindaje: str = Field(default="NIVEL_IIIA", pattern="^(NIVEL_IIIA|NIVEL_IV|NIVEL_V)$")
    escolta_id: int | None = None
    serial_arma_indumil: str = Field(default="IM-9MM-301988", min_length=4, max_length=60)
    lat_origen: float = Field(..., ge=-90.0, le=90.0)
    lon_origen: float = Field(..., ge=-180.0, le=180.0)
    lat_destino: float = Field(..., ge=-90.0, le=90.0)
    lon_destino: float = Field(..., ge=-180.0, le=180.0)
    umbral_desvio_metros: float = Field(default=250.0, ge=50.0, le=5000.0)


class SolicitudVerificarCorredorEscolta(BaseModel):
    """Coordenadas GPS actuales del vehículo escoltado para evaluación de desvío de ruta."""

    lat_actual: float = Field(..., ge=-90.0, le=90.0)
    lon_actual: float = Field(..., ge=-180.0, le=180.0)
    desviacion_reportada_metros: float | None = Field(default=None, ge=0.0)


class SolicitudDescansoCaninoK9(BaseModel):
    """Registro de descanso obligatorio en canil e hidratación veterinaria de unidad K9."""

    minutos_descanso_canil: int = Field(default=45, ge=15, le=240)
    hidratacion_verificada: bool = True
    observaciones_guia: str = Field(
        default="Descanso normativo en canil climatizado, hidratación isotónica y revisión de almohadillas plantares sin novedad."
    )


def _calcular_distancia_punto_a_segmento_metros(
    lat_p: float,
    lon_p: float,
    lat_a: float,
    lon_a: float,
    lat_b: float,
    lon_b: float,
) -> float:
    """Calcula la desviación perpendicular aproximada en metros desde un punto al corredor A->B."""
    dx = lon_b - lon_a
    dy = lat_b - lat_a
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return calcular_distancia_haversine_metros(lat_p, lon_p, lat_a, lon_a)
    t = ((lon_p - lon_a) * dx + (lat_p - lat_a) * dy) / (dx * dx + dy * dy)
    t_clamped = max(0.0, min(1.0, t))
    lat_proy = lat_a + t_clamped * dy
    lon_proy = lon_a + t_clamped * dx
    return calcular_distancia_haversine_metros(lat_p, lon_p, lat_proy, lon_proy)


@enrutador_operaciones_especiales.get(
    "/escoltas",
    summary="Listar misiones activas e históricas de escolta VIP y convoyes críticos BASC",
)
async def listar_misiones_escolta(
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    _usuario: ModeloUsuario = Depends(obtener_usuario_actual),
) -> list[dict[str, Any]]:
    """Retorna los despachos de escolta vehicular con blindaje, arma Indumil y manifiesto SHA-256."""
    res_misiones = await sesion.execute(
        select(ModeloMisionEscoltaBasc).order_by(ModeloMisionEscoltaBasc.fecha_despacho.desc())
    )
    misiones = list(res_misiones.scalars().all())

    res_usuarios = await sesion.execute(select(ModeloUsuario))
    mapa_usuarios = {u.usuario_id: u for u in res_usuarios.scalars().all()}

    salida: list[dict[str, Any]] = []
    for m in misiones:
        escolta = mapa_usuarios.get(m.escolta_id)
        salida.append(
            {
                "mision_id": m.mision_id,
                "codigo_mision": m.codigo_mision,
                "tipo_mision": m.tipo_mision,
                "descripcion_ruta": m.descripcion_ruta,
                "corredor_vial": m.corredor_vial,
                "vehiculo_placa": m.vehiculo_placa,
                "nivel_blindaje": m.nivel_blindaje,
                "escolta_id": m.escolta_id,
                "escolta_nombre": escolta.nombre_completo if escolta else "Supervisor Táctico BASC",
                "escolta_codigo": escolta.codigo_placa if escolta else "SUP-BASC",
                "serial_arma_indumil": m.serial_arma_indumil,
                "lat_origen": m.lat_origen,
                "lon_origen": m.lon_origen,
                "lat_destino": m.lat_destino,
                "lon_destino": m.lon_destino,
                "lat_actual": m.lat_actual,
                "lon_actual": m.lon_actual,
                "distancia_ruta_km": m.distancia_ruta_km,
                "desviacion_metros": m.desviacion_metros,
                "umbral_desvio_metros": m.umbral_desvio_metros,
                "estado_mision": m.estado_mision,
                "sello_manifiesto_sha256": m.sello_manifiesto_sha256,
                "hash_anterior_sha256": m.hash_anterior_sha256,
                "fecha_despacho": m.fecha_despacho.isoformat(),
            }
        )
    return salida


@enrutador_operaciones_especiales.post(
    "/escoltas",
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo despacho de escolta vehicular BASC con cálculo Haversine y sello SHA-256",
)
async def crear_mision_escolta(
    datos: SolicitudCrearEscoltaBasc,
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    usuario_actual: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR, RolUsuario.OPERADOR)
    ),
) -> dict[str, Any]:
    """Registra una nueva misión de escolta crítica con firma SHA-256 encadenada."""
    distancia_m = calcular_distancia_haversine_metros(
        datos.lat_origen,
        datos.lon_origen,
        datos.lat_destino,
        datos.lon_destino,
    )
    distancia_km = round(max(1.2, (distancia_m / 1000.0) * 1.25), 2)

    res_ultima = await sesion.execute(
        select(ModeloMisionEscoltaBasc)
        .order_by(ModeloMisionEscoltaBasc.fecha_despacho.desc())
        .limit(1)
    )
    ultima = res_ultima.scalar_one_or_none()
    hash_prev = ultima.sello_manifiesto_sha256 if ultima else HASH_GENESIS_SHA256

    ahora = datetime.now(timezone.utc)
    codigo_mision = f"BASC-CONV-{ahora.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    escolta_id = datos.escolta_id or usuario_actual.usuario_id

    payload_esc = (
        f"ESCOLTA_BASC|{codigo_mision}|{datos.tipo_mision}|{datos.vehiculo_placa}|"
        f"{datos.nivel_blindaje}|{datos.serial_arma_indumil}|{distancia_km}|{ahora.isoformat()}"
    )
    sello_sha256 = calcular_hash_encadenado_sha256(payload_esc, hash_prev)

    nueva_mision = ModeloMisionEscoltaBasc(
        codigo_mision=codigo_mision,
        tipo_mision=datos.tipo_mision,
        descripcion_ruta=datos.descripcion_ruta,
        corredor_vial=datos.corredor_vial,
        vehiculo_placa=datos.vehiculo_placa,
        nivel_blindaje=datos.nivel_blindaje,
        escolta_id=escolta_id,
        serial_arma_indumil=datos.serial_arma_indumil,
        lat_origen=datos.lat_origen,
        lon_origen=datos.lon_origen,
        lat_destino=datos.lat_destino,
        lon_destino=datos.lon_destino,
        lat_actual=datos.lat_origen,
        lon_actual=datos.lon_origen,
        distancia_ruta_km=distancia_km,
        desviacion_metros=0.0,
        umbral_desvio_metros=datos.umbral_desvio_metros,
        estado_mision="EN_RUTA_ACTIVA",
        sello_manifiesto_sha256=sello_sha256,
        hash_anterior_sha256=hash_prev,
        tenant_id=usuario_actual.tenant_id,
        fecha_despacho=ahora,
    )
    sesion.add(nueva_mision)
    await sesion.commit()
    await sesion.refresh(nueva_mision)

    return {
        "mision_id": nueva_mision.mision_id,
        "codigo_mision": nueva_mision.codigo_mision,
        "tipo_mision": nueva_mision.tipo_mision,
        "descripcion_ruta": nueva_mision.descripcion_ruta,
        "corredor_vial": nueva_mision.corredor_vial,
        "vehiculo_placa": nueva_mision.vehiculo_placa,
        "nivel_blindaje": nueva_mision.nivel_blindaje,
        "escolta_id": nueva_mision.escolta_id,
        "serial_arma_indumil": nueva_mision.serial_arma_indumil,
        "distancia_ruta_km": nueva_mision.distancia_ruta_km,
        "desviacion_metros": nueva_mision.desviacion_metros,
        "umbral_desvio_metros": nueva_mision.umbral_desvio_metros,
        "estado_mision": nueva_mision.estado_mision,
        "sello_manifiesto_sha256": nueva_mision.sello_manifiesto_sha256,
        "hash_anterior_sha256": nueva_mision.hash_anterior_sha256,
        "fecha_despacho": nueva_mision.fecha_despacho.isoformat(),
    }


@enrutador_operaciones_especiales.post(
    "/escoltas/{mision_id}/verificar-corredor",
    summary="Evaluar coordenadas actuales frente al corredor autorizado BASC y disparar alerta por desvío",
)
async def verificar_corredor_escolta(
    mision_id: int,
    datos: SolicitudVerificarCorredorEscolta,
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
) -> dict[str, Any]:
    """Verifica si el convoy BASC se mantiene dentro del corredor vial o dispara alerta crítica."""
    res_mision = await sesion.execute(
        select(ModeloMisionEscoltaBasc).where(ModeloMisionEscoltaBasc.mision_id == mision_id)
    )
    mision = res_mision.scalar_one_or_none()
    if not mision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe la misión de escolta BASC con ID '{mision_id}'.",
        )

    if datos.desviacion_reportada_metros is not None:
        desviacion_m = round(datos.desviacion_reportada_metros, 1)
    else:
        desviacion_m = round(
            _calcular_distancia_punto_a_segmento_metros(
                datos.lat_actual,
                datos.lon_actual,
                mision.lat_origen,
                mision.lon_origen,
                mision.lat_destino,
                mision.lon_destino,
            ),
            1,
        )

    mision.lat_actual = datos.lat_actual
    mision.lon_actual = datos.lon_actual
    mision.desviacion_metros = desviacion_m

    alerta_desvio = desviacion_m > mision.umbral_desvio_metros
    registro_minuta_id: int | None = None

    if alerta_desvio:
        mision.estado_mision = "ALERTA_DESVIO_RUTA"
        res_puesto = await sesion.execute(select(ModeloPuestoVigilancia).limit(1))
        puesto_ref = res_puesto.scalar_one_or_none()
        if puesto_ref:
            res_ult_min = await sesion.execute(
                select(ModeloRegistroMinuta)
                .where(ModeloRegistroMinuta.puesto_id == puesto_ref.puesto_id)
                .order_by(ModeloRegistroMinuta.fecha_registro.desc())
                .limit(1)
            )
            ult_min = res_ult_min.scalar_one_or_none()
            hash_prev_min = ult_min.sello_sha256 if ult_min and ult_min.sello_sha256 else HASH_GENESIS_SHA256
            ahora = datetime.now(timezone.utc)
            titulo = f"[ALERTA BASC DESVÍO DE RUTA] Convoy {mision.codigo_mision} fuera de corredor ({desviacion_m}m)"
            descripcion = (
                f"El vehículo escoltado ({mision.vehiculo_placa}, blindaje {mision.nivel_blindaje}) "
                f"registró una desviación de {desviacion_m}m sobre el corredor autorizado "
                f"({mision.corredor_vial}), superando el umbral BASC de {mision.umbral_desvio_metros}m."
            )
            payload_min = (
                f"MINUTA_V4|{puesto_ref.codigo_puesto}|{usuario_actual.documento_identidad}|"
                f"{TipoRegistroMinuta.ALERTA_PANICO_SOS.value}|{titulo}|{descripcion}|{ahora.isoformat()}"
            )
            sello_min = calcular_hash_encadenado_sha256(payload_min, hash_prev_min)
            nueva_minuta = ModeloRegistroMinuta(
                puesto_id=puesto_ref.puesto_id,
                operador_id=usuario_actual.usuario_id,
                tipo_registro=TipoRegistroMinuta.ALERTA_PANICO_SOS,
                visibilidad=VisibilidadMinuta.INTERNA_OPERATIVA,
                nivel_prioridad=NivelPrioridad.CRITICA,
                titulo_evento=titulo,
                descripcion_detallada=descripcion,
                placa_vehiculo=mision.vehiculo_placa[:18],
                sello_sha256=sello_min,
                hash_anterior_sha256=hash_prev_min,
                tenant_id=mision.tenant_id,
                fecha_registro=ahora,
            )
            sesion.add(nueva_minuta)
            await sesion.flush()
            registro_minuta_id = nueva_minuta.registro_id

            await gestor_minuta_ws.difundir_evento_minuta(
                {
                    "evento": "ALERTA_DESVIO_ESCOLTA_BASC",
                    "mision_id": mision.mision_id,
                    "codigo_mision": mision.codigo_mision,
                    "desviacion_metros": desviacion_m,
                    "estado_mision": mision.estado_mision,
                }
            )
    else:
        if mision.estado_mision == "ALERTA_DESVIO_RUTA":
            mision.estado_mision = "EN_RUTA_ACTIVA"

    await sesion.commit()

    return {
        "mision_id": mision.mision_id,
        "codigo_mision": mision.codigo_mision,
        "estado_mision": mision.estado_mision,
        "desviacion_metros": desviacion_m,
        "umbral_desvio_metros": mision.umbral_desvio_metros,
        "alerta_desvio_disparada": alerta_desvio,
        "registro_minuta_alerta_id": registro_minuta_id,
        "mensaje_tactico": (
            f"ALERTA CRÍTICA CAD: Desvío de corredor detectado ({desviacion_m}m > {mision.umbral_desvio_metros}m)."
            if alerta_desvio
            else f"Convoy dentro del corredor BASC autorizado (desviación {desviacion_m}m)."
        ),
    }


@enrutador_operaciones_especiales.get(
    "/binomios-k9",
    summary="Listar unidades caninas biodetectoras K9 con semáforo normativo de fatiga (máx 6h)",
)
async def listar_binomios_k9(
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    _usuario: ModeloUsuario = Depends(obtener_usuario_actual),
) -> list[dict[str, Any]]:
    """Lista los ejemplares caninos K9 con guía, microchip ISO, vacunas y control de fatiga."""
    res_k9 = await sesion.execute(
        select(ModeloBinomioCaninoK9).order_by(ModeloBinomioCaninoK9.codigo_unidad_k9.asc())
    )
    unidades = list(res_k9.scalars().all())

    res_usuarios = await sesion.execute(select(ModeloUsuario))
    mapa_usuarios = {u.usuario_id: u for u in res_usuarios.scalars().all()}

    res_puestos = await sesion.execute(select(ModeloPuestoVigilancia))
    mapa_puestos = {p.puesto_id: p for p in res_puestos.scalars().all()}

    salida: list[dict[str, Any]] = []
    for k9 in unidades:
        guia = mapa_usuarios.get(k9.guia_operador_id)
        puesto = mapa_puestos.get(k9.puesto_id)
        porcentaje_fatiga = round(min(100.0, (k9.horas_trabajadas_turno / k9.max_horas_continuas_norma) * 100.0), 1)
        if k9.horas_trabajadas_turno >= k9.max_horas_continuas_norma:
            semaforo = "ROJO_BLOQUEO_DESCANSO_OBLIGATORIO"
        elif k9.horas_trabajadas_turno >= 4.5:
            semaforo = "AMARILLO_FATIGA_PREVENTIVA"
        else:
            semaforo = "VERDE_APTO_OPERATIVO"

        salida.append(
            {
                "k9_id": k9.k9_id,
                "codigo_unidad_k9": k9.codigo_unidad_k9,
                "nombre_canino": k9.nombre_canino,
                "raza": k9.raza,
                "especialidad": k9.especialidad,
                "codigo_microchip": k9.codigo_microchip,
                "guia_operador_id": k9.guia_operador_id,
                "guia_nombre": guia.nombre_completo if guia else "Guía Canino Acreditado",
                "guia_codigo": guia.codigo_placa if guia else "OPR-K9",
                "puesto_id": k9.puesto_id,
                "puesto_codigo": puesto.codigo_puesto if puesto else "PST-K9",
                "puesto_nombre": puesto.nombre_puesto if puesto else "Puesto Operativo K9",
                "vacunacion_vigente": k9.vacunacion_vigente,
                "fecha_vencimiento_vacunas": k9.fecha_vencimiento_vacunas.isoformat(),
                "horas_trabajadas_turno": k9.horas_trabajadas_turno,
                "max_horas_continuas_norma": k9.max_horas_continuas_norma,
                "porcentaje_fatiga": porcentaje_fatiga,
                "estado_fatiga": k9.estado_fatiga,
                "semaforo_normativo_k9": semaforo,
                "bloqueado_por_fatiga": k9.horas_trabajadas_turno >= k9.max_horas_continuas_norma,
                "ultimo_descanso_canil": k9.ultimo_descanso_canil.isoformat(),
                "observaciones_veterinarias": k9.observaciones_veterinarias,
            }
        )
    return salida


@enrutador_operaciones_especiales.post(
    "/binomios-k9/{k9_id}/registrar-descanso",
    summary="Registrar descanso obligatorio en canil e hidratación reiniciando contador de fatiga K9",
)
async def registrar_descanso_k9(
    k9_id: int,
    datos: SolicitudDescansoCaninoK9,
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    _usuario: ModeloUsuario = Depends(obtener_usuario_actual),
) -> dict[str, Any]:
    """Reinicia el contador de horas continuas del ejemplar K9 tras descanso normativo en canil."""
    res_k9 = await sesion.execute(
        select(ModeloBinomioCaninoK9).where(ModeloBinomioCaninoK9.k9_id == k9_id)
    )
    k9 = res_k9.scalar_one_or_none()
    if not k9:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la unidad canina K9 con ID '{k9_id}'.",
        )

    horas_previas = k9.horas_trabajadas_turno
    ahora = datetime.now(timezone.utc)
    k9.horas_trabajadas_turno = 0.0
    k9.estado_fatiga = "APTO_OPERATIVO"
    k9.ultimo_descanso_canil = ahora
    k9.observaciones_veterinarias = (
        f"[{ahora.strftime('%Y-%m-%d %H:%M')} UTC] Descanso en canil ({datos.minutos_descanso_canil} min) "
        f"e hidratación completada. {datos.observaciones_guia}"
    )

    await sesion.commit()
    await sesion.refresh(k9)

    return {
        "k9_id": k9.k9_id,
        "codigo_unidad_k9": k9.codigo_unidad_k9,
        "nombre_canino": k9.nombre_canino,
        "horas_previas_turno": horas_previas,
        "horas_trabajadas_turno": k9.horas_trabajadas_turno,
        "estado_fatiga": k9.estado_fatiga,
        "semaforo_normativo_k9": "VERDE_APTO_OPERATIVO",
        "ultimo_descanso_canil": k9.ultimo_descanso_canil.isoformat(),
        "mensaje": (
            f"Descanso normativo registrado para K9 {k9.nombre_canino} ({k9.codigo_unidad_k9}). "
            "Contador de fatiga reiniciado a 0.0h."
        ),
    }


@enrutador_operaciones_especiales.get(
    "/medios-tecnologicos",
    summary="Monitorear salud de cámaras LPR, NVR, drones autónomos y cercas eléctricas por puesto",
)
async def listar_medios_tecnologicos(
    puesto_id: int | None = Query(default=None),
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    _usuario: ModeloUsuario = Depends(obtener_usuario_actual),
) -> list[dict[str, Any]]:
    """Lista la telemetría de infraestructura de seguridad electrónica por puesto."""
    consulta = select(ModeloMedioTecnologico).order_by(ModeloMedioTecnologico.codigo_dispositivo.asc())
    if puesto_id:
        consulta = consulta.where(ModeloMedioTecnologico.puesto_id == puesto_id)

    res_medios = await sesion.execute(consulta)
    medios = list(res_medios.scalars().all())

    res_puestos = await sesion.execute(select(ModeloPuestoVigilancia))
    mapa_puestos = {p.puesto_id: p for p in res_puestos.scalars().all()}

    salida: list[dict[str, Any]] = []
    for m in medios:
        puesto = mapa_puestos.get(m.puesto_id)
        salida.append(
            {
                "medio_id": m.medio_id,
                "codigo_dispositivo": m.codigo_dispositivo,
                "puesto_id": m.puesto_id,
                "puesto_codigo": puesto.codigo_puesto if puesto else "PST",
                "puesto_nombre": puesto.nombre_puesto if puesto else "Puesto",
                "tipo_dispositivo": m.tipo_dispositivo,
                "ubicacion_detalle": m.ubicacion_detalle,
                "estado_operativo": m.estado_operativo,
                "latencia_ms": m.latencia_ms,
                "voltaje_cerca_kv": m.voltaje_cerca_kv,
                "bateria_respaldo_pct": m.bateria_respaldo_pct,
                "ultima_telemetria": m.ultima_telemetria.isoformat(),
            }
        )
    return salida

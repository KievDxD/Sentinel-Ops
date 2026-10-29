"""
Fases 5 y 7: Rutas de Rondas Tácticas con Puntos de Control (QR/GPS),
Sincronización de Cola Offline-First (PWA) y Auditoría de Cobertura de Puestos.
"""

import math
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.esquemas.esquemas_pydantic import (
    AlertaCoberturaPuesto,
    RegistrarMarcacionRondaSolicitud,
    RespuestaMarcacionRonda,
    RespuestaPuntoControlRonda,
    SincronizarLoteOfflineSolicitud,
)
from app.modelos.modelos_bd import (
    ModeloMarcacionRonda,
    ModeloPuestoVigilancia,
    ModeloPuntoControlRonda,
    ModeloRegistroMinuta,
    ModeloTurno,
    ModeloUsuario,
    NivelPrioridad,
    TipoRegistroMinuta,
    TipoTurno,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.seguridad import obtener_usuario_actual
from app.rutas.rutas_minuta import mapear_minuta_a_respuesta
from app.servicios.gestor_websockets import gestor_minuta_ws

enrutador_rondas = APIRouter(
    prefix="/api/rondas",
    tags=["Fases 5 y 7 - Rondas QR/GPS, Cola Offline y Alertas de Cobertura"],
)


def calcular_distancia_haversine_metros(
    latitud_1: float,
    longitud_1: float,
    latitud_2: float,
    longitud_2: float,
) -> float:
    """
    Calcula la distancia geodésica en metros entre dos coordenadas GPS utilizando
    la fórmula del semiverseno (Haversine) sobre el radio medio terrestre (6,371,000 m).
    """
    radio_tierra_metros: float = 6371000.0
    fi_1: float = math.radians(latitud_1)
    fi_2: float = math.radians(latitud_2)
    delta_fi: float = math.radians(latitud_2 - latitud_1)
    delta_lambda: float = math.radians(longitud_2 - longitud_1)

    a: float = (
        math.sin(delta_fi / 2.0) ** 2
        + math.cos(fi_1) * math.cos(fi_2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c: float = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(radio_tierra_metros * c, 2)


@enrutador_rondas.get(
    "/puntos-control",
    response_model=list[RespuestaPuntoControlRonda],
    summary="Listar checkpoints QR/GPS configurados en los puestos de vigilancia",
)
async def listar_puntos_control(
    _usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaPuntoControlRonda]:
    """Retorna todos los puntos de control QR/GPS ordenados por puesto y secuencia."""
    consulta = select(ModeloPuntoControlRonda).order_by(
        ModeloPuntoControlRonda.puesto_id.asc(),
        ModeloPuntoControlRonda.orden_secuencia.asc(),
    )
    resultado = await sesion_bd.execute(consulta)
    puntos = resultado.scalars().all()
    return [RespuestaPuntoControlRonda.model_validate(p) for p in puntos]


@enrutador_rondas.get(
    "/marcaciones",
    response_model=list[RespuestaMarcacionRonda],
    summary="Consultar historial de verificaciones QR/GPS de rondas",
)
async def listar_marcaciones_ronda(
    _usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaMarcacionRonda]:
    """Retorna las marcaciones de ronda con los datos del checkpoint y del operador."""
    consulta_marcaciones = (
        select(ModeloMarcacionRonda)
        .order_by(ModeloMarcacionRonda.fecha_marcacion.desc())
        .limit(50)
    )
    marcaciones = list((await sesion_bd.execute(consulta_marcaciones)).scalars().all())

    puntos_mapa = {
        p.punto_id: p
        for p in (await sesion_bd.execute(select(ModeloPuntoControlRonda)))
        .scalars()
        .all()
    }
    usuarios_mapa = {
        u.usuario_id: u
        for u in (await sesion_bd.execute(select(ModeloUsuario))).scalars().all()
    }

    respuestas: list[RespuestaMarcacionRonda] = []
    for m in marcaciones:
        punto = puntos_mapa.get(m.punto_id)
        operador = usuarios_mapa.get(m.operador_id)
        respuestas.append(
            RespuestaMarcacionRonda(
                marcacion_id=m.marcacion_id,
                punto_id=m.punto_id,
                nombre_punto=(
                    punto.nombre_punto if punto else f"Punto #{m.punto_id}"
                ),
                codigo_qr_hash=punto.codigo_qr_hash if punto else "QR-DESCONOCIDO",
                operador_id=m.operador_id,
                nombre_operador=(
                    operador.nombre_completo if operador else "Operador"
                ),
                latitud_capturada=m.latitud_capturada,
                longitud_capturada=m.longitud_capturada,
                distancia_calculada_metros=m.distancia_calculada_metros,
                dentro_de_geocerca=m.dentro_de_geocerca,
                sincronizado_desde_offline=m.sincronizado_desde_offline,
                observacion_ronda=m.observacion_ronda,
                fecha_marcacion=m.fecha_marcacion,
            )
        )
    return respuestas


@enrutador_rondas.post(
    "/marcar",
    response_model=RespuestaMarcacionRonda,
    status_code=status.HTTP_201_CREATED,
    summary="Verificar checkpoint QR/GPS en campo y transmitir a Minuta en Vivo",
)
async def registrar_marcacion_ronda(
    solicitud: RegistrarMarcacionRondaSolicitud,
    usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaMarcacionRonda:
    """
    Calcula la distancia geodésica entre la posición GPS capturada y el punto QR.
    Registra la marcación y emite automáticamente una anotación en la Minuta Digital.
    """
    punto = (
        await sesion_bd.execute(
            select(ModeloPuntoControlRonda).where(
                ModeloPuntoControlRonda.punto_id == solicitud.punto_id
            )
        )
    ).scalar_one_or_none()

    if punto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El punto de control QR/GPS especificado no existe.",
        )

    distancia_metros = calcular_distancia_haversine_metros(
        punto.latitud_gps,
        punto.longitud_gps,
        solicitud.latitud_capturada,
        solicitud.longitud_capturada,
    )
    en_geocerca: bool = distancia_metros <= punto.radio_tolerancia_metros

    nueva_marcacion = ModeloMarcacionRonda(
        punto_id=punto.punto_id,
        operador_id=usuario_actual.usuario_id,
        latitud_capturada=solicitud.latitud_capturada,
        longitud_capturada=solicitud.longitud_capturada,
        distancia_calculada_metros=distancia_metros,
        dentro_de_geocerca=en_geocerca,
        sincronizado_desde_offline=solicitud.sincronizado_desde_offline,
        observacion_ronda=solicitud.observacion_ronda.strip(),
    )
    sesion_bd.add(nueva_marcacion)

    prioridad_evento = (
        NivelPrioridad.BAJA if en_geocerca else NivelPrioridad.ALTA
    )
    etiqueta_origen = "[SINCRONIZADO OFFLINE]" if solicitud.sincronizado_desde_offline else "[EN LÍNEA]"
    estado_geocerca = (
        f"DENTRO DE GEOCERCA ({distancia_metros}m <= {punto.radio_tolerancia_metros}m)"
        if en_geocerca
        else f"FUERA DE RANGO GPS ({distancia_metros}m > {punto.radio_tolerancia_metros}m)"
    )

    registro_minuta = ModeloRegistroMinuta(
        operador_id=usuario_actual.usuario_id,
        puesto_id=punto.puesto_id,
        tipo_registro=TipoRegistroMinuta.RONDA_CONTROL,
        nivel_prioridad=prioridad_evento,
        titulo_evento=f"{etiqueta_origen} Marcación QR {punto.codigo_qr_hash} - {punto.nombre_punto}",
        descripcion_detallada=f"{estado_geocerca}. Observación: {solicitud.observacion_ronda.strip()}",
    )
    sesion_bd.add(registro_minuta)
    await sesion_bd.commit()
    await sesion_bd.refresh(nueva_marcacion)

    consulta_minuta = (
        select(ModeloRegistroMinuta)
        .options(
            selectinload(ModeloRegistroMinuta.operador),
            selectinload(ModeloRegistroMinuta.puesto_vigilancia),
        )
        .where(ModeloRegistroMinuta.registro_id == registro_minuta.registro_id)
    )
    minuta_hidratada = (await sesion_bd.execute(consulta_minuta)).scalar_one()
    await gestor_minuta_ws.difundir_evento_minuta(
        {
            "tipo_mensaje": "NUEVO_REGISTRO_MINUTA",
            "registro": mapear_minuta_a_respuesta(minuta_hidratada).model_dump(
                mode="json"
            ),
        }
    )

    return RespuestaMarcacionRonda(
        marcacion_id=nueva_marcacion.marcacion_id,
        punto_id=punto.punto_id,
        nombre_punto=punto.nombre_punto,
        codigo_qr_hash=punto.codigo_qr_hash,
        operador_id=usuario_actual.usuario_id,
        nombre_operador=usuario_actual.nombre_completo,
        latitud_capturada=nueva_marcacion.latitud_capturada,
        longitud_capturada=nueva_marcacion.longitud_capturada,
        distancia_calculada_metros=nueva_marcacion.distancia_calculada_metros,
        dentro_de_geocerca=nueva_marcacion.dentro_de_geocerca,
        sincronizado_desde_offline=nueva_marcacion.sincronizado_desde_offline,
        observacion_ronda=nueva_marcacion.observacion_ronda,
        fecha_marcacion=nueva_marcacion.fecha_marcacion,
    )


@enrutador_rondas.post(
    "/sincronizar-cola-offline",
    response_model=list[RespuestaMarcacionRonda],
    summary="Sincronizar lote de marcaciones almacenadas en modo Offline-First (PWA)",
)
async def sincronizar_lote_offline(
    lote: SincronizarLoteOfflineSolicitud,
    usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaMarcacionRonda]:
    """Procesa en lote todas las marcaciones retenidas localmente durante falta de señal."""
    procesadas: list[RespuestaMarcacionRonda] = []
    for item in lote.marcaciones:
        item.sincronizado_desde_offline = True
        resultado = await registrar_marcacion_ronda(
            solicitud=item,
            usuario_actual=usuario_actual,
            sesion_bd=sesion_bd,
        )
        procesadas.append(resultado)
    return procesadas


@enrutador_rondas.get(
    "/auditoria-cobertura",
    response_model=list[AlertaCoberturaPuesto],
    summary="Auditoría en tiempo real de cobertura de puestos y alertas de relevo (Fase 7)",
)
async def auditar_cobertura_puestos(
    _usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[AlertaCoberturaPuesto]:
    """
    Evalúa cada puesto de vigilancia cruzando turnos programados, puntos de control QR/GPS
    y marcaciones efectuadas para detectar puestos cubiertos o sin verificación reciente.
    """
    puestos = list(
        (await sesion_bd.execute(select(ModeloPuestoVigilancia))).scalars().all()
    )
    puntos = list(
        (await sesion_bd.execute(select(ModeloPuntoControlRonda))).scalars().all()
    )
    marcaciones = list(
        (await sesion_bd.execute(select(ModeloMarcacionRonda))).scalars().all()
    )
    turnos = list(
        (
            await sesion_bd.execute(
                select(ModeloTurno).options(selectinload(ModeloTurno.operador))
            )
        )
        .scalars()
        .all()
    )

    alertas: list[AlertaCoberturaPuesto] = []
    for puesto in puestos:
        puntos_puesto = [p for p in puntos if p.puesto_id == puesto.puesto_id]
        ids_puntos = {p.punto_id for p in puntos_puesto}
        marcaciones_puesto = [
            m for m in marcaciones if m.punto_id in ids_puntos
        ]
        turnos_puesto = [
            t
            for t in turnos
            if t.puesto_id == puesto.puesto_id
            and t.tipo_turno != TipoTurno.DESCANSO
        ]

        operador_nombre = (
            f"{turnos_puesto[0].operador.nombre_completo} ({turnos_puesto[0].operador.codigo_placa})"
            if turnos_puesto
            else "SIN OPERADOR ASIGNADO"
        )

        if not turnos_puesto:
            alertas.append(
                AlertaCoberturaPuesto(
                    puesto_id=puesto.puesto_id,
                    codigo_puesto=puesto.codigo_puesto,
                    nombre_puesto=puesto.nombre_puesto,
                    estado_cobertura="PUESTO DESCUBIERTO (SIN RELEVO)",
                    nivel_alerta=NivelPrioridad.CRITICA,
                    operador_en_turno=operador_nombre,
                    puntos_control_verificados=len(marcaciones_puesto),
                    total_puntos_control=len(puntos_puesto),
                    detalle_operativo=(
                        "Alerta Táctica: No hay turnos operativos activos asignados a esta instalación. "
                        "Se requiere despacho inmediato de supervisor."
                    ),
                )
            )
        elif len(marcaciones_puesto) == 0 and len(puntos_puesto) > 0:
            alertas.append(
                AlertaCoberturaPuesto(
                    puesto_id=puesto.puesto_id,
                    codigo_puesto=puesto.codigo_puesto,
                    nombre_puesto=puesto.nombre_puesto,
                    estado_cobertura="RONDA PENDIENTE DE VERIFICACIÓN",
                    nivel_alerta=NivelPrioridad.MEDIA,
                    operador_en_turno=operador_nombre,
                    puntos_control_verificados=0,
                    total_puntos_control=len(puntos_puesto),
                    detalle_operativo=(
                        f"Guardia en puesto, pero aún no registra lecturas en los "
                        f"{len(puntos_puesto)} puntos QR/GPS asignados."
                    ),
                )
            )
        else:
            alertas.append(
                AlertaCoberturaPuesto(
                    puesto_id=puesto.puesto_id,
                    codigo_puesto=puesto.codigo_puesto,
                    nombre_puesto=puesto.nombre_puesto,
                    estado_cobertura="COBERTURA ÓPTIMA Y RONDA VERIFICADA",
                    nivel_alerta=NivelPrioridad.BAJA,
                    operador_en_turno=operador_nombre,
                    puntos_control_verificados=len(marcaciones_puesto),
                    total_puntos_control=len(puntos_puesto),
                    detalle_operativo=(
                        f"Relevo confirmado y {len(marcaciones_puesto)} marcaciones "
                        f"georreferenciadas auditadas satisfactoriamente."
                    ),
                )
            )

    return alertas


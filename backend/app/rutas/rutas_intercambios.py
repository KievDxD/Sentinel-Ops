"""
Módulo 4 (Enterprise V2.0): Rutas del Sistema de Intercambio de Turnos.
Permite a los guardias solicitar cambios de turno validando cruces de horario,
descanso mínimo legal (>= 12 horas) y vigencia de credencial SuperVigilancia.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.esquemas.esquemas_pydantic import (
    CrearSolicitudIntercambio,
    ResolverSolicitudIntercambio,
    RespuestaSolicitudIntercambio,
)
from app.modelos.modelos_bd import (
    EstadoSolicitudIntercambio,
    EstadoTurno,
    ModeloSolicitudIntercambio,
    ModeloTurno,
    ModeloUsuario,
    RolUsuario,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.seguridad import obtener_usuario_actual, requerir_roles
from app.servicios.motor_turnos import (
    validar_factibilidad_intercambio,
    verificar_vigencia_credencial_sv,
)

enrutador_intercambios = APIRouter(
    prefix="/api/intercambios",
    tags=["Módulo 4 - Sistema de Intercambio de Turnos"],
)


async def construir_respuesta_intercambio(
    solicitud: ModeloSolicitudIntercambio,
    sesion_bd: AsyncSession,
) -> RespuestaSolicitudIntercambio:
    """Hidrata los nombres de los operadores, supervisor y resúmenes de los turnos."""
    usuarios_ids = [
        solicitud.operador_solicitante_id,
        solicitud.operador_receptor_id,
    ]
    if solicitud.supervisor_validador_id is not None:
        usuarios_ids.append(solicitud.supervisor_validador_id)

    resultado_usuarios = await sesion_bd.execute(
        select(ModeloUsuario).where(ModeloUsuario.usuario_id.in_(usuarios_ids))
    )
    mapa_usuarios = {
        u.usuario_id: u for u in resultado_usuarios.scalars().all()
    }

    resultado_turnos = await sesion_bd.execute(
        select(ModeloTurno)
        .options(selectinload(ModeloTurno.puesto_vigilancia))
        .where(
            ModeloTurno.turno_id.in_(
                [solicitud.turno_origen_id, solicitud.turno_destino_id]
            )
        )
    )
    mapa_turnos = {t.turno_id: t for t in resultado_turnos.scalars().all()}

    turno_origen = mapa_turnos.get(solicitud.turno_origen_id)
    turno_destino = mapa_turnos.get(solicitud.turno_destino_id)

    resumen_origen = (
        f"Turno #{turno_origen.turno_id} ({turno_origen.tipo_turno.value}) - "
        f"{turno_origen.fecha_inicio.strftime('%Y-%m-%d %H:%M')} en "
        f"{turno_origen.puesto_vigilancia.codigo_puesto}"
        if turno_origen
        else f"Turno #{solicitud.turno_origen_id}"
    )
    resumen_destino = (
        f"Turno #{turno_destino.turno_id} ({turno_destino.tipo_turno.value}) - "
        f"{turno_destino.fecha_inicio.strftime('%Y-%m-%d %H:%M')} en "
        f"{turno_destino.puesto_vigilancia.codigo_puesto}"
        if turno_destino
        else f"Turno #{solicitud.turno_destino_id}"
    )

    solicitante = mapa_usuarios.get(solicitud.operador_solicitante_id)
    receptor = mapa_usuarios.get(solicitud.operador_receptor_id)
    supervisor = (
        mapa_usuarios.get(solicitud.supervisor_validador_id)
        if solicitud.supervisor_validador_id
        else None
    )

    return RespuestaSolicitudIntercambio(
        intercambio_id=solicitud.intercambio_id,
        operador_solicitante_id=solicitud.operador_solicitante_id,
        nombre_solicitante=(
            solicitante.nombre_completo if solicitante else "Operador"
        ),
        operador_receptor_id=solicitud.operador_receptor_id,
        nombre_receptor=receptor.nombre_completo if receptor else "Operador",
        turno_origen_id=solicitud.turno_origen_id,
        resumen_turno_origen=resumen_origen,
        turno_destino_id=solicitud.turno_destino_id,
        resumen_turno_destino=resumen_destino,
        motivo_solicitud=solicitud.motivo_solicitud,
        estado_solicitud=solicitud.estado_solicitud,
        validacion_sin_cruces=solicitud.validacion_sin_cruces,
        horas_descanso_minimo_calculadas=solicitud.horas_descanso_minimo_calculadas,
        detalle_validacion_motor=solicitud.detalle_validacion_motor,
        supervisor_validador_id=solicitud.supervisor_validador_id,
        nombre_supervisor=supervisor.nombre_completo if supervisor else None,
        comentario_supervisor=solicitud.comentario_supervisor,
        fecha_solicitud=solicitud.fecha_solicitud,
        fecha_resolucion=solicitud.fecha_resolucion,
    )


@enrutador_intercambios.get(
    "",
    response_model=list[RespuestaSolicitudIntercambio],
    summary="Listar solicitudes de intercambio de turnos",
)
async def listar_solicitudes_intercambio(
    _usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaSolicitudIntercambio]:
    """Retorna todas las solicitudes de intercambio ordenadas por fecha de creación."""
    consulta = select(ModeloSolicitudIntercambio).order_by(
        ModeloSolicitudIntercambio.fecha_solicitud.desc()
    )
    resultado = await sesion_bd.execute(consulta)
    solicitudes = resultado.scalars().all()
    respuestas: list[RespuestaSolicitudIntercambio] = []
    for s in solicitudes:
        respuestas.append(await construir_respuesta_intercambio(s, sesion_bd))
    return respuestas


@enrutador_intercambios.post(
    "",
    response_model=RespuestaSolicitudIntercambio,
    status_code=status.HTTP_201_CREATED,
    summary="Solicitar intercambio de turno (Valida credencial SV, no-cruce y descanso >= 12h)",
)
async def crear_solicitud_intercambio(
    datos: CrearSolicitudIntercambio,
    _usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaSolicitudIntercambio:
    """
    Evalúa la solicitud mediante el Motor de Turnos y verifica que ambos guardas tengan
    su credencial SuperVigilancia vigente (o excepción autorizada).
    """
    turno_origen = (
        await sesion_bd.execute(
            select(ModeloTurno)
            .options(selectinload(ModeloTurno.operador))
            .where(ModeloTurno.turno_id == datos.turno_origen_id)
        )
    ).scalar_one_or_none()
    turno_destino = (
        await sesion_bd.execute(
            select(ModeloTurno)
            .options(selectinload(ModeloTurno.operador))
            .where(ModeloTurno.turno_id == datos.turno_destino_id)
        )
    ).scalar_one_or_none()

    if turno_origen is None or turno_destino is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uno o ambos turnos especificados no existen en la programación.",
        )

    for op in [turno_origen.operador, turno_destino.operador]:
        habilitado, motivo_sv = verificar_vigencia_credencial_sv(
            op.fecha_vencimiento_credencial,
            op.excepcion_credencial_autorizada,
            turno_origen.fecha_inicio.date(),
        )
        if not habilitado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Relevo bloqueado por normativa SuperVigilancia para "
                    f"{op.nombre_completo} ({op.codigo_placa}): {motivo_sv}"
                ),
            )

    turnos_solicitante = list(
        (
            await sesion_bd.execute(
                select(ModeloTurno).where(
                    ModeloTurno.operador_id == turno_origen.operador_id
                )
            )
        )
        .scalars()
        .all()
    )
    turnos_receptor = list(
        (
            await sesion_bd.execute(
                select(ModeloTurno).where(
                    ModeloTurno.operador_id == turno_destino.operador_id
                )
            )
        )
        .scalars()
        .all()
    )

    es_factible, menor_descanso, mensaje_motor = validar_factibilidad_intercambio(
        turno_origen=turno_origen,
        turno_destino=turno_destino,
        turnos_operador_solicitante=turnos_solicitante,
        turnos_operador_receptor=turnos_receptor,
    )

    if not es_factible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=mensaje_motor,
        )

    nueva_solicitud = ModeloSolicitudIntercambio(
        operador_solicitante_id=turno_origen.operador_id,
        operador_receptor_id=turno_destino.operador_id,
        turno_origen_id=turno_origen.turno_id,
        turno_destino_id=turno_destino.turno_id,
        motivo_solicitud=datos.motivo_solicitud.strip(),
        estado_solicitud=EstadoSolicitudIntercambio.PENDIENTE,
        validacion_sin_cruces=True,
        horas_descanso_minimo_calculadas=menor_descanso,
        detalle_validacion_motor=mensaje_motor,
    )

    sesion_bd.add(nueva_solicitud)
    await sesion_bd.commit()
    await sesion_bd.refresh(nueva_solicitud)
    return await construir_respuesta_intercambio(nueva_solicitud, sesion_bd)


@enrutador_intercambios.patch(
    "/{intercambio_id}/resolver",
    response_model=RespuestaSolicitudIntercambio,
    summary="Aprobar o rechazar intercambio de turno (Exclusivo SUPERVISOR o ADMINISTRADOR)",
)
async def resolver_solicitud_intercambio(
    intercambio_id: int,
    decision: ResolverSolicitudIntercambio,
    supervisor_actual: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.SUPERVISOR, RolUsuario.ADMINISTRADOR)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaSolicitudIntercambio:
    """
    Revalida en tiempo real que no haya cruces ni violación del descanso mínimo antes
    de aprobar y permutar atómicamente los operadores asignados a ambos turnos.
    """
    solicitud = (
        await sesion_bd.execute(
            select(ModeloSolicitudIntercambio).where(
                ModeloSolicitudIntercambio.intercambio_id == intercambio_id
            )
        )
    ).scalar_one_or_none()

    if solicitud is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La solicitud de intercambio no existe.",
        )

    if solicitud.estado_solicitud != EstadoSolicitudIntercambio.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Esta solicitud ya fue procesada ({solicitud.estado_solicitud.value}).",
        )

    if decision.aprobar:
        turno_origen = (
            await sesion_bd.execute(
                select(ModeloTurno)
                .options(selectinload(ModeloTurno.operador))
                .where(ModeloTurno.turno_id == solicitud.turno_origen_id)
            )
        ).scalar_one_or_none()
        turno_destino = (
            await sesion_bd.execute(
                select(ModeloTurno)
                .options(selectinload(ModeloTurno.operador))
                .where(ModeloTurno.turno_id == solicitud.turno_destino_id)
            )
        ).scalar_one_or_none()

        if turno_origen is None or turno_destino is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Los turnos asociados ya no se encuentran disponibles.",
            )

        for op in [turno_origen.operador, turno_destino.operador]:
            habilitado, motivo_sv = verificar_vigencia_credencial_sv(
                op.fecha_vencimiento_credencial,
                op.excepcion_credencial_autorizada,
                turno_origen.fecha_inicio.date(),
            )
            if not habilitado:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"No se puede aprobar el intercambio por credencial SV vencida de "
                        f"{op.nombre_completo}: {motivo_sv}"
                    ),
                )

        turnos_solicitante = list(
            (
                await sesion_bd.execute(
                    select(ModeloTurno).where(
                        ModeloTurno.operador_id == turno_origen.operador_id
                    )
                )
            )
            .scalars()
            .all()
        )
        turnos_receptor = list(
            (
                await sesion_bd.execute(
                    select(ModeloTurno).where(
                        ModeloTurno.operador_id == turno_destino.operador_id
                    )
                )
            )
            .scalars()
            .all()
        )

        es_factible, menor_descanso, mensaje_motor = validar_factibilidad_intercambio(
            turno_origen=turno_origen,
            turno_destino=turno_destino,
            turnos_operador_solicitante=turnos_solicitante,
            turnos_operador_receptor=turnos_receptor,
        )
        if not es_factible:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede aprobar el intercambio: {mensaje_motor}",
            )

        operador_temp = turno_origen.operador_id
        turno_origen.operador_id = turno_destino.operador_id
        turno_destino.operador_id = operador_temp
        turno_origen.estado_turno = EstadoTurno.INTERCAMBIADO
        turno_destino.estado_turno = EstadoTurno.INTERCAMBIADO

        solicitud.estado_solicitud = EstadoSolicitudIntercambio.APROBADA
        solicitud.horas_descanso_minimo_calculadas = menor_descanso
        solicitud.detalle_validacion_motor = mensaje_motor
    else:
        solicitud.estado_solicitud = EstadoSolicitudIntercambio.RECHAZADA

    solicitud.supervisor_validador_id = supervisor_actual.usuario_id
    solicitud.comentario_supervisor = decision.comentario_supervisor.strip()
    solicitud.fecha_resolucion = datetime.now(timezone.utc)

    await sesion_bd.commit()
    await sesion_bd.refresh(solicitud)
    return await construir_respuesta_intercambio(solicitud, sesion_bd)

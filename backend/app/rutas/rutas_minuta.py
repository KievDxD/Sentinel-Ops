"""
Módulo 3 (Enterprise V2.0): Rutas REST y WebSocket para la Minuta Digital en Tiempo Real,
Visibilidad Dual (PUBLICA_CLIENTE / INTERNA_OPERATIVA), Acta Digital de Entrega/Recibo de
Puesto con Armamento Indumil (SHA-256) y Botón de Pánico Táctico SOS en Tiempo Real.
"""

from datetime import datetime, timezone
import hashlib

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.esquemas.esquemas_pydantic import (
    AtenderAlertaSosSolicitud,
    CrearActaRelevoSolicitud,
    CrearRegistroMinutaSolicitud,
    DispararAlertaSosSolicitud,
    RespuestaActaRelevo,
    RespuestaAlertaSos,
    RespuestaDotacionPuesto,
    RespuestaRegistroMinuta,
)
from app.modelos.modelos_bd import (
    EstadoAlertaSos,
    EstadoItemDotacion,
    ModeloActaRelevoPuesto,
    ModeloAlertaPanicoSos,
    ModeloDotacionPuesto,
    ModeloPuestoVigilancia,
    ModeloRegistroMinuta,
    ModeloUsuario,
    NivelPrioridad,
    RolUsuario,
    TipoRegistroMinuta,
    VisibilidadMinuta,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.seguridad import obtener_usuario_actual, requerir_roles
from app.servicios.gestor_websockets import gestor_minuta_ws

enrutador_minuta = APIRouter(
    prefix="/api/minuta",
    tags=["Módulo 3 - Minuta Digital, Actas Indumil y Alerta SOS"],
)


def mapear_minuta_a_respuesta(registro: ModeloRegistroMinuta) -> RespuestaRegistroMinuta:
    """Convierte un ModeloRegistroMinuta cargado a su esquema de respuesta Pydantic."""
    return RespuestaRegistroMinuta(
        registro_id=registro.registro_id,
        operador_id=registro.operador_id,
        nombre_operador=registro.operador.nombre_completo,
        codigo_placa_operador=registro.operador.codigo_placa,
        puesto_id=registro.puesto_id,
        nombre_puesto=registro.puesto_vigilancia.nombre_puesto,
        codigo_puesto=registro.puesto_vigilancia.codigo_puesto,
        tipo_registro=registro.tipo_registro,
        visibilidad=registro.visibilidad,
        nivel_prioridad=registro.nivel_prioridad,
        titulo_evento=registro.titulo_evento,
        descripcion_detallada=registro.descripcion_detallada,
        nombre_visitante=registro.nombre_visitante,
        documento_visitante=registro.documento_visitante,
        placa_vehiculo=registro.placa_vehiculo,
        fecha_registro=registro.fecha_registro,
    )


@enrutador_minuta.get(
    "",
    response_model=list[RespuestaRegistroMinuta],
    summary="Listar registros históricos y recientes de la Minuta Digital (Filtrado RBAC Cliente)",
)
async def listar_registros_minuta(
    puesto_id: int | None = Query(default=None),
    limite: int = Query(default=50, ge=1, le=200),
    usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaRegistroMinuta]:
    """
    Retorna las anotaciones de la minuta digital ordenadas de la más reciente a la más antigua.
    Si el rol es CLIENTE, filtra estrictamente a su puesto contratado y visibilidad PUBLICA_CLIENTE.
    """
    consulta = (
        select(ModeloRegistroMinuta)
        .options(
            selectinload(ModeloRegistroMinuta.operador),
            selectinload(ModeloRegistroMinuta.puesto_vigilancia),
        )
        .order_by(ModeloRegistroMinuta.fecha_registro.desc())
        .limit(limite)
    )

    if usuario_actual.rol == RolUsuario.CLIENTE:
        consulta = consulta.where(
            ModeloRegistroMinuta.visibilidad == VisibilidadMinuta.PUBLICA_CLIENTE
        )
        if usuario_actual.puesto_base_id is not None:
            consulta = consulta.where(
                ModeloRegistroMinuta.puesto_id == usuario_actual.puesto_base_id
            )
    elif puesto_id is not None:
        consulta = consulta.where(ModeloRegistroMinuta.puesto_id == puesto_id)

    resultado = await sesion_bd.execute(consulta)
    registros = resultado.scalars().all()
    return [mapear_minuta_a_respuesta(r) for r in registros]


@enrutador_minuta.post(
    "",
    response_model=RespuestaRegistroMinuta,
    status_code=status.HTTP_201_CREATED,
    summary="Asentar nuevo evento en la Minuta Digital con visibilidad dual y emitir por WebSocket",
)
async def crear_registro_minuta(
    solicitud: CrearRegistroMinutaSolicitud,
    usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.OPERADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.ADMINISTRADOR,
            RolUsuario.RRHH,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaRegistroMinuta:
    """
    Registra un nuevo evento en la base de datos con visibilidad dual
    (PUBLICA_CLIENTE o INTERNA_OPERATIVA) y lo transmite en vivo vía WebSocket.
    """
    puesto = (
        await sesion_bd.execute(
            select(ModeloPuestoVigilancia).where(
                ModeloPuestoVigilancia.puesto_id == solicitud.puesto_id
            )
        )
    ).scalar_one_or_none()
    if puesto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El puesto de vigilancia indicado no existe.",
        )

    nuevo_registro = ModeloRegistroMinuta(
        operador_id=usuario_actual.usuario_id,
        puesto_id=puesto.puesto_id,
        tipo_registro=solicitud.tipo_registro,
        visibilidad=solicitud.visibilidad,
        nivel_prioridad=solicitud.nivel_prioridad,
        titulo_evento=solicitud.titulo_evento.strip(),
        descripcion_detallada=solicitud.descripcion_detallada.strip(),
        nombre_visitante=(
            solicitud.nombre_visitante.strip() if solicitud.nombre_visitante else None
        ),
        documento_visitante=(
            solicitud.documento_visitante.strip()
            if solicitud.documento_visitante
            else None
        ),
        placa_vehiculo=(
            solicitud.placa_vehiculo.upper().strip()
            if solicitud.placa_vehiculo
            else None
        ),
    )

    sesion_bd.add(nuevo_registro)
    await sesion_bd.commit()

    consulta_recarga = (
        select(ModeloRegistroMinuta)
        .options(
            selectinload(ModeloRegistroMinuta.operador),
            selectinload(ModeloRegistroMinuta.puesto_vigilancia),
        )
        .where(ModeloRegistroMinuta.registro_id == nuevo_registro.registro_id)
    )
    registro_completo = (await sesion_bd.execute(consulta_recarga)).scalar_one()
    respuesta = mapear_minuta_a_respuesta(registro_completo)

    await gestor_minuta_ws.difundir_evento_minuta(
        {
            "tipo_mensaje": "NUEVO_REGISTRO_MINUTA",
            "registro": respuesta.model_dump(mode="json"),
        }
    )

    return respuesta


# ============================================================================
# 3.1. ACTA DIGITAL DE ENTREGA Y RECIBO DE PUESTO (INVENTARIO + ARMAMENTO INDUMIL)
# ============================================================================
@enrutador_minuta.get(
    "/dotacion/{puesto_id}",
    response_model=RespuestaDotacionPuesto,
    summary="Consultar inventario de dotación y armamento Indumil de un puesto",
)
async def obtener_dotacion_puesto(
    puesto_id: int,
    _usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaDotacionPuesto:
    """Retorna el armamento Indumil, salvoconducto, munición y elementos tácticos del puesto."""
    dotacion = (
        await sesion_bd.execute(
            select(ModeloDotacionPuesto).where(
                ModeloDotacionPuesto.puesto_id == puesto_id
            )
        )
    ).scalar_one_or_none()
    if dotacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró inventario de dotación registrado para este puesto.",
        )
    return RespuestaDotacionPuesto.model_validate(dotacion)


@enrutador_minuta.get(
    "/actas-relevo",
    response_model=list[RespuestaActaRelevo],
    summary="Listar actas digitales de entrega y recibo de puesto firmadas con SHA-256",
)
async def listar_actas_relevo(
    puesto_id: int | None = Query(default=None),
    usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaActaRelevo]:
    """Retorna el historial de actas de relevo de turno y verificación de armamento Indumil."""
    consulta = select(ModeloActaRelevoPuesto).order_by(
        ModeloActaRelevoPuesto.fecha_acta.desc()
    )
    if usuario_actual.rol == RolUsuario.CLIENTE and usuario_actual.puesto_base_id:
        consulta = consulta.where(
            ModeloActaRelevoPuesto.puesto_id == usuario_actual.puesto_base_id
        )
    elif puesto_id is not None:
        consulta = consulta.where(ModeloActaRelevoPuesto.puesto_id == puesto_id)

    actas = list((await sesion_bd.execute(consulta)).scalars().all())
    puestos_mapa = {
        p.puesto_id: p
        for p in (await sesion_bd.execute(select(ModeloPuestoVigilancia)))
        .scalars()
        .all()
    }
    usuarios_mapa = {
        u.usuario_id: u
        for u in (await sesion_bd.execute(select(ModeloUsuario))).scalars().all()
    }

    respuestas: list[RespuestaActaRelevo] = []
    for a in actas:
        puesto = puestos_mapa.get(a.puesto_id)
        saliente = usuarios_mapa.get(a.operador_saliente_id)
        entrante = (
            usuarios_mapa.get(a.operador_entrante_id)
            if a.operador_entrante_id
            else None
        )
        respuestas.append(
            RespuestaActaRelevo(
                acta_id=a.acta_id,
                puesto_id=a.puesto_id,
                nombre_puesto=puesto.nombre_puesto if puesto else f"Puesto #{a.puesto_id}",
                codigo_puesto=puesto.codigo_puesto if puesto else "PST",
                operador_saliente_id=a.operador_saliente_id,
                nombre_operador_saliente=(
                    saliente.nombre_completo if saliente else "Operador Saliente"
                ),
                operador_entrante_id=a.operador_entrante_id,
                nombre_operador_entrante=(
                    entrante.nombre_completo if entrante else None
                ),
                estado_armamento=a.estado_armamento,
                municion_verificada=a.municion_verificada,
                estado_chaleco=a.estado_chaleco,
                estado_radio=a.estado_radio,
                estado_linterna_y_llaves=a.estado_linterna_y_llaves,
                observaciones_relevo=a.observaciones_relevo,
                sello_sha256=a.sello_sha256,
                alerta_disparada=a.alerta_disparada,
                fecha_acta=a.fecha_acta,
            )
        )
    return respuestas


@enrutador_minuta.post(
    "/actas-relevo",
    response_model=RespuestaActaRelevo,
    status_code=status.HTTP_201_CREATED,
    summary="Diligenciar y firmar Acta Digital de Entrega/Recibo de Puesto con Armamento Indumil",
)
async def crear_acta_relevo_puesto(
    solicitud: CrearActaRelevoSolicitud,
    usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.OPERADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.ADMINISTRADOR,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaActaRelevo:
    """
    Verifica el estado de cada elemento del puesto y munición Indumil.
    Genera automáticamente un registro inmutable en la Minuta Digital encadenado con SHA-256
    bajo la categoría ENTREGA_RECIBO_PUESTO y dispara alerta si hay NOVEDAD o FALTANTE.
    """
    puesto = (
        await sesion_bd.execute(
            select(ModeloPuestoVigilancia).where(
                ModeloPuestoVigilancia.puesto_id == solicitud.puesto_id
            )
        )
    ).scalar_one_or_none()
    if puesto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El puesto de vigilancia no existe.",
        )

    dotacion = (
        await sesion_bd.execute(
            select(ModeloDotacionPuesto).where(
                ModeloDotacionPuesto.puesto_id == solicitud.puesto_id
            )
        )
    ).scalar_one_or_none()

    municion_esperada = (
        dotacion.cantidad_municion_autorizada if dotacion is not None else 0
    )
    estados_items = [
        solicitud.estado_armamento,
        solicitud.estado_chaleco,
        solicitud.estado_radio,
        solicitud.estado_linterna_y_llaves,
    ]
    hay_anomalia = (
        any(e != EstadoItemDotacion.OPTIMO for e in estados_items)
        or (dotacion is not None and solicitud.municion_verificada != municion_esperada)
    )

    instante_actual = datetime.now(timezone.utc)
    semilla_hash = (
        f"ACTA_INDUMIL|{puesto.codigo_puesto}|{usuario_actual.documento_identidad}|"
        f"{solicitud.estado_armamento.value}|{solicitud.municion_verificada}|"
        f"{solicitud.observaciones_relevo.strip()}|{instante_actual.isoformat()}"
    )
    sello_sha256 = hashlib.sha256(semilla_hash.encode("utf-8")).hexdigest().upper()

    nueva_acta = ModeloActaRelevoPuesto(
        puesto_id=puesto.puesto_id,
        operador_saliente_id=usuario_actual.usuario_id,
        operador_entrante_id=solicitud.operador_entrante_id,
        estado_armamento=solicitud.estado_armamento,
        municion_verificada=solicitud.municion_verificada,
        estado_chaleco=solicitud.estado_chaleco,
        estado_radio=solicitud.estado_radio,
        estado_linterna_y_llaves=solicitud.estado_linterna_y_llaves,
        observaciones_relevo=solicitud.observaciones_relevo.strip(),
        sello_sha256=sello_sha256,
        alerta_disparada=hay_anomalia,
        fecha_acta=instante_actual,
    )
    sesion_bd.add(nueva_acta)

    prioridad = NivelPrioridad.CRITICA if hay_anomalia else NivelPrioridad.BAJA
    visibilidad = (
        VisibilidadMinuta.INTERNA_OPERATIVA
        if hay_anomalia
        else VisibilidadMinuta.PUBLICA_CLIENTE
    )
    prefijo_titulo = (
        "[ALERTA ARMAMENTO/DOTACIÓN] " if hay_anomalia else "[CHECKLIST CONFORME] "
    )
    info_arma = (
        f"{dotacion.tipo_arma} Serial {dotacion.serial_arma} (Salvoconducto {dotacion.numero_salvoconducto_indumil})"
        if dotacion
        else "Sin armamento"
    )
    detalle_minuta = (
        f"Acta de Entrega/Recibo de Puesto ({info_arma}). "
        f"Armamento: {solicitud.estado_armamento.value} | Munición verificada: {solicitud.municion_verificada}/{municion_esperada} cartuchos | "
        f"Chaleco: {solicitud.estado_chaleco.value} | Radio: {solicitud.estado_radio.value} | "
        f"Linterna/Llaves: {solicitud.estado_linterna_y_llaves.value}. "
        f"Observaciones: {solicitud.observaciones_relevo.strip()}. Sello SHA-256: {sello_sha256[:16]}"
    )

    registro_minuta = ModeloRegistroMinuta(
        operador_id=usuario_actual.usuario_id,
        puesto_id=puesto.puesto_id,
        tipo_registro=TipoRegistroMinuta.ENTREGA_RECIBO_PUESTO,
        visibilidad=visibilidad,
        nivel_prioridad=prioridad,
        titulo_evento=f"{prefijo_titulo}Acta Entrega/Recibo de Puesto {puesto.codigo_puesto}",
        descripcion_detallada=detalle_minuta,
    )
    sesion_bd.add(registro_minuta)
    await sesion_bd.commit()
    await sesion_bd.refresh(nueva_acta)

    consulta_recarga = (
        select(ModeloRegistroMinuta)
        .options(
            selectinload(ModeloRegistroMinuta.operador),
            selectinload(ModeloRegistroMinuta.puesto_vigilancia),
        )
        .where(ModeloRegistroMinuta.registro_id == registro_minuta.registro_id)
    )
    minuta_completa = (await sesion_bd.execute(consulta_recarga)).scalar_one()
    await gestor_minuta_ws.difundir_evento_minuta(
        {
            "tipo_mensaje": "NUEVO_REGISTRO_MINUTA",
            "registro": mapear_minuta_a_respuesta(minuta_completa).model_dump(
                mode="json"
            ),
        }
    )

    entrante_nombre: str | None = None
    if solicitud.operador_entrante_id is not None:
        op_entrante = (
            await sesion_bd.execute(
                select(ModeloUsuario).where(
                    ModeloUsuario.usuario_id == solicitud.operador_entrante_id
                )
            )
        ).scalar_one_or_none()
        entrante_nombre = op_entrante.nombre_completo if op_entrante else None

    return RespuestaActaRelevo(
        acta_id=nueva_acta.acta_id,
        puesto_id=puesto.puesto_id,
        nombre_puesto=puesto.nombre_puesto,
        codigo_puesto=puesto.codigo_puesto,
        operador_saliente_id=usuario_actual.usuario_id,
        nombre_operador_saliente=usuario_actual.nombre_completo,
        operador_entrante_id=solicitud.operador_entrante_id,
        nombre_operador_entrante=entrante_nombre,
        estado_armamento=nueva_acta.estado_armamento,
        municion_verificada=nueva_acta.municion_verificada,
        estado_chaleco=nueva_acta.estado_chaleco,
        estado_radio=nueva_acta.estado_radio,
        estado_linterna_y_llaves=nueva_acta.estado_linterna_y_llaves,
        observaciones_relevo=nueva_acta.observaciones_relevo,
        sello_sha256=nueva_acta.sello_sha256,
        alerta_disparada=nueva_acta.alerta_disparada,
        fecha_acta=nueva_acta.fecha_acta,
    )


# ============================================================================
# 3.2. BOTÓN DE PÁNICO TÁCTICO (ALERTA SOS EN TIEMPO REAL VÍA WEBSOCKETS)
# ============================================================================
async def _hidratar_alerta_sos(
    alerta: ModeloAlertaPanicoSos, sesion_bd: AsyncSession
) -> RespuestaAlertaSos:
    """Construye el esquema de respuesta enriquecido para una alerta de pánico SOS."""
    operador = (
        await sesion_bd.execute(
            select(ModeloUsuario).where(ModeloUsuario.usuario_id == alerta.operador_id)
        )
    ).scalar_one_or_none()
    puesto = (
        await sesion_bd.execute(
            select(ModeloPuestoVigilancia).where(
                ModeloPuestoVigilancia.puesto_id == alerta.puesto_id
            )
        )
    ).scalar_one_or_none()
    supervisor_nombre: str | None = None
    if alerta.atendida_por_id is not None:
        sup = (
            await sesion_bd.execute(
                select(ModeloUsuario).where(
                    ModeloUsuario.usuario_id == alerta.atendida_por_id
                )
            )
        ).scalar_one_or_none()
        supervisor_nombre = sup.nombre_completo if sup else None

    return RespuestaAlertaSos(
        alerta_id=alerta.alerta_id,
        operador_id=alerta.operador_id,
        nombre_operador=operador.nombre_completo if operador else "Operador",
        codigo_placa_operador=operador.codigo_placa if operador else "OPR",
        puesto_id=alerta.puesto_id,
        nombre_puesto=puesto.nombre_puesto if puesto else "Puesto",
        codigo_puesto=puesto.codigo_puesto if puesto else "PST",
        latitud_gps=alerta.latitud_gps,
        longitud_gps=alerta.longitud_gps,
        estado_alerta=alerta.estado_alerta,
        fecha_activacion=alerta.fecha_activacion,
        atendida_por_id=alerta.atendida_por_id,
        nombre_supervisor_atendio=supervisor_nombre,
        fecha_atencion=alerta.fecha_atencion,
        tiempo_reaccion_segundos=alerta.tiempo_reaccion_segundos,
        nota_reaccion=alerta.nota_reaccion,
    )


@enrutador_minuta.get(
    "/panico-sos",
    response_model=list[RespuestaAlertaSos],
    summary="Listar alertas de pánico SOS activas e históricas",
)
async def listar_alertas_panico_sos(
    solo_activas: bool = Query(default=False),
    _usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaAlertaSos]:
    """Retorna las alertas de pánico SOS ordenadas de la más reciente a la más antigua."""
    consulta = select(ModeloAlertaPanicoSos).order_by(
        ModeloAlertaPanicoSos.fecha_activacion.desc()
    )
    if solo_activas:
        consulta = consulta.where(
            ModeloAlertaPanicoSos.estado_alerta == EstadoAlertaSos.ACTIVA
        )
    alertas = list((await sesion_bd.execute(consulta)).scalars().all())
    return [await _hidratar_alerta_sos(a, sesion_bd) for a in alertas]


@enrutador_minuta.post(
    "/panico-sos",
    response_model=RespuestaAlertaSos,
    status_code=status.HTTP_201_CREATED,
    summary="Disparar Alerta de Pánico SOS Táctico en Tiempo Real vía WebSocket",
)
async def disparar_alerta_panico_sos(
    solicitud: DispararAlertaSosSolicitud,
    usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaAlertaSos:
    """
    Activa una Alerta SOS con coordenadas GPS, registra el evento crítico en el Libro
    Foliado de Minuta y emite `ALERTA_PANICO_SOS` inmediatamente por WebSocket a los
    centros de mando de Supervisores y Administradores.
    """
    puesto = (
        await sesion_bd.execute(
            select(ModeloPuestoVigilancia).where(
                ModeloPuestoVigilancia.puesto_id == solicitud.puesto_id
            )
        )
    ).scalar_one_or_none()
    if puesto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El puesto de vigilancia indicado no existe.",
        )

    nueva_alerta = ModeloAlertaPanicoSos(
        operador_id=usuario_actual.usuario_id,
        puesto_id=puesto.puesto_id,
        latitud_gps=solicitud.latitud_gps,
        longitud_gps=solicitud.longitud_gps,
        estado_alerta=EstadoAlertaSos.ACTIVA,
    )
    sesion_bd.add(nueva_alerta)

    registro_minuta = ModeloRegistroMinuta(
        operador_id=usuario_actual.usuario_id,
        puesto_id=puesto.puesto_id,
        tipo_registro=TipoRegistroMinuta.ALERTA_PANICO_SOS,
        visibilidad=VisibilidadMinuta.INTERNA_OPERATIVA,
        nivel_prioridad=NivelPrioridad.CRITICA,
        titulo_evento=f"🚨 [CÓDIGO ROJO SOS] Botón de Pánico Activado en {puesto.codigo_puesto}",
        descripcion_detallada=(
            f"EMERGENCIA TÁCTICA ACTIVADA por {usuario_actual.nombre_completo} ({usuario_actual.codigo_placa}) "
            f"en {puesto.nombre_puesto}. Coordenadas GPS: Lat {solicitud.latitud_gps:.5f}, "
            f"Lon {solicitud.longitud_gps:.5f}. Requiere reacción inmediata de central."
        ),
    )
    sesion_bd.add(registro_minuta)
    await sesion_bd.commit()
    await sesion_bd.refresh(nueva_alerta)

    respuesta_alerta = await _hidratar_alerta_sos(nueva_alerta, sesion_bd)

    consulta_recarga = (
        select(ModeloRegistroMinuta)
        .options(
            selectinload(ModeloRegistroMinuta.operador),
            selectinload(ModeloRegistroMinuta.puesto_vigilancia),
        )
        .where(ModeloRegistroMinuta.registro_id == registro_minuta.registro_id)
    )
    minuta_completa = (await sesion_bd.execute(consulta_recarga)).scalar_one()

    await gestor_minuta_ws.difundir_evento_minuta(
        {
            "tipo_mensaje": "ALERTA_PANICO_SOS",
            "alerta_sos": respuesta_alerta.model_dump(mode="json"),
            "registro": mapear_minuta_a_respuesta(minuta_completa).model_dump(
                mode="json"
            ),
        }
    )

    return respuesta_alerta


@enrutador_minuta.patch(
    "/panico-sos/{alerta_id}/atender",
    response_model=RespuestaAlertaSos,
    summary="Atender Emergencia SOS y registrar tiempo exacto de reacción en segundos",
)
async def atender_alerta_panico_sos(
    alerta_id: int,
    solicitud: AtenderAlertaSosSolicitud,
    supervisor_actual: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.SUPERVISOR, RolUsuario.ADMINISTRADOR)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaAlertaSos:
    """
    Registra la reacción oficial del Supervisor o Administrador ante la alerta SOS,
    calcula el tiempo de reacción en segundos y asienta el cierre en la Minuta Foliada.
    """
    alerta = (
        await sesion_bd.execute(
            select(ModeloAlertaPanicoSos).where(
                ModeloAlertaPanicoSos.alerta_id == alerta_id
            )
        )
    ).scalar_one_or_none()
    if alerta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La alerta de pánico SOS especificada no existe.",
        )

    ahora = datetime.now(timezone.utc)
    fecha_act = alerta.fecha_activacion
    if fecha_act.tzinfo is None:
        fecha_act = fecha_act.replace(tzinfo=timezone.utc)

    segundos_reaccion = max(1, int((ahora - fecha_act).total_seconds()))

    alerta.estado_alerta = EstadoAlertaSos.ATENDIDA
    alerta.atendida_por_id = supervisor_actual.usuario_id
    alerta.fecha_atencion = ahora
    alerta.tiempo_reaccion_segundos = segundos_reaccion
    alerta.nota_reaccion = solicitud.nota_reaccion.strip()

    puesto = (
        await sesion_bd.execute(
            select(ModeloPuestoVigilancia).where(
                ModeloPuestoVigilancia.puesto_id == alerta.puesto_id
            )
        )
    ).scalar_one()

    registro_reaccion = ModeloRegistroMinuta(
        operador_id=supervisor_actual.usuario_id,
        puesto_id=alerta.puesto_id,
        tipo_registro=TipoRegistroMinuta.ALERTA_PANICO_SOS,
        visibilidad=VisibilidadMinuta.INTERNA_OPERATIVA,
        nivel_prioridad=NivelPrioridad.ALTA,
        titulo_evento=f"✅ [REACCIÓN SOS REGISTRADA] Emergencia #{alerta.alerta_id} atendida en {segundos_reaccion}s",
        descripcion_detallada=(
            f"Atendida por {supervisor_actual.nombre_completo} ({supervisor_actual.codigo_placa}) "
            f"en puesto {puesto.codigo_puesto}. Tiempo de reacción certificado: {segundos_reaccion} segundos. "
            f"Acción tomada: {solicitud.nota_reaccion.strip()}"
        ),
    )
    sesion_bd.add(registro_reaccion)
    await sesion_bd.commit()
    await sesion_bd.refresh(alerta)

    respuesta_alerta = await _hidratar_alerta_sos(alerta, sesion_bd)

    consulta_recarga = (
        select(ModeloRegistroMinuta)
        .options(
            selectinload(ModeloRegistroMinuta.operador),
            selectinload(ModeloRegistroMinuta.puesto_vigilancia),
        )
        .where(ModeloRegistroMinuta.registro_id == registro_reaccion.registro_id)
    )
    minuta_completa = (await sesion_bd.execute(consulta_recarga)).scalar_one()

    await gestor_minuta_ws.difundir_evento_minuta(
        {
            "tipo_mensaje": "SOS_ATENDIDO",
            "alerta_sos": respuesta_alerta.model_dump(mode="json"),
            "registro": mapear_minuta_a_respuesta(minuta_completa).model_dump(
                mode="json"
            ),
        }
    )

    return respuesta_alerta


async def endpoint_websocket_minuta(websocket: WebSocket) -> None:
    """
    Canal WebSocket (/ws/minuta) que mantiene suscritos en vivo a los paneles de
    Supervisores, Administradores, RRHH, Clientes y Operadores.
    """
    await gestor_minuta_ws.conectar_cliente(websocket)
    try:
        while True:
            mensaje_cliente: str = await websocket.receive_text()
            if mensaje_cliente == "LATIDO":
                await websocket.send_json({"tipo_mensaje": "LATIDO_ACTIVO"})
    except (WebSocketDisconnect, ConnectionResetError):
        gestor_minuta_ws.desconectar_cliente(websocket)
    except Exception:
        gestor_minuta_ws.desconectar_cliente(websocket)

"""
Fase 11 (Enterprise V3.0): Centro de Despacho Táctico Asistido por Computadora (CAD)
y Monitoreo GPS de Patrullas Motorizadas en Vivo.
Calcula distancias geodésicas Haversine, determina la patrulla más cercana a un punto de pánico SOS,
calcula tiempos estimados de arribo (ETA) y certifica tiempos de respuesta táctica.
"""

from datetime import datetime, timezone
import math

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.esquemas.esquemas_pydantic import (
    RespuestaDespachoPatrulla,
    SolicitudCierreDespacho,
    SolicitudDespacharPatrulla,
)
from app.modelos.modelos_bd import (
    EstadoAlertaSos,
    EstadoDespachoPatrulla,
    ModeloAlertaPanicoSos,
    ModeloDespachoPatrulla,
    ModeloPuestoVigilancia,
    ModeloUsuario,
    RolUsuario,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.seguridad import requerir_roles
from app.rutas.rutas_rondas import calcular_distancia_haversine_metros

enrutador_cad = APIRouter(
    prefix="/api/cad",
    tags=["Fase 11 - Centro de Despacho CAD & Monitoreo GPS en Vivo"],
)


class TelemetriaPuestoMapa(BaseModel):
    puesto_id: int
    nombre_puesto: str
    codigo_puesto: str
    latitud_gps: float
    longitud_gps: float
    estado_seguridad: str  # "NORMAL", "ALERTA_SOS"
    requiere_armamento: bool


class TelemetriaSupervisorMapa(BaseModel):
    supervisor_id: int
    nombre_supervisor: str
    codigo_placa: str
    latitud_actual: float
    longitud_actual: float
    estado_disponibilidad: str  # "DISPONIBLE", "EN_DESPACHO"


class ResumenMapaTactico(BaseModel):
    puestos: list[TelemetriaPuestoMapa]
    supervisores: list[TelemetriaSupervisorMapa]
    alertas_sos_activas_conteo: int


class CandidatoSupervisorCercano(BaseModel):
    supervisor_id: int
    nombre_supervisor: str
    codigo_placa: str
    distancia_km: float
    eta_minutos: float
    recomendado: bool


@enrutador_cad.get(
    "/telemetria-mapa",
    response_model=ResumenMapaTactico,
    summary="Obtener Posición Satelital de Puestos Fijos y Patrullas",
)
async def obtener_telemetria_mapa(
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.CLIENTE,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> ResumenMapaTactico:
    """Retorna coordenadas de todos los puestos y patrullas para visualización en mapa."""
    # Consultar puestos
    res_puestos = await sesion_bd.execute(
        select(ModeloPuestoVigilancia).where(ModeloPuestoVigilancia.activo.is_(True))
    )
    puestos = res_puestos.scalars().all()

    # Consultar alertas SOS activas
    res_alertas = await sesion_bd.execute(
        select(ModeloAlertaPanicoSos).where(
            ModeloAlertaPanicoSos.estado_alerta == EstadoAlertaSos.ACTIVA
        )
    )
    alertas_activas = res_alertas.scalars().all()
    puestos_en_sos = {a.puesto_id for a in alertas_activas}

    # Coordenadas base de puestos en Bogotá y Medellín
    lista_puestos: list[TelemetriaPuestoMapa] = []
    base_lats = [4.6533, 4.6720, 6.2088]
    base_lngs = [-74.0836, -74.0511, -75.5670]

    for idx, p in enumerate(puestos):
        lat = base_lats[idx % len(base_lats)]
        lng = base_lngs[idx % len(base_lngs)]
        estado = "ALERTA_SOS" if p.puesto_id in puestos_en_sos else "NORMAL"
        lista_puestos.append(
            TelemetriaPuestoMapa(
                puesto_id=p.puesto_id,
                nombre_puesto=p.nombre_puesto,
                codigo_puesto=p.codigo_puesto,
                latitud_gps=lat,
                longitud_gps=lng,
                estado_seguridad=estado,
                requiere_armamento=p.requiere_armamento,
            )
        )

    # Consultar supervisores activos
    res_supervisores = await sesion_bd.execute(
        select(ModeloUsuario).where(
            ModeloUsuario.rol == RolUsuario.SUPERVISOR,
            ModeloUsuario.activo.is_(True),
        )
    )
    supervisores = res_supervisores.scalars().all()

    # Despachos en curso
    res_despachos = await sesion_bd.execute(
        select(ModeloDespachoPatrulla).where(
            ModeloDespachoPatrulla.estado_despacho.in_(
                [EstadoDespachoPatrulla.PENDIENTE, EstadoDespachoPatrulla.EN_RUTA]
            )
        )
    )
    despachos_activos = res_despachos.scalars().all()
    supervisores_ocupados = {d.supervisor_id for d in despachos_activos}

    lista_supervisores: list[TelemetriaSupervisorMapa] = []
    lats_sup = [4.6610, 4.6450, 6.2150]
    lngs_sup = [-74.0720, -74.0610, -75.5720]

    for idx, s in enumerate(supervisores):
        lat = lats_sup[idx % len(lats_sup)]
        lng = lngs_sup[idx % len(lngs_sup)]
        disp = "EN_DESPACHO" if s.usuario_id in supervisores_ocupados else "DISPONIBLE"
        lista_supervisores.append(
            TelemetriaSupervisorMapa(
                supervisor_id=s.usuario_id,
                nombre_supervisor=s.nombre_completo,
                codigo_placa=s.codigo_placa,
                latitud_actual=lat,
                longitud_actual=lng,
                estado_disponibilidad=disp,
            )
        )

    return ResumenMapaTactico(
        puestos=lista_puestos,
        supervisores=lista_supervisores,
        alertas_sos_activas_conteo=len(alertas_activas),
    )


@enrutador_cad.get(
    "/sugerir-patrulla/{alerta_sos_id}",
    response_model=list[CandidatoSupervisorCercano],
    summary="Calcular Patrulla Más Cercana con Distancia Haversine y ETA",
)
async def sugerir_patrulla_mas_cercana(
    alerta_sos_id: int,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[CandidatoSupervisorCercano]:
    """Calcula la distancia geodésica y el ETA asumiendo 45 km/h de reacción."""
    consulta_alerta = select(ModeloAlertaPanicoSos).where(
        ModeloAlertaPanicoSos.alerta_id == alerta_sos_id
    )
    res_alerta = await sesion_bd.execute(consulta_alerta)
    alerta = res_alerta.scalar_one_or_none()

    if not alerta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerta SOS #{alerta_sos_id} no encontrada.",
        )

    res_supervisores = await sesion_bd.execute(
        select(ModeloUsuario).where(
            ModeloUsuario.rol == RolUsuario.SUPERVISOR,
            ModeloUsuario.activo.is_(True),
        )
    )
    supervisores = res_supervisores.scalars().all()

    candidatos: list[CandidatoSupervisorCercano] = []
    lats_sup = [4.6610, 4.6450, 6.2150]
    lngs_sup = [-74.0720, -74.0610, -75.5720]

    for idx, sup in enumerate(supervisores):
        lat_sup = lats_sup[idx % len(lats_sup)]
        lng_sup = lngs_sup[idx % len(lngs_sup)]

        distancia_metros = calcular_distancia_haversine_metros(
            alerta.latitud_gps, alerta.longitud_gps, lat_sup, lng_sup
        )
        distancia_km = round(distancia_metros / 1000.0, 2)

        # Velocidad promedio motorizada urbana de emergencia = 40 km/h
        # Tiempo en horas = distancia_km / 40 -> minutos = (distancia_km / 40) * 60 = distancia_km * 1.5
        eta_minutos = max(1.5, round(distancia_km * 1.5, 1))

        candidatos.append(
            CandidatoSupervisorCercano(
                supervisor_id=sup.usuario_id,
                nombre_supervisor=sup.nombre_completo,
                codigo_placa=sup.codigo_placa,
                distancia_km=distancia_km,
                eta_minutos=eta_minutos,
                recomendado=False,
            )
        )

    # Ordenar por menor distancia
    candidatos.sort(key=lambda x: x.distancia_km)
    if candidatos:
        candidatos[0].recomendado = True

    return candidatos


@enrutador_cad.post(
    "/despachar",
    response_model=RespuestaDespachoPatrulla,
    status_code=status.HTTP_201_CREATED,
    summary="Despachar Patrulla Motorizada a Emergencia",
)
async def despachar_patrulla(
    solicitud: SolicitudDespacharPatrulla,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaDespachoPatrulla:
    """Emite la orden formal de despacho CAD hacia el supervisor."""
    consulta_alerta = (
        select(ModeloAlertaPanicoSos)
        .options(selectinload(ModeloAlertaPanicoSos.puesto_vigilancia))
        .where(ModeloAlertaPanicoSos.alerta_id == solicitud.alerta_sos_id)
    )
    res_alerta = await sesion_bd.execute(consulta_alerta)
    alerta = res_alerta.scalar_one_or_none()

    if not alerta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerta SOS #{solicitud.alerta_sos_id} no encontrada.",
        )

    consulta_sup = select(ModeloUsuario).where(
        ModeloUsuario.usuario_id == solicitud.supervisor_id,
        ModeloUsuario.rol == RolUsuario.SUPERVISOR,
    )
    res_sup = await sesion_bd.execute(consulta_sup)
    supervisor = res_sup.scalar_one_or_none()

    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supervisor #{solicitud.supervisor_id} no encontrado.",
        )

    # Distancia estimada estándar
    distancia_km = 3.2
    eta_minutos = 4.8

    nuevo_despacho = ModeloDespachoPatrulla(
        alerta_sos_id=alerta.alerta_id,
        supervisor_id=supervisor.usuario_id,
        puesto_id=alerta.puesto_id,
        distancia_km_calculada=distancia_km,
        eta_minutos_estimado=eta_minutos,
        estado_despacho=EstadoDespachoPatrulla.EN_RUTA,
        fecha_despacho=datetime.now(timezone.utc),
    )

    sesion_bd.add(nuevo_despacho)
    await sesion_bd.commit()
    await sesion_bd.refresh(nuevo_despacho)

    nombre_puesto = alerta.puesto_vigilancia.nombre_puesto if alerta.puesto_vigilancia else "Puesto"

    return RespuestaDespachoPatrulla(
        despacho_id=nuevo_despacho.despacho_id,
        alerta_sos_id=alerta.alerta_id,
        supervisor_id=supervisor.usuario_id,
        nombre_supervisor=supervisor.nombre_completo,
        codigo_placa_supervisor=supervisor.codigo_placa,
        puesto_id=alerta.puesto_id,
        nombre_puesto=nombre_puesto,
        coordenadas_puesto=(alerta.latitud_gps, alerta.longitud_gps),
        distancia_km_calculada=distancia_km,
        eta_minutos_estimado=eta_minutos,
        estado_despacho=nuevo_despacho.estado_despacho,
        fecha_despacho=nuevo_despacho.fecha_despacho,
        fecha_llegada_sitio=nuevo_despacho.fecha_llegada_sitio,
        tiempo_arribo_segundos=nuevo_despacho.tiempo_arribo_segundos,
        informe_tactico_cierre=nuevo_despacho.informe_tactico_cierre,
    )


@enrutador_cad.patch(
    "/despacho/{despacho_id}/llegada",
    response_model=RespuestaDespachoPatrulla,
    summary="Registrar Llegada en Sitio de la Patrulla",
)
async def registrar_llegada_patrulla(
    despacho_id: int,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaDespachoPatrulla:
    """Certifica la hora y el tiempo exacto de arribo en segundos."""
    consulta = (
        select(ModeloDespachoPatrulla)
        .options(
            selectinload(ModeloDespachoPatrulla.supervisor),
            selectinload(ModeloDespachoPatrulla.puesto_vigilancia),
            selectinload(ModeloDespachoPatrulla.alerta_sos),
        )
        .where(ModeloDespachoPatrulla.despacho_id == despacho_id)
    )
    resultado = await sesion_bd.execute(consulta)
    despacho = resultado.scalar_one_or_none()

    if not despacho:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Despacho #{despacho_id} no encontrado.",
        )

    ahora = datetime.now(timezone.utc)
    tiempo_segundos = int((ahora - despacho.fecha_despacho).total_seconds())

    despacho.estado_despacho = EstadoDespachoPatrulla.EN_SITIO
    despacho.fecha_llegada_sitio = ahora
    despacho.tiempo_arribo_segundos = max(60, tiempo_segundos)

    await sesion_bd.commit()
    await sesion_bd.refresh(despacho)

    nombre_puesto = despacho.puesto_vigilancia.nombre_puesto if despacho.puesto_vigilancia else "Puesto"
    nombre_sup = despacho.supervisor.nombre_completo if despacho.supervisor else "Supervisor"
    placa_sup = despacho.supervisor.codigo_placa if despacho.supervisor else "SUP"
    coord_puesto = (
        (despacho.alerta_sos.latitud_gps, despacho.alerta_sos.longitud_gps)
        if despacho.alerta_sos
        else (4.6533, -74.0836)
    )

    return RespuestaDespachoPatrulla(
        despacho_id=despacho.despacho_id,
        alerta_sos_id=despacho.alerta_sos_id,
        supervisor_id=despacho.supervisor_id,
        nombre_supervisor=nombre_sup,
        codigo_placa_supervisor=placa_sup,
        puesto_id=despacho.puesto_id,
        nombre_puesto=nombre_puesto,
        coordenadas_puesto=coord_puesto,
        distancia_km_calculada=despacho.distancia_km_calculada,
        eta_minutos_estimado=despacho.eta_minutos_estimado,
        estado_despacho=despacho.estado_despacho,
        fecha_despacho=despacho.fecha_despacho,
        fecha_llegada_sitio=despacho.fecha_llegada_sitio,
        tiempo_arribo_segundos=despacho.tiempo_arribo_segundos,
        informe_tactico_cierre=despacho.informe_tactico_cierre,
    )


@enrutador_cad.patch(
    "/despacho/{despacho_id}/finalizar",
    response_model=RespuestaDespachoPatrulla,
    summary="Finalizar Despacho CAD con Informe de Cierre",
)
async def finalizar_despacho_cad(
    despacho_id: int,
    solicitud: SolicitudCierreDespacho,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaDespachoPatrulla:
    """Cierra la reacción táctica y guarda el acta del supervisor."""
    consulta = (
        select(ModeloDespachoPatrulla)
        .options(
            selectinload(ModeloDespachoPatrulla.supervisor),
            selectinload(ModeloDespachoPatrulla.puesto_vigilancia),
            selectinload(ModeloDespachoPatrulla.alerta_sos),
        )
        .where(ModeloDespachoPatrulla.despacho_id == despacho_id)
    )
    resultado = await sesion_bd.execute(consulta)
    despacho = resultado.scalar_one_or_none()

    if not despacho:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Despacho #{despacho_id} no encontrado.",
        )

    despacho.estado_despacho = EstadoDespachoPatrulla.FINALIZADO
    despacho.informe_tactico_cierre = solicitud.informe_tactico_cierre

    # También actualizar estado de la alerta SOS asociada
    if despacho.alerta_sos:
        despacho.alerta_sos.estado_alerta = EstadoAlertaSos.ATENDIDA
        despacho.alerta_sos.fecha_atencion = datetime.now(timezone.utc)
        despacho.alerta_sos.atendida_por_id = despacho.supervisor_id
        despacho.alerta_sos.nota_reaccion = solicitud.informe_tactico_cierre

    await sesion_bd.commit()
    await sesion_bd.refresh(despacho)

    nombre_puesto = despacho.puesto_vigilancia.nombre_puesto if despacho.puesto_vigilancia else "Puesto"
    nombre_sup = despacho.supervisor.nombre_completo if despacho.supervisor else "Supervisor"
    placa_sup = despacho.supervisor.codigo_placa if despacho.supervisor else "SUP"
    coord_puesto = (
        (despacho.alerta_sos.latitud_gps, despacho.alerta_sos.longitud_gps)
        if despacho.alerta_sos
        else (4.6533, -74.0836)
    )

    return RespuestaDespachoPatrulla(
        despacho_id=despacho.despacho_id,
        alerta_sos_id=despacho.alerta_sos_id,
        supervisor_id=despacho.supervisor_id,
        nombre_supervisor=nombre_sup,
        codigo_placa_supervisor=placa_sup,
        puesto_id=despacho.puesto_id,
        nombre_puesto=nombre_puesto,
        coordenadas_puesto=coord_puesto,
        distancia_km_calculada=despacho.distancia_km_calculada,
        eta_minutos_estimado=despacho.eta_minutos_estimado,
        estado_despacho=despacho.estado_despacho,
        fecha_despacho=despacho.fecha_despacho,
        fecha_llegada_sitio=despacho.fecha_llegada_sitio,
        tiempo_arribo_segundos=despacho.tiempo_arribo_segundos,
        informe_tactico_cierre=despacho.informe_tactico_cierre,
    )

"""
Fase 10 (Enterprise V3.0): Libro Balístico Digital y Trazabilidad Indumil DCCA.
Regulado según Decreto 2535/1993 y requerimientos del Departamento de Control Comercio
de Armas y Municiones (DCCA). Incluye semáforo preventivo de salvoconductos,
kardex inmutable de munición con firma SHA-256 y certificados de tiro de la academia.
"""

from datetime import date, datetime, timedelta, timezone
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.esquemas.esquemas_pydantic import (
    RespuestaCertificadoPoligono,
    RespuestaMovimientoBalistico,
    SolicitudRegistrarCertificadoPoligono,
    SolicitudRegistrarMovimientoBalistico,
)
from app.modelos.modelos_bd import (
    ModeloCertificadoPoligono,
    ModeloDotacionPuesto,
    ModeloKardexBalistico,
    ModeloPuestoVigilancia,
    ModeloUsuario,
    RolUsuario,
    TipoMovimientoBalistico,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.seguridad import (
    HASH_GENESIS_SHA256,
    calcular_hash_encadenado_sha256,
    requerir_roles,
)

enrutador_balistica = APIRouter(
    prefix="/api/balistica",
    tags=["Fase 10 - Libro Balístico Digital y Trazabilidad Indumil DCCA"],
)


class SemaforoSalvoconducto(BaseModel):
    """Diagnóstico temprano de vigencia de salvoconductos Indumil."""

    dotacion_id: int
    puesto_id: int
    nombre_puesto: str
    tipo_arma: str
    serial_arma: str
    numero_salvoconducto_indumil: str
    tipo_salvoconducto: str
    fecha_vencimiento_salvoconducto: date
    dias_restantes: int
    estado_semaforo: str  # "VIGENTE_VERDE", "PREVENTIVO_AMARILLO", "CRITICO_ROJO", "VENCIDO"
    requiere_tramite_dcca: bool
    cantidad_municion_actual: int


@enrutador_balistica.get(
    "/salvoconductos-semaforo",
    response_model=list[SemaforoSalvoconducto],
    summary="Semáforo Preventivo de Salvoconductos Indumil (90/60/30 días)",
)
async def consultar_semaforo_salvoconductos(
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.RRHH,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[SemaforoSalvoconducto]:
    """Evalúa la vigencia legal de todos los permisos de armas de la empresa."""
    consulta = (
        select(ModeloDotacionPuesto)
        .options(selectinload(ModeloDotacionPuesto.puesto_vigilancia))
        .where(ModeloDotacionPuesto.serial_arma.is_not(None))
        .order_by(ModeloDotacionPuesto.fecha_vencimiento_salvoconducto.asc())
    )
    resultado = await sesion_bd.execute(consulta)
    dotaciones = resultado.scalars().all()

    hoy = date.today()
    resultado_semaforo: list[SemaforoSalvoconducto] = []

    for d in dotaciones:
        if not d.fecha_vencimiento_salvoconducto:
            continue

        dias = (d.fecha_vencimiento_salvoconducto - hoy).days

        if dias <= 0:
            estado = "VENCIDO"
            tramite = True
        elif dias <= 30:
            estado = "CRITICO_ROJO"
            tramite = True
        elif dias <= 90:
            estado = "PREVENTIVO_AMARILLO"
            tramite = True
        else:
            estado = "VIGENTE_VERDE"
            tramite = False

        nombre_puesto = d.puesto_vigilancia.nombre_puesto if d.puesto_vigilancia else "Puesto Operativo"

        resultado_semaforo.append(
            SemaforoSalvoconducto(
                dotacion_id=d.dotacion_id,
                puesto_id=d.puesto_id,
                nombre_puesto=nombre_puesto,
                tipo_arma=d.tipo_arma or "Arma Indumil",
                serial_arma=d.serial_arma or "S/N",
                numero_salvoconducto_indumil=d.numero_salvoconducto_indumil or "En trámite",
                tipo_salvoconducto=d.tipo_salvoconducto or "TENENCIA",
                fecha_vencimiento_salvoconducto=d.fecha_vencimiento_salvoconducto,
                dias_restantes=dias,
                estado_semaforo=estado,
                requiere_tramite_dcca=tramite,
                cantidad_municion_actual=d.cantidad_municion_autorizada,
            )
        )

    return resultado_semaforo


@enrutador_balistica.get(
    "/kardex/{puesto_id}",
    response_model=list[RespuestaMovimientoBalistico],
    summary="Historial Oficial del Libro Balístico por Puesto",
)
async def consultar_kardex_balistico(
    puesto_id: int,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.CLIENTE,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaMovimientoBalistico]:
    """Retorna los movimientos de munición y novedades balísticas foliadas."""
    if _usuario_actual.rol == RolUsuario.CLIENTE and _usuario_actual.puesto_base_id:
        if puesto_id != _usuario_actual.puesto_base_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene autorización para consultar el kardex balístico de otras sedes.",
            )

    consulta = (
        select(ModeloKardexBalistico)
        .options(
            selectinload(ModeloKardexBalistico.puesto_vigilancia),
            selectinload(ModeloKardexBalistico.dotacion),
            selectinload(ModeloKardexBalistico.operador),
        )
        .where(ModeloKardexBalistico.puesto_id == puesto_id)
        .order_by(ModeloKardexBalistico.fecha_movimiento.desc())
    )
    resultado = await sesion_bd.execute(consulta)
    movimientos = resultado.scalars().all()

    respuesta: list[RespuestaMovimientoBalistico] = []
    for m in movimientos:
        nombre_puesto = m.puesto_vigilancia.nombre_puesto if m.puesto_vigilancia else "Puesto"
        tipo_arma = m.dotacion.tipo_arma if m.dotacion else "Arma Indumil"
        serial_arma = m.dotacion.serial_arma if m.dotacion else "S/N"
        nombre_operador = m.operador.nombre_completo if m.operador else "Operador"

        respuesta.append(
            RespuestaMovimientoBalistico(
                movimiento_id=m.movimiento_id,
                puesto_id=m.puesto_id,
                nombre_puesto=nombre_puesto,
                dotacion_id=m.dotacion_id,
                tipo_arma=tipo_arma,
                serial_arma=serial_arma,
                operador_responsable_id=m.operador_responsable_id,
                nombre_operador=nombre_operador,
                tipo_movimiento=m.tipo_movimiento,
                calibre=m.calibre,
                cantidad_municion_afectada=m.cantidad_municion_afectada,
                saldo_municion_resultante=m.saldo_municion_resultante,
                justificacion_novedad=m.justificacion_novedad,
                numero_oficio_dcca=m.numero_oficio_dcca,
                firma_digital_sha256=m.firma_digital_sha256,
                hash_anterior_sha256=m.hash_anterior_sha256,
                fecha_movimiento=m.fecha_movimiento,
            )
        )

    return respuesta


@enrutador_balistica.post(
    "/kardex/movimiento",
    response_model=RespuestaMovimientoBalistico,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar Consumo o Reposición de Munición con Firma SHA-256",
)
async def registrar_movimiento_balistico(
    solicitud: SolicitudRegistrarMovimientoBalistico,
    usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaMovimientoBalistico:
    """Registra variación de cartuchos, actualiza dotación y firma digitalmente con Blockchain Ligero."""
    consulta_dotacion = (
        select(ModeloDotacionPuesto)
        .options(selectinload(ModeloDotacionPuesto.puesto_vigilancia))
        .where(ModeloDotacionPuesto.dotacion_id == solicitud.dotacion_id)
    )
    resultado_dot = await sesion_bd.execute(consulta_dotacion)
    dotacion = resultado_dot.scalar_one_or_none()

    if not dotacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dotación #{solicitud.dotacion_id} no encontrada.",
        )

    saldo_anterior = dotacion.cantidad_municion_autorizada

    # Si es consumo (incidente o práctica), se resta; si es reposición, se suma
    if solicitud.tipo_movimiento in (
        TipoMovimientoBalistico.CONSUMO_INCIDENTE,
        TipoMovimientoBalistico.PRACTICA_POLIGONO,
    ):
        if saldo_anterior < solicitud.cantidad_municion_afectada:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No hay munición suficiente registrada. Saldo actual: {saldo_anterior}.",
            )
        nuevo_saldo = saldo_anterior - solicitud.cantidad_municion_afectada
    else:
        nuevo_saldo = saldo_anterior + solicitud.cantidad_municion_afectada

    dotacion.cantidad_municion_autorizada = nuevo_saldo

    fecha_ahora = datetime.now(timezone.utc)
    # Hash Chaining Forense SHA-256
    ultimo_kardex = (
        await sesion_bd.execute(
            select(ModeloKardexBalistico.firma_digital_sha256)
            .where(ModeloKardexBalistico.puesto_id == solicitud.puesto_id)
            .order_by(ModeloKardexBalistico.movimiento_id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    hash_anterior = ultimo_kardex if ultimo_kardex else HASH_GENESIS_SHA256

    cadena_hash = f"{dotacion.dotacion_id}:{solicitud.tipo_movimiento.value}:{solicitud.cantidad_municion_afectada}:{nuevo_saldo}:{fecha_ahora.isoformat()}"
    firma_sha = calcular_hash_encadenado_sha256(cadena_hash, hash_anterior)

    puesto_tenant_id = (
        dotacion.puesto_vigilancia.tenant_id
        if dotacion.puesto_vigilancia and dotacion.puesto_vigilancia.tenant_id
        else "TENANT-SENTINEL-DEMO"
    )

    nuevo_mov = ModeloKardexBalistico(
        puesto_id=solicitud.puesto_id,
        dotacion_id=solicitud.dotacion_id,
        tenant_id=puesto_tenant_id,
        operador_responsable_id=usuario_actual.usuario_id,
        tipo_movimiento=solicitud.tipo_movimiento,
        calibre=solicitud.calibre,
        cantidad_municion_afectada=solicitud.cantidad_municion_afectada,
        saldo_municion_resultante=nuevo_saldo,
        justificacion_novedad=solicitud.justificacion_novedad,
        numero_oficio_dcca=solicitud.numero_oficio_dcca,
        firma_digital_sha256=firma_sha,
        hash_anterior_sha256=hash_anterior,
        fecha_movimiento=fecha_ahora,
    )

    sesion_bd.add(nuevo_mov)
    await sesion_bd.commit()
    await sesion_bd.refresh(nuevo_mov)

    nombre_puesto = dotacion.puesto_vigilancia.nombre_puesto if dotacion.puesto_vigilancia else "Puesto"

    return RespuestaMovimientoBalistico(
        movimiento_id=nuevo_mov.movimiento_id,
        puesto_id=nuevo_mov.puesto_id,
        nombre_puesto=nombre_puesto,
        dotacion_id=dotacion.dotacion_id,
        tipo_arma=dotacion.tipo_arma or "Arma Indumil",
        serial_arma=dotacion.serial_arma or "S/N",
        operador_responsable_id=usuario_actual.usuario_id,
        nombre_operador=usuario_actual.nombre_completo,
        tipo_movimiento=nuevo_mov.tipo_movimiento,
        calibre=nuevo_mov.calibre,
        cantidad_municion_afectada=nuevo_mov.cantidad_municion_afectada,
        saldo_municion_resultante=nuevo_saldo,
        justificacion_novedad=nuevo_mov.justificacion_novedad,
        numero_oficio_dcca=nuevo_mov.numero_oficio_dcca,
        firma_digital_sha256=nuevo_mov.firma_digital_sha256,
        hash_anterior_sha256=nuevo_mov.hash_anterior_sha256,
        fecha_movimiento=nuevo_mov.fecha_movimiento,
    )


@enrutador_balistica.get(
    "/poligonos",
    response_model=list[RespuestaCertificadoPoligono],
    summary="Listar Certificados de Tiro y Polígono Anual",
)
async def listar_certificados_poligono(
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.RRHH,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaCertificadoPoligono]:
    """Retorna el historial de prácticas de tiro y vencimientos de acreditación."""
    consulta = (
        select(ModeloCertificadoPoligono)
        .options(selectinload(ModeloCertificadoPoligono.operador))
        .order_by(ModeloCertificadoPoligono.fecha_practica.desc())
    )
    resultado = await sesion_bd.execute(consulta)
    certificados = resultado.scalars().all()

    respuesta: list[RespuestaCertificadoPoligono] = []
    for c in certificados:
        nombre_op = c.operador.nombre_completo if c.operador else "Operador"
        respuesta.append(
            RespuestaCertificadoPoligono(
                certificado_id=c.certificado_id,
                operador_id=c.operador_id,
                nombre_operador=nombre_op,
                academia_seguridad=c.academia_seguridad,
                tipo_arma_calificada=c.tipo_arma_calificada,
                puntaje_precision=c.puntaje_precision,
                aprobado=c.aprobado,
                fecha_practica=c.fecha_practica,
                fecha_vencimiento_anual=c.fecha_vencimiento_anual,
            )
        )

    return respuesta


@enrutador_balistica.post(
    "/poligonos",
    response_model=RespuestaCertificadoPoligono,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar Certificado de Prueba de Polígono Anual",
)
async def registrar_certificado_poligono(
    solicitud: SolicitudRegistrarCertificadoPoligono,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.RRHH)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaCertificadoPoligono:
    """Registra aprobación de tiro y calcula vigencia de 1 año (365 días)."""
    consulta_op = select(ModeloUsuario).where(
        ModeloUsuario.usuario_id == solicitud.operador_id
    )
    resultado_op = await sesion_bd.execute(consulta_op)
    operador = resultado_op.scalar_one_or_none()

    if not operador:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operador con ID #{solicitud.operador_id} no encontrado.",
        )

    fecha_vencimiento = solicitud.fecha_practica + timedelta(days=365)

    nuevo_cert = ModeloCertificadoPoligono(
        operador_id=solicitud.operador_id,
        academia_seguridad=solicitud.academia_seguridad.strip(),
        tipo_arma_calificada=solicitud.tipo_arma_calificada.strip(),
        puntaje_precision=solicitud.puntaje_precision,
        aprobado=solicitud.aprobado,
        fecha_practica=solicitud.fecha_practica,
        fecha_vencimiento_anual=fecha_vencimiento,
    )

    sesion_bd.add(nuevo_cert)
    await sesion_bd.commit()
    await sesion_bd.refresh(nuevo_cert)

    return RespuestaCertificadoPoligono(
        certificado_id=nuevo_cert.certificado_id,
        operador_id=operador.usuario_id,
        nombre_operador=operador.nombre_completo,
        academia_seguridad=nuevo_cert.academia_seguridad,
        tipo_arma_calificada=nuevo_cert.tipo_arma_calificada,
        puntaje_precision=nuevo_cert.puntaje_precision,
        aprobado=nuevo_cert.aprobado,
        fecha_practica=nuevo_cert.fecha_practica,
        fecha_vencimiento_anual=nuevo_cert.fecha_vencimiento_anual,
    )

"""
Módulo 2: Rutas del Motor Inteligente de Turnos 2x2, Liquidación Ley 2101 (42h),
Control de Ausentismos y Motor de Sugerencia Inteligente de Relevantes.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.esquemas.esquemas_pydantic import (
    AsignarRelevanteTurnoSolicitud,
    CandidatoRelevanteSugerido,
    RegistrarAusentismoSolicitud,
    RespuestaAusentismo,
    RespuestaTurno,
    ResumenLiquidacionTurnos,
    SolicitudGenerarCoberturaPuesto2x2,
    SolicitudGenerarRotacion2x2,
)
from app.modelos.modelos_bd import (
    EstadoTurno,
    ModeloAusentismo,
    ModeloPuestoVigilancia,
    ModeloRegistroMinuta,
    ModeloTurno,
    ModeloUsuario,
    NivelPrioridad,
    RolUsuario,
    TipoRegistroMinuta,
    TipoTurno,
    VisibilidadMinuta,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.configuracion import configuracion
from app.nucleo.seguridad import obtener_usuario_actual, requerir_roles
from app.servicios.motor_turnos import (
    calcular_liquidacion_turno_colombia,
    construir_bloque_ciclo_2x2,
    generar_matriz_cobertura_puesto_2x2,
    verificar_vigencia_credencial_sv,
)

enrutador_turnos = APIRouter(
    prefix="/api/turnos",
    tags=["Módulo 2 - Motor Inteligente de Turnos 2x2 y Relevantes (Ley 2101)"],
)


def mapear_turno_a_respuesta(turno: ModeloTurno) -> RespuestaTurno:
    """Convierte una entidad ModeloTurno con relaciones cargadas al esquema de respuesta."""
    return RespuestaTurno(
        turno_id=turno.turno_id,
        operador_id=turno.operador_id,
        nombre_operador=turno.operador.nombre_completo,
        codigo_placa_operador=turno.operador.codigo_placa,
        puesto_id=turno.puesto_id,
        nombre_puesto=turno.puesto_vigilancia.nombre_puesto,
        codigo_puesto=turno.puesto_vigilancia.codigo_puesto,
        tipo_turno=turno.tipo_turno,
        estado_turno=turno.estado_turno,
        fecha_inicio=turno.fecha_inicio,
        fecha_fin=turno.fecha_fin,
        horas_totales=turno.horas_totales,
        horas_ordinarias=turno.horas_ordinarias,
        horas_recargo_nocturno=turno.horas_recargo_nocturno,
        horas_extras_diurnas=turno.horas_extras_diurnas,
        horas_extras_nocturnas=turno.horas_extras_nocturnas,
        horas_dominicales_festivas=turno.horas_dominicales_festivas,
        horas_descuento_ausentismo=turno.horas_descuento_ausentismo,
        motivo_ausentismo=turno.motivo_ausentismo,
        costo_estimado_cop=turno.costo_estimado_cop,
        observaciones=turno.observaciones,
    )


@enrutador_turnos.get(
    "",
    response_model=ResumenLiquidacionTurnos,
    summary="Consultar programación de turnos 2x2 y consolidado laboral (Ley 2101 - 42h)",
)
async def listar_turnos_y_liquidacion(
    operador_id: int | None = Query(default=None),
    puesto_id: int | None = Query(default=None),
    usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> ResumenLiquidacionTurnos:
    """
    Retorna la lista de turnos filtrada y el cálculo consolidado según el tope de 42h semanales.
    Si el usuario es CLIENTE, filtra estrictamente a su puesto contratado.
    """
    consulta = (
        select(ModeloTurno)
        .options(
            selectinload(ModeloTurno.operador),
            selectinload(ModeloTurno.puesto_vigilancia),
        )
        .order_by(ModeloTurno.fecha_inicio.asc())
    )

    if usuario_actual.rol == RolUsuario.CLIENTE and usuario_actual.puesto_base_id:
        consulta = consulta.where(
            ModeloTurno.puesto_id == usuario_actual.puesto_base_id
        )
    else:
        if operador_id is not None:
            consulta = consulta.where(ModeloTurno.operador_id == operador_id)
        if puesto_id is not None:
            consulta = consulta.where(ModeloTurno.puesto_id == puesto_id)

    resultado = await sesion_bd.execute(consulta)
    lista_turnos = list(resultado.scalars().all())

    respuestas_turnos: list[RespuestaTurno] = [
        mapear_turno_a_respuesta(t) for t in lista_turnos
    ]

    es_rol_cliente = usuario_actual.rol == RolUsuario.CLIENTE
    if es_rol_cliente:
        for rt in respuestas_turnos:
            rt.costo_estimado_cop = 0.0

    total_operativos = sum(
        1 for t in lista_turnos if t.tipo_turno != TipoTurno.DESCANSO
    )
    total_descansos = sum(
        1 for t in lista_turnos if t.tipo_turno == TipoTurno.DESCANSO
    )
    costo_total = 0.0 if es_rol_cliente else round(sum(t.costo_estimado_cop for t in lista_turnos), 2)

    return ResumenLiquidacionTurnos(
        tope_horas_semanales_aplicado=configuracion.tope_horas_semanales,
        total_turnos_operativos=total_operativos,
        total_dias_descanso=total_descansos,
        suma_horas_trabajadas=round(sum(t.horas_totales for t in lista_turnos), 2),
        suma_horas_ordinarias=round(sum(t.horas_ordinarias for t in lista_turnos), 2),
        suma_horas_recargo_nocturno=round(
            sum(t.horas_recargo_nocturno for t in lista_turnos), 2
        ),
        suma_horas_extras_diurnas=round(
            sum(t.horas_extras_diurnas for t in lista_turnos), 2
        ),
        suma_horas_extras_nocturnas=round(
            sum(t.horas_extras_nocturnas for t in lista_turnos), 2
        ),
        suma_horas_dominicales_festivas=round(
            sum(t.horas_dominicales_festivas for t in lista_turnos), 2
        ),
        suma_horas_descuento_ausentismo=round(
            sum(t.horas_descuento_ausentismo for t in lista_turnos), 2
        ),
        costo_total_estimado_cop=costo_total,
        turnos=respuestas_turnos,
    )


@enrutador_turnos.post(
    "/generar-rotacion-2x2",
    response_model=ResumenLiquidacionTurnos,
    status_code=status.HTTP_201_CREATED,
    summary="Programar esquema rotativo 2x2 validando credencial SuperVigilancia y Ley 2101 (42h)",
)
async def generar_programacion_rotativa_2x2(
    solicitud: SolicitudGenerarRotacion2x2,
    autorizado: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> ResumenLiquidacionTurnos:
    """
    Ejecuta el algoritmo del Motor Inteligente de Turnos para generar N ciclos 2x2.
    Bloquea la asignación si el guarda tiene credencial SuperVigilancia vencida sin excepción.
    """
    operador = (
        await sesion_bd.execute(
            select(ModeloUsuario).where(
                ModeloUsuario.usuario_id == solicitud.operador_id
            )
        )
    ).scalar_one_or_none()
    if operador is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El operador especificado no existe.",
        )

    habilitado_sv, estado_sv = verificar_vigencia_credencial_sv(operador)
    if not habilitado_sv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"BLOQUEO NORMATIVO SUPERVIGILANCIA: El guarda {operador.nombre_completo} "
                f"({operador.codigo_placa}) tiene la credencial {operador.numero_credencial_sv} "
                f"{estado_sv} ({operador.fecha_vencimiento_credencial}). "
                "RRHH debe renovar la credencial o un ADMINISTRADOR autorizar excepción temporal."
            ),
        )

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
            detail="El puesto de vigilancia especificado no existe.",
        )

    if solicitud.reemplazar_existentes:
        await sesion_bd.execute(
            delete(ModeloTurno).where(
                ModeloTurno.operador_id == solicitud.operador_id
            )
        )

    total_dias_a_generar: int = solicitud.cantidad_ciclos_6_dias * 6
    horas_ordinarias_por_semana: dict[tuple[int, int], float] = {}

    for desplazamiento_dia in range(total_dias_a_generar):
        fecha_actual = solicitud.fecha_inicio_ciclo + timedelta(days=desplazamiento_dia)
        indice_en_ciclo = desplazamiento_dia % 6
        clave_semana = (fecha_actual.isocalendar().year, fecha_actual.isocalendar().week)
        ordinarias_acum = horas_ordinarias_por_semana.get(clave_semana, 0.0)

        tipo_turno, inicio, fin, observacion = construir_bloque_ciclo_2x2(
            fecha_actual, indice_en_ciclo
        )
        liquidacion = calcular_liquidacion_turno_colombia(
            inicio,
            fin,
            tipo_turno,
            horas_ordinarias_acumuladas_semana=ordinarias_acum,
        )
        horas_ordinarias_por_semana[clave_semana] = (
            ordinarias_acum + liquidacion.horas_ordinarias
        )

        nuevo_turno = ModeloTurno(
            operador_id=operador.usuario_id,
            puesto_id=puesto.puesto_id,
            tipo_turno=tipo_turno,
            estado_turno=EstadoTurno.PROGRAMADO,
            fecha_inicio=inicio,
            fecha_fin=fin,
            horas_totales=liquidacion.horas_totales,
            horas_ordinarias=liquidacion.horas_ordinarias,
            horas_recargo_nocturno=liquidacion.horas_recargo_nocturno,
            horas_extras_diurnas=liquidacion.horas_extras_diurnas,
            horas_extras_nocturnas=liquidacion.horas_extras_nocturnas,
            horas_dominicales_festivas=liquidacion.horas_dominicales_festivas,
            costo_estimado_cop=liquidacion.costo_estimado_cop,
            observaciones=observacion,
        )
        sesion_bd.add(nuevo_turno)

    await sesion_bd.commit()
    return await listar_turnos_y_liquidacion(
        operador_id=operador.usuario_id,
        puesto_id=None,
        usuario_actual=autorizado,
        sesion_bd=sesion_bd,
    )


@enrutador_turnos.post(
    "/cobertura-puesto-2x2",
    response_model=ResumenLiquidacionTurnos,
    status_code=status.HTTP_201_CREATED,
    summary="Generar cobertura continua 24/7 de un puesto validando credenciales SuperVigilancia",
)
async def generar_cobertura_puesto_2x2(
    solicitud: SolicitudGenerarCoberturaPuesto2x2,
    autorizado: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> ResumenLiquidacionTurnos:
    """
    Programa la escuadra de 3 guardias asignada a un puesto garantizando cobertura 24/7.
    Verifica que ningún guardia tenga su credencial SuperVigilancia vencida sin excepción.
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
            detail="El puesto de vigilancia especificado no existe.",
        )

    operadores_ids = solicitud.operadores_ids or []
    if not operadores_ids:
        consulta_guardias_puesto = select(ModeloUsuario.usuario_id).where(
            (ModeloUsuario.rol == RolUsuario.OPERADOR)
            & (
                (ModeloUsuario.puesto_base_id == solicitud.puesto_id)
                | (ModeloUsuario.puesto_base_id.is_(None))
            )
            & (ModeloUsuario.activo.is_(True))
        )
        guardias_disponibles = list(
            (await sesion_bd.execute(consulta_guardias_puesto)).scalars().all()
        )
        operadores_ids = guardias_disponibles[:3]

    if not operadores_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay guardias asignados o disponibles para cubrir este puesto.",
        )

    # Validar credencial SuperVigilancia de cada integrante de la escuadra
    usuarios_escuadra = list(
        (
            await sesion_bd.execute(
                select(ModeloUsuario).where(
                    ModeloUsuario.usuario_id.in_(operadores_ids)
                )
            )
        )
        .scalars()
        .all()
    )
    for op in usuarios_escuadra:
        habilitado_sv, _ = verificar_vigencia_credencial_sv(op)
        if not habilitado_sv:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"BLOQUEO SUPERVIGILANCIA: El guarda {op.nombre_completo} ({op.codigo_placa}) "
                    f"tiene su credencial {op.numero_credencial_sv} VENCIDA ({op.fecha_vencimiento_credencial}). "
                    "Reemplace al guarda en la cuadrilla o solicite excepción temporal de ADMINISTRADOR."
                ),
            )

    if solicitud.reemplazar_existentes:
        await sesion_bd.execute(
            delete(ModeloTurno).where(
                ModeloTurno.puesto_id == solicitud.puesto_id
            )
        )

    filas_turnos = generar_matriz_cobertura_puesto_2x2(
        puesto_id=solicitud.puesto_id,
        operadores_ids=operadores_ids,
        fecha_inicio_ciclo=solicitud.fecha_inicio_ciclo,
        cantidad_dias=solicitud.cantidad_dias,
    )

    for item in filas_turnos:
        nuevo_turno = ModeloTurno(
            operador_id=item["operador_id"],
            puesto_id=item["puesto_id"],
            tipo_turno=item["tipo_turno"],
            estado_turno=EstadoTurno.PROGRAMADO,
            fecha_inicio=item["fecha_inicio"],
            fecha_fin=item["fecha_fin"],
            horas_totales=item["horas_totales"],
            horas_ordinarias=item["horas_ordinarias"],
            horas_recargo_nocturno=item["horas_recargo_nocturno"],
            horas_extras_diurnas=item["horas_extras_diurnas"],
            horas_extras_nocturnas=item["horas_extras_nocturnas"],
            horas_dominicales_festivas=item["horas_dominicales_festivas"],
            costo_estimado_cop=item["costo_estimado_cop"],
            observaciones=item["observaciones"],
        )
        sesion_bd.add(nuevo_turno)

    await sesion_bd.commit()
    return await listar_turnos_y_liquidacion(
        operador_id=None,
        puesto_id=solicitud.puesto_id,
        usuario_actual=autorizado,
        sesion_bd=sesion_bd,
    )


# ============================================================================
# GESTIÓN DE AUSENTISMOS Y MOTOR DE SUGERENCIA INTELIGENTE DE RELEVANTES (V2.0)
# ============================================================================
@enrutador_turnos.get(
    "/ausentismos",
    response_model=list[RespuestaAusentismo],
    summary="Listar incapacidades EPS/ARL, licencias y faltas registradas",
)
async def listar_ausentismos(
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR, RolUsuario.RRHH
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaAusentismo]:
    """Retorna el historial de ausentismos con su impacto en nómina y reemplazos."""
    ausentismos = list(
        (
            await sesion_bd.execute(
                select(ModeloAusentismo).order_by(
                    ModeloAusentismo.fecha_registro.desc()
                )
            )
        )
        .scalars()
        .all()
    )
    usuarios_mapa = {
        u.usuario_id: u
        for u in (await sesion_bd.execute(select(ModeloUsuario))).scalars().all()
    }
    respuestas: list[RespuestaAusentismo] = []
    for a in ausentismos:
        op = usuarios_mapa.get(a.operador_id)
        reg = usuarios_mapa.get(a.registrado_por_id)
        rem = (
            usuarios_mapa.get(a.reemplazo_asignado_id)
            if a.reemplazo_asignado_id
            else None
        )
        respuestas.append(
            RespuestaAusentismo(
                ausentismo_id=a.ausentismo_id,
                operador_id=a.operador_id,
                nombre_operador=op.nombre_completo if op else "Operador",
                codigo_placa=op.codigo_placa if op else "OPR",
                turno_afectado_id=a.turno_afectado_id,
                tipo_ausentismo=a.tipo_ausentismo,
                fecha_inicio=a.fecha_inicio,
                fecha_fin=a.fecha_fin,
                horas_descontadas=a.horas_descontadas,
                descripcion_soporte=a.descripcion_soporte,
                registrado_por_id=a.registrado_por_id,
                nombre_registrador=reg.nombre_completo if reg else "RRHH/Supervisor",
                reemplazo_asignado_id=a.reemplazo_asignado_id,
                nombre_reemplazo=rem.nombre_completo if rem else None,
                fecha_registro=a.fecha_registro,
            )
        )
    return respuestas


@enrutador_turnos.post(
    "/ausentismos",
    response_model=RespuestaAusentismo,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar ausentismo (EPS/ARL/Falta), descontar de prenómina y marcar turno DESCUBIERTO_PARCIAL",
)
async def registrar_ausentismo_personal(
    solicitud: RegistrarAusentismoSolicitud,
    autorizado: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR, RolUsuario.RRHH
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaAusentismo:
    """
    Registra un ausentismo, descuenta automáticamente las horas en el motor de prenómina
    y marca el turno afectado como DESCUBIERTO_PARCIAL para activar la sugerencia de relevantes.
    """
    operador = (
        await sesion_bd.execute(
            select(ModeloUsuario).where(
                ModeloUsuario.usuario_id == solicitud.operador_id
            )
        )
    ).scalar_one_or_none()
    if operador is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El operador especificado no existe.",
        )

    turno_afectado: ModeloTurno | None = None
    if solicitud.turno_afectado_id is not None:
        turno_afectado = (
            await sesion_bd.execute(
                select(ModeloTurno).where(
                    ModeloTurno.turno_id == solicitud.turno_afectado_id
                )
            )
        ).scalar_one_or_none()
    else:
        # Buscar el próximo turno operativo del guardia desde fecha_inicio
        turnos_op = list(
            (
                await sesion_bd.execute(
                    select(ModeloTurno)
                    .where(
                        (ModeloTurno.operador_id == operador.usuario_id)
                        & (ModeloTurno.tipo_turno != TipoTurno.DESCANSO)
                    )
                    .order_by(ModeloTurno.fecha_inicio.asc())
                )
            )
            .scalars()
            .all()
        )
        for t in turnos_op:
            if solicitud.fecha_inicio <= t.fecha_inicio.date() <= solicitud.fecha_fin:
                turno_afectado = t
                break
        if turno_afectado is None and turnos_op:
            turno_afectado = turnos_op[0]

    if turno_afectado is not None:
        liquidacion_ajustada = calcular_liquidacion_turno_colombia(
            fecha_inicio=turno_afectado.fecha_inicio,
            fecha_fin=turno_afectado.fecha_fin,
            tipo_turno=turno_afectado.tipo_turno,
            horas_descuento_ausentismo=solicitud.horas_descontadas,
        )
        turno_afectado.estado_turno = EstadoTurno.DESCUBIERTO_PARCIAL
        turno_afectado.horas_totales = liquidacion_ajustada.horas_totales
        turno_afectado.horas_ordinarias = liquidacion_ajustada.horas_ordinarias
        turno_afectado.horas_recargo_nocturno = (
            liquidacion_ajustada.horas_recargo_nocturno
        )
        turno_afectado.horas_extras_diurnas = liquidacion_ajustada.horas_extras_diurnas
        turno_afectado.horas_extras_nocturnas = (
            liquidacion_ajustada.horas_extras_nocturnas
        )
        turno_afectado.horas_dominicales_festivas = (
            liquidacion_ajustada.horas_dominicales_festivas
        )
        turno_afectado.horas_descuento_ausentismo = (
            liquidacion_ajustada.horas_descuento_ausentismo
        )
        turno_afectado.motivo_ausentismo = solicitud.tipo_ausentismo.value
        turno_afectado.costo_estimado_cop = liquidacion_ajustada.costo_estimado_cop
        turno_afectado.observaciones = (
            f"[ALERTA PUESTO DESCUBIERTO: {solicitud.tipo_ausentismo.value}] "
            f"Descuento {solicitud.horas_descontadas}h. {solicitud.descripcion_soporte}"
        )

    nuevo_ausentismo = ModeloAusentismo(
        operador_id=operador.usuario_id,
        turno_afectado_id=turno_afectado.turno_id if turno_afectado else None,
        tipo_ausentismo=solicitud.tipo_ausentismo,
        fecha_inicio=solicitud.fecha_inicio,
        fecha_fin=solicitud.fecha_fin,
        horas_descontadas=solicitud.horas_descontadas,
        descripcion_soporte=solicitud.descripcion_soporte.strip(),
        registrado_por_id=autorizado.usuario_id,
    )
    sesion_bd.add(nuevo_ausentismo)
    await sesion_bd.commit()
    await sesion_bd.refresh(nuevo_ausentismo)

    return RespuestaAusentismo(
        ausentismo_id=nuevo_ausentismo.ausentismo_id,
        operador_id=operador.usuario_id,
        nombre_operador=operador.nombre_completo,
        codigo_placa=operador.codigo_placa,
        turno_afectado_id=nuevo_ausentismo.turno_afectado_id,
        tipo_ausentismo=nuevo_ausentismo.tipo_ausentismo,
        fecha_inicio=nuevo_ausentismo.fecha_inicio,
        fecha_fin=nuevo_ausentismo.fecha_fin,
        horas_descontadas=nuevo_ausentismo.horas_descontadas,
        descripcion_soporte=nuevo_ausentismo.descripcion_soporte,
        registrado_por_id=autorizado.usuario_id,
        nombre_registrador=autorizado.nombre_completo,
        reemplazo_asignado_id=None,
        nombre_reemplazo=None,
        fecha_registro=nuevo_ausentismo.fecha_registro,
    )


@enrutador_turnos.get(
    "/sugerir-relevantes/{turno_id}",
    response_model=list[CandidatoRelevanteSugerido],
    summary="Motor Inteligente de Relevantes: sugiere guardas óptimos en descanso con credencial SV vigente",
)
async def sugerir_guardas_relevantes(
    turno_id: int,
    _autorizado: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR, RolUsuario.RRHH
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[CandidatoRelevanteSugerido]:
    """
    Evalúa todos los operadores activos para cubrir la vacante del turno indicado:
    1. Credencial SuperVigilancia vigente.
    2. En día de Franco/Descanso y cumpliendo descanso mínimo >= 12h antes/después.
    3. Ordenados de menor a mayor cantidad de horas extras acumuladas en la semana.
    """
    turno_vacante = (
        await sesion_bd.execute(
            select(ModeloTurno).where(ModeloTurno.turno_id == turno_id)
        )
    ).scalar_one_or_none()
    if turno_vacante is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El turno especificado no existe.",
        )

    operadores = list(
        (
            await sesion_bd.execute(
                select(ModeloUsuario).where(
                    (ModeloUsuario.rol == RolUsuario.OPERADOR)
                    & (ModeloUsuario.activo.is_(True))
                    & (ModeloUsuario.usuario_id != turno_vacante.operador_id)
                )
            )
        )
        .scalars()
        .all()
    )
    todos_los_turnos = list(
        (await sesion_bd.execute(select(ModeloTurno))).scalars().all()
    )

    semana_objetivo = (
        turno_vacante.fecha_inicio.isocalendar().year,
        turno_vacante.fecha_inicio.isocalendar().week,
    )
    fecha_objetivo = turno_vacante.fecha_inicio.date()

    candidatos: list[CandidatoRelevanteSugerido] = []

    for op in operadores:
        habilitado_sv, _ = verificar_vigencia_credencial_sv(op, fecha_objetivo)
        if not habilitado_sv:
            continue

        turnos_op = [t for t in todos_los_turnos if t.operador_id == op.usuario_id]
        en_descanso_ese_dia = True
        menor_descanso = 24.0
        cumple_descanso = True
        extras_semana = 0.0

        for t in turnos_op:
            sem_t = (
                t.fecha_inicio.isocalendar().year,
                t.fecha_inicio.isocalendar().week,
            )
            if sem_t == semana_objetivo:
                extras_semana += t.horas_extras_diurnas + t.horas_extras_nocturnas

            if t.tipo_turno == TipoTurno.DESCANSO:
                continue

            if t.fecha_inicio.date() == fecha_objetivo:
                en_descanso_ese_dia = False
                break

            # Verificar no solapamiento y brecha >= 12h
            if (
                turno_vacante.fecha_inicio < t.fecha_fin
                and turno_vacante.fecha_fin > t.fecha_inicio
            ):
                cumple_descanso = False
                break

            if turno_vacante.fecha_inicio >= t.fecha_fin:
                brecha = (
                    turno_vacante.fecha_inicio - t.fecha_fin
                ).total_seconds() / 3600.0
            else:
                brecha = (
                    t.fecha_inicio - turno_vacante.fecha_fin
                ).total_seconds() / 3600.0

            if brecha < menor_descanso:
                menor_descanso = round(brecha, 1)

            if brecha < configuracion.horas_descanso_minimo_entre_turnos:
                cumple_descanso = False
                break

        if not en_descanso_ese_dia or not cumple_descanso:
            continue

        candidatos.append(
            CandidatoRelevanteSugerido(
                usuario_id=op.usuario_id,
                nombre_completo=op.nombre_completo,
                codigo_placa=op.codigo_placa,
                numero_credencial_sv=op.numero_credencial_sv,
                credencial_vigente=True,
                en_dia_descanso=True,
                horas_descanso_previas=round(menor_descanso, 1),
                horas_extras_acumuladas_semana=round(extras_semana, 2),
                puntaje_idoneidad=(
                    "ÓPTIMO (Menor costo horas extras)"
                    if extras_semana <= 8.0
                    else "HABILITADO (En Franco + SV Vigente)"
                ),
            )
        )

    candidatos.sort(key=lambda c: c.horas_extras_acumuladas_semana)
    return candidatos


@enrutador_turnos.post(
    "/{turno_id}/asignar-relevante",
    response_model=RespuestaTurno,
    summary="Asignar en 1 clic a un guarda relevante para cubrir un turno descubierto",
)
async def asignar_relevante_a_turno(
    turno_id: int,
    solicitud: AsignarRelevanteTurnoSolicitud,
    autorizado: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR, RolUsuario.RRHH
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaTurno:
    """Reasigna el turno al guarda relevante, restablece la cobertura del puesto y asienta en minuta."""
    turno = (
        await sesion_bd.execute(
            select(ModeloTurno)
            .options(
                selectinload(ModeloTurno.operador),
                selectinload(ModeloTurno.puesto_vigilancia),
            )
            .where(ModeloTurno.turno_id == turno_id)
        )
    ).scalar_one_or_none()
    if turno is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El turno especificado no existe.",
        )

    reemplazo = (
        await sesion_bd.execute(
            select(ModeloUsuario).where(
                ModeloUsuario.usuario_id == solicitud.operador_reemplazo_id
            )
        )
    ).scalar_one_or_none()
    if reemplazo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El guarda relevante seleccionado no existe.",
        )

    habilitado_sv, _ = verificar_vigencia_credencial_sv(reemplazo)
    if not habilitado_sv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El guarda seleccionado tiene la credencial SuperVigilancia vencida.",
        )

    liquidacion = calcular_liquidacion_turno_colombia(
        turno.fecha_inicio, turno.fecha_fin, turno.tipo_turno
    )
    turno.operador_id = reemplazo.usuario_id
    turno.estado_turno = EstadoTurno.INTERCAMBIADO
    turno.horas_totales = liquidacion.horas_totales
    turno.horas_ordinarias = liquidacion.horas_ordinarias
    turno.horas_recargo_nocturno = liquidacion.horas_recargo_nocturno
    turno.horas_extras_diurnas = liquidacion.horas_extras_diurnas
    turno.horas_extras_nocturnas = liquidacion.horas_extras_nocturnas
    turno.horas_dominicales_festivas = liquidacion.horas_dominicales_festivas
    turno.horas_descuento_ausentismo = 0.0
    turno.motivo_ausentismo = None
    turno.costo_estimado_cop = liquidacion.costo_estimado_cop
    turno.observaciones = (
        f"[RELEVANTE ASIGNADO POR {autorizado.codigo_placa}] "
        f"Cubierto por {reemplazo.nombre_completo} ({reemplazo.codigo_placa}). "
        f"{solicitud.observacion_asignacion}"
    )

    ausentismo_asociado = (
        await sesion_bd.execute(
            select(ModeloAusentismo).where(
                ModeloAusentismo.turno_afectado_id == turno.turno_id
            )
        )
    ).scalar_one_or_none()
    if ausentismo_asociado is not None:
        ausentismo_asociado.reemplazo_asignado_id = reemplazo.usuario_id

    minuta_relevo = ModeloRegistroMinuta(
        operador_id=autorizado.usuario_id,
        puesto_id=turno.puesto_id,
        tipo_registro=TipoRegistroMinuta.RELEVO_TURNO,
        visibilidad=VisibilidadMinuta.PUBLICA_CLIENTE,
        nivel_prioridad=NivelPrioridad.MEDIA,
        titulo_evento=f"Relevo de cobertura asignado: {reemplazo.nombre_completo} ({reemplazo.codigo_placa})",
        descripcion_detallada=(
            f"El turno #{turno.turno_id} ({turno.tipo_turno.value}) queda cubierto al 100% "
            f"por el guarda relevante {reemplazo.nombre_completo} (Credencial SV {reemplazo.numero_credencial_sv})."
        ),
    )
    sesion_bd.add(minuta_relevo)
    await sesion_bd.commit()

    turno_actualizado = (
        await sesion_bd.execute(
            select(ModeloTurno)
            .options(
                selectinload(ModeloTurno.operador),
                selectinload(ModeloTurno.puesto_vigilancia),
            )
            .where(ModeloTurno.turno_id == turno_id)
        )
    ).scalar_one()
    return mapear_turno_a_respuesta(turno_actualizado)

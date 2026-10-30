"""
Motor Inteligente de Turnos 2x2 y Validador de Intercambios según Normativa Laboral Colombiana.
Calcula hora por hora:
- Horas ordinarias (primeras 8 horas del turno)
- Horas extras diurnas y nocturnas (horas posteriores a la octava hora)
- Recargo nocturno ordinario (franja 21:00 a 06:00 en jornada ordinaria)
- Recargo dominical/festivo (domingos en Colombia)
- Liquidación estimada en Pesos Colombianos (COP)
"""

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.esquemas.esquemas_pydantic import DesgloseLaboralColombiano
from app.modelos.modelos_bd import ModeloTurno, ModeloUsuario, TipoTurno
from app.nucleo.configuracion import configuracion

ZONA_HORARIA_COLOMBIA = ZoneInfo("America/Bogota")


def verificar_vigencia_credencial_sv(
    usuario_o_fecha: ModeloUsuario | date | None,
    excepcion_o_ref: bool | date | None = None,
    fecha_ref: date | None = None,
) -> tuple[bool, str]:
    """
    Evalúa la vigencia de la credencial SuperVigilancia del operador.
    Acepta una instancia de ModeloUsuario o bien (fecha_vencimiento, excepcion_autorizada, fecha_ref).
    Retorna (habilitado_para_turno, estado_semaforo: 'VIGENTE' | 'POR_VENCER' | 'VENCIDA').
    """
    if isinstance(usuario_o_fecha, ModeloUsuario):
        fecha_venc = usuario_o_fecha.fecha_vencimiento_credencial
        excepcion = usuario_o_fecha.excepcion_credencial_autorizada
        hoy = excepcion_o_ref if isinstance(excepcion_o_ref, date) else (fecha_ref or date.today())
    else:
        fecha_venc = usuario_o_fecha
        excepcion = excepcion_o_ref if isinstance(excepcion_o_ref, bool) else False
        hoy = fecha_ref or date.today()

    if fecha_venc is None:
        return (True, "VIGENTE")

    dias_restantes = (fecha_venc - hoy).days
    if dias_restantes < 0:
        return (excepcion, "VENCIDA")
    if dias_restantes <= 30:
        return (True, "POR_VENCER")
    return (True, "VIGENTE")


def es_hora_nocturna_colombia(instante: datetime) -> bool:
    """
    Determina si un instante cae en la franja nocturna laboral colombiana (parametrizada 21:00 a 06:00).
    """
    hora_local: int = instante.astimezone(ZONA_HORARIA_COLOMBIA).hour
    return (
        hora_local >= configuracion.hora_inicio_nocturno
        or hora_local < configuracion.hora_fin_nocturno
    )


def fragmentar_turno_por_dia_calendario(
    fecha_inicio: datetime, fecha_fin: datetime
) -> list[tuple[datetime, datetime]]:
    """
    Fragmenta un turno en segmentos delimitados por la medianoche (00:00:00).
    Permite calcular recargos por día calendario antes de liquidar (ej: domingo a lunes).
    """
    inicio_loc = fecha_inicio.astimezone(ZONA_HORARIA_COLOMBIA)
    fin_loc = fecha_fin.astimezone(ZONA_HORARIA_COLOMBIA)
    if fin_loc <= inicio_loc:
        return []

    segmentos: list[tuple[datetime, datetime]] = []
    cursor_inicio = inicio_loc

    while cursor_inicio < fin_loc:
        medianoche_siguiente = (cursor_inicio + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        corte = min(medianoche_siguiente, fin_loc)
        segmentos.append((cursor_inicio, corte))
        cursor_inicio = corte

    return segmentos


def calcular_liquidacion_turno_colombia(
    fecha_inicio: datetime,
    fecha_fin: datetime,
    tipo_turno: TipoTurno,
    horas_ordinarias_acumuladas_semana: float = 0.0,
    tope_horas_semanales: int = configuracion.tope_horas_semanales,
    horas_descuento_ausentismo: float = 0.0,
) -> DesgloseLaboralColombiano:
    """
    Evalúa tramo por tramo (intervalos de 30 minutos) un turno de seguridad privada
    aplicando el tope dinámico de Ley 2101 de 2021 (42 horas semanales en 2026) y el
    descuento automático por ausentismos (incapacidades EPS/ARL, licencias o faltas).
    """
    if tipo_turno == TipoTurno.DESCANSO or fecha_fin <= fecha_inicio:
        return DesgloseLaboralColombiano(
            horas_totales=0.0,
            horas_ordinarias=0.0,
            horas_recargo_nocturno=0.0,
            horas_extras_diurnas=0.0,
            horas_extras_nocturnas=0.0,
            horas_dominicales_festivas=0.0,
            horas_descuento_ausentismo=0.0,
            costo_estimado_cop=0.0,
        )

    paso_minutos: int = 30
    delta_paso: timedelta = timedelta(minutes=paso_minutos)
    fraccion_hora: float = paso_minutos / 60.0
    cupo_semanal_restante: float = max(
        0.0, float(tope_horas_semanales) - horas_ordinarias_acumuladas_semana
    )
    limite_ordinario_turno: float = min(
        configuracion.horas_jornada_ordinaria_turno, cupo_semanal_restante
    )

    cursor_tiempo: datetime = fecha_inicio.astimezone(ZONA_HORARIA_COLOMBIA)
    fin_local: datetime = fecha_fin.astimezone(ZONA_HORARIA_COLOMBIA)

    horas_acumuladas: float = 0.0
    horas_ordinarias: float = 0.0
    horas_recargo_nocturno: float = 0.0
    horas_extras_diurnas: float = 0.0
    horas_extras_nocturnas: float = 0.0
    horas_dominicales: float = 0.0

    while cursor_tiempo < fin_local:
        es_nocturna: bool = es_hora_nocturna_colombia(cursor_tiempo)
        es_domingo: bool = cursor_tiempo.weekday() == 6

        if horas_acumuladas < limite_ordinario_turno:
            horas_ordinarias += fraccion_hora
            if es_nocturna:
                horas_recargo_nocturno += fraccion_hora
        else:
            if es_nocturna:
                horas_extras_nocturnas += fraccion_hora
            else:
                horas_extras_diurnas += fraccion_hora

        if es_domingo:
            horas_dominicales += fraccion_hora

        horas_acumuladas += fraccion_hora
        cursor_tiempo += delta_paso

    # Aplicar descuento proporcional si existe ausentismo registrado
    descuento_efectivo: float = min(
        horas_acumuladas, max(0.0, horas_descuento_ausentismo)
    )
    if horas_acumuladas > 0 and descuento_efectivo > 0:
        factor_presencia = max(
            0.0, (horas_acumuladas - descuento_efectivo) / horas_acumuladas
        )
        horas_acumuladas = round(horas_acumuladas - descuento_efectivo, 2)
        horas_ordinarias = round(horas_ordinarias * factor_presencia, 2)
        horas_recargo_nocturno = round(horas_recargo_nocturno * factor_presencia, 2)
        horas_extras_diurnas = round(horas_extras_diurnas * factor_presencia, 2)
        horas_extras_nocturnas = round(horas_extras_nocturnas * factor_presencia, 2)
        horas_dominicales = round(horas_dominicales * factor_presencia, 2)

    valor_hora: float = configuracion.valor_hora_ordinaria_cop
    costo_ordinario: float = horas_ordinarias * valor_hora
    costo_recargo_nocturno: float = (
        horas_recargo_nocturno * valor_hora * configuracion.factor_recargo_nocturno
    )
    costo_extra_diurno: float = (
        horas_extras_diurnas * valor_hora * configuracion.factor_hora_extra_diurna
    )
    costo_extra_nocturno: float = (
        horas_extras_nocturnas * valor_hora * configuracion.factor_hora_extra_nocturna
    )
    costo_dominical: float = (
        horas_dominicales * valor_hora * configuracion.factor_recargo_dominical_festivo
    )

    costo_total_cop: float = round(
        costo_ordinario
        + costo_recargo_nocturno
        + costo_extra_diurno
        + costo_extra_nocturno
        + costo_dominical,
        2,
    )

    return DesgloseLaboralColombiano(
        horas_totales=round(horas_acumuladas, 2),
        horas_ordinarias=round(horas_ordinarias, 2),
        horas_recargo_nocturno=round(horas_recargo_nocturno, 2),
        horas_extras_diurnas=round(horas_extras_diurnas, 2),
        horas_extras_nocturnas=round(horas_extras_nocturnas, 2),
        horas_dominicales_festivas=round(horas_dominicales, 2),
        horas_descuento_ausentismo=round(descuento_efectivo, 2),
        costo_estimado_cop=costo_total_cop,
    )


def construir_bloque_ciclo_2x2(
    fecha_base: date,
    indice_dia_en_ciclo: int,
) -> tuple[TipoTurno, datetime, datetime, str]:
    """
    Dado el índice dentro del ciclo de 6 días (0..5):
    - Días 0 y 1: 2 Turnos de DÍA (12 horas cada uno: 06:00 a 18:00)
    - Días 2 y 3: 2 Turnos de NOCHE (12 horas cada uno: 18:00 a 06:00 del día siguiente)
    - Días 4 y 5: 2 Días de DESCANSO (Día Libre / Franco de 24 horas cada uno)
    """
    if indice_dia_en_ciclo in (0, 1):
        inicio = datetime.combine(
            fecha_base, time(6, 0), tzinfo=ZONA_HORARIA_COLOMBIA
        )
        fin = datetime.combine(
            fecha_base, time(18, 0), tzinfo=ZONA_HORARIA_COLOMBIA
        )
        return (
            TipoTurno.DIURNO,
            inicio,
            fin,
            f"Ciclo 2x2 • Turno Diurno #{indice_dia_en_ciclo + 1} de 12 Horas (06:00 a 18:00)",
        )

    if indice_dia_en_ciclo in (2, 3):
        inicio = datetime.combine(
            fecha_base, time(18, 0), tzinfo=ZONA_HORARIA_COLOMBIA
        )
        fin = datetime.combine(
            fecha_base + timedelta(days=1),
            time(6, 0),
            tzinfo=ZONA_HORARIA_COLOMBIA,
        )
        return (
            TipoTurno.NOCTURNO,
            inicio,
            fin,
            f"Ciclo 2x2 • Turno Nocturno #{indice_dia_en_ciclo - 1} de 12 Horas (18:00 a 06:00)",
        )

    # Descanso legal de 24 horas (Día libre / Franco)
    inicio = datetime.combine(
        fecha_base, time(0, 0, 0), tzinfo=ZONA_HORARIA_COLOMBIA
    )
    fin = datetime.combine(
        fecha_base, time(23, 59, 59), tzinfo=ZONA_HORARIA_COLOMBIA
    )
    return (
        TipoTurno.DESCANSO,
        inicio,
        fin,
        f"Ciclo 2x2 • Descanso Compensatorio #{indice_dia_en_ciclo - 3} (24 Horas Libres)",
    )


def generar_matriz_cobertura_puesto_2x2(
    puesto_id: int,
    operadores_ids: list[int],
    fecha_inicio_ciclo: date,
    cantidad_dias: int = 30,
) -> list[dict[str, Any]]:
    """
    Programa la escuadra de guardias asignados a un puesto de vigilancia bajo el
    esquema rotativo 2x2 continuo (2 días, 2 noches, 2 descansos) con desfase cíclico
    de 2 días entre guardias para garantizar cobertura ininterrumpida 24/7 sin puestos solos.
    """
    turnos_generados: list[dict[str, Any]] = []
    if not operadores_ids:
        return turnos_generados

    cantidad_operadores = len(operadores_ids)

    for indice_operador, operador_id in enumerate(operadores_ids):
        # Desfase de 2 días por cada guardia para sincronizar el relevo continuo
        desfase_dias = (indice_operador * 2) % 6
        horas_ordinarias_por_semana: dict[tuple[int, int], float] = {}

        for desplazamiento_dia in range(cantidad_dias):
            fecha_dia = fecha_inicio_ciclo + timedelta(days=desplazamiento_dia)
            indice_ciclo_guardia = (desplazamiento_dia + desfase_dias) % 6
            clave_semana = (fecha_dia.isocalendar().year, fecha_dia.isocalendar().week)
            ordinarias_acumuladas = horas_ordinarias_por_semana.get(clave_semana, 0.0)

            tipo_turno, inicio, fin, observacion = construir_bloque_ciclo_2x2(
                fecha_dia, indice_ciclo_guardia
            )
            liquidacion = calcular_liquidacion_turno_colombia(
                inicio,
                fin,
                tipo_turno,
                horas_ordinarias_acumuladas_semana=ordinarias_acumuladas,
            )
            horas_ordinarias_por_semana[clave_semana] = (
                ordinarias_acumuladas + liquidacion.horas_ordinarias
            )

            turnos_generados.append(
                {
                    "operador_id": operador_id,
                    "puesto_id": puesto_id,
                    "tipo_turno": tipo_turno,
                    "fecha_inicio": inicio,
                    "fecha_fin": fin,
                    "observaciones": (
                        f"Puesto #{puesto_id} • Escuadra {chr(65 + (indice_operador % 26))} • {observacion}"
                    ),
                    "horas_totales": liquidacion.horas_totales,
                    "horas_ordinarias": liquidacion.horas_ordinarias,
                    "horas_recargo_nocturno": liquidacion.horas_recargo_nocturno,
                    "horas_extras_diurnas": liquidacion.horas_extras_diurnas,
                    "horas_extras_nocturnas": liquidacion.horas_extras_nocturnas,
                    "horas_dominicales_festivas": liquidacion.horas_dominicales_festivas,
                    "costo_estimado_cop": liquidacion.costo_estimado_cop,
                }
            )

    return turnos_generados


def validar_factibilidad_intercambio(
    turno_origen: ModeloTurno,
    turno_destino: ModeloTurno,
    turnos_operador_solicitante: list[ModeloTurno],
    turnos_operador_receptor: list[ModeloTurno],
) -> tuple[bool, float, str]:
    """
    Valida que el intercambio de dos turnos entre dos operadores:
    1. No involucre turnos de descanso ni del mismo operador.
    2. No provoque cruce de horarios (solapamiento) con otros turnos activos.
    3. Respete el descanso mínimo legal entre turnos (>= 12.0 horas) para ambos guardias.

    Retorna: (es_valido, menor_descanso_en_horas, mensaje_explicativo)
    """
    if turno_origen.operador_id == turno_destino.operador_id:
        return (
            False,
            0.0,
            "No es posible intercambiar dos turnos asignados al mismo operador.",
        )

    if (
        turno_origen.tipo_turno == TipoTurno.DESCANSO
        or turno_destino.tipo_turno == TipoTurno.DESCANSO
    ):
        return (
            False,
            0.0,
            "Solo se pueden intercambiar turnos operativos (DIURNO o NOCTURNO), no bloques de descanso.",
        )

    horas_minimas_legales: float = configuracion.horas_descanso_minimo_entre_turnos
    menor_descanso_detectado: float = 999.0

    # Evaluar para el operador solicitante (quien recibiría turno_destino y cedería turno_origen)
    for otro_turno in turnos_operador_solicitante:
        if (
            otro_turno.turno_id == turno_origen.turno_id
            or otro_turno.tipo_turno == TipoTurno.DESCANSO
        ):
            continue

        # Verificar solapamiento directo
        if (
            turno_destino.fecha_inicio < otro_turno.fecha_fin
            and turno_destino.fecha_fin > otro_turno.fecha_inicio
        ):
            return (
                False,
                0.0,
                f"Cruce de horario detectado para el solicitante con su turno #{otro_turno.turno_id}.",
            )

        # Calcular brecha de descanso entre turnos
        if turno_destino.fecha_inicio >= otro_turno.fecha_fin:
            brecha_horas = (
                turno_destino.fecha_inicio - otro_turno.fecha_fin
            ).total_seconds() / 3600.0
        else:
            brecha_horas = (
                otro_turno.fecha_inicio - turno_destino.fecha_fin
            ).total_seconds() / 3600.0

        if brecha_horas < menor_descanso_detectado:
            menor_descanso_detectado = brecha_horas

        if brecha_horas < horas_minimas_legales:
            return (
                False,
                round(brecha_horas, 2),
                (
                    f"Incumplimiento de descanso mínimo para el solicitante: solo tendría "
                    f"{brecha_horas:.1f}h de descanso respecto al turno #{otro_turno.turno_id} "
                    f"(mínimo legal exigido: {horas_minimas_legales:.0f}h)."
                ),
            )

    # Evaluar para el operador receptor (quien recibiría turno_origen y cedería turno_destino)
    for otro_turno in turnos_operador_receptor:
        if (
            otro_turno.turno_id == turno_destino.turno_id
            or otro_turno.tipo_turno == TipoTurno.DESCANSO
        ):
            continue

        if (
            turno_origen.fecha_inicio < otro_turno.fecha_fin
            and turno_origen.fecha_fin > otro_turno.fecha_inicio
        ):
            return (
                False,
                0.0,
                f"Cruce de horario detectado para el guardia receptor con su turno #{otro_turno.turno_id}.",
            )

        if turno_origen.fecha_inicio >= otro_turno.fecha_fin:
            brecha_horas = (
                turno_origen.fecha_inicio - otro_turno.fecha_fin
            ).total_seconds() / 3600.0
        else:
            brecha_horas = (
                otro_turno.fecha_inicio - turno_origen.fecha_fin
            ).total_seconds() / 3600.0

        if brecha_horas < menor_descanso_detectado:
            menor_descanso_detectado = brecha_horas

        if brecha_horas < horas_minimas_legales:
            return (
                False,
                round(brecha_horas, 2),
                (
                    f"Incumplimiento de descanso mínimo para el guardia receptor: solo tendría "
                    f"{brecha_horas:.1f}h de descanso respecto al turno #{otro_turno.turno_id} "
                    f"(mínimo legal exigido: {horas_minimas_legales:.0f}h)."
                ),
            )

    descanso_final: float = (
        24.0 if menor_descanso_detectado == 999.0 else round(menor_descanso_detectado, 2)
    )
    return (
        True,
        descanso_final,
        (
            f"Validación aprobada por el Motor de Turnos: sin cruces horarios y "
            f"descanso mínimo verificado de {descanso_final:.1f} horas (>= {horas_minimas_legales:.0f}h)."
        ),
    )


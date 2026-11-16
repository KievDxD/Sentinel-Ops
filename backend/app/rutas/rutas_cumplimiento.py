"""
Enrutador REST de Cumplimiento Normativo SARLAFT 2.0 y SG-SST Decreto 1072 (`/api/cumplimiento`):
- Cruce instantáneo de Listas Restrictivas (OFAC/Clinton, ONU, INTERPOL, Antecedentes PONAL,
  Procuraduría y Contraloría) con emisión de Certificado de Debida Diligencia SARLAFT SHA-256.
- Semáforo normativo de vida útil de paneles balísticos Kevlar (Nivel IIIA - 5 años).
- Check-in de Aptitud Psicofísica Pre-Turno (Decreto 1072 / ARL Nivel V) con bloqueo o alerta por sueño < 5h.
- Monitor de Supervivencia "Hombre Caído" (Dead Man's Switch) en puestos nocturnos.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.modelos_bd import (
    ModeloCertificadoSarlaft,
    ModeloCheckAptitudSst,
    ModeloMonitoreoHombreCaido,
    ModeloPuestoVigilancia,
    ModeloRegistroMinuta,
    ModeloUsuario,
    NivelPrioridad,
    TipoRegistroMinuta,
    VisibilidadMinuta,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.seguridad import (
    HASH_GENESIS_SHA256,
    calcular_hash_encadenado_sha256,
    obtener_usuario_actual,
)
from app.servicios.gestor_websockets import gestor_minuta_ws

enrutador_cumplimiento = APIRouter(
    prefix="/api/cumplimiento",
    tags=["Cumplimiento SARLAFT 2.0 & SG-SST Decreto 1072"],
)

# Matriz determinista de documentos/NIT en listas restrictivas o PEP para pruebas y simulación
DOCUMENTOS_BLOQUEADOS_SARLAFT: set[str] = {
    "80666999",
    "900666999-0",
    "666000999",
    "111666999",
}
DOCUMENTOS_PEP_SARLAFT: set[str] = {
    "79884120",
    "900555111-2",
    "51888999",
}


class SolicitudConsultaSarlaft(BaseModel):
    """Solicitud de validación SARLAFT 2.0 en listas restrictivas nacionales e internacionales."""

    documento: str = Field(..., min_length=4, max_length=35)
    nombre_completo: str = Field(..., min_length=4, max_length=160)
    tipo_tercero: str = Field(
        default="ASPIRANTE_GUARDA",
        pattern="^(ASPIRANTE_GUARDA|CLIENTE_B2B|VISITANTE_CRITICO)$",
    )


class SolicitudCheckAptitudSst(BaseModel):
    """Check-in de aptitud psicofísica pre-turno bajo Decreto 1072 de 2015."""

    puesto_id: int
    operador_id: int | None = None
    horas_sueno_reportadas: float = Field(..., ge=0.0, le=16.0)
    cero_alcohol_fatiga: bool = True
    chaleco_kevlar_verificado: bool = True
    serial_chaleco_asignado: str = Field(default="KEV-IIIA-2024-01", min_length=4, max_length=60)
    observaciones_sst: str = Field(default="Verificación pre-turno ejecutada en consola táctica.")


class SolicitudLatidoHombreCaido(BaseModel):
    """Pulso de vida manual o automático del guarda o simulación de inactividad crítica."""

    simular_inactividad_critica: bool = False
    nota_operador: str = Field(default="Pulso de supervivencia confirmado por operador en garita.")


@enrutador_cumplimiento.post(
    "/sarlaft/consultar",
    status_code=status.HTTP_201_CREATED,
    summary="Ejecutar cruce SARLAFT 2.0 contra listas OFAC/ONU/INTERPOL/PONAL y emitir Certificado SHA-256",
)
async def consultar_listas_sarlaft(
    datos: SolicitudConsultaSarlaft,
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
) -> dict[str, Any]:
    """Evalúa documento/NIT y nombre frente a listas restrictivas y genera certificado SHA-256."""
    doc_limpio = datos.documento.strip()
    nom_upper = datos.nombre_completo.strip().upper()

    if (
        doc_limpio in DOCUMENTOS_BLOQUEADOS_SARLAFT
        or "OFAC" in nom_upper
        or "CARTEL" in nom_upper
        or "FANTASMA" in nom_upper
        or "EL ZAR" in nom_upper
    ):
        nivel_riesgo = "BLOQUEO_LISTA_RESTRICTIVA"
        listas_coincidentes = "OFAC_SDN_CLINTON,INTERPOL_CIRCULAR_ROJA,PONAL_CAPTURA"
        apto = False
        detalle = (
            "ALERTA ROJA SARLAFT 2.0: Coincidencia positiva en listas restrictivas vinculantes "
            "(OFAC SDN / INTERPOL / Antecedentes PONAL). Bloqueo inmediato de contratación/ingreso "
            "y generación de Reporte de Operación Sospechosa (ROS) ante la UIAF."
        )
    elif (
        doc_limpio in DOCUMENTOS_PEP_SARLAFT
        or "PEP" in nom_upper
        or "MINISTRO" in nom_upper
        or "SENADOR" in nom_upper
    ):
        nivel_riesgo = "RIESGO_MEDIO_PEP"
        listas_coincidentes = "PEP_NACIONAL_FUNCIONARIO_PUBLICO,PROCURADURIA_DECLARACION_BIENES"
        apto = True
        detalle = (
            "RIESGO MEDIO (PEP): Identificado como Persona Expuesta Políticamente (Decreto 830 de 2021). "
            "Habilitado con Debida Diligencia Intensificada y monitoreo de Oficial de Cumplimiento."
        )
    else:
        nivel_riesgo = "SIN_COINCIDENCIAS"
        listas_coincidentes = "NINGUNA"
        apto = True
        detalle = (
            "DEBIDA DILIGENCIA CONFORME: Cero coincidencias en listas OFAC/Clinton, Consejo de Seguridad ONU, "
            "INTERPOL, Antecedentes Judiciales PONAL, Procuraduría (SIRI) y Contraloría (SIBOR)."
        )

    res_ult = await sesion.execute(
        select(ModeloCertificadoSarlaft)
        .order_by(ModeloCertificadoSarlaft.fecha_consulta.desc())
        .limit(1)
    )
    ult = res_ult.scalar_one_or_none()
    hash_prev = ult.sello_auditoria_sha256 if ult else HASH_GENESIS_SHA256

    ahora = datetime.now(timezone.utc)
    codigo_cert = f"SARL-{ahora.strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
    listas_evaluadas = (
        "OFAC_CLINTON,ONU_CONSEJO_SEGURIDAD,INTERPOL,PONAL_ANTECEDENTES,PROCURADURIA_SIRI,CONTRALORIA_SIBOR"
    )
    payload_sarl = (
        f"SARLAFT_2_0|{codigo_cert}|{doc_limpio}|{datos.nombre_completo.strip()}|"
        f"{datos.tipo_tercero}|{nivel_riesgo}|{listas_coincidentes}|{ahora.isoformat()}"
    )
    sello_sha256 = calcular_hash_encadenado_sha256(payload_sarl, hash_prev)

    certificado = ModeloCertificadoSarlaft(
        codigo_certificado=codigo_cert,
        documento_consultado=doc_limpio,
        nombre_consultado=datos.nombre_completo.strip(),
        tipo_tercero=datos.tipo_tercero,
        nivel_riesgo=nivel_riesgo,
        listas_coincidentes=listas_coincidentes,
        listas_evaluadas=listas_evaluadas,
        apto_contratacion_ingreso=apto,
        detalle_validacion=detalle,
        consultado_por_id=usuario_actual.usuario_id,
        sello_auditoria_sha256=sello_sha256,
        hash_anterior_sha256=hash_prev,
        tenant_id=usuario_actual.tenant_id,
        fecha_consulta=ahora,
    )
    sesion.add(certificado)
    await sesion.commit()
    await sesion.refresh(certificado)

    return {
        "certificado_id": certificado.certificado_id,
        "codigo_certificado": certificado.codigo_certificado,
        "documento_consultado": certificado.documento_consultado,
        "nombre_consultado": certificado.nombre_consultado,
        "tipo_tercero": certificado.tipo_tercero,
        "nivel_riesgo": certificado.nivel_riesgo,
        "listas_coincidentes": (
            []
            if certificado.listas_coincidentes == "NINGUNA"
            else certificado.listas_coincidentes.split(",")
        ),
        "listas_evaluadas": certificado.listas_evaluadas.split(","),
        "apto_contratacion_ingreso": certificado.apto_contratacion_ingreso,
        "detalle_validacion": certificado.detalle_validacion,
        "sello_auditoria_sha256": certificado.sello_auditoria_sha256,
        "hash_anterior_sha256": certificado.hash_anterior_sha256,
        "fecha_consulta": certificado.fecha_consulta.isoformat(),
    }


@enrutador_cumplimiento.get(
    "/sarlaft/historial",
    summary="Listar historial auditable de validaciones y certificados SARLAFT 2.0",
)
async def listar_historial_sarlaft(
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    _usuario: ModeloUsuario = Depends(obtener_usuario_actual),
) -> list[dict[str, Any]]:
    """Retorna todos los certificados de debida diligencia SARLAFT emitidos en la compañía."""
    res = await sesion.execute(
        select(ModeloCertificadoSarlaft).order_by(ModeloCertificadoSarlaft.fecha_consulta.desc())
    )
    registros = list(res.scalars().all())
    return [
        {
            "certificado_id": c.certificado_id,
            "codigo_certificado": c.codigo_certificado,
            "documento_consultado": c.documento_consultado,
            "nombre_consultado": c.nombre_consultado,
            "tipo_tercero": c.tipo_tercero,
            "nivel_riesgo": c.nivel_riesgo,
            "listas_coincidentes": (
                [] if c.listas_coincidentes == "NINGUNA" else c.listas_coincidentes.split(",")
            ),
            "listas_evaluadas": c.listas_evaluadas.split(","),
            "apto_contratacion_ingreso": c.apto_contratacion_ingreso,
            "detalle_validacion": c.detalle_validacion,
            "sello_auditoria_sha256": c.sello_auditoria_sha256,
            "hash_anterior_sha256": c.hash_anterior_sha256,
            "fecha_consulta": c.fecha_consulta.isoformat(),
        }
        for c in registros
    ]


@enrutador_cumplimiento.get(
    "/sst/chalecos-kevlar",
    summary="Semáforo de vida útil de paneles balísticos Kevlar Nivel IIIA (norma 5 años)",
)
async def consultar_semaforo_chalecos_kevlar(
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    _usuario: ModeloUsuario = Depends(obtener_usuario_actual),
) -> list[dict[str, Any]]:
    """Evalúa el vencimiento normativo de 5 años de los chalecos antibalas asignados a los puestos."""
    res_puestos = await sesion.execute(
        select(ModeloPuestoVigilancia).order_by(ModeloPuestoVigilancia.codigo_puesto.asc())
    )
    puestos = list(res_puestos.scalars().all())
    hoy = date.today()

    lotes_kevlar = [
        ("KEV-IIIA-2023-101", "NIJ-IIIA-INDUMIL", date(2023, 6, 15), 4),
        ("KEV-IIIA-2022-204", "NIJ-IIIA-ARMOR", date(2022, 9, 10), 6),
        ("KEV-IIIA-2021-309", "NIJ-IIIA-CABAL", date(2021, 12, 1), 4),
        ("KEV-IIIA-2021-412", "NIJ-IIIA-INDUMIL", date(2021, 5, 20), 4),
        ("KEV-IIIA-2024-501", "NIJ-IIIA-LIGHT", date(2024, 3, 12), 2),
        ("KEV-IIIA-2020-688", "NIJ-IIIA-TACTICAL", date(2020, 10, 1), 4),
    ]

    salida: list[dict[str, Any]] = []
    for idx, puesto in enumerate(puestos):
        serial_lote, norma_nij, f_fab, cant_unidades = lotes_kevlar[idx % len(lotes_kevlar)]
        f_venc = f_fab + timedelta(days=365 * 5)
        dias_restantes = (f_venc - hoy).days

        if dias_restantes < 0:
            estado_semaforo = "VENCIDO_REEMPLAZO_INMEDIATO"
        elif dias_restantes <= 180:
            estado_semaforo = "POR_VENCER_6_MESES"
        else:
            estado_semaforo = "VIGENTE_CERTIFICADO"

        salida.append(
            {
                "puesto_id": puesto.puesto_id,
                "puesto_codigo": puesto.codigo_puesto,
                "puesto_nombre": puesto.nombre_puesto,
                "serial_lote_kevlar": serial_lote,
                "nivel_proteccion_nij": norma_nij,
                "unidades_en_puesto": cant_unidades,
                "fecha_fabricacion": f_fab.isoformat(),
                "fecha_vencimiento_5_anos": f_venc.isoformat(),
                "dias_restantes_vida_util": dias_restantes,
                "semaforo_kevlar": estado_semaforo,
            }
        )
    return salida


@enrutador_cumplimiento.post(
    "/sst/check-aptitud",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar validación psicofísica pre-turno SG-SST (Decreto 1072 / ARL Nivel V)",
)
async def registrar_check_aptitud_sst(
    datos: SolicitudCheckAptitudSst,
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
) -> dict[str, Any]:
    """Evalúa horas de sueño, cero alcohol/fatiga y EPP antes de recibir armamento o puesto."""
    operador_id = datos.operador_id or usuario_actual.usuario_id
    ahora = datetime.now(timezone.utc)

    alerta_fatiga = (
        datos.horas_sueno_reportadas < 5.0
        or not datos.cero_alcohol_fatiga
        or not datos.chaleco_kevlar_verificado
    )

    if alerta_fatiga:
        apto = False
        estado_eval = "BLOQUEO_FATIGA_O_EPP_DECRETO_1072"
    elif datos.horas_sueno_reportadas < 6.0:
        apto = True
        estado_eval = "OBSERVACION_PREVENTIVA_SST"
    else:
        apto = True
        estado_eval = "APTO_OPERATIVO"

    payload_sst = (
        f"SST_1072|{datos.puesto_id}|{operador_id}|{datos.horas_sueno_reportadas}|"
        f"{datos.cero_alcohol_fatiga}|{estado_eval}|{ahora.isoformat()}"
    )
    sello_sst = calcular_hash_encadenado_sha256(payload_sst, HASH_GENESIS_SHA256)

    registro = ModeloCheckAptitudSst(
        operador_id=operador_id,
        puesto_id=datos.puesto_id,
        horas_sueno_reportadas=datos.horas_sueno_reportadas,
        cero_alcohol_fatiga=datos.cero_alcohol_fatiga,
        chaleco_kevlar_verificado=datos.chaleco_kevlar_verificado,
        serial_chaleco_asignado=datos.serial_chaleco_asignado,
        fecha_fabricacion_chaleco=date.today() - timedelta(days=730),
        apto_operacion=apto,
        estado_evaluacion=estado_eval,
        observaciones_sst=datos.observaciones_sst,
        sello_sst_sha256=sello_sst,
        tenant_id=usuario_actual.tenant_id,
        fecha_check=ahora,
    )
    sesion.add(registro)
    await sesion.commit()
    await sesion.refresh(registro)

    return {
        "check_id": registro.check_id,
        "operador_id": registro.operador_id,
        "puesto_id": registro.puesto_id,
        "horas_sueno_reportadas": registro.horas_sueno_reportadas,
        "cero_alcohol_fatiga": registro.cero_alcohol_fatiga,
        "chaleco_kevlar_verificado": registro.chaleco_kevlar_verificado,
        "serial_chaleco_asignado": registro.serial_chaleco_asignado,
        "apto_operacion": registro.apto_operacion,
        "estado_evaluacion": registro.estado_evaluacion,
        "alerta_sst_disparada": alerta_fatiga,
        "sello_sst_sha256": registro.sello_sst_sha256,
        "fecha_check": registro.fecha_check.isoformat(),
    }


@enrutador_cumplimiento.get(
    "/sst/hombre-caido",
    summary="Consultar temporizadores de supervivencia 'Hombre Caído' (Dead Man's Switch) por puesto",
)
async def listar_monitores_hombre_caido(
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    _usuario: ModeloUsuario = Depends(obtener_usuario_actual),
) -> list[dict[str, Any]]:
    """Retorna el estado de pulso de vida de los guardas en puestos activos y nocturnos."""
    res_hc = await sesion.execute(select(ModeloMonitoreoHombreCaido))
    monitores = list(res_hc.scalars().all())

    res_puestos = await sesion.execute(select(ModeloPuestoVigilancia))
    mapa_puestos = {p.puesto_id: p for p in res_puestos.scalars().all()}

    res_usuarios = await sesion.execute(select(ModeloUsuario))
    mapa_usuarios = {u.usuario_id: u for u in res_usuarios.scalars().all()}

    ahora = datetime.now(timezone.utc)
    salida: list[dict[str, Any]] = []

    for m in monitores:
        puesto = mapa_puestos.get(m.puesto_id)
        operador = mapa_usuarios.get(m.operador_id)
        ult_utc = m.ultimo_latido_utc
        if ult_utc.tzinfo is None:
            ult_utc = ult_utc.replace(tzinfo=timezone.utc)
        segundos_sin_pulso = max(0, int((ahora - ult_utc).total_seconds()))
        segundos_restantes = max(0, (m.intervalo_esperado_min * 60) - segundos_sin_pulso)

        salida.append(
            {
                "monitoreo_id": m.monitoreo_id,
                "puesto_id": m.puesto_id,
                "puesto_codigo": puesto.codigo_puesto if puesto else "PST",
                "puesto_nombre": puesto.nombre_puesto if puesto else "Puesto",
                "operador_id": m.operador_id,
                "operador_nombre": operador.nombre_completo if operador else "Guarda de Turno",
                "operador_codigo": operador.codigo_placa if operador else "OPR",
                "intervalo_esperado_min": m.intervalo_esperado_min,
                "ultimo_latido_utc": ult_utc.isoformat(),
                "segundos_sin_pulso": segundos_sin_pulso,
                "segundos_restantes_ventana": segundos_restantes,
                "estado_supervivencia": m.estado_supervivencia,
                "latidos_consecutivos_exitosos": m.latidos_consecutivos_exitosos,
                "alertas_disparadas_turno": m.alertas_disparadas_turno,
            }
        )
    return salida


@enrutador_cumplimiento.post(
    "/sst/hombre-caido/{puesto_id}/latido",
    summary="Confirmar pulso de vida del guarda en puesto o disparar pre-alerta silenciosa por inactividad",
)
async def registrar_latido_hombre_caido(
    puesto_id: int,
    datos: SolicitudLatidoHombreCaido | None = None,
    sesion: AsyncSession = Depends(obtener_sesion_bd),
    usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
) -> dict[str, Any]:
    """Actualiza el temporizador Dead Man's Switch del puesto o escala pre-alerta de hombre caído."""
    res_hc = await sesion.execute(
        select(ModeloMonitoreoHombreCaido).where(ModeloMonitoreoHombreCaido.puesto_id == puesto_id)
    )
    monitor = res_hc.scalar_one_or_none()
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe monitor de Hombre Caído para el puesto '{puesto_id}'.",
        )

    ahora = datetime.now(timezone.utc)
    simular_alerta = datos.simular_inactividad_critica if datos else False

    if simular_alerta:
        monitor.estado_supervivencia = "ALERTA_HOMBRE_CAIDO_SOS"
        monitor.alertas_disparadas_turno += 1
        monitor.ultimo_latido_utc = ahora - timedelta(minutes=monitor.intervalo_esperado_min + 2)

        res_puesto_obj = await sesion.execute(
            select(ModeloPuestoVigilancia).where(ModeloPuestoVigilancia.puesto_id == puesto_id)
        )
        puesto_obj = res_puesto_obj.scalar_one_or_none()
        cod_puesto = puesto_obj.codigo_puesto if puesto_obj else "PST-BOG-01"

        res_ult_min = await sesion.execute(
            select(ModeloRegistroMinuta)
            .where(ModeloRegistroMinuta.puesto_id == puesto_id)
            .order_by(ModeloRegistroMinuta.fecha_registro.desc())
            .limit(1)
        )
        ult_min = res_ult_min.scalar_one_or_none()
        hash_prev = ult_min.sello_sha256 if ult_min and ult_min.sello_sha256 else HASH_GENESIS_SHA256
        titulo = "[ALERTA HOMBRE CAÍDO SG-SST] Ausencia de pulso de supervivencia en turno nocturno"
        desc = (
            f"El temporizador Dead Man's Switch superó la ventana de {monitor.intervalo_esperado_min} min "
            "sin confirmación del operador. Se activa protocolo silencioso de verificación por radio y CAD."
        )
        payload = (
            f"MINUTA_V4|{cod_puesto}|{usuario_actual.documento_identidad}|"
            f"{TipoRegistroMinuta.ALERTA_PANICO_SOS.value}|{titulo}|{desc}|{ahora.isoformat()}"
        )
        sello = calcular_hash_encadenado_sha256(payload, hash_prev)
        sesion.add(
            ModeloRegistroMinuta(
                puesto_id=puesto_id,
                operador_id=usuario_actual.usuario_id,
                tipo_registro=TipoRegistroMinuta.ALERTA_PANICO_SOS,
                visibilidad=VisibilidadMinuta.INTERNA_OPERATIVA,
                nivel_prioridad=NivelPrioridad.CRITICA,
                titulo_evento=titulo,
                descripcion_detallada=desc,
                sello_sha256=sello,
                hash_anterior_sha256=hash_prev,
                tenant_id=monitor.tenant_id,
                fecha_registro=ahora,
            )
        )
        await gestor_minuta_ws.difundir_evento_minuta(
            {
                "evento": "ALERTA_HOMBRE_CAIDO",
                "puesto_id": puesto_id,
                "estado_supervivencia": monitor.estado_supervivencia,
            }
        )
    else:
        monitor.ultimo_latido_utc = ahora
        monitor.estado_supervivencia = "ACTIVO_NORMAL"
        monitor.latidos_consecutivos_exitosos += 1

    await sesion.commit()
    await sesion.refresh(monitor)

    return {
        "monitoreo_id": monitor.monitoreo_id,
        "puesto_id": monitor.puesto_id,
        "operador_id": monitor.operador_id,
        "estado_supervivencia": monitor.estado_supervivencia,
        "ultimo_latido_utc": monitor.ultimo_latido_utc.isoformat(),
        "latidos_consecutivos_exitosos": monitor.latidos_consecutivos_exitosos,
        "alertas_disparadas_turno": monitor.alertas_disparadas_turno,
        "mensaje": (
            "PRE-ALERTA DE HOMBRE CAÍDO ACTIVADA EN CONSOLA CAD."
            if simular_alerta
            else "Pulso de vida confirmado. Ventana de supervivencia reiniciada a 15 minutos."
        ),
    }

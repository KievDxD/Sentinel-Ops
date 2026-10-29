"""
Fase 9 (Enterprise V3.0): Módulo de Control de Acceso en Garita y Decodificación PDF417 de Cédulas.
Permite lectura de código de barras 2D, control peatonal y vehicular, y alerta de listas restrictivas.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.esquemas.esquemas_pydantic import (
    RespuestaAccesoGarita,
    RespuestaCedulaColombiana,
    RespuestaEscanearPlaca,
    SolicitudDecodificarCedula,
    SolicitudEscanearPlaca,
    SolicitudRegistrarAccesoGarita,
)
from app.modelos.modelos_bd import (
    EstadoAccesoGarita,
    ModeloPuestoVigilancia,
    ModeloRegistroAccesoGarita,
    ModeloUsuario,
    RolUsuario,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.seguridad import requerir_roles
from app.servicios.decodificador_cedula import decodificar_trama_pdf417_colombia

enrutador_acceso = APIRouter(
    prefix="/api/acceso",
    tags=["Fase 9 - Control de Acceso Garita & Escáner Cédulas PDF417"],
)


@enrutador_acceso.post(
    "/decodificar-cedula",
    response_model=RespuestaCedulaColombiana,
    summary="Decodificar Código de Barras PDF417 de Cédula de Ciudadanía",
)
async def decodificar_cedula_endpoint(
    solicitud: SolicitudDecodificarCedula,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.RRHH,
            RolUsuario.OPERADOR,
        )
    ),
) -> RespuestaCedulaColombiana:
    """Extrae automáticamente cédula, nombres, apellidos, RH y fecha de nacimiento."""
    datos = decodificar_trama_pdf417_colombia(solicitud.trama_cruda)
    return RespuestaCedulaColombiana(
        documento_identidad=datos.documento_identidad,
        primer_apellido=datos.primer_apellido,
        segundo_apellido=datos.segundo_apellido,
        primer_nombre=datos.primer_nombre,
        segundo_nombre=datos.segundo_nombre,
        nombre_completo=datos.nombre_completo,
        sexo=datos.sexo,
        fecha_nacimiento=datos.fecha_nacimiento,
        grupo_sanguineo_rh=datos.grupo_sanguineo_rh,
        es_valido=datos.es_valido,
        mensaje_validacion=datos.mensaje_validacion,
    )


@enrutador_acceso.post(
    "/escanear-placa",
    response_model=RespuestaEscanearPlaca,
    summary="Reconocimiento y Normalización OCR de Placas Vehiculares (LPR)",
)
async def escanear_placa_vehicular(
    solicitud: SolicitudEscanearPlaca,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.OPERADOR,
        )
    ),
) -> RespuestaEscanearPlaca:
    """Valida y normaliza la placa colombiana capturada por cámara o digitación."""
    import re

    limpia = re.sub(r"[^A-Za-z0-9]", "", solicitud.texto_placa).upper()

    # Patrón 1: Automóvil particular / público (3 letras + 3 números, ej: ABC123)
    if re.match(r"^[A-Z]{3}\d{3}$", limpia):
        normalizada = f"{limpia[:3]}-{limpia[3:]}"
        return RespuestaEscanearPlaca(
            placa_normalizada=normalizada,
            tipo_vehiculo="AUTOMOVIL_PARTICULAR",
            es_valida=True,
            mensaje=f"Placa de automóvil colombiana válida: {normalizada}",
        )

    # Patrón 2: Motocicleta (3 letras + 2 números + 1 letra, ej: ABC12D)
    if re.match(r"^[A-Z]{3}\d{2}[A-Z]$", limpia):
        normalizada = f"{limpia[:3]}-{limpia[3:]}"
        return RespuestaEscanearPlaca(
            placa_normalizada=normalizada,
            tipo_vehiculo="MOTOCICLETA",
            es_valida=True,
            mensaje=f"Placa de motocicleta colombiana válida: {normalizada}",
        )

    # Si contiene al menos 5 o 6 caracteres alfanuméricos, devolver normalizada como genérica
    if len(limpia) >= 5:
        return RespuestaEscanearPlaca(
            placa_normalizada=limpia,
            tipo_vehiculo="VEHICULO_ESPECIAL",
            es_valida=True,
            mensaje=f"Matrícula identificada: {limpia}",
        )

    return RespuestaEscanearPlaca(
        placa_normalizada=limpia,
        tipo_vehiculo="DESCONOCIDO",
        es_valida=False,
        mensaje="Formato de placa no reconocido para Colombia.",
    )


@enrutador_acceso.post(
    "/ingreso",
    response_model=RespuestaAccesoGarita,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar Ingreso en Garita",
)
async def registrar_ingreso_garita(
    solicitud: SolicitudRegistrarAccesoGarita,
    usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.OPERADOR,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaAccesoGarita:
    """Registra la entrada peatonal o vehicular en garita."""
    consulta_puesto = select(ModeloPuestoVigilancia).where(
        ModeloPuestoVigilancia.puesto_id == solicitud.puesto_id
    )
    resultado_puesto = await sesion_bd.execute(consulta_puesto)
    puesto = resultado_puesto.scalar_one_or_none()
    if not puesto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Puesto de vigilancia #{solicitud.puesto_id} no encontrado.",
        )

    # Verificar si el visitante ya está adentro sin registrar salida
    consulta_activo = select(ModeloRegistroAccesoGarita).where(
        ModeloRegistroAccesoGarita.puesto_id == solicitud.puesto_id,
        ModeloRegistroAccesoGarita.documento_identidad == solicitud.documento_identidad,
        ModeloRegistroAccesoGarita.estado_acceso == EstadoAccesoGarita.DENTRO,
    )
    resultado_activo = await sesion_bd.execute(consulta_activo)
    if resultado_activo.scalar_one_or_none():
        # Ya tiene un ingreso abierto en este puesto
        pass

    nuevo_acceso = ModeloRegistroAccesoGarita(
        puesto_id=solicitud.puesto_id,
        operador_id=usuario_actual.usuario_id,
        tipo_acceso=solicitud.tipo_acceso,
        documento_identidad=solicitud.documento_identidad.strip(),
        nombres=solicitud.nombres.strip(),
        apellidos=solicitud.apellidos.strip(),
        tipo_sangre_rh=solicitud.tipo_sangre_rh,
        placa_vehiculo=solicitud.placa_vehiculo.upper() if solicitud.placa_vehiculo else None,
        empresa_o_destino=solicitud.empresa_o_destino.strip(),
        motivo_ingreso=solicitud.motivo_ingreso.strip(),
        es_sospechoso_alerta=False,
        estado_acceso=EstadoAccesoGarita.DENTRO,
        fecha_ingreso=datetime.now(timezone.utc),
        observaciones=solicitud.observaciones,
    )

    sesion_bd.add(nuevo_acceso)
    await sesion_bd.commit()
    await sesion_bd.refresh(nuevo_acceso)

    return RespuestaAccesoGarita(
        acceso_id=nuevo_acceso.acceso_id,
        puesto_id=nuevo_acceso.puesto_id,
        nombre_puesto=puesto.nombre_puesto,
        operador_id=nuevo_acceso.operador_id,
        nombre_operador=usuario_actual.nombre_completo,
        tipo_acceso=nuevo_acceso.tipo_acceso,
        documento_identidad=nuevo_acceso.documento_identidad,
        nombres=nuevo_acceso.nombres,
        apellidos=nuevo_acceso.apellidos,
        nombre_completo=f"{nuevo_acceso.nombres} {nuevo_acceso.apellidos}",
        tipo_sangre_rh=nuevo_acceso.tipo_sangre_rh,
        placa_vehiculo=nuevo_acceso.placa_vehiculo,
        empresa_o_destino=nuevo_acceso.empresa_o_destino,
        motivo_ingreso=nuevo_acceso.motivo_ingreso,
        es_sospechoso_alerta=nuevo_acceso.es_sospechoso_alerta,
        estado_acceso=nuevo_acceso.estado_acceso,
        fecha_ingreso=nuevo_acceso.fecha_ingreso,
        fecha_salida=nuevo_acceso.fecha_salida,
        observaciones=nuevo_acceso.observaciones,
    )


@enrutador_acceso.patch(
    "/{acceso_id}/salida",
    response_model=RespuestaAccesoGarita,
    summary="Registrar Salida de Garita",
)
async def registrar_salida_garita(
    acceso_id: int,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.OPERADOR,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaAccesoGarita:
    """Registra la hora de egreso de un visitante o vehículo."""
    consulta = (
        select(ModeloRegistroAccesoGarita)
        .options(
            selectinload(ModeloRegistroAccesoGarita.puesto_vigilancia),
            selectinload(ModeloRegistroAccesoGarita.operador),
        )
        .where(ModeloRegistroAccesoGarita.acceso_id == acceso_id)
    )
    resultado = await sesion_bd.execute(consulta)
    acceso = resultado.scalar_one_or_none()

    if not acceso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registro de acceso #{acceso_id} no encontrado.",
        )

    if acceso.estado_acceso == EstadoAccesoGarita.SALIO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La salida ya había sido registrada previamente.",
        )

    acceso.estado_acceso = EstadoAccesoGarita.SALIO
    acceso.fecha_salida = datetime.now(timezone.utc)
    await sesion_bd.commit()
    await sesion_bd.refresh(acceso)

    nombre_puesto = acceso.puesto_vigilancia.nombre_puesto if acceso.puesto_vigilancia else "Puesto General"
    nombre_operador = acceso.operador.nombre_completo if acceso.operador else "Operador Garita"

    return RespuestaAccesoGarita(
        acceso_id=acceso.acceso_id,
        puesto_id=acceso.puesto_id,
        nombre_puesto=nombre_puesto,
        operador_id=acceso.operador_id,
        nombre_operador=nombre_operador,
        tipo_acceso=acceso.tipo_acceso,
        documento_identidad=acceso.documento_identidad,
        nombres=acceso.nombres,
        apellidos=acceso.apellidos,
        nombre_completo=f"{acceso.nombres} {acceso.apellidos}",
        tipo_sangre_rh=acceso.tipo_sangre_rh,
        placa_vehiculo=acceso.placa_vehiculo,
        empresa_o_destino=acceso.empresa_o_destino,
        motivo_ingreso=acceso.motivo_ingreso,
        es_sospechoso_alerta=acceso.es_sospechoso_alerta,
        estado_acceso=acceso.estado_acceso,
        fecha_ingreso=acceso.fecha_ingreso,
        fecha_salida=acceso.fecha_salida,
        observaciones=acceso.observaciones,
    )


@enrutador_acceso.get(
    "/puesto/{puesto_id}/activos",
    response_model=list[RespuestaAccesoGarita],
    summary="Listar Visitantes/Vehículos Actualmente en Instalaciones",
)
async def listar_activos_en_puesto(
    puesto_id: int,
    _usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.OPERADOR,
            RolUsuario.CLIENTE,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaAccesoGarita]:
    """Retorna personas y vehículos con estado DENTRO."""
    consulta = (
        select(ModeloRegistroAccesoGarita)
        .options(
            selectinload(ModeloRegistroAccesoGarita.puesto_vigilancia),
            selectinload(ModeloRegistroAccesoGarita.operador),
        )
        .where(
            ModeloRegistroAccesoGarita.puesto_id == puesto_id,
            ModeloRegistroAccesoGarita.estado_acceso == EstadoAccesoGarita.DENTRO,
        )
        .order_by(ModeloRegistroAccesoGarita.fecha_ingreso.desc())
    )
    resultado = await sesion_bd.execute(consulta)
    accesos = resultado.scalars().all()

    respuesta: list[RespuestaAccesoGarita] = []
    for a in accesos:
        nombre_puesto = a.puesto_vigilancia.nombre_puesto if a.puesto_vigilancia else "Puesto"
        nombre_operador = a.operador.nombre_completo if a.operador else "Operador"
        respuesta.append(
            RespuestaAccesoGarita(
                acceso_id=a.acceso_id,
                puesto_id=a.puesto_id,
                nombre_puesto=nombre_puesto,
                operador_id=a.operador_id,
                nombre_operador=nombre_operador,
                tipo_acceso=a.tipo_acceso,
                documento_identidad=a.documento_identidad,
                nombres=a.nombres,
                apellidos=a.apellidos,
                nombre_completo=f"{a.nombres} {a.apellidos}",
                tipo_sangre_rh=a.tipo_sangre_rh,
                placa_vehiculo=a.placa_vehiculo,
                empresa_o_destino=a.empresa_o_destino,
                motivo_ingreso=a.motivo_ingreso,
                es_sospechoso_alerta=a.es_sospechoso_alerta,
                estado_acceso=a.estado_acceso,
                fecha_ingreso=a.fecha_ingreso,
                fecha_salida=a.fecha_salida,
                observaciones=a.observaciones,
            )
        )
    return respuesta


@enrutador_acceso.get(
    "/historial",
    response_model=list[RespuestaAccesoGarita],
    summary="Consultar Historial General de Accesos",
)
async def consultar_historial_accesos(
    puesto_id: int | None = None,
    limite: int = 50,
    usuario_actual: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR,
            RolUsuario.SUPERVISOR,
            RolUsuario.OPERADOR,
            RolUsuario.CLIENTE,
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaAccesoGarita]:
    """Retorna los últimos registros de acceso para auditoría."""
    consulta = (
        select(ModeloRegistroAccesoGarita)
        .options(
            selectinload(ModeloRegistroAccesoGarita.puesto_vigilancia),
            selectinload(ModeloRegistroAccesoGarita.operador),
        )
        .order_by(ModeloRegistroAccesoGarita.fecha_ingreso.desc())
        .limit(limite)
    )

    if puesto_id:
        consulta = consulta.where(ModeloRegistroAccesoGarita.puesto_id == puesto_id)

    resultado = await sesion_bd.execute(consulta)
    accesos = resultado.scalars().all()

    respuesta: list[RespuestaAccesoGarita] = []
    for a in accesos:
        nombre_puesto = a.puesto_vigilancia.nombre_puesto if a.puesto_vigilancia else "Puesto"
        nombre_operador = a.operador.nombre_completo if a.operador else "Operador"
        respuesta.append(
            RespuestaAccesoGarita(
                acceso_id=a.acceso_id,
                puesto_id=a.puesto_id,
                nombre_puesto=nombre_puesto,
                operador_id=a.operador_id,
                nombre_operador=nombre_operador,
                tipo_acceso=a.tipo_acceso,
                documento_identidad=a.documento_identidad,
                nombres=a.nombres,
                apellidos=a.apellidos,
                nombre_completo=f"{a.nombres} {a.apellidos}",
                tipo_sangre_rh=a.tipo_sangre_rh,
                placa_vehiculo=a.placa_vehiculo,
                empresa_o_destino=a.empresa_o_destino,
                motivo_ingreso=a.motivo_ingreso,
                es_sospechoso_alerta=a.es_sospechoso_alerta,
                estado_acceso=a.estado_acceso,
                fecha_ingreso=a.fecha_ingreso,
                fecha_salida=a.fecha_salida,
                observaciones=a.observaciones,
            )
        )
    return respuesta

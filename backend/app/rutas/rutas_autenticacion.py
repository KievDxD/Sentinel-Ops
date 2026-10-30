"""
Módulo 1: Rutas de Autenticación JWT, Control de Roles (RBAC), Usuarios y Puestos.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.esquemas.esquemas_pydantic import (
    ActualizarCredencialUsuarioSolicitud,
    AsignarPuestoUsuarioSolicitud,
    CrearPuestoVigilanciaSolicitud,
    CrearUsuarioSolicitud,
    RegistroUsuarioRealSolicitud,
    RespuestaImportacionUsuariosCsv,
    RespuestaPuestoVigilancia,
    RespuestaTokensAutenticacion,
    RespuestaUsuario,
    SolicitudImportarUsuariosCsv,
    SolicitudInicioSesion,
    SolicitudRefrescarToken,
)
from app.modelos.modelos_bd import (
    ModeloPuestoVigilancia,
    ModeloUsuario,
    NivelCursoVigilancia,
    RolUsuario,
)
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.seguridad import (
    crear_token_acceso,
    crear_token_refresco,
    decodificar_token_jwt,
    encriptar_contrasena,
    obtener_usuario_actual,
    requerir_roles,
    verificar_contrasena,
)

enrutador_autenticacion = APIRouter(
    prefix="/api/autenticacion",
    tags=["Módulo 1 - Autenticación y RBAC"],
)

enrutador_organizacion = APIRouter(
    prefix="/api/organizacion",
    tags=["Módulo 1 - Personal y Puestos de Vigilancia"],
)


@enrutador_autenticacion.post(
    "/iniciar-sesion",
    response_model=RespuestaTokensAutenticacion,
    summary="Autenticar usuario y emitir tokens JWT (Access y Refresh)",
)
async def iniciar_sesion(
    solicitud: SolicitudInicioSesion,
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaTokensAutenticacion:
    """Verifica credenciales y retorna los tokens JWT junto con el perfil del usuario."""
    consulta = select(ModeloUsuario).where(
        ModeloUsuario.correo_electronico == solicitud.correo_electronico.lower()
    )
    resultado = await sesion_bd.execute(consulta)
    usuario: ModeloUsuario | None = resultado.scalar_one_or_none()

    if usuario is None or not verificar_contrasena(
        solicitud.contrasena, usuario.contrasena_encriptada
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos.",
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta operativa se encuentra suspendida.",
        )

    token_acceso = crear_token_acceso(
        usuario_id=usuario.usuario_id,
        correo_electronico=usuario.correo_electronico,
        rol=usuario.rol,
    )
    token_refresco = crear_token_refresco(
        usuario_id=usuario.usuario_id,
        correo_electronico=usuario.correo_electronico,
        rol=usuario.rol,
    )

    return RespuestaTokensAutenticacion(
        token_acceso=token_acceso,
        token_refresco=token_refresco,
        usuario=RespuestaUsuario.model_validate(usuario),
    )


@enrutador_autenticacion.post(
    "/registro",
    response_model=RespuestaTokensAutenticacion,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un usuario o guardia real en la plataforma y emitir tokens",
)
async def registrar_usuario_real(
    solicitud: RegistroUsuarioRealSolicitud,
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaTokensAutenticacion:
    """
    Permite dar de alta a cualquier guardia, supervisor o administrador real,
    verificando la no-duplicidad de cédula o correo electrónico.
    """
    consulta_duplicado = select(ModeloUsuario).where(
        (ModeloUsuario.correo_electronico == solicitud.correo_electronico.lower().strip())
        | (ModeloUsuario.documento_identidad == solicitud.documento_identidad.strip())
        | (ModeloUsuario.codigo_placa == solicitud.codigo_placa.upper().strip())
    )
    existente = (await sesion_bd.execute(consulta_duplicado)).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Ya existe un integrante con ese documento de identidad, "
                "correo electrónico o código de placa en el sistema."
            ),
        )

    if solicitud.puesto_base_id is not None:
        puesto_existe = (
            await sesion_bd.execute(
                select(ModeloPuestoVigilancia).where(
                    ModeloPuestoVigilancia.puesto_id == solicitud.puesto_base_id
                )
            )
        ).scalar_one_or_none()
        if puesto_existe is None:
            solicitud.puesto_base_id = None

    nuevo_usuario = ModeloUsuario(
        documento_identidad=solicitud.documento_identidad.strip(),
        nombre_completo=solicitud.nombre_completo.strip(),
        correo_electronico=solicitud.correo_electronico.lower().strip(),
        telefono=solicitud.telefono.strip(),
        contrasena_encriptada=encriptar_contrasena(solicitud.contrasena),
        rol=solicitud.rol,
        codigo_placa=solicitud.codigo_placa.upper().strip(),
        puesto_base_id=solicitud.puesto_base_id,
        activo=True,
    )
    sesion_bd.add(nuevo_usuario)
    await sesion_bd.commit()
    await sesion_bd.refresh(nuevo_usuario)

    token_acceso = crear_token_acceso(
        usuario_id=nuevo_usuario.usuario_id,
        correo_electronico=nuevo_usuario.correo_electronico,
        rol=nuevo_usuario.rol,
    )
    token_refresco = crear_token_refresco(
        usuario_id=nuevo_usuario.usuario_id,
        correo_electronico=nuevo_usuario.correo_electronico,
        rol=nuevo_usuario.rol,
    )

    return RespuestaTokensAutenticacion(
        token_acceso=token_acceso,
        token_refresco=token_refresco,
        usuario=RespuestaUsuario.model_validate(nuevo_usuario),
    )


@enrutador_autenticacion.post(
    "/refrescar-token",
    response_model=RespuestaTokensAutenticacion,
    summary="Renovar par de tokens JWT utilizando el Refresh Token",
)
async def refrescar_token_sesion(
    solicitud: SolicitudRefrescarToken,
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaTokensAutenticacion:
    """Valida el Refresh Token y emite un nuevo Access Token y Refresh Token."""
    carga_util: dict[str, Any] = decodificar_token_jwt(
        solicitud.token_refresco,
        tipo_esperado="refresco",
    )
    identificador_texto: str | None = carga_util.get("sub")
    if identificador_texto is None or not identificador_texto.isdigit():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido.",
        )

    consulta = select(ModeloUsuario).where(
        ModeloUsuario.usuario_id == int(identificador_texto)
    )
    resultado = await sesion_bd.execute(consulta)
    usuario: ModeloUsuario | None = resultado.scalar_one_or_none()

    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no disponible para renovación de sesión.",
        )

    nuevo_acceso = crear_token_acceso(
        usuario_id=usuario.usuario_id,
        correo_electronico=usuario.correo_electronico,
        rol=usuario.rol,
    )
    nuevo_refresco = crear_token_refresco(
        usuario_id=usuario.usuario_id,
        correo_electronico=usuario.correo_electronico,
        rol=usuario.rol,
    )

    return RespuestaTokensAutenticacion(
        token_acceso=nuevo_acceso,
        token_refresco=nuevo_refresco,
        usuario=RespuestaUsuario.model_validate(usuario),
    )


@enrutador_autenticacion.get(
    "/perfil",
    response_model=RespuestaUsuario,
    summary="Obtener datos del usuario autenticado actualmente",
)
async def obtener_perfil_actual(
    usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
) -> RespuestaUsuario:
    """Retorna la información del usuario propietario del token JWT activo."""
    return RespuestaUsuario.model_validate(usuario_actual)


@enrutador_organizacion.get(
    "/usuarios",
    response_model=list[RespuestaUsuario],
    summary="Listar el personal registrado en la plataforma",
)
async def listar_usuarios(
    _usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaUsuario]:
    """Lista todos los usuarios activos ordenados por rol y nombre."""
    consulta = select(ModeloUsuario).order_by(
        ModeloUsuario.rol.asc(), ModeloUsuario.nombre_completo.asc()
    )
    resultado = await sesion_bd.execute(consulta)
    usuarios = resultado.scalars().all()
    return [RespuestaUsuario.model_validate(u) for u in usuarios]


@enrutador_organizacion.post(
    "/usuarios",
    response_model=RespuestaUsuario,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo integrante (ADMINISTRADOR o RRHH)",
)
async def crear_nuevo_usuario(
    solicitud: CrearUsuarioSolicitud,
    autorizado: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.RRHH)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaUsuario:
    """Crea un nuevo integrante validando unicidad y restricciones jerárquicas de RRHH."""
    if (
        autorizado.rol == RolUsuario.RRHH
        and solicitud.rol == RolUsuario.ADMINISTRADOR
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El rol RRHH no tiene privilegios para crear cuentas de ADMINISTRADOR.",
        )

    consulta_correo = select(ModeloUsuario).where(
        (ModeloUsuario.correo_electronico == solicitud.correo_electronico.lower())
        | (ModeloUsuario.documento_identidad == solicitud.documento_identidad)
    )
    existente = (await sesion_bd.execute(consulta_correo)).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese correo electrónico o documento de identidad.",
        )

    nuevo_usuario = ModeloUsuario(
        documento_identidad=solicitud.documento_identidad.strip(),
        nombre_completo=solicitud.nombre_completo.strip(),
        correo_electronico=solicitud.correo_electronico.lower().strip(),
        telefono=solicitud.telefono.strip(),
        contrasena_encriptada=encriptar_contrasena(solicitud.contrasena),
        rol=solicitud.rol,
        codigo_placa=solicitud.codigo_placa.upper().strip(),
        puesto_base_id=solicitud.puesto_base_id,
        numero_credencial_sv=solicitud.numero_credencial_sv,
        fecha_vencimiento_credencial=solicitud.fecha_vencimiento_credencial,
        fecha_vencimiento_psicofisico=solicitud.fecha_vencimiento_psicofisico,
        nivel_curso=solicitud.nivel_curso,
        activo=True,
    )
    sesion_bd.add(nuevo_usuario)
    await sesion_bd.commit()
    await sesion_bd.refresh(nuevo_usuario)
    return RespuestaUsuario.model_validate(nuevo_usuario)


@enrutador_organizacion.post(
    "/usuarios/importar-csv",
    response_model=RespuestaImportacionUsuariosCsv,
    summary="Carga masiva de usuarios y credenciales desde CSV (ADMINISTRADOR o RRHH)",
)
async def importar_usuarios_csv(
    solicitud: SolicitudImportarUsuariosCsv,
    _autorizado: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.RRHH)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaImportacionUsuariosCsv:
    """Importa masivamente personal a la plataforma desde una cadena o archivo CSV."""
    import csv
    import io
    from datetime import datetime

    lineas = solicitud.contenido_csv.strip().splitlines()
    if not lineas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo CSV está vacío.",
        )

    if len(solicitud.contenido_csv) > 2_000_000:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El contenido CSV supera el límite de seguridad de 2 MB.",
        )

    if len(lineas) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El lote excede el límite máximo permitido de 1,000 registros por importación.",
        )

    primera_linea = lineas[0]
    delimitador = ";" if ";" in primera_linea and "," not in primera_linea else ","
    lector = csv.DictReader(io.StringIO(solicitud.contenido_csv), delimiter=delimitador)

    # Pre-cálculo único del digest bcrypt fuera del bucle para evitar bloqueo del Event Loop
    hash_contrasena_defecto: str = encriptar_contrasena("Sentinel2026*")

    # Pre-carga de documentos y correos existentes para validación en memoria O(1)
    existentes_bd = (
        await sesion_bd.execute(
            select(ModeloUsuario.documento_identidad, ModeloUsuario.correo_electronico)
        )
    ).all()
    documentos_registrados: set[str] = {fila_bd[0] for fila_bd in existentes_bd}
    correos_registrados: set[str] = {fila_bd[1].lower() for fila_bd in existentes_bd}

    total = 0
    creados = 0
    omitidos = 0
    errores: list[str] = []
    nuevos_modelos: list[ModeloUsuario] = []

    for idx, fila in enumerate(lector, start=2):
        total += 1
        fila_norm = {
            str(k).strip().lower(): (str(v).strip() if v else "")
            for k, v in fila.items()
            if k is not None
        }

        doc = fila_norm.get("documento_identidad") or fila_norm.get("documento") or fila_norm.get("cedula")
        nombre = fila_norm.get("nombre_completo") or fila_norm.get("nombre")
        correo = fila_norm.get("correo_electronico") or fila_norm.get("correo") or fila_norm.get("email")
        tel = fila_norm.get("telefono") or "3000000000"
        rol_str = (fila_norm.get("rol") or "OPERADOR").upper()
        placa = fila_norm.get("codigo_placa") or fila_norm.get("placa") or f"PL-{doc}"
        cred_sv = fila_norm.get("numero_credencial_sv") or fila_norm.get("credencial") or None
        f_venc_str = fila_norm.get("fecha_vencimiento_credencial") or fila_norm.get("vencimiento_credencial") or None
        curso_str = (fila_norm.get("nivel_curso") or "FUNDAMENTACION").upper()

        if not doc or not nombre or not correo:
            errores.append(f"Fila {idx}: Faltan campos obligatorios (cédula, nombre o correo).")
            omitidos += 1
            continue

        correo_limpio = correo.lower()
        if doc in documentos_registrados or correo_limpio in correos_registrados:
            omitidos += 1
            continue

        try:
            rol_enum = RolUsuario(rol_str)
        except ValueError:
            rol_enum = RolUsuario.OPERADOR

        try:
            curso_enum = NivelCursoVigilancia(curso_str)
        except ValueError:
            curso_enum = NivelCursoVigilancia.FUNDAMENTACION

        fecha_venc = None
        if f_venc_str:
            try:
                fecha_venc = datetime.strptime(f_venc_str, "%Y-%m-%d").date()
            except ValueError:
                try:
                    fecha_venc = datetime.strptime(f_venc_str, "%d/%m/%Y").date()
                except ValueError:
                    fecha_venc = None

        nuevo = ModeloUsuario(
            documento_identidad=doc,
            nombre_completo=nombre,
            correo_electronico=correo_limpio,
            telefono=tel,
            contrasena_encriptada=hash_contrasena_defecto,
            rol=rol_enum,
            codigo_placa=placa,
            puesto_base_id=None,
            numero_credencial_sv=cred_sv,
            fecha_vencimiento_credencial=fecha_venc,
            fecha_vencimiento_psicofisico=fecha_venc,
            nivel_curso=curso_enum,
            activo=True,
        )
        nuevos_modelos.append(nuevo)
        documentos_registrados.add(doc)
        correos_registrados.add(correo_limpio)
        creados += 1

    if nuevos_modelos:
        sesion_bd.add_all(nuevos_modelos)
        await sesion_bd.commit()
        for modelo in nuevos_modelos:
            await sesion_bd.refresh(modelo)

    usuarios_creados = [RespuestaUsuario.model_validate(m) for m in nuevos_modelos]

    return RespuestaImportacionUsuariosCsv(
        total_procesados=total,
        creados=creados,
        omitidos=omitidos,
        errores=errores,
        usuarios_creados=usuarios_creados,
    )


@enrutador_organizacion.patch(
    "/usuarios/{usuario_id}/credencial-sv",
    response_model=RespuestaUsuario,
    summary="Actualizar credencial SuperVigilancia, curso y examen psicofísico (RRHH o ADMINISTRADOR)",
)
async def actualizar_credencial_supervigilancia(
    usuario_id: int,
    solicitud: ActualizarCredencialUsuarioSolicitud,
    autorizado: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.RRHH)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaUsuario:
    """Actualiza la documentación legal ante la SuperVigilancia de un guarda o supervisor."""
    consulta_usuario = select(ModeloUsuario).where(
        ModeloUsuario.usuario_id == usuario_id
    )
    usuario = (await sesion_bd.execute(consulta_usuario)).scalar_one_or_none()
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario especificado no existe.",
        )

    usuario.numero_credencial_sv = solicitud.numero_credencial_sv.upper().strip()
    usuario.fecha_vencimiento_credencial = solicitud.fecha_vencimiento_credencial
    usuario.fecha_vencimiento_psicofisico = solicitud.fecha_vencimiento_psicofisico
    usuario.nivel_curso = solicitud.nivel_curso
    if autorizado.rol == RolUsuario.ADMINISTRADOR:
        usuario.excepcion_credencial_autorizada = (
            solicitud.excepcion_credencial_autorizada
        )

    await sesion_bd.commit()
    await sesion_bd.refresh(usuario)
    return RespuestaUsuario.model_validate(usuario)


@enrutador_organizacion.patch(
    "/usuarios/{usuario_id}/puesto",
    response_model=RespuestaUsuario,
    summary="Asignar o reasignar el puesto de vigilancia base de un integrante",
)
async def asignar_puesto_usuario(
    usuario_id: int,
    solicitud: AsignarPuestoUsuarioSolicitud,
    _autorizado: ModeloUsuario = Depends(
        requerir_roles(
            RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR, RolUsuario.RRHH
        )
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaUsuario:
    """Actualiza la asignación de puesto base de un guardia o colaborador."""
    consulta_usuario = select(ModeloUsuario).where(ModeloUsuario.usuario_id == usuario_id)
    usuario = (await sesion_bd.execute(consulta_usuario)).scalar_one_or_none()
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado en el sistema.",
        )

    if solicitud.puesto_base_id is not None:
        consulta_puesto = select(ModeloPuestoVigilancia).where(
            ModeloPuestoVigilancia.puesto_id == solicitud.puesto_base_id
        )
        puesto = (await sesion_bd.execute(consulta_puesto)).scalar_one_or_none()
        if puesto is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El puesto de vigilancia especificado no existe.",
            )

    usuario.puesto_base_id = solicitud.puesto_base_id
    await sesion_bd.commit()
    await sesion_bd.refresh(usuario)
    return RespuestaUsuario.model_validate(usuario)


@enrutador_organizacion.get(
    "/puestos",
    response_model=list[RespuestaPuestoVigilancia],
    summary="Listar puestos de vigilancia activos (Público / Autenticado)",
)
async def listar_puestos_vigilancia(
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> list[RespuestaPuestoVigilancia]:
    """Retorna todos los puestos de vigilancia registrados."""
    consulta = select(ModeloPuestoVigilancia).order_by(
        ModeloPuestoVigilancia.codigo_puesto.asc()
    )
    resultado = await sesion_bd.execute(consulta)
    puestos = resultado.scalars().all()
    return [RespuestaPuestoVigilancia.model_validate(p) for p in puestos]


@enrutador_organizacion.post(
    "/puestos",
    response_model=RespuestaPuestoVigilancia,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo puesto de vigilancia (ADMINISTRADOR o SUPERVISOR)",
)
async def crear_puesto_vigilancia(
    solicitud: CrearPuestoVigilanciaSolicitud,
    _autorizado: ModeloUsuario = Depends(
        requerir_roles(RolUsuario.ADMINISTRADOR, RolUsuario.SUPERVISOR)
    ),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> RespuestaPuestoVigilancia:
    """Registra una nueva instalación o sede protegida."""
    consulta = select(ModeloPuestoVigilancia).where(
        ModeloPuestoVigilancia.codigo_puesto == solicitud.codigo_puesto.upper().strip()
    )
    if (await sesion_bd.execute(consulta)).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un puesto de vigilancia con ese código.",
        )

    nuevo_puesto = ModeloPuestoVigilancia(
        codigo_puesto=solicitud.codigo_puesto.upper().strip(),
        nombre_puesto=solicitud.nombre_puesto.strip(),
        empresa_cliente=solicitud.empresa_cliente.strip(),
        direccion_ubicacion=solicitud.direccion_ubicacion.strip(),
        ciudad=solicitud.ciudad.strip(),
        requiere_armamento=solicitud.requiere_armamento,
        activo=True,
    )
    sesion_bd.add(nuevo_puesto)
    await sesion_bd.commit()
    await sesion_bd.refresh(nuevo_puesto)
    return RespuestaPuestoVigilancia.model_validate(nuevo_puesto)


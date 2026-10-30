"""
Módulo de Seguridad, Criptografía y Control de Acceso Basado en Roles (RBAC).
Implementa hashing con bcrypt, emisión/verificación de tokens JWT (Acceso y Refresco)
y dependencias de autorización por rol para FastAPI.
"""

from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.modelos_bd import ModeloUsuario, RolUsuario
from app.nucleo.base_datos import obtener_sesion_bd
from app.nucleo.configuracion import configuracion

esquema_portador_jwt = HTTPBearer(auto_error=False)


def encriptar_contrasena(contrasena_plana: str) -> str:
    """Genera un hash seguro usando bcrypt a partir de una contraseña en texto plano."""
    bytes_contrasena: bytes = contrasena_plana.encode("utf-8")
    sal: bytes = bcrypt.gensalt()
    hash_generado: bytes = bcrypt.hashpw(bytes_contrasena, sal)
    return hash_generado.decode("utf-8")


def verificar_contrasena(contrasena_plana: str, contrasena_encriptada: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con su hash bcrypt."""
    try:
        return bcrypt.checkpw(
            contrasena_plana.encode("utf-8"),
            contrasena_encriptada.encode("utf-8"),
        )
    except ValueError:
        return False


def crear_token_acceso(
    usuario_id: int,
    correo_electronico: str,
    rol: RolUsuario,
) -> str:
    """Crea un JWT de corta duración para autorizar peticiones a la API."""
    ahora: datetime = datetime.now(timezone.utc)
    expiracion: datetime = ahora + timedelta(
        minutes=configuracion.minutos_expiracion_acceso
    )
    carga_util: dict[str, Any] = {
        "sub": str(usuario_id),
        "correo": correo_electronico,
        "rol": rol.value,
        "tipo_token": "acceso",
        "iat": int(ahora.timestamp()),
        "exp": int(expiracion.timestamp()),
    }
    return jwt.encode(
        carga_util,
        configuracion.clave_secreta_jwt,
        algorithm=configuracion.algoritmo_jwt,
    )


def crear_token_refresco(
    usuario_id: int,
    correo_electronico: str,
    rol: RolUsuario,
) -> str:
    """Crea un JWT de larga duración para renovar sesiones sin reautenticar."""
    ahora: datetime = datetime.now(timezone.utc)
    expiracion: datetime = ahora + timedelta(
        days=configuracion.dias_expiracion_refresco
    )
    carga_util: dict[str, Any] = {
        "sub": str(usuario_id),
        "correo": correo_electronico,
        "rol": rol.value,
        "tipo_token": "refresco",
        "iat": int(ahora.timestamp()),
        "exp": int(expiracion.timestamp()),
    }
    return jwt.encode(
        carga_util,
        configuracion.clave_secreta_jwt,
        algorithm=configuracion.algoritmo_jwt,
    )


def decodificar_token_jwt(token: str, tipo_esperado: str = "acceso") -> dict[str, Any]:
    """Decodifica y valida la firma, expiración y tipo de un token JWT."""
    try:
        carga_util: dict[str, Any] = jwt.decode(
            token,
            configuracion.clave_secreta_jwt,
            algorithms=[configuracion.algoritmo_jwt],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de seguridad ha expirado. Inicie sesión nuevamente.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de seguridad inválido o corrupto.",
        ) from exc

    if carga_util.get("tipo_token") != tipo_esperado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Se esperaba un token de tipo '{tipo_esperado}'.",
        )

    return carga_util


async def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_portador_jwt),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> ModeloUsuario:
    """Dependencia que extrae y valida el usuario autenticado a partir del encabezado Bearer."""
    if credenciales is None or not credenciales.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionaron credenciales de autenticación.",
        )

    carga_util: dict[str, Any] = decodificar_token_jwt(
        credenciales.credentials,
        tipo_esperado="acceso",
    )
    identificador_texto: str | None = carga_util.get("sub")
    if identificador_texto is None or not identificador_texto.isdigit():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuario inválido dentro del token.",
        )

    usuario_id: int = int(identificador_texto)
    consulta = select(ModeloUsuario).where(ModeloUsuario.usuario_id == usuario_id)
    resultado = await sesion_bd.execute(consulta)
    usuario: ModeloUsuario | None = resultado.scalar_one_or_none()

    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario no existe o su cuenta se encuentra inactiva.",
        )

    return usuario


async def obtener_usuario_opcional(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_portador_jwt),
    sesion_bd: AsyncSession = Depends(obtener_sesion_bd),
) -> ModeloUsuario | None:
    """Extrae el usuario autenticado si existe un token válido; retorna None si es anónimo."""
    if credenciales is None or not credenciales.credentials:
        return None
    try:
        carga_util = decodificar_token_jwt(credenciales.credentials, tipo_esperado="acceso")
        identificador_texto = carga_util.get("sub")
        if identificador_texto is None or not identificador_texto.isdigit():
            return None
        consulta = select(ModeloUsuario).where(
            ModeloUsuario.usuario_id == int(identificador_texto)
        )
        resultado = await sesion_bd.execute(consulta)
        return resultado.scalar_one_or_none()
    except Exception:
        return None


def requerir_roles(
    *roles_permitidos: RolUsuario,
) -> Callable[[ModeloUsuario], Coroutine[Any, Any, ModeloUsuario]]:
    """
    Fábrica de dependencias RBAC que restringe el acceso a una ruta según el rol del usuario.
    """

    async def validador_rol(
        usuario_actual: ModeloUsuario = Depends(obtener_usuario_actual),
    ) -> ModeloUsuario:
        if usuario_actual.rol not in roles_permitidos:
            nombres_roles: str = ", ".join(rol.value for rol in roles_permitidos)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Acceso denegado. Tu rol ({usuario_actual.rol.value}) no tiene "
                    f"privilegios para esta operación. Roles requeridos: {nombres_roles}."
                ),
            )
        return usuario_actual

    return validador_rol


HASH_GENESIS_SHA256: str = "0" * 64


def calcular_hash_encadenado_sha256(
    datos_actuales: str, hash_anterior: str | None = None
) -> str:
    """
    Calcula un sello SHA-256 encadenado (Hash Chaining / Blockchain ligero) vinculando
    el payload actual con el hash del registro inmediatamente anterior del mismo puesto o tenant.
    Si es el primer registro de la cadena, utiliza el hash génesis ('0' * 64).
    """
    eslabon_previo = (
        hash_anterior.strip().upper()
        if hash_anterior and len(hash_anterior.strip()) == 64
        else HASH_GENESIS_SHA256
    )
    trama_encadenada = f"{datos_actuales}|PREV:{eslabon_previo}"
    return hashlib.sha256(trama_encadenada.encode("utf-8")).hexdigest().upper()


def enmascarar_dato_sensible(texto: str, caracteres_visibles: int = 2) -> str:
    """
    Enmascara parcialmente números de documento o datos sensibles en logs operativos
    en cumplimiento de la Ley Estatutaria 1581 de 2012 (Habeas Data).
    """
    limpio = texto.strip()
    if len(limpio) <= caracteres_visibles * 2:
        return "*" * len(limpio)
    return f"{limpio[:caracteres_visibles]}{'*' * (len(limpio) - (caracteres_visibles * 2))}{limpio[-caracteres_visibles:]}"



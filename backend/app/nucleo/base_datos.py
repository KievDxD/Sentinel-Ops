"""
Gestión asíncrona de la conexión a la base de datos con SQLAlchemy 2.0.
Detecta de forma no bloqueante si PostgreSQL 15 está activo en localhost:5432.
Si no lo está, inicia de inmediato con SQLite asíncrono (aiosqlite) para garantizar
operatividad instantánea y sin fricción.
"""

import socket
from collections.abc import AsyncGenerator
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.nucleo.configuracion import configuracion


class BaseModeloDeclarativo(DeclarativeBase):
    """Clase base declarativa de SQLAlchemy 2.0 para todas las tablas del sistema."""


def verificar_puerto_postgres() -> bool:
    """Verifica en menos de 0.2 segundos si el puerto 5432 de PostgreSQL está accesible."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex(("127.0.0.1", 5432)) == 0
    except Exception:
        return False


if verificar_puerto_postgres():
    motor_activo: AsyncEngine = create_async_engine(
        configuracion.url_base_datos_postgres,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )
    motor_en_uso_descripcion: str = "PostgreSQL 15 (Docker)"
else:
    motor_activo = create_async_engine(
        configuracion.url_base_datos_respaldo,
        echo=False,
        future=True,
    )
    motor_en_uso_descripcion = "SQLite Asíncrono Local (Respaldo Automático)"

FabricaSesionesAsincronas: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=motor_activo,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def _verificar_y_sincronizar_esquema(conexion_sincrona: object) -> None:
    """Verifica si el esquema V2.0 está completo; si faltan columnas o tablas nuevas, recrea limpiamente."""
    inspector = inspect(conexion_sincrona)
    if inspector is not None:
        tablas_existentes = inspector.get_table_names()
        if "usuarios" in tablas_existentes:
            columnas_usuarios = {
                col["name"] for col in inspector.get_columns("usuarios")
            }
            if (
                "numero_credencial_sv" not in columnas_usuarios
                or "tenant_id" not in columnas_usuarios
                or "dotacion_armamento_puesto" not in tablas_existentes
            ):
                BaseModeloDeclarativo.metadata.drop_all(bind=conexion_sincrona)  # type: ignore[arg-type]
    BaseModeloDeclarativo.metadata.create_all(bind=conexion_sincrona)  # type: ignore[arg-type]


async def inicializar_motor_base_datos() -> str:
    """Crea o actualiza el esquema de tablas V2.0 en el motor activo."""
    async with motor_activo.begin() as conexion:
        await conexion.run_sync(_verificar_y_sincronizar_esquema)
    return motor_en_uso_descripcion


async def obtener_sesion_bd() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia asíncrona de FastAPI que provee una sesión de base de datos por petición."""
    async with FabricaSesionesAsincronas() as sesion:
        try:
            yield sesion
        finally:
            await sesion.close()


def obtener_descripcion_motor() -> str:
    """Retorna la descripción legible del motor de base de datos actualmente activo."""
    return motor_en_uso_descripcion

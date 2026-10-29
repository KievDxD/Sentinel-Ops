"""Configuración asíncrona de Alembic para las migraciones de SENTINEL // OPS."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.modelos.modelos_bd import BaseModeloDeclarativo
from app.nucleo.configuracion import configuracion

config = context.config
config.set_main_option("sqlalchemy.url", configuracion.url_base_datos_postgres)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

metadatos_objetivo = BaseModeloDeclarativo.metadata


def ejecutar_migraciones_en_linea(conexion: Connection) -> None:
    """Configura el contexto de migración sobre una conexión activa."""
    context.configure(
        connection=conexion,
        target_metadata=metadatos_objetivo,
    )
    with context.begin_transaction():
        context.run_migrations()


async def ejecutar_migraciones_asincronas() -> None:
    """Crea un motor asíncrono y ejecuta las migraciones de Alembic."""
    conectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with conectable.connect() as conexion:
        await conexion.run_sync(ejecutar_migraciones_en_linea)
    await conectable.dispose()


if context.is_offline_mode():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=metadatos_objetivo,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(ejecutar_migraciones_asincronas())


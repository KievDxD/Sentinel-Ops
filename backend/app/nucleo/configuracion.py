"""
Configuración global de la plataforma SENTINEL // OPS usando Pydantic Settings.
Todas las variables, propiedades y constantes se encuentran en español.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfiguracionSistema(BaseSettings):
    """Parámetros de configuración del entorno de ejecución del servidor."""

    nombre_proyecto: str = "SENTINEL // OPS - API Central Enterprise V3.5"
    version_api: str = "3.5.0"

    # Soporte Multi-Tenant SaaS (Fase 12)
    modo_multi_tenant: bool = True
    tenant_id_predeterminado: str = "EMPRESA-SEGURIDAD-COLOMBIA-01"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Conexión principal a PostgreSQL 15 definida en docker-compose.yml
    url_base_datos_postgres: str = (
        "postgresql+asyncpg://administrador_sentinel:clave_segura_sentinel_2026"
        "@localhost:5432/sentinel_ops_bd"
    )
    # Respaldo local asíncrono si el contenedor Docker no está encendido aún
    url_base_datos_respaldo: str = "sqlite+aiosqlite:///./sentinel_ops_local.db"

    # Parámetros criptográficos para JWT (Access y Refresh Tokens)
    clave_secreta_jwt: str = (
        "sentinel_ops_clave_maestra_2026_seguridad_privada_colombia_hmac_sha256"
    )
    algoritmo_jwt: str = "HS256"
    minutos_expiracion_acceso: int = 120
    dias_expiracion_refresco: int = 7

    # Parámetros de normativa laboral colombiana (Ley 2101 de 2021, Ley 1920 y CST)
    smlmv_vigente: float = 1_423_500.0
    auxilio_transporte_vigente: float = 200_000.0
    tope_horas_semanales: int = 42
    hora_inicio_nocturno: int = 21
    hora_fin_nocturno: int = 6
    horas_jornada_ordinaria_turno: float = 8.0
    horas_descanso_minimo_entre_turnos: float = 12.0
    valor_hora_ordinaria_cop: float = 6500.0
    factor_recargo_nocturno: float = 0.35
    factor_hora_extra_diurna: float = 1.25
    factor_hora_extra_nocturna: float = 1.75
    factor_recargo_dominical_festivo: float = 0.75

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


configuracion: ConfiguracionSistema = ConfiguracionSistema()


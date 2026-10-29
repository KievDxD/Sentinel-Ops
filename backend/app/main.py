"""
Módulo principal de entrada para la API de SENTINEL // OPS (Release Enterprise V2.0).
Integra el ciclo de vida asíncrono (inicialización de base de datos y semilla),
el middleware CORS, los módulos de negocio y el canal WebSocket en tiempo real.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from app.esquemas.esquemas_pydantic import RespuestaEstadoSistema
from app.nucleo.base_datos import (
    inicializar_motor_base_datos,
    obtener_descripcion_motor,
)
from app.nucleo.configuracion import configuracion
from app.rutas.rutas_autenticacion import (
    enrutador_autenticacion,
    enrutador_organizacion,
)
from app.rutas.rutas_intercambios import enrutador_intercambios
from app.rutas.rutas_minuta import endpoint_websocket_minuta, enrutador_minuta
from app.rutas.rutas_reportes import enrutador_reportes
from app.rutas.rutas_rondas import enrutador_rondas
from app.rutas.rutas_turnos import enrutador_turnos
from app.servicios.gestor_websockets import gestor_minuta_ws
from app.servicios.semilla import inicializar_datos_semilla


@asynccontextmanager
async def ciclo_vida_aplicacion(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Inicializa el esquema de base de datos y los datos semilla al arrancar el servidor."""
    await inicializar_motor_base_datos()
    await inicializar_datos_semilla()
    yield


aplicacion: FastAPI = FastAPI(
    title=configuracion.nombre_proyecto,
    description=(
        "Plataforma SaaS B2B Enterprise V2.0 para gestión operativa, armamento Indumil, "
        "credenciales SuperVigilancia, nómina Ley 2101 (42h), turnos 2x2 y alerta SOS."
    ),
    version=configuracion.version_api,
    lifespan=ciclo_vida_aplicacion,
)

origenes_permitidos: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_permitidos,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de enrutadores de los módulos principales
aplicacion.include_router(enrutador_autenticacion)
aplicacion.include_router(enrutador_organizacion)
aplicacion.include_router(enrutador_turnos)
aplicacion.include_router(enrutador_minuta)
aplicacion.include_router(enrutador_intercambios)
aplicacion.include_router(enrutador_rondas)
aplicacion.include_router(enrutador_reportes)

# Ruta WebSocket para la Minuta Digital y Alertas SOS en Tiempo Real
aplicacion.add_api_websocket_route("/ws/minuta", endpoint_websocket_minuta)


@aplicacion.get(
    "/",
    response_class=HTMLResponse,
    summary="Portal de bienvenida y diagnóstico rápido del Centro de Mando Táctico",
    include_in_schema=False,
)
async def inicio_centro_mando() -> HTMLResponse:
    """Retorna un panel táctico HTML con enlaces directos a la documentación y el frontend."""
    return HTMLResponse(
        content="""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>SENTINEL // OPS V2.0 - Servidor Central</title>
    <style>
        body { background: #020617; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
        .panel { background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 16px; padding: 32px; max-width: 600px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); backdrop-filter: blur(16px); }
        h1 { margin: 0 0 8px; font-size: 24px; color: #fff; }
        .resaltado { color: #10b981; }
        p { color: #94a3b8; font-size: 14px; line-height: 1.5; }
        .enlaces { display: flex; gap: 12px; margin-top: 24px; }
        a { display: inline-block; padding: 10px 18px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: bold; transition: all 0.2s; }
        .btn-primario { background: #10b981; color: #020617; }
        .btn-primario:hover { background: #34d399; }
        .btn-secundario { background: rgba(255,255,255,0.05); color: #e2e8f0; border: 1px solid rgba(255,255,255,0.1); }
        .btn-secundario:hover { border-color: #10b981; color: #34d399; }
        .estado { display: inline-flex; align-items: center; gap: 8px; padding: 4px 12px; border-radius: 9999px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); font-size: 12px; color: #34d399; margin-bottom: 16px; }
        .punto { width: 8px; height: 8px; border-radius: 50%; background: #10b981; }
    </style>
</head>
<body>
    <div class="panel">
        <div class="estado"><span class="punto"></span> Núcleo Operativo Enterprise V2.0 En Línea</div>
        <h1>SENTINEL <span class="resaltado">//</span> OPS</h1>
        <p>Plataforma SaaS B2B para Seguridad Privada en Colombia (SuperVigilancia, Ley 2101 de 42h semanales, Indumil y Turnos 2x2).</p>
        <div class="enlaces">
            <a href="/docs" class="btn-primario">Explorar Swagger UI (/docs)</a>
            <a href="http://localhost:5173" class="btn-secundario">Ir al Frontend Táctico (:5173)</a>
            <a href="/api/estado" class="btn-secundario">Telemetría JSON</a>
        </div>
    </div>
</body>
</html>"""
    )


@aplicacion.get(
    "/health",
    include_in_schema=False,
)
async def redireccion_salud() -> RedirectResponse:
    """Redirecciona /health hacia /api/estado para monitores de infraestructura."""
    return RedirectResponse(url="/api/estado")


@aplicacion.get(
    "/api/estado",
    response_model=RespuestaEstadoSistema,
    summary="Consultar el estado operativo del núcleo y parámetros de Ley 2101",
    tags=["Diagnóstico del Sistema"],
)
async def obtener_estado_sistema() -> RespuestaEstadoSistema:
    """
    Retorna el estado operativo del núcleo de SENTINEL // OPS junto con la fecha actual,
    el motor de base de datos activo, clientes WebSocket conectados y el tope de 42h semanales.
    """
    fecha_actual: str = datetime.now(timezone.utc).astimezone().isoformat()
    return RespuestaEstadoSistema(
        estado="Sentinel Core En Línea",
        fecha=fecha_actual,
        motor_base_datos=obtener_descripcion_motor(),
        conexiones_websocket_activas=gestor_minuta_ws.cantidad_conectados(),
        tope_horas_semanales_ley_2101=configuracion.tope_horas_semanales,
    )

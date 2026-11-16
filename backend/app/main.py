"""
Módulo principal de entrada para la API de SENTINEL // OPS (Release Enterprise V2.0).
Integra el ciclo de vida asíncrono (inicialización de base de datos y semilla),
el middleware CORS, los módulos de negocio y el canal WebSocket en tiempo real.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

import app.modelos.modelos_bd  # noqa: F401 - Registra todos los modelos en Base.metadata
from app.esquemas.esquemas_pydantic import RespuestaEstadoSistema
from app.nucleo.base_datos import (
    Base,
    inicializar_motor_base_datos,
    motor_bd,
    obtener_descripcion_motor,
    restaurar_base_datos_demo_limpia,
)
from app.nucleo.configuracion import configuracion
from app.rutas.rutas_autenticacion import (
    enrutador_autenticacion,
    enrutador_organizacion,
)
from app.rutas.rutas_balistica import enrutador_balistica
from app.rutas.rutas_control_acceso import enrutador_acceso
from app.rutas.rutas_cumplimiento import enrutador_cumplimiento
from app.rutas.rutas_despacho_cad import enrutador_cad
from app.rutas.rutas_facturacion import enrutador_facturacion
from app.rutas.rutas_inteligencia import enrutador_inteligencia
from app.rutas.rutas_intercambios import enrutador_intercambios
from app.rutas.rutas_minuta import endpoint_websocket_minuta, enrutador_minuta
from app.rutas.rutas_operaciones_especiales import enrutador_operaciones_especiales
from app.rutas.rutas_reportes import enrutador_reportes
from app.rutas.rutas_rondas import enrutador_rondas
from app.rutas.rutas_turnos import enrutador_turnos
from app.servicios.gestor_websockets import gestor_minuta_ws
from app.servicios.semilla import inicializar_datos_semilla


async def _bucle_auto_reset_demo_24h() -> None:
    """Tarea ligera en segundo plano que restaura la semilla demo cada 24 horas si MODO_DEMO=True."""
    segundos_intervalo = max(60, configuracion.intervalo_reset_demo_horas * 3600)
    while True:
        await asyncio.sleep(segundos_intervalo)
        try:
            await restaurar_base_datos_demo_limpia()
            async with motor_bd.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            await inicializar_datos_semilla()
        except asyncio.CancelledError:
            raise
        except Exception:
            # Evita derribar el Event Loop ante fallos transitorios de conexión durante el reset
            pass


@asynccontextmanager
async def ciclo_vida_aplicacion(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Inicializa el esquema de BD, semilla y tarea de auto-reset demo (si MODO_DEMO=True)."""
    await inicializar_motor_base_datos()
    async with motor_bd.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await inicializar_datos_semilla()
    tarea_reset_demo: asyncio.Task[None] | None = None
    if configuracion.modo_demo:
        tarea_reset_demo = asyncio.create_task(_bucle_auto_reset_demo_24h())
    try:
        yield
    finally:
        if tarea_reset_demo is not None:
            tarea_reset_demo.cancel()
            try:
                await tarea_reset_demo
            except asyncio.CancelledError:
                pass


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
aplicacion.include_router(enrutador_facturacion)
aplicacion.include_router(enrutador_acceso)
aplicacion.include_router(enrutador_balistica)
aplicacion.include_router(enrutador_cad)
aplicacion.include_router(enrutador_operaciones_especiales)
aplicacion.include_router(enrutador_cumplimiento)
aplicacion.include_router(enrutador_inteligencia)

# Ruta WebSocket para la Minuta Digital y Alertas SOS en Tiempo Real
aplicacion.add_api_websocket_route("/ws/minuta", endpoint_websocket_minuta)


def _resolver_directorio_frontend_dist() -> Path | None:
    """Detecta el bundle compilado de React (frontend_dist) en Docker o despliegue local."""
    candidatos: tuple[Path, ...] = (
        Path("frontend_dist"),
        Path("/app/frontend_dist"),
        Path(__file__).resolve().parent.parent / "frontend_dist",
        Path(__file__).resolve().parent.parent.parent / "frontend_dist",
    )
    for directorio in candidatos:
        if directorio.is_dir() and (directorio / "index.html").is_file():
            return directorio.resolve()
    return None


DIRECTORIO_FRONTEND_DIST: Path | None = _resolver_directorio_frontend_dist()
if DIRECTORIO_FRONTEND_DIST is not None and (DIRECTORIO_FRONTEND_DIST / "assets").is_dir():
    aplicacion.mount(
        "/assets",
        StaticFiles(directory=str(DIRECTORIO_FRONTEND_DIST / "assets"), html=False),
        name="frontend_assets",
    )


@aplicacion.get(
    "/",
    response_class=Response,
    summary="Portal principal SPA en producción o bienvenida diagnóstica en desarrollo",
    include_in_schema=False,
)
async def inicio_centro_mando() -> Response:
    """Sirve el frontend compilado si frontend_dist existe; sino, el portal de diagnóstico local."""
    if DIRECTORIO_FRONTEND_DIST is not None:
        return FileResponse(DIRECTORIO_FRONTEND_DIST / "index.html")
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


@aplicacion.get("/{full_path:path}", include_in_schema=False)
async def servir_spa_produccion(full_path: str) -> Response:
    """Catch-all de producción para servir activos estáticos de React o el fallback SPA."""
    if full_path.startswith("api/") or full_path.startswith("ws/") or full_path in {
        "api",
        "ws",
        "docs",
        "redoc",
        "openapi.json",
    }:
        raise HTTPException(status_code=404, detail="Endpoint no encontrado")
    if DIRECTORIO_FRONTEND_DIST is None:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    archivo_objetivo = (DIRECTORIO_FRONTEND_DIST / full_path).resolve()
    if (
        archivo_objetivo.is_relative_to(DIRECTORIO_FRONTEND_DIST)
        and archivo_objetivo.is_file()
    ):
        return FileResponse(archivo_objetivo)
    return FileResponse(DIRECTORIO_FRONTEND_DIST / "index.html")


app: FastAPI = aplicacion

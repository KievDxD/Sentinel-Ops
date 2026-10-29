"""
Gestor central de conexiones WebSocket para la Minuta Digital en Tiempo Real.
Permite difundir instantáneamente nuevos registros de minuta a todos los paneles
de Supervisores, Administradores y Operadores conectados.
"""

from typing import Any
from fastapi import WebSocket


class GestorMinutaWebSocket:
    """Administra las conexiones activas de WebSockets y la difusión de eventos."""

    def __init__(self) -> None:
        self.conexiones_activas: list[WebSocket] = []

    async def conectar_cliente(self, websocket: WebSocket) -> None:
        """Acepta y registra una nueva conexión WebSocket entrante."""
        await websocket.accept()
        self.conexiones_activas.append(websocket)

    def desconectar_cliente(self, websocket: WebSocket) -> None:
        """Elimina una conexión WebSocket cerrada del registro activo."""
        if websocket in self.conexiones_activas:
            self.conexiones_activas.remove(websocket)

    def cantidad_conectados(self) -> int:
        """Retorna el número de paneles conectados en vivo."""
        return len(self.conexiones_activas)

    async def difundir_evento_minuta(self, carga_evento: dict[str, Any]) -> None:
        """
        Envía un objeto JSON en tiempo real a todos los clientes conectados.
        Limpia automáticamente cualquier socket que haya perdido conexión.
        """
        conexiones_caidas: list[WebSocket] = []
        for conexion in self.conexiones_activas:
            try:
                await conexion.send_json(carga_evento)
            except Exception:
                conexiones_caidas.append(conexion)

        for conexion_caida in conexiones_caidas:
            self.desconectar_cliente(conexion_caida)


gestor_minuta_ws: GestorMinutaWebSocket = GestorMinutaWebSocket()


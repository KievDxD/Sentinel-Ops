/**
 * Cliente HTTP Axios centralizado con interceptores JWT (Access y Refresh Tokens)
 * y funciones asíncronas tipadas para Release Enterprise V2.0 de SENTINEL // OPS.
 */

import axios, {
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";
import { usarAlmacenAutenticacion } from "../estado/almacen_autenticacion";
import type {
  ActaRelevoPuesto,
  ActualizarCredencialUsuarioFormulario,
  AlertaCoberturaPuesto,
  AlertaPanicoSos,
  AsignarRelevanteTurnoFormulario,
  AtenderAlertaSosFormulario,
  AusentismoPersonal,
  CandidatoRelevanteSugerido,
  CrearActaRelevoFormulario,
  CrearPuestoFormulario,
  CrearRegistroMinutaFormulario,
  CrearSolicitudIntercambioFormulario,
  CrearUsuarioFormulario,
  DispararAlertaSosFormulario,
  DotacionPuesto,
  MarcacionRonda,
  PuestoVigilancia,
  PuntoControlRonda,
  RegistrarAusentismoFormulario,
  RegistrarMarcacionRondaFormulario,
  RegistroMinuta,
  RegistroUsuarioRealFormulario,
  ResolverIntercambioFormulario,
  RespuestaEstadoServidor,
  RespuestaTokensAutenticacion,
  ResumenLiquidacionTurnos,
  SolicitudGenerarCoberturaPuesto2x2,
  SolicitudGenerarRotacion2x2,
  SolicitudInicioSesion,
  SolicitudIntercambioTurno,
  TurnoOperativo,
  UsuarioSistema,
} from "../tipos/tipos_sistema";

export const URL_BASE_API: string =
  (import.meta.env.VITE_URL_BASE_API as string | undefined) ??
  "http://localhost:8000";

export const URL_WEBSOCKET_MINUTA: string =
  URL_BASE_API.replace(/^http/, "ws") + "/ws/minuta";

export const clienteApi: AxiosInstance = axios.create({
  baseURL: URL_BASE_API,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

clienteApi.interceptors.request.use(
  (configuracion: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = usarAlmacenAutenticacion.getState().tokenAcceso;
    if (token && configuracion.headers) {
      configuracion.headers.Authorization = `Bearer ${token}`;
    }
    return configuracion;
  }
);

/**
 * Extrae un mensaje de error legible en español desde una excepción de Axios o desconocida.
 */
export function extraerMensajeError(errorCapturado: unknown): string {
  if (axios.isAxiosError(errorCapturado)) {
    const datosRespuesta = errorCapturado.response?.data as
      | { detail?: string }
      | undefined;
    if (datosRespuesta && typeof datosRespuesta.detail === "string") {
      return datosRespuesta.detail;
    }
    return (
      errorCapturado.message ||
      "No fue posible comunicarse con el servidor central."
    );
  }
  if (errorCapturado instanceof Error) {
    return errorCapturado.message;
  }
  return "Ocurrió un error inesperado en la operación.";
}

// ============================================================================
// DIAGNÓSTICO DEL SISTEMA
// ============================================================================
export async function servicioConsultarEstado(): Promise<RespuestaEstadoServidor> {
  const respuesta = await clienteApi.get<RespuestaEstadoServidor>("/api/estado");
  return respuesta.data;
}

// ============================================================================
// MÓDULO 1: AUTENTICACIÓN, PERSONAL, CREDENCIALES SUPERVIGILANCIA Y PUESTOS
// ============================================================================
export async function servicioIniciarSesion(
  credenciales: SolicitudInicioSesion
): Promise<RespuestaTokensAutenticacion> {
  const respuesta = await clienteApi.post<RespuestaTokensAutenticacion>(
    "/api/autenticacion/iniciar-sesion",
    credenciales
  );
  return respuesta.data;
}

export async function servicioRegistrarUsuarioReal(
  datos: RegistroUsuarioRealFormulario
): Promise<RespuestaTokensAutenticacion> {
  const respuesta = await clienteApi.post<RespuestaTokensAutenticacion>(
    "/api/autenticacion/registro",
    datos
  );
  return respuesta.data;
}

export async function servicioListarUsuarios(): Promise<UsuarioSistema[]> {
  const respuesta = await clienteApi.get<UsuarioSistema[]>(
    "/api/organizacion/usuarios"
  );
  return respuesta.data;
}

export async function servicioCrearUsuario(
  datos: CrearUsuarioFormulario
): Promise<UsuarioSistema> {
  const respuesta = await clienteApi.post<UsuarioSistema>(
    "/api/organizacion/usuarios",
    datos
  );
  return respuesta.data;
}

export async function servicioAsignarPuestoUsuario(
  usuarioId: number,
  puestoBaseId: number | null
): Promise<UsuarioSistema> {
  const respuesta = await clienteApi.patch<UsuarioSistema>(
    `/api/organizacion/usuarios/${usuarioId}/puesto`,
    { puesto_base_id: puestoBaseId }
  );
  return respuesta.data;
}

export async function servicioActualizarCredencialSv(
  usuarioId: number,
  datos: ActualizarCredencialUsuarioFormulario
): Promise<UsuarioSistema> {
  const respuesta = await clienteApi.patch<UsuarioSistema>(
    `/api/organizacion/usuarios/${usuarioId}/credencial-sv`,
    datos
  );
  return respuesta.data;
}

export async function servicioListarPuestos(): Promise<PuestoVigilancia[]> {
  const respuesta = await clienteApi.get<PuestoVigilancia[]>(
    "/api/organizacion/puestos"
  );
  return respuesta.data;
}

export async function servicioCrearPuesto(
  datos: CrearPuestoFormulario
): Promise<PuestoVigilancia> {
  const respuesta = await clienteApi.post<PuestoVigilancia>(
    "/api/organizacion/puestos",
    datos
  );
  return respuesta.data;
}

// ============================================================================
// MÓDULO 2: MOTOR INTELIGENTE DE TURNOS 2X2, AUSENTISMOS Y RELEVANTES
// ============================================================================
export async function servicioConsultarTurnos(
  operadorId?: number,
  puestoId?: number
): Promise<ResumenLiquidacionTurnos> {
  const parametros: Record<string, number> = {};
  if (operadorId !== undefined && operadorId > 0) {
    parametros.operador_id = operadorId;
  }
  if (puestoId !== undefined && puestoId > 0) {
    parametros.puesto_id = puestoId;
  }
  const respuesta = await clienteApi.get<ResumenLiquidacionTurnos>(
    "/api/turnos",
    { params: parametros }
  );
  return respuesta.data;
}

export async function servicioGenerarRotacion2x2(
  solicitud: SolicitudGenerarRotacion2x2
): Promise<ResumenLiquidacionTurnos> {
  const respuesta = await clienteApi.post<ResumenLiquidacionTurnos>(
    "/api/turnos/generar-rotacion-2x2",
    solicitud
  );
  return respuesta.data;
}

export async function servicioGenerarCoberturaPuesto2x2(
  solicitud: SolicitudGenerarCoberturaPuesto2x2
): Promise<ResumenLiquidacionTurnos> {
  const respuesta = await clienteApi.post<ResumenLiquidacionTurnos>(
    "/api/turnos/cobertura-puesto-2x2",
    solicitud
  );
  return respuesta.data;
}

export async function servicioListarAusentismos(): Promise<
  AusentismoPersonal[]
> {
  const respuesta = await clienteApi.get<AusentismoPersonal[]>(
    "/api/turnos/ausentismos"
  );
  return respuesta.data;
}

export async function servicioRegistrarAusentismo(
  datos: RegistrarAusentismoFormulario
): Promise<AusentismoPersonal> {
  const respuesta = await clienteApi.post<AusentismoPersonal>(
    "/api/turnos/ausentismos",
    datos
  );
  return respuesta.data;
}

export async function servicioSugerirRelevantesTurno(
  turnoId: number
): Promise<CandidatoRelevanteSugerido[]> {
  const respuesta = await clienteApi.get<CandidatoRelevanteSugerido[]>(
    `/api/turnos/sugerir-relevantes/${turnoId}`
  );
  return respuesta.data;
}

export async function servicioAsignarRelevanteTurno(
  turnoId: number,
  datos: AsignarRelevanteTurnoFormulario
): Promise<TurnoOperativo> {
  const respuesta = await clienteApi.post<TurnoOperativo>(
    `/api/turnos/${turnoId}/asignar-relevante`,
    datos
  );
  return respuesta.data;
}

// ============================================================================
// MÓDULO 3: MINUTA DIGITAL, DOTACIÓN INDUMIL, ACTAS DE RELEVO Y ALERTA SOS
// ============================================================================
export async function servicioListarMinuta(
  puestoId?: number
): Promise<RegistroMinuta[]> {
  const parametros: Record<string, number> = {};
  if (puestoId !== undefined && puestoId > 0) {
    parametros.puesto_id = puestoId;
  }
  const respuesta = await clienteApi.get<RegistroMinuta[]>("/api/minuta", {
    params: parametros,
  });
  return respuesta.data;
}

export async function servicioCrearRegistroMinuta(
  datos: CrearRegistroMinutaFormulario
): Promise<RegistroMinuta> {
  const respuesta = await clienteApi.post<RegistroMinuta>("/api/minuta", datos);
  return respuesta.data;
}

export async function servicioObtenerDotacionPuesto(
  puestoId: number
): Promise<DotacionPuesto> {
  const respuesta = await clienteApi.get<DotacionPuesto>(
    `/api/minuta/dotacion/${puestoId}`
  );
  return respuesta.data;
}

export async function servicioListarActasRelevo(
  puestoId?: number
): Promise<ActaRelevoPuesto[]> {
  const parametros: Record<string, number> = {};
  if (puestoId !== undefined && puestoId > 0) {
    parametros.puesto_id = puestoId;
  }
  const respuesta = await clienteApi.get<ActaRelevoPuesto[]>(
    "/api/minuta/actas-relevo",
    { params: parametros }
  );
  return respuesta.data;
}

export async function servicioCrearActaRelevo(
  datos: CrearActaRelevoFormulario
): Promise<ActaRelevoPuesto> {
  const respuesta = await clienteApi.post<ActaRelevoPuesto>(
    "/api/minuta/actas-relevo",
    datos
  );
  return respuesta.data;
}

export async function servicioListarAlertasSos(
  soloActivas = false
): Promise<AlertaPanicoSos[]> {
  const respuesta = await clienteApi.get<AlertaPanicoSos[]>(
    "/api/minuta/panico-sos",
    { params: { solo_activas: soloActivas } }
  );
  return respuesta.data;
}

export async function servicioDispararAlertaSos(
  datos: DispararAlertaSosFormulario
): Promise<AlertaPanicoSos> {
  const respuesta = await clienteApi.post<AlertaPanicoSos>(
    "/api/minuta/panico-sos",
    datos
  );
  return respuesta.data;
}

export async function servicioAtenderAlertaSos(
  alertaId: number,
  datos: AtenderAlertaSosFormulario
): Promise<AlertaPanicoSos> {
  const respuesta = await clienteApi.patch<AlertaPanicoSos>(
    `/api/minuta/panico-sos/${alertaId}/atender`,
    datos
  );
  return respuesta.data;
}

// ============================================================================
// MÓDULO 4: SISTEMA DE INTERCAMBIO DE TURNOS
// ============================================================================
export async function servicioListarIntercambios(): Promise<
  SolicitudIntercambioTurno[]
> {
  const respuesta =
    await clienteApi.get<SolicitudIntercambioTurno[]>("/api/intercambios");
  return respuesta.data;
}

export async function servicioCrearIntercambio(
  datos: CrearSolicitudIntercambioFormulario
): Promise<SolicitudIntercambioTurno> {
  const respuesta = await clienteApi.post<SolicitudIntercambioTurno>(
    "/api/intercambios",
    datos
  );
  return respuesta.data;
}

export async function servicioResolverIntercambio(
  intercambioId: number,
  decision: ResolverIntercambioFormulario
): Promise<SolicitudIntercambioTurno> {
  const respuesta = await clienteApi.patch<SolicitudIntercambioTurno>(
    `/api/intercambios/${intercambioId}/resolver`,
    decision
  );
  return respuesta.data;
}

// ============================================================================
// FASES 5, 6 Y 7: RONDAS QR/GPS, COLA OFFLINE, AUDITORÍA Y REPORTES OFICIALES
// ============================================================================
export async function servicioListarPuntosControl(): Promise<
  PuntoControlRonda[]
> {
  const respuesta = await clienteApi.get<PuntoControlRonda[]>(
    "/api/rondas/puntos-control"
  );
  return respuesta.data;
}

export async function servicioListarMarcacionesRonda(): Promise<
  MarcacionRonda[]
> {
  const respuesta = await clienteApi.get<MarcacionRonda[]>(
    "/api/rondas/marcaciones"
  );
  return respuesta.data;
}

export async function servicioRegistrarMarcacionRonda(
  datos: RegistrarMarcacionRondaFormulario
): Promise<MarcacionRonda> {
  const respuesta = await clienteApi.post<MarcacionRonda>(
    "/api/rondas/marcar",
    datos
  );
  return respuesta.data;
}

export async function servicioSincronizarColaOffline(
  marcaciones: RegistrarMarcacionRondaFormulario[]
): Promise<MarcacionRonda[]> {
  const respuesta = await clienteApi.post<MarcacionRonda[]>(
    "/api/rondas/sincronizar-cola-offline",
    { marcaciones }
  );
  return respuesta.data;
}

export async function servicioAuditarCoberturaPuestos(): Promise<
  AlertaCoberturaPuesto[]
> {
  const respuesta = await clienteApi.get<AlertaCoberturaPuesto[]>(
    "/api/rondas/auditoria-cobertura"
  );
  return respuesta.data;
}

export async function servicioDescargarPrenominaCsv(): Promise<void> {
  const respuesta = await clienteApi.get<Blob>(
    "/api/reportes/prenomina-colombia-csv",
    { responseType: "blob" }
  );
  const urlDescarga = window.URL.createObjectURL(new Blob([respuesta.data]));
  const enlace = document.createElement("a");
  enlace.href = urlDescarga;
  enlace.setAttribute("download", "prenomina_laboral_colombia_sentinel.csv");
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  window.URL.revokeObjectURL(urlDescarga);
}

export async function servicioAbrirLibroFoliadoOficial(): Promise<void> {
  const respuesta = await clienteApi.get<string>(
    "/api/reportes/minuta-foliada-oficial",
    { responseType: "text" as "json" }
  );
  const nuevaVentana = window.open("", "_blank");
  if (nuevaVentana) {
    nuevaVentana.document.open();
    nuevaVentana.document.write(respuesta.data);
    nuevaVentana.document.close();
  }
}

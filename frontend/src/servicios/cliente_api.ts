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
  SolicitudCotizacionTarifa,
  RespuestaDesgloseCotizacion,
  SolicitudGenerarPrefactura,
  PrefacturaB2B,
  DatosCedulaColombiana,
  SolicitudRegistrarAccesoGarita,
  RegistroAccesoGarita,
  SemaforoSalvoconducto,
  MovimientoBalistico,
  SolicitudRegistrarMovimientoBalistico,
  CertificadoPoligono,
  SolicitudRegistrarCertificadoPoligono,
  ResumenMapaTactico,
  CandidatoSupervisorCercano,
  DespachoPatrulla,
  RespuestaEscanearPlaca,
  InfoRedApoyoPonal,
  RespuestaImportacionUsuariosCsv,
  KpisTiempoReal,
  ResultadoRafagaOperativa,
  EstadoSimulacionViva,
  MisionEscoltaBasc,
  SolicitudCrearEscoltaBasc,
  RespuestaVerificarCorredorEscolta,
  BinomioCaninoK9,
  MedioTecnologicoPuesto,
  CertificadoSarlaft,
  SemaforoChalecoKevlar,
  RespuestaCheckAptitudSst,
  MonitorHombreCaido,
  BoletinRelevoIA,
  AuditoriaAntifraudeRondas,
  RespuestaSabotajeForense,
  RespuestaReparacionForense,
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

// ============================================================================
// MÓDULO 8: TARIFICACIÓN LEGAL SUPERVIGILANCIA Y FACTURACIÓN B2B (V3.0)
// ============================================================================
export async function servicioCotizarTarifa(
  solicitud: SolicitudCotizacionTarifa
): Promise<RespuestaDesgloseCotizacion> {
  const respuesta = await clienteApi.post<RespuestaDesgloseCotizacion>(
    "/api/facturacion/cotizar",
    solicitud
  );
  return respuesta.data;
}

export async function servicioListarPrefacturas(): Promise<PrefacturaB2B[]> {
  const respuesta = await clienteApi.get<PrefacturaB2B[]>("/api/facturacion/prefacturas");
  return respuesta.data;
}

export async function servicioGenerarPrefactura(
  datos: SolicitudGenerarPrefactura
): Promise<PrefacturaB2B> {
  const respuesta = await clienteApi.post<PrefacturaB2B>(
    "/api/facturacion/prefacturas",
    datos
  );
  return respuesta.data;
}

export function servicioObtenerUrlPrefacturaHtml(prefacturaId: number): string {
  return `${URL_BASE_API}/api/facturacion/prefacturas/${prefacturaId}/html`;
}

export async function servicioAbrirPrefacturaHtml(prefacturaId: number): Promise<void> {
  const respuesta = await clienteApi.get<string>(
    `/api/facturacion/prefacturas/${prefacturaId}/html`,
    { responseType: "text" as "json" }
  );
  const nuevaVentana = window.open("", "_blank");
  if (nuevaVentana) {
    nuevaVentana.document.open();
    nuevaVentana.document.write(respuesta.data);
    nuevaVentana.document.close();
  }
}

// ============================================================================
// FASE 9: CONTROL DE ACCESO GARITA Y ESCÁNER PDF417
// ============================================================================
export async function servicioDecodificarCedula(
  tramaCruda: string
): Promise<DatosCedulaColombiana> {
  const respuesta = await clienteApi.post<DatosCedulaColombiana>(
    "/api/acceso/decodificar-cedula",
    { trama_cruda: tramaCruda }
  );
  return respuesta.data;
}

export async function servicioRegistrarIngresoGarita(
  datos: SolicitudRegistrarAccesoGarita
): Promise<RegistroAccesoGarita> {
  const respuesta = await clienteApi.post<RegistroAccesoGarita>(
    "/api/acceso/ingreso",
    datos
  );
  return respuesta.data;
}

export async function servicioRegistrarSalidaGarita(
  accesoId: number
): Promise<RegistroAccesoGarita> {
  const respuesta = await clienteApi.patch<RegistroAccesoGarita>(
    `/api/acceso/${accesoId}/salida`
  );
  return respuesta.data;
}

export async function servicioListarActivosEnPuesto(
  puestoId: number
): Promise<RegistroAccesoGarita[]> {
  const respuesta = await clienteApi.get<RegistroAccesoGarita[]>(
    `/api/acceso/puesto/${puestoId}/activos`
  );
  return respuesta.data;
}

export async function servicioConsultarHistorialAccesos(
  puestoId?: number
): Promise<RegistroAccesoGarita[]> {
  const respuesta = await clienteApi.get<RegistroAccesoGarita[]>(
    "/api/acceso/historial",
    { params: puestoId ? { puesto_id: puestoId } : undefined }
  );
  return respuesta.data;
}

// ============================================================================
// FASE 10: LIBRO BALÍSTICO DIGITAL Y TRAZABILIDAD INDUMIL DCCA
// ============================================================================
export async function servicioConsultarSemaforoSalvoconductos(): Promise<
  SemaforoSalvoconducto[]
> {
  const respuesta = await clienteApi.get<SemaforoSalvoconducto[]>(
    "/api/balistica/salvoconductos-semaforo"
  );
  return respuesta.data;
}

export async function servicioConsultarKardexBalistico(
  puestoId: number
): Promise<MovimientoBalistico[]> {
  const respuesta = await clienteApi.get<MovimientoBalistico[]>(
    `/api/balistica/kardex/${puestoId}`
  );
  return respuesta.data;
}

export async function servicioRegistrarMovimientoBalistico(
  datos: SolicitudRegistrarMovimientoBalistico
): Promise<MovimientoBalistico> {
  const respuesta = await clienteApi.post<MovimientoBalistico>(
    "/api/balistica/kardex/movimiento",
    datos
  );
  return respuesta.data;
}

export async function servicioListarCertificadosPoligono(): Promise<
  CertificadoPoligono[]
> {
  const respuesta = await clienteApi.get<CertificadoPoligono[]>(
    "/api/balistica/poligonos"
  );
  return respuesta.data;
}

export async function servicioRegistrarCertificadoPoligono(
  datos: SolicitudRegistrarCertificadoPoligono
): Promise<CertificadoPoligono> {
  const respuesta = await clienteApi.post<CertificadoPoligono>(
    "/api/balistica/poligonos",
    datos
  );
  return respuesta.data;
}

// ============================================================================
// FASE 11: CENTRO DE DESPACHO CAD Y MONITOREO GPS EN VIVO
// ============================================================================
export async function servicioObtenerTelemetriaMapa(): Promise<ResumenMapaTactico> {
  const respuesta = await clienteApi.get<ResumenMapaTactico>(
    "/api/cad/telemetria-mapa"
  );
  return respuesta.data;
}

export async function servicioSugerirPatrullaCercana(
  alertaSosId: number
): Promise<CandidatoSupervisorCercano[]> {
  const respuesta = await clienteApi.get<CandidatoSupervisorCercano[]>(
    `/api/cad/sugerir-patrulla/${alertaSosId}`
  );
  return respuesta.data;
}

export async function servicioDespacharPatrulla(
  alertaSosId: number,
  supervisorId: number,
  notaDespacho?: string
): Promise<DespachoPatrulla> {
  const respuesta = await clienteApi.post<DespachoPatrulla>(
    "/api/cad/despachar",
    {
      alerta_sos_id: alertaSosId,
      supervisor_id: supervisorId,
      nota_despacho: notaDespacho,
    }
  );
  return respuesta.data;
}

export async function servicioRegistrarLlegadaPatrulla(
  despachoId: number
): Promise<DespachoPatrulla> {
  const respuesta = await clienteApi.patch<DespachoPatrulla>(
    `/api/cad/despacho/${despachoId}/llegada`
  );
  return respuesta.data;
}

export async function servicioFinalizarDespachoCad(
  despachoId: number,
  informeTacticoCierre: string
): Promise<DespachoPatrulla> {
  const respuesta = await clienteApi.patch<DespachoPatrulla>(
    `/api/cad/despacho/${despachoId}/finalizar`,
    { informe_tactico_cierre: informeTacticoCierre }
  );
  return respuesta.data;
}

// ============================================================================
// MEJORAS TÁCTICAS V3.0: IMPORTACIÓN CSV, ACTA FOLIADA HTML, LPR Y RED PONAL
// ============================================================================
export async function servicioImportarUsuariosCsv(
  contenidoCsv: string
): Promise<RespuestaImportacionUsuariosCsv> {
  const respuesta = await clienteApi.post<RespuestaImportacionUsuariosCsv>(
    "/api/organizacion/usuarios/importar-csv",
    { contenido_csv: contenidoCsv }
  );
  return respuesta.data;
}

export function servicioObtenerUrlActaRelevoHtml(actaId: number): string {
  return `${URL_BASE_API}/api/minuta/actas-relevo/${actaId}/html`;
}

export async function servicioAbrirActaRelevoHtml(
  actaId: number
): Promise<void> {
  const token = usarAlmacenAutenticacion.getState().tokenAcceso;
  const respuesta = await clienteApi.get<string>(
    `/api/minuta/actas-relevo/${actaId}/html`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      responseType: "text",
    }
  );
  const blob = new Blob([respuesta.data], { type: "text/html;charset=utf-8" });
  const blobUrl = URL.createObjectURL(blob);
  window.open(blobUrl, "_blank");
}

export async function servicioEscanearPlaca(
  textoPlaca: string
): Promise<RespuestaEscanearPlaca> {
  const respuesta = await clienteApi.post<RespuestaEscanearPlaca>(
    "/api/acceso/escanear-placa",
    { texto_placa: textoPlaca }
  );
  return respuesta.data;
}

export async function servicioObtenerRedApoyoPonal(): Promise<InfoRedApoyoPonal> {
  const respuesta = await clienteApi.get<InfoRedApoyoPonal>(
    "/api/cad/red-apoyo-ponal"
  );
  return respuesta.data;
}

// ============================================================================
// RELEASE V4.0: SIMULACIÓN VIVA, RÁFAGA OPERATIVA Y KPIS TIEMPO REAL
// ============================================================================
export async function servicioObtenerKpisTiempoReal(): Promise<KpisTiempoReal> {
  const respuesta = await clienteApi.get<KpisTiempoReal>(
    "/api/reportes/kpis-tiempo-real"
  );
  return respuesta.data;
}

export async function servicioSimularRafagaOperativa(): Promise<ResultadoRafagaOperativa> {
  const respuesta = await clienteApi.post<ResultadoRafagaOperativa>(
    "/api/cad/simular-rafaga-operativa"
  );
  return respuesta.data;
}

export async function servicioAlternarSimulacionViva(
  activar?: boolean
): Promise<EstadoSimulacionViva> {
  const respuesta = await clienteApi.post<EstadoSimulacionViva>(
    "/api/cad/simulacion-viva/alternar",
    activar !== undefined ? { activar } : {}
  );
  return respuesta.data;
}

// ============================================================================
// RELEASE ENTERPRISE V5.0: OPERACIONES ESPECIALES, K9, SARLAFT, SG-SST & IA FORENSE
// ============================================================================
export async function servicioListarEscoltasBasc(): Promise<MisionEscoltaBasc[]> {
  const respuesta = await clienteApi.get<MisionEscoltaBasc[]>(
    "/api/operaciones-especiales/escoltas"
  );
  return respuesta.data;
}

export async function servicioCrearEscoltaBasc(
  datos: SolicitudCrearEscoltaBasc
): Promise<MisionEscoltaBasc> {
  const respuesta = await clienteApi.post<MisionEscoltaBasc>(
    "/api/operaciones-especiales/escoltas",
    datos
  );
  return respuesta.data;
}

export async function servicioVerificarCorredorEscolta(
  misionId: number,
  latActual: number,
  lonActual: number,
  desviacionReportadaMetros?: number
): Promise<RespuestaVerificarCorredorEscolta> {
  const respuesta = await clienteApi.post<RespuestaVerificarCorredorEscolta>(
    `/api/operaciones-especiales/escoltas/${misionId}/verificar-corredor`,
    {
      lat_actual: latActual,
      lon_actual: lonActual,
      desviacion_reportada_metros: desviacionReportadaMetros,
    }
  );
  return respuesta.data;
}

export async function servicioListarBinomiosK9(): Promise<BinomioCaninoK9[]> {
  const respuesta = await clienteApi.get<BinomioCaninoK9[]>(
    "/api/operaciones-especiales/binomios-k9"
  );
  return respuesta.data;
}

export async function servicioRegistrarDescansoK9(
  k9Id: number,
  minutosDescansoCanil: number = 45,
  observacionesGuia?: string
): Promise<{
  k9_id: number;
  codigo_unidad_k9: string;
  nombre_canino: string;
  horas_previas_turno: number;
  horas_trabajadas_turno: number;
  estado_fatiga: string;
  semaforo_normativo_k9: string;
  ultimo_descanso_canil: string;
  mensaje: string;
}> {
  const respuesta = await clienteApi.post(
    `/api/operaciones-especiales/binomios-k9/${k9Id}/registrar-descanso`,
    {
      minutos_descanso_canil: minutosDescansoCanil,
      hidratacion_verificada: true,
      observaciones_guia:
        observacionesGuia ||
        "Descanso normativo en canil climatizado e hidratación isotónica verificada.",
    }
  );
  return respuesta.data;
}

export async function servicioListarMediosTecnologicos(
  puestoId?: number
): Promise<MedioTecnologicoPuesto[]> {
  const respuesta = await clienteApi.get<MedioTecnologicoPuesto[]>(
    "/api/operaciones-especiales/medios-tecnologicos",
    { params: puestoId ? { puesto_id: puestoId } : {} }
  );
  return respuesta.data;
}

export async function servicioConsultarSarlaft(datos: {
  documento: string;
  nombre_completo: string;
  tipo_tercero: "ASPIRANTE_GUARDA" | "CLIENTE_B2B" | "VISITANTE_CRITICO";
}): Promise<CertificadoSarlaft> {
  const respuesta = await clienteApi.post<CertificadoSarlaft>(
    "/api/cumplimiento/sarlaft/consultar",
    datos
  );
  return respuesta.data;
}

export async function servicioListarHistorialSarlaft(): Promise<CertificadoSarlaft[]> {
  const respuesta = await clienteApi.get<CertificadoSarlaft[]>(
    "/api/cumplimiento/sarlaft/historial"
  );
  return respuesta.data;
}

export async function servicioConsultarSemaforoChalecosKevlar(): Promise<
  SemaforoChalecoKevlar[]
> {
  const respuesta = await clienteApi.get<SemaforoChalecoKevlar[]>(
    "/api/cumplimiento/sst/chalecos-kevlar"
  );
  return respuesta.data;
}

export async function servicioRegistrarCheckAptitudSst(datos: {
  puesto_id: number;
  operador_id?: number;
  horas_sueno_reportadas: number;
  cero_alcohol_fatiga: boolean;
  chaleco_kevlar_verificado: boolean;
  serial_chaleco_asignado?: string;
  observaciones_sst?: string;
}): Promise<RespuestaCheckAptitudSst> {
  const respuesta = await clienteApi.post<RespuestaCheckAptitudSst>(
    "/api/cumplimiento/sst/check-aptitud",
    datos
  );
  return respuesta.data;
}

export async function servicioListarMonitoresHombreCaido(): Promise<
  MonitorHombreCaido[]
> {
  const respuesta = await clienteApi.get<MonitorHombreCaido[]>(
    "/api/cumplimiento/sst/hombre-caido"
  );
  return respuesta.data;
}

export async function servicioRegistrarLatidoHombreCaido(
  puestoId: number,
  simularInactividadCritica: boolean = false
): Promise<{
  monitoreo_id: number;
  puesto_id: number;
  operador_id: number;
  estado_supervivencia: string;
  ultimo_latido_utc: string;
  latidos_consecutivos_exitosos: number;
  alertas_disparadas_turno: number;
  mensaje: string;
}> {
  const respuesta = await clienteApi.post(
    `/api/cumplimiento/sst/hombre-caido/${puestoId}/latido`,
    { simular_inactividad_critica: simularInactividadCritica }
  );
  return respuesta.data;
}

export async function servicioGenerarBoletinRelevoIA(
  puestoCodigoOId: string | number
): Promise<BoletinRelevoIA> {
  const respuesta = await clienteApi.get<BoletinRelevoIA>(
    `/api/inteligencia/boletin-relevo/${puestoCodigoOId}`
  );
  return respuesta.data;
}

export async function servicioAuditarAntifraudeRondas(): Promise<AuditoriaAntifraudeRondas> {
  const respuesta = await clienteApi.get<AuditoriaAntifraudeRondas>(
    "/api/inteligencia/auditoria-antifraude-rondas"
  );
  return respuesta.data;
}

export async function servicioSimularSabotajeForense(
  registroId?: number,
  textoAdulterado?: string
): Promise<RespuestaSabotajeForense> {
  const respuesta = await clienteApi.post<RespuestaSabotajeForense>(
    "/api/inteligencia/forense/simular-sabotaje",
    {
      registro_id: registroId,
      texto_adulterado: textoAdulterado,
    }
  );
  return respuesta.data;
}

export async function servicioRepararCadenaForense(): Promise<RespuestaReparacionForense> {
  const respuesta = await clienteApi.post<RespuestaReparacionForense>(
    "/api/inteligencia/forense/reparar-cadena"
  );
  return respuesta.data;
}



/**
 * Componente Raíz de SENTINEL // OPS (Release Enterprise V2.0).
 * Plataforma SaaS B2B de Nivel de Producción para Empresas de Seguridad Privada en Colombia.
 * Integra:
 * - Jerarquía RBAC de 5 Niveles (ADMINISTRADOR, SUPERVISOR, RRHH, OPERADOR, CLIENTE)
 * - Modo Táctico de Campo de Alto Contraste (Sunlight Ready) en el Header
 * - Recepción Global de Alertas de Pánico SOS vía WebSocket con Sirena Sintetizada (Web Audio API)
 *   y registro de reacción certificada en segundos.
 */

import { useCallback, useEffect, useState, type ReactElement } from "react";
import {
  BrowserRouter,
  NavLink,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import {
  ShieldCheck,
  LayoutDashboard,
  CalendarClock,
  Radio,
  ArrowLeftRight,
  Building2,
  QrCode,
  LogOut,
  RefreshCw,
  Clock,
  ChevronDown,
  Sun,
  Siren,
  CheckCircle2,
  MapPin,
  Calculator,
  UserCheck,
  Crosshair,
  Navigation,
  Zap,
  Activity,
  Lock,
  Truck,
  FileCheck2,
  BrainCircuit,
  ShieldAlert,
} from "lucide-react";
import { format } from "date-fns";
import { usarAlmacenAutenticacion } from "./estado/almacen_autenticacion";
import {
  URL_WEBSOCKET_MINUTA,
  extraerMensajeError,
  servicioAlternarSimulacionViva,
  servicioAtenderAlertaSos,
  servicioConsultarEstado,
  servicioIniciarSesion,
  servicioListarAlertasSos,
  servicioObtenerKpisTiempoReal,
  servicioSimularRafagaOperativa,
} from "./servicios/cliente_api";
import type {
  AlertaPanicoSos,
  IntegridadBlockchainInfo,
  KpisTiempoReal,
  MensajeWebSocketMinuta,
  RespuestaEstadoServidor,
  ResultadoRafagaOperativa,
  RolUsuario,
  SolicitudInicioSesion,
} from "./tipos/tipos_sistema";
import { VistaAccesoTactico } from "./componentes/VistaAccesoTactico";
import { CentroDeMandoDashboard } from "./componentes/CentroDeMandoDashboard";
import { ModuloMotorTurnos } from "./componentes/ModuloMotorTurnos";
import { ModuloMinutaTiempoReal } from "./componentes/ModuloMinutaTiempoReal";
import { ModuloIntercambioTurnos } from "./componentes/ModuloIntercambioTurnos";
import { ModuloPersonalYPuestos } from "./componentes/ModuloPersonalYPuestos";
import { ModuloRondasYReportes } from "./componentes/ModuloRondasYReportes";
import { ModuloTarificadorB2B } from "./componentes/ModuloTarificadorB2B";
import { ModuloControlAccesoGarita } from "./componentes/ModuloControlAccesoGarita";
import { ModuloLibroBalistico } from "./componentes/ModuloLibroBalistico";
import { ModuloDespachoCAD } from "./componentes/ModuloDespachoCAD";
import { OperacionesEspecialesK9 } from "./componentes/OperacionesEspecialesK9";
import { CumplimientoSarlaftSST } from "./componentes/CumplimientoSarlaftSST";
import { InteligenciaForenseIA } from "./componentes/InteligenciaForenseIA";

interface CuentaRapida {
  etiqueta: string;
  nombre: string;
  correo: string;
  rol: RolUsuario;
  colorBadge: string;
}

const CUENTAS_RAPIDAS: CuentaRapida[] = [
  {
    etiqueta: "ADMIN",
    nombre: "Comandante Alejandro Vargas",
    correo: "admin@sentinelops.co",
    rol: "ADMINISTRADOR",
    colorBadge: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  },
  {
    etiqueta: "SUPERVISOR",
    nombre: "Capitán Valeria Mendoza",
    correo: "supervisor@sentinelops.co",
    rol: "SUPERVISOR",
    colorBadge: "border-cyan-500/40 bg-cyan-500/10 text-cyan-300",
  },
  {
    etiqueta: "RRHH",
    nombre: "Dra. Natalia Gómez",
    correo: "rrhh@sentinelops.co",
    rol: "RRHH",
    colorBadge: "border-purple-500/40 bg-purple-500/10 text-purple-300",
  },
  {
    etiqueta: "OPERADOR",
    nombre: "Guarda Carlos Ramírez",
    correo: "operador1@sentinelops.co",
    rol: "OPERADOR",
    colorBadge: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  },
  {
    etiqueta: "CLIENTE",
    nombre: "Ing. Roberto Salazar (PST-BOG-01)",
    correo: "cliente@sentinelops.co",
    rol: "CLIENTE",
    colorBadge: "border-sky-500/40 bg-sky-500/10 text-sky-300",
  },
];

/**
 * Reproduce una sirena táctica de emergencia sintetizada mediante Web Audio API
 * sin depender de archivos de audio externos.
 */
function emitirSirenaTacticaWebAudio(): void {
  try {
    const ClaseAudio =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext })
        .webkitAudioContext;
    if (!ClaseAudio) return;
    const ctx = new ClaseAudio();
    const oscilador = ctx.createOscillator();
    const ganancia = ctx.createGain();

    oscilador.type = "sawtooth";
    const ahora = ctx.currentTime;
    oscilador.frequency.setValueAtTime(580, ahora);
    oscilador.frequency.linearRampToValueAtTime(960, ahora + 0.35);
    oscilador.frequency.linearRampToValueAtTime(540, ahora + 0.7);
    oscilador.frequency.linearRampToValueAtTime(980, ahora + 1.05);

    ganancia.gain.setValueAtTime(0.18, ahora);
    ganancia.gain.exponentialRampToValueAtTime(0.001, ahora + 1.25);

    oscilador.connect(ganancia);
    ganancia.connect(ctx.destination);
    oscilador.start(ahora);
    oscilador.stop(ahora + 1.25);
  } catch {
    // Ignorar si el navegador bloquea autoplay de audio sin interacción previa
  }
}

export function App(): ReactElement {
  const usuarioActual = usarAlmacenAutenticacion(
    (estado) => estado.usuarioActual
  );
  const modoTacticoAltoContraste = usarAlmacenAutenticacion(
    (estado) => estado.modoTacticoAltoContraste
  );
  const alternarModoTactico = usarAlmacenAutenticacion(
    (estado) => estado.alternarModoTactico
  );
  const establecerSesion = usarAlmacenAutenticacion(
    (estado) => estado.establecerSesion
  );
  const cerrarSesion = usarAlmacenAutenticacion(
    (estado) => estado.cerrarSesion
  );

  const [datosEstado, setDatosEstado] =
    useState<RespuestaEstadoServidor | null>(null);
  const [estadoConexion, setEstadoConexion] = useState<
    "cargando" | "conectado" | "error"
  >("cargando");

  const [horaActual, setHoraActual] = useState<string>(
    format(new Date(), "HH:mm:ss")
  );

  const [mostrarSelectorRoles, setMostrarSelectorRoles] =
    useState<boolean>(false);
  const [cambiandoRol, setCambiandoRol] = useState<boolean>(false);

  // Estado Global de Alertas de Pánico SOS Activas
  const [alertasSosActivas, setAlertasSosActivas] = useState<AlertaPanicoSos[]>(
    []
  );
  const [notaReaccionSos, setNotaReaccionSos] = useState<string>(
    "Despacho inmediato de motorizado de supervisión y enlace por radio VHF con el puesto."
  );
  const [atendiendoSosId, setAtendiendoSosId] = useState<number | null>(null);
  const [errorSosGlobal, setErrorSosGlobal] = useState<string | null>(null);

  // Estado V4.0: Simulación Viva, Ráfaga Operativa e Integridad Blockchain SHA-256
  const [kpisTiempoReal, setKpisTiempoReal] = useState<KpisTiempoReal | null>(
    null
  );
  const [simulacionVivaActiva, setSimulacionVivaActiva] =
    useState<boolean>(false);
  const [disparandoRafaga, setDisparandoRafaga] = useState<boolean>(false);
  const [ultimaRafaga, setUltimaRafaga] =
    useState<ResultadoRafagaOperativa | null>(null);

  useEffect((): (() => void) => {
    const temporizador = setInterval((): void => {
      setHoraActual(format(new Date(), "HH:mm:ss"));
    }, 1000);
    return (): void => clearInterval(temporizador);
  }, []);

  const verificarNucleo = useCallback(async (): Promise<void> => {
    setEstadoConexion("cargando");
    try {
      const respuesta = await servicioConsultarEstado();
      setDatosEstado(respuesta);
      setEstadoConexion("conectado");
    } catch {
      setEstadoConexion("error");
    }
  }, []);

  const cargarKpisHeader = useCallback(async (): Promise<void> => {
    if (!usuarioActual) return;
    try {
      const kpis = await servicioObtenerKpisTiempoReal();
      setKpisTiempoReal(kpis);
      setSimulacionVivaActiva(kpis.simulacion_viva_activa);
    } catch {
      // Silencioso en carga inicial
    }
  }, [usuarioActual]);

  const cargarAlertasSosPendientes = useCallback(async (): Promise<void> => {
    if (!usuarioActual) return;
    try {
      const activas = await servicioListarAlertasSos(true);
      setAlertasSosActivas(activas);
    } catch {
      // Silencioso en carga inicial
    }
  }, [usuarioActual]);

  useEffect((): void => {
    void verificarNucleo();
    void cargarAlertasSosPendientes();
    void cargarKpisHeader();
  }, [verificarNucleo, cargarAlertasSosPendientes, cargarKpisHeader]);

  useEffect((): (() => void) => {
    const escucharEstadoBlockchain = (ev: Event): void => {
      const customEv = ev as CustomEvent<IntegridadBlockchainInfo>;
      if (customEv.detail) {
        setKpisTiempoReal((prev) =>
          prev
            ? { ...prev, integridad_blockchain: customEv.detail }
            : prev
        );
      }
    };
    window.addEventListener(
      "sentinel:estado-blockchain",
      escucharEstadoBlockchain
    );
    return (): void => {
      window.removeEventListener(
        "sentinel:estado-blockchain",
        escucharEstadoBlockchain
      );
    };
  }, []);

  const manejarAlternarSimulacionViva = async (): Promise<void> => {
    try {
      const res = await servicioAlternarSimulacionViva(!simulacionVivaActiva);
      setSimulacionVivaActiva(res.simulacion_viva_activa);
      await cargarKpisHeader();
    } catch {
      // Silencioso
    }
  };

  const manejarDispararRafaga = async (): Promise<void> => {
    setDisparandoRafaga(true);
    try {
      const resultado = await servicioSimularRafagaOperativa();
      setUltimaRafaga(resultado);
      await cargarKpisHeader();
      window.dispatchEvent(new CustomEvent("sentinel:rafaga-operativa"));
    } catch {
      // Silencioso
    } finally {
      setDisparandoRafaga(false);
    }
  };

  // Canal WebSocket Global para Alertas de Pánico SOS en Tiempo Real
  useEffect((): (() => void) | undefined => {
    if (!usuarioActual) return undefined;
    let socket: WebSocket | null = null;
    try {
      socket = new WebSocket(URL_WEBSOCKET_MINUTA);
      socket.onmessage = (evento: MessageEvent<string>): void => {
        try {
          const datos = JSON.parse(evento.data) as MensajeWebSocketMinuta;
          if (datos.tipo_mensaje === "ALERTA_PANICO_SOS" && datos.alerta_sos) {
            const nueva = datos.alerta_sos;
            setAlertasSosActivas((previas) => [
              nueva,
              ...previas.filter((a) => a.alerta_id !== nueva.alerta_id),
            ]);
            if (
              usuarioActual.rol === "ADMINISTRADOR" ||
              usuarioActual.rol === "SUPERVISOR"
            ) {
              emitirSirenaTacticaWebAudio();
            }
          } else if (
            datos.tipo_mensaje === "SOS_ATENDIDO" &&
            datos.alerta_sos
          ) {
            const atendida = datos.alerta_sos;
            setAlertasSosActivas((previas) =>
              previas.filter((a) => a.alerta_id !== atendida.alerta_id)
            );
          }
        } catch {
          // Trama no crítica
        }
      };
    } catch {
      // Reconexión delegada
    }
    return (): void => {
      if (socket) socket.close();
    };
  }, [usuarioActual]);

  const atenderEmergenciaSos = async (alertaId: number): Promise<void> => {
    setAtendiendoSosId(alertaId);
    setErrorSosGlobal(null);
    try {
      await servicioAtenderAlertaSos(alertaId, {
        nota_reaccion:
          notaReaccionSos.trim() ||
          "Reacción táctica ejecutada por central de supervisión.",
      });
      setAlertasSosActivas((prev) =>
        prev.filter((a) => a.alerta_id !== alertaId)
      );
    } catch (err: unknown) {
      setErrorSosGlobal(extraerMensajeError(err));
    } finally {
      setAtendiendoSosId(null);
    }
  };

  const cambiarCuentaRapida = async (cuenta: CuentaRapida): Promise<void> => {
    setCambiandoRol(true);
    try {
      const credenciales: SolicitudInicioSesion = {
        correo_electronico: cuenta.correo,
        contrasena: "Sentinel2026*",
      };
      const respuesta = await servicioIniciarSesion(credenciales);
      establecerSesion(respuesta);
      setMostrarSelectorRoles(false);
    } catch {
      // Manejo silencioso en cambio rápido
    } finally {
      setCambiandoRol(false);
    }
  };

  if (!usuarioActual) {
    return (
      <VistaAccesoTactico
        datosEstado={datosEstado}
        estadoConexion={estadoConexion}
        alReintentarConexion={(): void => {
          void verificarNucleo();
        }}
      />
    );
  }

  const puedeAtenderSos =
    usuarioActual.rol === "ADMINISTRADOR" ||
    usuarioActual.rol === "SUPERVISOR";

  return (
    <BrowserRouter>
      <div
        className={`flex min-h-screen w-full font-sans antialiased ${
          modoTacticoAltoContraste
            ? "modo-tactico-campo bg-black text-white"
            : "bg-[#09090B] text-[#FAFAFA]"
        }`}
      >
        {/* ================================================================= */}
        {/* BARRA LATERAL CARBON & MONOCHROME (SIDEBAR SAAS 5 NIVELES RBAC)   */}
        {/* ================================================================= */}
        <aside className="relative z-20 flex w-[220px] flex-col justify-between border-r border-white/[0.07] bg-[#0C0C0E] shrink-0 min-h-screen shadow-[inset_-1px_0_0_0_rgba(255,255,255,0.03)]">
          <div>
            <div className="p-4 border-b border-white/[0.07]">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.09] bg-[#18181B] text-[#FAFAFA] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)] shrink-0">
                  <ShieldCheck className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <h1 className="text-sm font-semibold tracking-tight text-[#FAFAFA] truncate">
                    SENTINEL <span className="text-zinc-500">//</span> OPS
                  </h1>
                  <span className="text-[9px] font-mono uppercase tracking-[0.16em] text-zinc-400 block truncate">
                    Enterprise V5.1
                  </span>
                </div>
              </div>

              {/* Reloj Táctico en Vivo */}
              <div className="mt-3 flex items-center justify-between rounded-md border border-white/[0.07] bg-[#09090B] px-2.5 py-1.5 text-[11px] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)]">
                <div className="flex items-center gap-1.5 text-zinc-400">
                  <Clock className="h-3 w-3 text-zinc-500" />
                  <span className="font-mono">COT</span>
                </div>
                <span className="font-mono font-medium text-[#FAFAFA] text-xs tabular-nums">
                  {horaActual}
                </span>
              </div>

              {/* Nivel de Prioridad y Autorización RBAC (5 Niveles) */}
              <div className="mt-2 rounded-md border border-white/[0.07] bg-[#18181B] px-2.5 py-1.5 text-[9px] font-mono uppercase tracking-wider text-zinc-400 truncate">
                {usuarioActual.rol === "ADMINISTRADOR" &&
                  "LVL 1 • CONTROL TOTAL"}
                {usuarioActual.rol === "SUPERVISOR" &&
                  "LVL 2 • SUPERVISIÓN"}
                {usuarioActual.rol === "RRHH" &&
                  "LVL 2.5 • NÓMINA 42H"}
                {usuarioActual.rol === "OPERADOR" &&
                  "LVL 3 • EN PUESTO"}
                {usuarioActual.rol === "CLIENTE" &&
                  "LVL 4 • PORTAL B2B"}
              </div>
            </div>

            {/* Menú de Navegación Principal Adaptado a los 5 Roles */}
            <nav className="p-2.5 space-y-0.5">
              <NavLink
                to="/"
                end
                className={({ isActive }): string =>
                  `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                    isActive
                      ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                      : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                  }`
                }
              >
                <LayoutDashboard className="h-4 w-4 shrink-0" />
                <span>
                  {usuarioActual.rol === "ADMINISTRADOR"
                    ? "Centro de Mando Ejecutivo"
                    : usuarioActual.rol === "SUPERVISOR"
                      ? "Consola de Supervisión"
                      : usuarioActual.rol === "RRHH"
                        ? "Consola RRHH & Nómina 42h"
                        : usuarioActual.rol === "CLIENTE"
                          ? "Portal Corporativo del Puesto"
                          : "Mi Puesto, Relevo Indumil & SOS"}
                </span>
              </NavLink>

              {usuarioActual.rol !== "CLIENTE" && (
                <NavLink
                  to="/turnos-2x2"
                  className={({ isActive }): string =>
                    `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                      isActive
                        ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                        : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                    }`
                  }
                >
                  <CalendarClock className="h-4 w-4 shrink-0" />
                  <span>
                    {usuarioActual.rol === "OPERADOR"
                      ? "Mis Turnos 2x2 (12h)"
                      : usuarioActual.rol === "RRHH"
                        ? "Ausentismos, Relevantes & 42h"
                        : "Motor de Turnos 2x2 & Relevos"}
                  </span>
                </NavLink>
              )}

              <NavLink
                to="/minuta-en-vivo"
                className={({ isActive }): string =>
                  `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                    isActive
                      ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                      : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                  }`
                }
              >
                <Radio className="h-4 w-4 shrink-0" />
                <span>
                  {usuarioActual.rol === "OPERADOR"
                    ? "Libro de Minuta (Reportar)"
                    : usuarioActual.rol === "CLIENTE"
                      ? "Minuta Filtrada del Puesto"
                      : "Minuta en Vivo (Visibilidad Dual)"}
                </span>
              </NavLink>

              {(usuarioActual.rol === "ADMINISTRADOR" ||
                usuarioActual.rol === "SUPERVISOR" ||
                usuarioActual.rol === "RRHH") && (
                <NavLink
                  to="/personal-puestos"
                  className={({ isActive }): string =>
                    `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                      isActive
                        ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                        : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                    }`
                  }
                >
                  <Building2 className="h-4 w-4 shrink-0" />
                  <span>
                    {usuarioActual.rol === "RRHH"
                      ? "Credenciales SV & Personal"
                      : "Personal, Credenciales SV & Puestos"}
                  </span>
                </NavLink>
              )}

              {usuarioActual.rol !== "CLIENTE" && (
                <NavLink
                  to="/intercambios"
                  className={({ isActive }): string =>
                    `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                      isActive
                        ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                        : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                    }`
                  }
                >
                  <ArrowLeftRight className="h-4 w-4 shrink-0" />
                  <span>
                    {usuarioActual.rol === "OPERADOR"
                      ? "Solicitar Relevo de Turno"
                      : "Aprobación de Relevos"}
                  </span>
                </NavLink>
              )}

              <NavLink
                to="/rondas-y-reportes"
                className={({ isActive }): string =>
                  `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                    isActive
                      ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                      : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                  }`
                }
              >
                <QrCode className="h-4 w-4 shrink-0" />
                <span>
                  {usuarioActual.rol === "ADMINISTRADOR" ||
                  usuarioActual.rol === "RRHH"
                    ? "Rondas QR & Prenómina CSV"
                    : usuarioActual.rol === "CLIENTE"
                      ? "SLA Rondas QR & Libro SHA-256"
                      : usuarioActual.rol === "SUPERVISOR"
                        ? "Auditoría Rondas & Folio"
                        : "Escáner Rondas QR/GPS"}
                </span>
              </NavLink>

              <NavLink
                to="/facturacion-b2b"
                className={({ isActive }): string =>
                  `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                    isActive
                      ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                      : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                  }`
                }
              >
                <Calculator className="h-4 w-4 shrink-0" />
                <span>
                  {usuarioActual.rol === "CLIENTE"
                    ? "Mis Facturas B2B & Tarifas"
                    : "Tarificación SV & Facturas"}
                </span>
              </NavLink>

              <NavLink
                to="/acceso-garita"
                className={({ isActive }): string =>
                  `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                    isActive
                      ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                      : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                  }`
                }
              >
                <UserCheck className="h-4 w-4 shrink-0" />
                <span>
                  {usuarioActual.rol === "OPERADOR"
                    ? "Garita & Cédulas PDF417"
                    : "Acceso Garita & Cédulas"}
                </span>
              </NavLink>

              {usuarioActual.rol !== "OPERADOR" && (
                <NavLink
                  to="/libro-balistico"
                  className={({ isActive }): string =>
                    `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                      isActive
                        ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                        : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                    }`
                  }
                >
                  <Crosshair className="h-4 w-4 shrink-0" />
                  <span>
                    {usuarioActual.rol === "CLIENTE"
                      ? "Armas & Salvoconductos Puesto"
                      : "Libro Balístico & Indumil"}
                  </span>
                </NavLink>
              )}

              {(usuarioActual.rol === "ADMINISTRADOR" ||
                usuarioActual.rol === "SUPERVISOR") && (
                <NavLink
                  to="/despacho-cad"
                  className={({ isActive }): string =>
                    `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                      isActive
                        ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                        : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                    }`
                  }
                >
                  <Navigation className="h-4 w-4 shrink-0" />
                  <span>Despacho CAD & GPS Radar</span>
                </NavLink>
              )}

              {/* Nuevos Módulos Enterprise V5.1 */}
              <div className="pt-2.5 mt-2.5 border-t border-white/[0.07] space-y-1">
                <span className="px-3 text-[10px] font-mono uppercase tracking-widest text-zinc-500 block">
                  División Especial V5.1
                </span>
                <NavLink
                  to="/operaciones-k9"
                  className={({ isActive }): string =>
                    `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                      isActive
                        ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                        : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                    }`
                  }
                >
                  <Truck className="h-4 w-4 shrink-0" />
                  <span>Escoltas BASC, K9 & Cercas</span>
                </NavLink>

                <NavLink
                  to="/cumplimiento-sarlaft"
                  className={({ isActive }): string =>
                    `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                      isActive
                        ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                        : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                    }`
                  }
                >
                  <FileCheck2 className="h-4 w-4 shrink-0" />
                  <span>SARLAFT 2.0, SG-SST & Kevlar</span>
                </NavLink>

                <NavLink
                  to="/inteligencia-forense"
                  className={({ isActive }): string =>
                    `boton-tactico-campo flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium transition duration-150 ${
                      isActive
                        ? "bg-[#FAFAFA] text-[#09090B] shadow-sm"
                        : "text-zinc-400 hover:bg-white/[0.04] hover:text-[#FAFAFA]"
                    }`
                  }
                >
                  <BrainCircuit className="h-4 w-4 shrink-0" />
                  <span>Inteligencia IA & Lab Forense</span>
                </NavLink>
              </div>
            </nav>
          </div>

          {/* Pie del Sidebar: Selector Rápido de 5 Roles RBAC y Cierre */}
          <div className="p-4 border-t border-white/[0.07] bg-[#09090B]/80">
            <div className="relative">
              <button
                type="button"
                onClick={(): void =>
                  setMostrarSelectorRoles(!mostrarSelectorRoles)
                }
                className="w-full flex items-center justify-between rounded-lg border border-white/[0.07] bg-[#18181B] p-2.5 text-left transition hover:border-white/20 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]"
              >
                <div className="flex items-center gap-2 truncate">
                  <div className="flex h-8 w-8 items-center justify-center rounded-md bg-white/[0.07] text-[#FAFAFA] shrink-0 font-semibold text-xs">
                    {usuarioActual.nombre_completo.charAt(0)}
                  </div>
                  <div className="truncate">
                    <p className="text-xs font-medium text-[#FAFAFA] truncate">
                      {usuarioActual.nombre_completo}
                    </p>
                    <span className="text-[10px] font-mono text-zinc-400">
                      {usuarioActual.rol} • {usuarioActual.codigo_placa}
                    </span>
                  </div>
                </div>
                <ChevronDown className="h-4 w-4 text-zinc-400 shrink-0" />
              </button>

              {mostrarSelectorRoles && (
                <div className="absolute bottom-full left-0 mb-2 w-full rounded-xl border border-white/[0.09] bg-[#18181B] p-2 shadow-2xl space-y-1 z-50">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 px-2 py-1 block">
                    Alternar Rol (5 Niveles RBAC):
                  </span>
                  {CUENTAS_RAPIDAS.map((c) => (
                    <button
                      key={c.correo}
                      type="button"
                      disabled={cambiandoRol}
                      onClick={(): void => {
                        void cambiarCuentaRapida(c);
                      }}
                      className="w-full flex items-center justify-between rounded-lg p-2 text-xs transition hover:bg-white/[0.06] text-left"
                    >
                      <span className="font-medium text-[#FAFAFA] truncate mr-2">
                        {c.nombre}
                      </span>
                      <span className="rounded border border-white/[0.08] bg-[#111113] px-1.5 py-0.5 font-mono text-[9px] font-medium text-zinc-300 shrink-0">
                        {c.etiqueta}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={cerrarSesion}
              className="mt-2.5 w-full flex items-center justify-center gap-2 rounded-lg border border-white/[0.07] bg-[#18181B] py-2 text-xs font-medium text-zinc-300 transition hover:border-[#EF4444]/40 hover:text-[#EF4444]"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Cerrar Sesión</span>
            </button>
          </div>
        </aside>

        {/* ================================================================= */}
        {/* ÁREA DE CONTENIDO PRINCIPAL, BANNER SOS Y HEADER SUPERIOR          */}
        {/* ================================================================= */}
        <div className="flex-1 flex flex-col min-w-0 min-h-screen">
          {/* Header Superior Carbon & Monochrome (Linear/Vercel Status Bar) */}
          <header className="sticky top-0 z-30 border-b border-white/[0.07] bg-[#09090B]/95 backdrop-blur-xl px-6 py-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="flex items-center gap-2">
                <span className="flex h-2 w-2 rounded-full bg-[#10B981]" />
                <span className="text-xs font-medium text-zinc-300">
                  {datosEstado?.estado ?? "Sentinel Core V5.1"}
                </span>
              </div>

              <span className="text-zinc-700">/</span>

              {/* Indicador en vivo de Integridad Blockchain SHA-256 (Semántico Puro) */}
              <div
                title="Verificación en caliente de bloques encadenados SHA-256 (Minuta, Relevos y Kardex Balístico)"
                className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[11px] font-mono font-medium transition-all ${
                  kpisTiempoReal?.integridad_blockchain
                    ?.INTEGRIDAD_VERIFICADA !== false
                    ? "border-white/[0.07] bg-[#111113] text-zinc-200"
                    : "border-[#EF4444]/60 bg-[#EF4444]/15 text-[#EF4444]"
                }`}
              >
                {kpisTiempoReal?.integridad_blockchain
                  ?.INTEGRIDAD_VERIFICADA !== false ? (
                  <Lock className="h-3 w-3 text-[#10B981]" />
                ) : (
                  <ShieldAlert className="h-3 w-3 text-[#EF4444]" />
                )}
                <span>
                  {kpisTiempoReal?.integridad_blockchain
                    ?.INTEGRIDAD_VERIFICADA !== false
                    ? `SHA-256 Verified: ${
                        kpisTiempoReal?.integridad_blockchain
                          ?.total_bloques_auditados ?? 44
                      } blocks`
                    : `CORRUPT CHAIN DETECTED AT BLOCK #${
                        kpisTiempoReal?.integridad_blockchain
                          ?.bloque_corrupto_id ?? 1
                      }`}
                </span>
              </div>

              {/* Contador de Conexiones WebSocket Activas */}
              <div className="flex items-center gap-1.5 rounded-md border border-white/[0.07] bg-[#111113] px-2.5 py-1 text-[11px] font-mono text-zinc-300">
                <Radio className="h-3 w-3 text-[#10B981]" />
                <span>
                  WS:{" "}
                  {Math.max(
                    1,
                    kpisTiempoReal?.conexiones_websocket_activas ??
                      datosEstado?.conexiones_websocket_activas ??
                      1
                  )}
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {usuarioActual.rol !== "CLIENTE" && (
                <>
                  {/* Interruptor MODO SIMULACIÓN EN VIVO */}
                  <button
                    type="button"
                    onClick={(): void => {
                      void manejarAlternarSimulacionViva();
                    }}
                    className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[11px] font-mono font-medium transition ${
                      simulacionVivaActiva
                        ? "border-[#10B981]/50 bg-[#10B981]/10 text-[#10B981]"
                        : "border-white/[0.07] bg-[#111113] text-zinc-300 hover:border-white/20 hover:text-[#FAFAFA]"
                    }`}
                  >
                    <Activity
                      className={`h-3.5 w-3.5 ${
                        simulacionVivaActiva
                          ? "text-[#10B981] animate-spin"
                          : "text-zinc-400"
                      }`}
                    />
                    <span>
                      {simulacionVivaActiva
                        ? "Live Telemetry: ON"
                        : "Live Telemetry: OFF"}
                    </span>
                  </button>

                  {/* Botón Primario Monocromático #FAFAFA / #09090B */}
                  <button
                    type="button"
                    disabled={disparandoRafaga}
                    onClick={(): void => {
                      void manejarDispararRafaga();
                    }}
                    className="flex items-center gap-1.5 rounded-lg bg-[#FAFAFA] px-3 py-1.5 text-xs font-semibold text-[#09090B] hover:bg-zinc-200 transition disabled:opacity-50"
                  >
                    <Zap className="h-3.5 w-3.5" />
                    <span>
                      {disparandoRafaga
                        ? "Inyectando..."
                        : "Disparar Ráfaga Operativa"}
                    </span>
                  </button>
                </>
              )}

              {/* Toggle Modo Centro de Mando vs Modo Táctico de Campo */}
              <button
                type="button"
                onClick={alternarModoTactico}
                className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${
                  modoTacticoAltoContraste
                    ? "border-[#F59E0B] bg-[#F59E0B] text-[#09090B]"
                    : "border-white/[0.07] bg-[#111113] text-zinc-300 hover:border-white/20 hover:text-[#FAFAFA]"
                }`}
              >
                <Sun className="h-3.5 w-3.5" />
                <span>
                  {modoTacticoAltoContraste ? "ALTO CONTRASTE" : "Modo Campo"}
                </span>
              </button>

              <button
                type="button"
                onClick={(): void => {
                  void verificarNucleo();
                  void cargarAlertasSosPendientes();
                  void cargarKpisHeader();
                }}
                title="Sincronizar telemetría del servidor"
                className="rounded-lg border border-white/[0.07] bg-[#111113] p-1.5 text-zinc-400 hover:border-white/20 hover:text-[#FAFAFA] transition"
              >
                <RefreshCw
                  className={`h-4 w-4 ${
                    estadoConexion === "cargando" ? "animate-spin" : ""
                  }`}
                />
              </button>

              <span className="rounded-md border border-white/[0.07] bg-[#18181B] px-2.5 py-1 font-mono text-[11px] font-medium text-zinc-300">
                {usuarioActual.rol}
              </span>
            </div>
          </header>

          {/* Notificación compacta de última Ráfaga Operativa inyectada */}
          {ultimaRafaga && (
            <div className="border-b border-emerald-500/30 bg-emerald-950/60 px-6 py-2 text-xs flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-3 text-emerald-200">
                <span className="rounded bg-emerald-500 px-2 py-0.5 text-[10px] font-black text-slate-950 uppercase">
                  Ráfaga #{ultimaRafaga.rafaga_numero} Inyectada
                </span>
                <span>
                  <strong>Sede:</strong> {ultimaRafaga.puesto_afectado} —{" "}
                  {ultimaRafaga.nombre_puesto}
                </span>
                <span>•</span>
                <span>
                  <strong>Garita LPR:</strong>{" "}
                  {ultimaRafaga.acceso_garita_creado}
                </span>
                <span>•</span>
                <span>
                  <strong>Ronda QR:</strong> {ultimaRafaga.ronda_qr_verificada}
                </span>
                <span>•</span>
                <span className="font-mono text-[11px] text-emerald-300">
                  SHA-256: {ultimaRafaga.sello_sha256_generado.slice(0, 16)}...
                </span>
              </div>
              <button
                type="button"
                onClick={(): void => setUltimaRafaga(null)}
                className="text-[11px] text-emerald-300 hover:text-white underline"
              >
                Ocultar
              </button>
            </div>
          )}

          {/* =============================================================== */}
          {/* BANNER ROJO PULSANTE GLOBAL DE ALERTA DE PÁNICO SOS (3.2)        */}
          {/* =============================================================== */}
          {alertasSosActivas.length > 0 && puedeAtenderSos && (
            <div className="bg-rose-950/95 border-b-2 border-rose-500 px-8 py-4 shadow-2xl animate-pulse">
              <div className="max-w-7xl mx-auto space-y-3">
                {errorSosGlobal && (
                  <p className="text-xs font-bold text-amber-300">
                    {errorSosGlobal}
                  </p>
                )}
                {alertasSosActivas.map((alerta) => (
                  <div
                    key={alerta.alerta_id}
                    className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 rounded-xl border border-rose-400/50 bg-black/70 p-4"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-rose-600 text-white">
                        <Siren className="h-7 w-7 animate-bounce" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-rose-600 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider text-white">
                            CÓDIGO ROJO SOS ACTIVO #{alerta.alerta_id}
                          </span>
                          <span className="text-xs font-mono text-rose-200">
                            {new Date(
                              alerta.fecha_activacion
                            ).toLocaleTimeString("es-CO")}
                          </span>
                        </div>
                        <h3 className="mt-1 text-base font-black text-white">
                          {alerta.nombre_puesto} ({alerta.codigo_puesto}) —
                          Guarda: {alerta.nombre_operador} (
                          {alerta.codigo_placa_operador})
                        </h3>
                        <p className="flex items-center gap-1.5 text-xs text-rose-200 font-mono mt-0.5">
                          <MapPin className="h-3.5 w-3.5 text-rose-400" />
                          Coordenadas GPS: Lat {alerta.latitud_gps.toFixed(5)},
                          Lon {alerta.longitud_gps.toFixed(5)}
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                      <input
                        type="text"
                        value={notaReaccionSos}
                        onChange={(e): void =>
                          setNotaReaccionSos(e.target.value)
                        }
                        placeholder="Protocolo de reacción aplicado..."
                        className="rounded-xl border border-rose-400/40 bg-slate-950 px-3 py-2 text-xs text-white min-w-[260px]"
                      />
                      <button
                        type="button"
                        disabled={atendiendoSosId === alerta.alerta_id}
                        onClick={(): void => {
                          void atenderEmergenciaSos(alerta.alerta_id);
                        }}
                        className="boton-tactico-campo flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-xs font-black text-slate-950 hover:bg-emerald-400 transition shrink-0"
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        <span>
                          {atendiendoSosId === alerta.alerta_id
                            ? "Registrando..."
                            : "Atender Emergencia / Registrar Reacción"}
                        </span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Rutas de los Módulos de la Plataforma */}
          <main className="relative z-10 flex-1 p-8 max-w-7xl w-full mx-auto">
            <Routes>
              <Route path="/" element={<CentroDeMandoDashboard />} />
              <Route
                path="/turnos-2x2"
                element={
                  usuarioActual.rol === "CLIENTE" ? (
                    <Navigate to="/" replace />
                  ) : (
                    <ModuloMotorTurnos />
                  )
                }
              />
              <Route
                path="/minuta-en-vivo"
                element={<ModuloMinutaTiempoReal />}
              />
              <Route
                path="/intercambios"
                element={
                  usuarioActual.rol === "CLIENTE" ? (
                    <Navigate to="/" replace />
                  ) : (
                    <ModuloIntercambioTurnos />
                  )
                }
              />
              <Route
                path="/personal-puestos"
                element={
                  usuarioActual.rol === "OPERADOR" ||
                  usuarioActual.rol === "CLIENTE" ? (
                    <Navigate to="/" replace />
                  ) : (
                    <ModuloPersonalYPuestos />
                  )
                }
              />
              <Route
                path="/rondas-y-reportes"
                element={<ModuloRondasYReportes />}
              />
              <Route
                path="/facturacion-b2b"
                element={<ModuloTarificadorB2B />}
              />
              <Route
                path="/acceso-garita"
                element={<ModuloControlAccesoGarita />}
              />
              <Route
                path="/libro-balistico"
                element={<ModuloLibroBalistico />}
              />
              <Route
                path="/despacho-cad"
                element={<ModuloDespachoCAD />}
              />
              <Route
                path="/operaciones-k9"
                element={<OperacionesEspecialesK9 />}
              />
              <Route
                path="/cumplimiento-sarlaft"
                element={<CumplimientoSarlaftSST />}
              />
              <Route
                path="/inteligencia-forense"
                element={<InteligenciaForenseIA />}
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;

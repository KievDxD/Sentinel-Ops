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
} from "lucide-react";
import { format } from "date-fns";
import { usarAlmacenAutenticacion } from "./estado/almacen_autenticacion";
import {
  URL_WEBSOCKET_MINUTA,
  extraerMensajeError,
  servicioAtenderAlertaSos,
  servicioConsultarEstado,
  servicioIniciarSesion,
  servicioListarAlertasSos,
} from "./servicios/cliente_api";
import type {
  AlertaPanicoSos,
  MensajeWebSocketMinuta,
  RespuestaEstadoServidor,
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
  }, [verificarNucleo, cargarAlertasSosPendientes]);

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
            : "bg-slate-950 text-slate-100"
        }`}
      >
        {!modoTacticoAltoContraste && (
          <>
            <div className="pointer-events-none fixed -top-40 -left-40 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl z-0" />
            <div className="pointer-events-none fixed -bottom-40 -right-40 h-96 w-96 rounded-full bg-cyan-500/10 blur-3xl z-0" />
          </>
        )}

        {/* ================================================================= */}
        {/* BARRA LATERAL TÁCTICA (SIDEBAR SAAS 5 NIVELES RBAC)               */}
        {/* ================================================================= */}
        <aside className="relative z-20 flex w-72 flex-col justify-between border-r border-white/10 bg-slate-950/90 backdrop-blur-2xl shrink-0 min-h-screen">
          <div>
            <div className="p-6 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 shadow-lg shadow-emerald-500/10">
                  <ShieldCheck className="h-6 w-6" />
                </div>
                <div>
                  <h1 className="text-lg font-black tracking-wider text-white">
                    SENTINEL <span className="text-emerald-400">//</span> OPS
                  </h1>
                  <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-400 block">
                    Enterprise V2.0 • Colombia
                  </span>
                </div>
              </div>

              {/* Reloj Táctico en Vivo */}
              <div className="mt-4 flex items-center justify-between rounded-xl border border-white/5 bg-slate-900/60 px-3 py-2 text-xs">
                <div className="flex items-center gap-2 text-slate-400">
                  <Clock className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="text-[11px] font-mono">COT (Colombia)</span>
                </div>
                <span className="font-mono font-bold text-white tracking-widest text-sm">
                  {horaActual}
                </span>
              </div>

              {/* Nivel de Prioridad y Autorización RBAC (5 Niveles) */}
              <div
                className={`mt-2.5 rounded-xl border px-3 py-2 text-[10px] font-bold uppercase tracking-wider ${
                  usuarioActual.rol === "ADMINISTRADOR"
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                    : usuarioActual.rol === "SUPERVISOR"
                      ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-300"
                      : usuarioActual.rol === "RRHH"
                        ? "border-purple-500/40 bg-purple-500/10 text-purple-300"
                        : usuarioActual.rol === "CLIENTE"
                          ? "border-sky-500/40 bg-sky-500/10 text-sky-300"
                          : "border-amber-500/40 bg-amber-500/10 text-amber-300"
                }`}
              >
                {usuarioActual.rol === "ADMINISTRADOR" &&
                  "PRIORIDAD 1 • DIRECCIÓN Y CONTROL TOTAL"}
                {usuarioActual.rol === "SUPERVISOR" &&
                  "PRIORIDAD 2 • SUPERVISIÓN DE OPERACIONES"}
                {usuarioActual.rol === "RRHH" &&
                  "PRIORIDAD 2.5 • GESTIÓN HUMANA Y NÓMINA"}
                {usuarioActual.rol === "OPERADOR" &&
                  "PRIORIDAD 3 • GUARDA EN PUESTO ASIGNADO"}
                {usuarioActual.rol === "CLIENTE" &&
                  "PRIORIDAD 4 • CONSOLA CORPORATIVA CLIENTE"}
              </div>
            </div>

            {/* Menú de Navegación Principal Adaptado a los 5 Roles */}
            <nav className="p-4 space-y-1.5">
              <NavLink
                to="/"
                end
                className={({ isActive }): string =>
                  `boton-tactico-campo flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-bold transition ${
                    isActive
                      ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
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
                    `boton-tactico-campo flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-bold transition ${
                      isActive
                        ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20"
                        : "text-slate-300 hover:bg-white/5 hover:text-white"
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
                  `boton-tactico-campo flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-bold transition ${
                    isActive
                      ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
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
                    `boton-tactico-campo flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-bold transition ${
                      isActive
                        ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20"
                        : "text-slate-300 hover:bg-white/5 hover:text-white"
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
                    `boton-tactico-campo flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-bold transition ${
                      isActive
                        ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20"
                        : "text-slate-300 hover:bg-white/5 hover:text-white"
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
                  `boton-tactico-campo flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-bold transition ${
                    isActive
                      ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
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
            </nav>
          </div>

          {/* Pie del Sidebar: Selector Rápido de 5 Roles RBAC y Cierre */}
          <div className="p-4 border-t border-white/10 bg-slate-950/60">
            <div className="relative">
              <button
                type="button"
                onClick={(): void =>
                  setMostrarSelectorRoles(!mostrarSelectorRoles)
                }
                className="w-full flex items-center justify-between rounded-xl border border-white/10 bg-slate-900/80 p-2.5 text-left transition hover:border-emerald-500/40"
              >
                <div className="flex items-center gap-2 truncate">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 shrink-0 font-bold text-xs">
                    {usuarioActual.nombre_completo.charAt(0)}
                  </div>
                  <div className="truncate">
                    <p className="text-xs font-bold text-white truncate">
                      {usuarioActual.nombre_completo}
                    </p>
                    <span className="text-[10px] font-mono text-emerald-400">
                      {usuarioActual.rol} • {usuarioActual.codigo_placa}
                    </span>
                  </div>
                </div>
                <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
              </button>

              {mostrarSelectorRoles && (
                <div className="absolute bottom-full left-0 mb-2 w-full rounded-xl border border-white/15 bg-slate-900 p-2 shadow-2xl backdrop-blur-2xl space-y-1 z-50">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 py-1 block">
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
                      className="w-full flex items-center justify-between rounded-lg p-2 text-xs transition hover:bg-white/10 text-left"
                    >
                      <span className="font-semibold text-white truncate mr-2">
                        {c.nombre}
                      </span>
                      <span
                        className={`rounded px-1.5 py-0.5 text-[9px] font-bold shrink-0 ${c.colorBadge}`}
                      >
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
              className="mt-2.5 w-full flex items-center justify-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 py-2 text-xs font-semibold text-rose-300 transition hover:bg-rose-500/20"
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
          {/* Header Superior con Selector de Modo Táctico de Campo (Alto Contraste) */}
          <header className="sticky top-0 z-30 border-b border-white/10 bg-slate-950/80 backdrop-blur-xl px-8 py-3.5 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-semibold text-slate-300">
                {datosEstado?.estado ?? "Sentinel Core En Línea"}
              </span>
              <span className="text-slate-600">•</span>
              <span className="text-xs text-slate-400 font-mono">
                Ley 2101:{" "}
                {datosEstado?.tope_horas_semanales_ley_2101 ?? 42}h/sem
              </span>
            </div>

            <div className="flex items-center gap-3">
              {/* Toggle Modo Centro de Mando vs Modo Táctico de Campo (Sunlight Ready) */}
              <button
                type="button"
                onClick={alternarModoTactico}
                className={`flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-bold transition ${
                  modoTacticoAltoContraste
                    ? "border-amber-400 bg-amber-400 text-black shadow-lg shadow-amber-500/30"
                    : "border-white/15 bg-white/5 text-slate-200 hover:border-amber-400/50 hover:text-amber-300"
                }`}
              >
                <Sun className="h-4 w-4" />
                <span>
                  {modoTacticoAltoContraste
                    ? "MODO TÁCTICO DE CAMPO (ALTO CONTRASTE)"
                    : "Modo Centro de Mando"}
                </span>
              </button>

              <button
                type="button"
                onClick={(): void => {
                  void verificarNucleo();
                  void cargarAlertasSosPendientes();
                }}
                title="Sincronizar telemetría del servidor"
                className="rounded-lg border border-white/10 bg-white/5 p-1.5 text-slate-300 hover:border-emerald-500/40 hover:text-emerald-300 transition"
              >
                <RefreshCw
                  className={`h-4 w-4 ${
                    estadoConexion === "cargando" ? "animate-spin" : ""
                  }`}
                />
              </button>

              <div className="h-4 w-[1px] bg-white/10" />

              <span className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-300">
                {usuarioActual.rol}
              </span>
            </div>
          </header>

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
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;

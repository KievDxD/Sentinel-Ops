/**
 * Centro de Mando Operativo y Dashboard Ejecutivo B2B (Enterprise V2.0 - SENTINEL // OPS).
 * Vistas dedicadas según Jerarquía RBAC de 5 Niveles:
 * - ADMINISTRADOR / SUPERVISOR: KPIs de Flota (Puestos 24/7, SOS Activos, Credenciales SV, SLA Rondas QR,
 *   Barra de Proporción Nómina Ley 2101 42h Ordinarias vs Extras/Recargos) y Armamento Indumil por Puesto.
 * - RRHH: Consola de Gestión Humana, Semáforo SuperVigilancia, Ausentismos y Exportación Prenómina CSV.
 * - OPERADOR: Botón de Pánico Táctico SOS (Hold 2.5s / Doble Confirmación), Checklist Criptográfico SHA-256
 *   de Entrega y Recibo de Puesto (Armamento Indumil + Munición) y Turno 2x2.
 * - CLIENTE: Consola Corporativa de Solo Lectura vinculada a su puesto contratado (PST-BOG-01),
 *   Guarda en turno con Vigencia SV, SLA Rondas QR, Minuta Filtrada y Libro Foliado SHA-256.
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactElement,
} from "react";
import { Link } from "react-router-dom";
import { format, differenceInDays } from "date-fns";
import { es } from "date-fns/locale";
import {
  Building2,
  Sun,
  Moon,
  Coffee,
  Radio,
  QrCode,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  TrendingUp,
  MapPin,
  Clock,
  Shield,
  Siren,
  FileSpreadsheet,
  FileCheck2,
  Award,
  ClipboardCheck,
} from "lucide-react";
import {
  extraerMensajeError,
  servicioAbrirLibroFoliadoOficial,
  servicioAuditarCoberturaPuestos,
  servicioConsultarTurnos,
  servicioCrearActaRelevo,
  servicioDescargarPrenominaCsv,
  servicioDispararAlertaSos,
  servicioListarActasRelevo,
  servicioListarAlertasSos,
  servicioListarMinuta,
  servicioListarPuestos,
  servicioListarUsuarios,
  servicioObtenerDotacionPuesto,
} from "../servicios/cliente_api";
import { usarAlmacenAutenticacion } from "../estado/almacen_autenticacion";
import type {
  ActaRelevoPuesto,
  AlertaCoberturaPuesto,
  AlertaPanicoSos,
  DotacionPuesto,
  EstadoItemDotacion,
  PuestoVigilancia,
  RegistroMinuta,
  ResumenLiquidacionTurnos,
  UsuarioSistema,
} from "../tipos/tipos_sistema";

function formatearPesosColombianos(valor: number): string {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(valor);
}

export function evaluarSemaforoCredencialSv(
  fechaVencimiento?: string | null,
  excepcionAutorizada?: boolean
): {
  estado: "VIGENTE" | "POR_VENCER" | "VENCIDO" | "EXCEPCION";
  etiqueta: string;
  claseColor: string;
  diasRestantes: number;
} {
  if (!fechaVencimiento) {
    return {
      estado: "VENCIDO",
      etiqueta: "SIN CREDENCIAL SV",
      claseColor: "border-rose-500/50 bg-rose-500/20 text-rose-200",
      diasRestantes: -999,
    };
  }
  const dias = differenceInDays(new Date(fechaVencimiento), new Date());
  if (dias < 0) {
    if (excepcionAutorizada) {
      return {
        estado: "EXCEPCION",
        etiqueta: `EXCEPCIÓN ADMIN (${dias}d)`,
        claseColor: "border-purple-500/50 bg-purple-500/20 text-purple-200",
        diasRestantes: dias,
      };
    }
    return {
      estado: "VENCIDO",
      etiqueta: `VENCIDA (${Math.abs(dias)}d)`,
      claseColor: "border-rose-500/50 bg-rose-500/20 text-rose-200",
      diasRestantes: dias,
    };
  }
  if (dias <= 30) {
    return {
      estado: "POR_VENCER",
      etiqueta: `POR VENCER (${dias}d)`,
      claseColor: "border-amber-500/50 bg-amber-500/20 text-amber-200",
      diasRestantes: dias,
    };
  }
  return {
    estado: "VIGENTE",
    etiqueta: `SV VIGENTE (${dias}d)`,
    claseColor: "border-emerald-500/40 bg-emerald-500/15 text-emerald-300",
    diasRestantes: dias,
  };
}

export function CentroDeMandoDashboard(): ReactElement {
  const usuarioActual = usarAlmacenAutenticacion(
    (estado) => estado.usuarioActual
  );

  const [puestos, setPuestos] = useState<PuestoVigilancia[]>([]);
  const [usuarios, setUsuarios] = useState<UsuarioSistema[]>([]);
  const [resumenTurnos, setResumenTurnos] =
    useState<ResumenLiquidacionTurnos | null>(null);
  const [ultimosRegistros, setUltimosRegistros] = useState<RegistroMinuta[]>(
    []
  );
  const [alertasCobertura, setAlertasCobertura] = useState<
    AlertaCoberturaPuesto[]
  >([]);
  const [alertasSos, setAlertasSos] = useState<AlertaPanicoSos[]>([]);
  const [dotacionMiPuesto, setDotacionMiPuesto] =
    useState<DotacionPuesto | null>(null);
  const [actasRelevo, setActasRelevo] = useState<ActaRelevoPuesto[]>([]);

  const [cargando, setCargando] = useState<boolean>(true);
  const [mensajeError, setMensajeError] = useState<string | null>(null);
  const [mensajeExito, setMensajeExito] = useState<string | null>(null);

  // Estado del Botón de Pánico SOS (Hold 2.5s o Doble Confirmación)
  const [progresoSos, setProgresoSos] = useState<number>(0);
  const [confirmacionRapidaSos, setConfirmacionRapidaSos] =
    useState<boolean>(false);
  const [enviandoSos, setEnviandoSos] = useState<boolean>(false);
  const intervaloHoldRef = useRef<number | null>(null);

  // Estado del Checklist de Entrega/Recibo de Puesto (Armamento Indumil)
  const [estadoArmamento, setEstadoArmamento] =
    useState<EstadoItemDotacion>("OPTIMO");
  const [municionVerificada, setMunicionVerificada] = useState<number>(18);
  const [estadoChaleco, setEstadoChaleco] =
    useState<EstadoItemDotacion>("OPTIMO");
  const [estadoRadio, setEstadoRadio] = useState<EstadoItemDotacion>("OPTIMO");
  const [estadoLinternaLlaves, setEstadoLinternaLlaves] =
    useState<EstadoItemDotacion>("OPTIMO");
  const [observacionesActa, setObservacionesActa] = useState<string>(
    "Relevo de turno 12h sin novedad. Armamento Indumil, salvoconducto y chaleco verificados físicamente."
  );
  const [guardandoActa, setGuardandoActa] = useState<boolean>(false);

  const hoyTexto = format(new Date(), "yyyy-MM-dd");

  const rol = usuarioActual?.rol ?? "OPERADOR";
  const esOperador = rol === "OPERADOR";
  const esCliente = rol === "CLIENTE";
  const esRrhh = rol === "RRHH";

  const cargarDatosCentroMando = useCallback(async (): Promise<void> => {
    setCargando(true);
    try {
      const puestoFiltro =
        (esOperador || esCliente) && usuarioActual?.puesto_base_id
          ? usuarioActual.puesto_base_id
          : undefined;

      const [
        listaPuestos,
        listaUsuarios,
        datosTurnos,
        listaMinuta,
        listaCobertura,
        listaSos,
        listaActas,
      ] = await Promise.all([
        servicioListarPuestos(),
        servicioListarUsuarios(),
        servicioConsultarTurnos(
          esOperador ? usuarioActual?.usuario_id : undefined,
          esCliente ? puestoFiltro : undefined
        ),
        servicioListarMinuta(puestoFiltro),
        servicioAuditarCoberturaPuestos(),
        servicioListarAlertasSos(false),
        servicioListarActasRelevo(puestoFiltro),
      ]);

      setPuestos(listaPuestos);
      setUsuarios(listaUsuarios);
      setResumenTurnos(datosTurnos);
      setUltimosRegistros(listaMinuta.slice(0, 8));
      setAlertasCobertura(listaCobertura);
      setAlertasSos(listaSos);
      setActasRelevo(listaActas.slice(0, 4));

      const idPuestoDotacion =
        puestoFiltro ?? listaPuestos[0]?.puesto_id ?? 1;
      try {
        const dotacion = await servicioObtenerDotacionPuesto(idPuestoDotacion);
        setDotacionMiPuesto(dotacion);
        setMunicionVerificada(dotacion.cantidad_municion_autorizada);
      } catch {
        // Sin dotación registrada
      }
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    } finally {
      setCargando(false);
    }
  }, [esCliente, esOperador, usuarioActual?.puesto_base_id, usuarioActual?.usuario_id]);

  useEffect((): void => {
    void cargarDatosCentroMando();
  }, [cargarDatosCentroMando]);

  // Lógica de activación del Botón de Pánico SOS (3.2)
  const ejecutarDisparoSos = useCallback(async (): Promise<void> => {
    if (enviandoSos) return;
    setEnviandoSos(true);
    setMensajeError(null);
    const puestoId = usuarioActual?.puesto_base_id ?? puestos[0]?.puesto_id ?? 1;

    const enviarAlBackend = async (lat: number, lon: number): Promise<void> => {
      try {
        const alerta = await servicioDispararAlertaSos({
          puesto_id: puestoId,
          latitud_gps: lat,
          longitud_gps: lon,
        });
        setMensajeExito(
          `🚨 ALERTA SOS #${alerta.alerta_id} TRANSMITIDA EN VIVO AL CENTRO DE MANDO (Lat ${lat.toFixed(4)}, Lon ${lon.toFixed(4)}).`
        );
        setConfirmacionRapidaSos(false);
        void cargarDatosCentroMando();
      } catch (err: unknown) {
        setMensajeError(extraerMensajeError(err));
      } finally {
        setEnviandoSos(false);
      }
    };

    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos): void => {
          void enviarAlBackend(
            pos.coords.latitude,
            pos.coords.longitude
          );
        },
        (): void => {
          void enviarAlBackend(4.67681, -74.04825);
        },
        { timeout: 3000 }
      );
    } else {
      await enviarAlBackend(4.67681, -74.04825);
    }
  }, [cargarDatosCentroMando, enviandoSos, puestos, usuarioActual?.puesto_base_id]);

  const iniciarPresionSos = (): void => {
    if (intervaloHoldRef.current) window.clearInterval(intervaloHoldRef.current);
    const inicio = Date.now();
    intervaloHoldRef.current = window.setInterval((): void => {
      const transcurrido = Date.now() - inicio;
      const pct = Math.min(100, Math.round((transcurrido / 2500) * 100));
      setProgresoSos(pct);
      if (pct >= 100) {
        if (intervaloHoldRef.current) {
          window.clearInterval(intervaloHoldRef.current);
          intervaloHoldRef.current = null;
        }
        setProgresoSos(0);
        void ejecutarDisparoSos();
      }
    }, 50);
  };

  const cancelarPresionSos = (): void => {
    if (intervaloHoldRef.current) {
      window.clearInterval(intervaloHoldRef.current);
      intervaloHoldRef.current = null;
    }
    setProgresoSos(0);
  };

  const enviarActaEntregaPuesto = async (): Promise<void> => {
    const puestoId =
      dotacionMiPuesto?.puesto_id ??
      usuarioActual?.puesto_base_id ??
      puestos[0]?.puesto_id ??
      1;
    setGuardandoActa(true);
    setMensajeError(null);
    setMensajeExito(null);
    try {
      const acta = await servicioCrearActaRelevo({
        puesto_id: puestoId,
        estado_armamento: estadoArmamento,
        municion_verificada: Number(municionVerificada),
        estado_chaleco: estadoChaleco,
        estado_radio: estadoRadio,
        estado_linterna_y_llaves: estadoLinternaLlaves,
        observaciones_relevo: observacionesActa,
      });
      setMensajeExito(
        `Acta de Entrega/Recibo #${acta.acta_id} firmada con Sello SHA-256: ${acta.sello_sha256.slice(0, 16)}...`
      );
      await cargarDatosCentroMando();
    } catch (err: unknown) {
      setMensajeError(extraerMensajeError(err));
    } finally {
      setGuardandoActa(false);
    }
  };

  const guardias = usuarios.filter((u) => u.rol === "OPERADOR");
  const puestosVisibles =
    esOperador || esCliente
      ? puestos.filter((p) => p.puesto_id === usuarioActual?.puesto_base_id)
      : puestos;

  const turnosHoy = (resumenTurnos?.turnos ?? []).filter((t) =>
    t.fecha_inicio.startsWith(hoyTexto)
  );
  const miTurnoHoy = turnosHoy[0] ?? null;

  // Métricas Ejecutivas / Supervisión (4.2)
  const puestosCubiertosCount = alertasCobertura.filter(
    (a) => !a.estado_cobertura.includes("DESCUBIERTO")
  ).length;
  const alertasSosActivasCount = alertasSos.filter(
    (a) => a.estado_alerta === "ACTIVA"
  ).length;
  const credencialesAlertaCount = guardias.filter((g) => {
    const sem = evaluarSemaforoCredencialSv(
      g.fecha_vencimiento_credencial,
      g.excepcion_credencial_autorizada
    );
    return sem.estado === "POR_VENCER" || sem.estado === "VENCIDO";
  }).length;

  const totalPuntosQr = alertasCobertura.reduce(
    (acc, a) => acc + a.total_puntos_control,
    0
  );
  const totalVerificadosQr = alertasCobertura.reduce(
    (acc, a) => acc + Math.min(a.puntos_control_verificados, a.total_puntos_control),
    0
  );
  const porcentajeSlaRondas =
    totalPuntosQr > 0
      ? Math.min(100, Math.round((totalVerificadosQr / totalPuntosQr) * 100))
      : 100;

  // Proporción de Horas Ordinarias vs Extras/Recargos (Ley 2101 de 42h)
  const horasOrd = resumenTurnos?.suma_horas_ordinarias ?? 0;
  const horasExtrasYRecargos =
    (resumenTurnos?.suma_horas_extras_diurnas ?? 0) +
    (resumenTurnos?.suma_horas_extras_nocturnas ?? 0) +
    (resumenTurnos?.suma_horas_recargo_nocturno ?? 0) +
    (resumenTurnos?.suma_horas_dominicales_festivas ?? 0);
  const totalHorasBaseBarra = Math.max(1, horasOrd + horasExtrasYRecargos);
  const pctOrdinarias = Math.round((horasOrd / totalHorasBaseBarra) * 100);
  const pctRecargosExtras = 100 - pctOrdinarias;

  return (
    <div className="space-y-8">
      {/* Encabezado Táctico Diferenciado para los 5 Roles RBAC */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b border-white/10 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>
              {rol === "ADMINISTRADOR" &&
                "Centro de Mando Ejecutivo // Dirección General & SuperVigilancia"}
              {rol === "SUPERVISOR" &&
                "Consola Táctica de Supervisión // Cobertura 24/7, Indumil & Reacción SOS"}
              {rol === "RRHH" &&
                "Consola de Gestión Humana y Nómina // Ley 2101 (42h) & Credenciales SV"}
              {rol === "OPERADOR" &&
                "Consola Operativa de Guarda en Puesto // Relevo Indumil & Botón SOS"}
              {rol === "CLIENTE" &&
                "Consola Corporativa de Cliente // Auditoría de Puesto Contratado en Vivo"}
            </span>
          </div>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-white sm:text-3xl">
            {usuarioActual?.nombre_completo}
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            {format(new Date(), "EEEE, dd 'de' MMMM 'de' yyyy", { locale: es })}{" "}
            • Rol: <strong className="text-white">{rol}</strong> (Placa:{" "}
            {usuarioActual?.codigo_placa})
            {usuarioActual?.numero_credencial_sv && (
              <span className="ml-2 font-mono text-emerald-300">
                • Credencial SV: {usuarioActual.numero_credencial_sv}
              </span>
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {(rol === "ADMINISTRADOR" || esRrhh) && (
            <button
              type="button"
              onClick={(): void => {
                void servicioDescargarPrenominaCsv();
              }}
              className="boton-tactico-campo inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:bg-emerald-400 shadow-lg shadow-emerald-500/20"
            >
              <FileSpreadsheet className="h-4 w-4" />
              <span>Exportar Prenómina Ley 2101 (CSV)</span>
            </button>
          )}

          {(rol === "ADMINISTRADOR" ||
            rol === "SUPERVISOR" ||
            esCliente) && (
            <button
              type="button"
              onClick={(): void => {
                void servicioAbrirLibroFoliadoOficial();
              }}
              className="boton-tactico-campo inline-flex items-center gap-2 rounded-xl border border-cyan-500/40 bg-cyan-500/15 px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-cyan-200 transition hover:bg-cyan-500/25"
            >
              <FileCheck2 className="h-4 w-4 text-cyan-300" />
              <span>
                {esCliente
                  ? "Descargar Libro Foliado SHA-256 del Puesto"
                  : "Libro Foliado SHA-256"}
              </span>
            </button>
          )}
        </div>
      </div>

      {mensajeError && (
        <div className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-sm text-rose-200">
          <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0" />
          <span>{mensajeError}</span>
        </div>
      )}

      {mensajeExito && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-950/40 p-4 text-sm font-bold text-emerald-200">
          <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
          <span>{mensajeExito}</span>
        </div>
      )}

      {/* ================================================================= */}
      {/* VISTA DEDICADA 1: CONSOLA TÁCTICA DEL OPERADOR (SOS + ACTA INDUMIL) */}
      {/* ================================================================= */}
      {esOperador && (
        <div className="space-y-6">
          {/* KPIs del Guarda con Semáforo SuperVigilancia */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-cyan-500/30 bg-slate-900/70 p-4">
              <div className="flex items-center justify-between text-cyan-300">
                <span className="text-[11px] font-bold uppercase">
                  Mi Puesto Asignado
                </span>
                <Building2 className="h-4 w-4" />
              </div>
              <p className="mt-2 text-lg font-black text-white">
                {puestosVisibles[0]?.codigo_puesto ?? "PST-BOG-01"}
              </p>
              <span className="text-xs text-slate-300 block truncate">
                {puestosVisibles[0]?.nombre_puesto ?? "Centro Empresarial"}
              </span>
            </div>

            <div className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-4">
              <div className="flex items-center justify-between text-amber-300">
                <span className="text-[11px] font-bold uppercase">
                  Mi Turno 2x2 Hoy
                </span>
                <Clock className="h-4 w-4" />
              </div>
              <p className="mt-2 text-lg font-black text-amber-200">
                {miTurnoHoy ? `${miTurnoHoy.tipo_turno} (12H)` : "EN RELEVO"}
              </p>
              <span className="text-xs text-amber-300/80">
                {miTurnoHoy?.tipo_turno === "DIURNO"
                  ? "06:00 a 18:00"
                  : miTurnoHoy?.tipo_turno === "NOCTURNO"
                    ? "18:00 a 06:00"
                    : "Descanso Compensatorio 24h"}
              </span>
            </div>

            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-4">
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-[11px] font-bold uppercase">
                  Acreditación SuperVigilancia
                </span>
                <Award className="h-4 w-4 text-emerald-400" />
              </div>
              {(() => {
                const sem = evaluarSemaforoCredencialSv(
                  usuarioActual?.fecha_vencimiento_credencial,
                  usuarioActual?.excepcion_credencial_autorizada
                );
                return (
                  <>
                    <span
                      className={`mt-2 inline-block rounded border px-2 py-0.5 text-xs font-black ${sem.claseColor}`}
                    >
                      {sem.etiqueta}
                    </span>
                    <span className="mt-1 block text-[11px] text-slate-400 font-mono">
                      {usuarioActual?.numero_credencial_sv ?? "SV-2026"} •{" "}
                      {usuarioActual?.nivel_curso ?? "FUNDAMENTACION"}
                    </span>
                  </>
                );
              })()}
            </div>

            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/25 p-4">
              <div className="flex items-center justify-between text-emerald-300">
                <span className="text-[11px] font-bold uppercase">
                  Devengado Ley 2101 (42h)
                </span>
                <TrendingUp className="h-4 w-4" />
              </div>
              <p className="mt-2 text-lg font-black text-emerald-300">
                {resumenTurnos
                  ? formatearPesosColombianos(
                      resumenTurnos.costo_total_estimado_cop
                    )
                  : "$0"}
              </p>
              <span className="text-xs text-emerald-400/80">
                {resumenTurnos?.suma_horas_trabajadas ?? 0}h trabajadas
              </span>
            </div>
          </div>

          {/* Botón de Pánico Táctico SOS (3.2) + Acta Digital de Entrega/Recibo de Puesto (3.1) */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* Botón de Pánico SOS */}
            <section className="lg:col-span-5 rounded-2xl border-2 border-rose-500/60 bg-rose-950/20 p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2.5 text-rose-300">
                  <Siren className="h-6 w-6 text-rose-400 animate-pulse" />
                  <h2 className="text-lg font-black uppercase tracking-wider text-white">
                    Botón de Pánico Táctico SOS
                  </h2>
                </div>
                <p className="mt-2 text-xs text-rose-200/90 leading-relaxed">
                  Protección contra toques accidentales: mantenga presionado{" "}
                  <strong>2.5 segundos</strong> o use la doble confirmación
                  rápida. Captura coordenadas GPS y activa sirena inmediata en
                  la consola de Supervisores y Administradores.
                </p>

                <div className="mt-5 space-y-3">
                  <button
                    type="button"
                    disabled={enviandoSos}
                    onMouseDown={iniciarPresionSos}
                    onMouseUp={cancelarPresionSos}
                    onMouseLeave={cancelarPresionSos}
                    onTouchStart={iniciarPresionSos}
                    onTouchEnd={cancelarPresionSos}
                    className="boton-tactico-campo relative w-full overflow-hidden rounded-2xl border-2 border-rose-400 bg-rose-600 py-5 text-center font-black uppercase tracking-wider text-white shadow-2xl shadow-rose-600/30 transition hover:bg-rose-500 select-none"
                  >
                    <div
                      className="absolute inset-y-0 left-0 bg-amber-400/40 transition-all"
                      style={{ width: `${progresoSos}%` }}
                    />
                    <span className="relative z-10 flex items-center justify-center gap-2 text-sm">
                      <Siren className="h-5 w-5" />
                      {progresoSos > 0
                        ? `MANTENGA PRESIONADO... (${progresoSos}%)`
                        : "MANTENER 2.5s PARA DISPARAR SOS"}
                    </span>
                  </button>

                  {!confirmacionRapidaSos ? (
                    <button
                      type="button"
                      onClick={(): void => setConfirmacionRapidaSos(true)}
                      className="w-full rounded-xl border border-rose-500/40 bg-slate-950 py-2.5 text-xs font-bold text-rose-300 hover:bg-rose-950/60"
                    >
                      O Activar mediante Doble Confirmación Rápida (Paso 1/2)
                    </button>
                  ) : (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={enviandoSos}
                        onClick={(): void => {
                          void ejecutarDisparoSos();
                        }}
                        className="boton-tactico-campo flex-1 rounded-xl bg-amber-400 py-3 text-xs font-black uppercase text-black"
                      >
                        ¡CONFIRMAR ENVÍO SOS AHORA! (Paso 2/2)
                      </button>
                      <button
                        type="button"
                        onClick={(): void => setConfirmacionRapidaSos(false)}
                        className="rounded-xl border border-white/20 bg-slate-900 px-3 py-2 text-xs font-bold text-slate-300"
                      >
                        Cancelar
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-6 rounded-xl border border-white/10 bg-slate-950/80 p-3 text-[11px] text-slate-300">
                <strong>Trazabilidad SuperVigilancia:</strong> Toda activación
                SOS queda asentada en el Libro Foliado SHA-256 con el tiempo de
                reacción en segundos del Supervisor.
              </div>
            </section>

            {/* Acta Digital de Entrega y Recibo de Puesto (Armamento Indumil 3.1) */}
            <section className="lg:col-span-7 rounded-2xl border border-white/10 bg-slate-900/70 p-6">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-4">
                <div className="flex items-center gap-2.5">
                  <ClipboardCheck className="h-5 w-5 text-emerald-400" />
                  <div>
                    <h2 className="text-base font-bold text-white">
                      Acta Digital de Entrega y Recibo de Puesto (Armamento Indumil)
                    </h2>
                    <p className="text-xs text-slate-400">
                      Checklist criptográfico SHA-256 obligatorio en relevos de
                      06:00 y 18:00
                    </p>
                  </div>
                </div>
                {dotacionMiPuesto && (
                  <span className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 font-mono text-xs font-bold text-emerald-300">
                    Salvoconducto {dotacionMiPuesto.numero_salvoconducto_indumil}
                  </span>
                )}
              </div>

              {dotacionMiPuesto && (
                <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3 rounded-xl border border-white/10 bg-slate-950/80 p-3 text-xs">
                  <div>
                    <span className="text-[10px] uppercase text-slate-400 block">
                      Arma de Dotación
                    </span>
                    <strong className="text-white">
                      {dotacionMiPuesto.tipo_arma}
                    </strong>
                    <span className="block font-mono text-[11px] text-cyan-300">
                      Serial: {dotacionMiPuesto.serial_arma}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-slate-400 block">
                      Salvoconducto Indumil ({dotacionMiPuesto.tipo_salvoconducto})
                    </span>
                    <strong className="text-white">
                      Vence: {dotacionMiPuesto.fecha_vencimiento_salvoconducto}
                    </strong>
                    <span className="block font-mono text-[11px] text-amber-300">
                      Munición Autorizada:{" "}
                      {dotacionMiPuesto.cantidad_municion_autorizada} cartuchos
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-slate-400 block">
                      Chaleco & Radio
                    </span>
                    <strong className="text-white">
                      {dotacionMiPuesto.serial_chaleco_balistico}
                    </strong>
                    <span className="block font-mono text-[11px] text-slate-300">
                      Radio: {dotacionMiPuesto.serie_radio_comunicacion}
                    </span>
                  </div>
                </div>
              )}

              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">
                    Estado Arma
                  </label>
                  <select
                    value={estadoArmamento}
                    onChange={(e): void =>
                      setEstadoArmamento(e.target.value as EstadoItemDotacion)
                    }
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-2.5 py-2 text-xs text-white"
                  >
                    <option value="OPTIMO">ÓPTIMO</option>
                    <option value="NOVEDAD">NOVEDAD</option>
                    <option value="FALTANTE">FALTANTE</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">
                    Munición Contada
                  </label>
                  <input
                    type="number"
                    value={municionVerificada}
                    onChange={(e): void =>
                      setMunicionVerificada(Number(e.target.value))
                    }
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-2.5 py-2 text-xs text-white font-mono"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">
                    Chaleco Balístico
                  </label>
                  <select
                    value={estadoChaleco}
                    onChange={(e): void =>
                      setEstadoChaleco(e.target.value as EstadoItemDotacion)
                    }
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-2.5 py-2 text-xs text-white"
                  >
                    <option value="OPTIMO">ÓPTIMO</option>
                    <option value="NOVEDAD">NOVEDAD</option>
                    <option value="FALTANTE">FALTANTE</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">
                    Radio VHF/UHF
                  </label>
                  <select
                    value={estadoRadio}
                    onChange={(e): void =>
                      setEstadoRadio(e.target.value as EstadoItemDotacion)
                    }
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-2.5 py-2 text-xs text-white"
                  >
                    <option value="OPTIMO">ÓPTIMO</option>
                    <option value="NOVEDAD">NOVEDAD</option>
                    <option value="FALTANTE">FALTANTE</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">
                    Linterna / Llaves
                  </label>
                  <select
                    value={estadoLinternaLlaves}
                    onChange={(e): void =>
                      setEstadoLinternaLlaves(
                        e.target.value as EstadoItemDotacion
                      )
                    }
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-2.5 py-2 text-xs text-white"
                  >
                    <option value="OPTIMO">ÓPTIMO</option>
                    <option value="NOVEDAD">NOVEDAD</option>
                    <option value="FALTANTE">FALTANTE</option>
                  </select>
                </div>
              </div>

              <div className="mt-3">
                <label className="block text-[11px] font-bold text-slate-300 mb-1">
                  Observaciones de Entrega / Recibo de Turno
                </label>
                <input
                  type="text"
                  value={observacionesActa}
                  onChange={(e): void => setObservacionesActa(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white"
                />
              </div>

              <button
                type="button"
                disabled={guardandoActa}
                onClick={(): void => {
                  void enviarActaEntregaPuesto();
                }}
                className="boton-tactico-campo mt-4 w-full rounded-xl bg-emerald-500 py-3 text-xs font-black uppercase tracking-wider text-slate-950 hover:bg-emerald-400 transition"
              >
                {guardandoActa
                  ? "Firmando Criptográficamente con SHA-256..."
                  : "Firmar Acta de Entrega/Recibo y Asentar en Minuta SHA-256"}
              </button>
            </section>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* VISTA DEDICADA 2: CONSOLA CORPORATIVA DE CLIENTE (SOLO LECTURA)   */}
      {/* ================================================================= */}
      {esCliente && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-sky-500/40 bg-sky-950/20 p-4">
              <span className="text-[11px] font-bold uppercase text-sky-300">
                Instalación Contratada
              </span>
              <p className="mt-1 text-lg font-black text-white">
                {puestosVisibles[0]?.codigo_puesto ?? "PST-BOG-01"}
              </p>
              <span className="text-xs text-slate-300">
                {puestosVisibles[0]?.nombre_puesto ??
                  "Centro Empresarial Torre Séptima"}
              </span>
            </div>

            <div className="rounded-2xl border border-emerald-500/40 bg-emerald-950/20 p-4">
              <span className="text-[11px] font-bold uppercase text-emerald-300">
                Cumplimiento SLA Rondas QR/GPS
              </span>
              <p className="mt-1 text-2xl font-black text-emerald-300">
                {porcentajeSlaRondas}%
              </p>
              <span className="text-xs text-emerald-200/80">
                Verificación geodésica Haversine activa
              </span>
            </div>

            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-4">
              <span className="text-[11px] font-bold uppercase text-slate-300">
                Armamento & Salvoconducto Puesto
              </span>
              <p className="mt-1 text-sm font-black text-white">
                {dotacionMiPuesto?.tipo_arma ?? "Revólver Llama Martial .38L"}
              </p>
              <span className="text-xs font-mono text-cyan-300">
                Indumil:{" "}
                {dotacionMiPuesto?.numero_salvoconducto_indumil ??
                  "IND-TEN-2026-88412"}
              </span>
            </div>

            <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-4">
              <span className="text-[11px] font-bold uppercase text-slate-300">
                Folios Públicos Auditados
              </span>
              <p className="mt-1 text-2xl font-black text-white">
                {ultimosRegistros.length}
              </p>
              <span className="text-xs text-slate-400">
                Cadena de custodia SHA-256 verificada
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ================================================================= */}
      {/* VISTA 3: KPIs EJECUTIVOS, SUPERVISIÓN Y RRHH (CON BARRA LEY 2101) */}
      {/* ================================================================= */}
      {!esOperador && !esCliente && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[11px] font-bold uppercase">
                  Puestos Cubiertos 24/7
                </span>
                <Building2 className="h-4 w-4 text-cyan-400" />
              </div>
              <p className="mt-2 text-2xl font-black text-white">
                {puestosCubiertosCount} / {puestos.length}
              </p>
              <span className="text-[11px] text-emerald-400 font-semibold">
                Esquema 2x2 continuo activo
              </span>
            </div>

            <div className="rounded-2xl border border-rose-500/30 bg-rose-950/20 p-4">
              <div className="flex items-center justify-between text-rose-300">
                <span className="text-[11px] font-bold uppercase">
                  Alertas SOS Activas
                </span>
                <Siren className="h-4 w-4 text-rose-400" />
              </div>
              <p className="mt-2 text-2xl font-black text-white">
                {alertasSosActivasCount}
              </p>
              <span className="text-[11px] text-rose-300">
                {alertasSos.length} eventos históricos registrados
              </span>
            </div>

            <div className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-4">
              <div className="flex items-center justify-between text-amber-300">
                <span className="text-[11px] font-bold uppercase">
                  Credenciales SV Alerta
                </span>
                <Award className="h-4 w-4 text-amber-400" />
              </div>
              <p className="mt-2 text-2xl font-black text-amber-200">
                {credencialesAlertaCount}
              </p>
              <span className="text-[11px] text-amber-300/80">
                Por vencer (&lt;=30d) o vencidas
              </span>
            </div>

            <div className="rounded-2xl border border-cyan-500/30 bg-cyan-950/20 p-4">
              <div className="flex items-center justify-between text-cyan-300">
                <span className="text-[11px] font-bold uppercase">
                  SLA Rondas QR/GPS
                </span>
                <QrCode className="h-4 w-4 text-cyan-400" />
              </div>
              <p className="mt-2 text-2xl font-black text-cyan-200">
                {porcentajeSlaRondas}%
              </p>
              <span className="text-[11px] text-cyan-300/80">
                Cumplimiento geocerca Haversine
              </span>
            </div>

            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/25 p-4">
              <div className="flex items-center justify-between text-emerald-300">
                <span className="text-[11px] font-bold uppercase">
                  Nómina Ley 2101 (42h)
                </span>
                <TrendingUp className="h-4 w-4 text-emerald-400" />
              </div>
              <p className="mt-2 text-xl font-black text-emerald-300">
                {resumenTurnos
                  ? formatearPesosColombianos(
                      resumenTurnos.costo_total_estimado_cop
                    )
                  : "$0"}
              </p>
              <span className="text-[11px] text-emerald-400/80">
                Desc. Ausentismo:{" "}
                {resumenTurnos?.suma_horas_descuento_ausentismo ?? 0}h
              </span>
            </div>
          </div>

          {/* Barra Visual de Proporción Horas Ordinarias vs Extras y Recargos (Ley 2101 - 42h) */}
          <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="font-bold text-white">
                Proporción de Horas Liquidadas (Tope Legal Semanal:{" "}
                {resumenTurnos?.tope_horas_semanales_aplicado ?? 42} Horas — Ley
                2101 de 2021)
              </span>
              <div className="flex items-center gap-4 text-[11px]">
                <span className="text-emerald-300 font-semibold">
                  ● Ordinarias Base: {horasOrd.toFixed(1)}h ({pctOrdinarias}%)
                </span>
                <span className="text-amber-300 font-semibold">
                  ● Extras (+25%/+75%) y Recargos Nocturnos/Festivos:{" "}
                  {horasExtrasYRecargos.toFixed(1)}h ({pctRecargosExtras}%)
                </span>
              </div>
            </div>
            <div className="mt-2.5 h-3 w-full overflow-hidden rounded-full bg-slate-950 flex border border-white/10">
              <div
                className="bg-emerald-500 h-full transition-all"
                style={{ width: `${pctOrdinarias}%` }}
              />
              <div
                className="bg-amber-400 h-full transition-all"
                style={{ width: `${pctRecargosExtras}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* SECCIÓN CENTRAL: PUESTOS DE VIGILANCIA, GUARDAS EN TURNO Y CREDENCIALES SV */}
      <section className="space-y-4">
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div className="flex items-center gap-2.5">
            <Building2 className="h-5 w-5 text-cyan-400" />
            <div>
              <h2 className="text-lg font-bold text-white">
                {esCliente
                  ? "Estado en Tiempo Real de su Puesto Contratado & Guardas Acreditados"
                  : esOperador
                    ? "Mi Puesto Asignado & Escuadra de Relevo 2x2"
                    : "Puestos de Vigilancia, Cobertura 2x2 y Semáforo SuperVigilancia"}
              </h2>
              <p className="text-xs text-slate-400">
                Verificación en vivo de guardas en turno Diurno (06:00-18:00),
                Nocturno (18:00-06:00) y vigencia de credencial SuperVigilancia.
              </p>
            </div>
          </div>

          {!esOperador && !esCliente && (
            <Link
              to="/personal-puestos"
              className="inline-flex items-center gap-1 text-xs font-semibold text-cyan-400 hover:text-cyan-300"
            >
              <span>Gestionar Credenciales SV & Puestos</span>
              <ChevronRight className="h-4 w-4" />
            </Link>
          )}
        </div>

        {cargando ? (
          <p className="py-12 text-center text-sm text-slate-400">
            Cargando estado táctico de los puestos de vigilancia...
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {puestosVisibles.map((puesto) => {
              const guardiasDelPuesto = guardias.filter(
                (g) => g.puesto_base_id === puesto.puesto_id
              );
              const turnosPuestoHoy = turnosHoy.filter(
                (t) => t.puesto_id === puesto.puesto_id
              );
              const guardiaDia = turnosPuestoHoy.find(
                (t) => t.tipo_turno === "DIURNO"
              );
              const guardiaNoche = turnosPuestoHoy.find(
                (t) => t.tipo_turno === "NOCTURNO"
              );
              const guardiaDescanso = turnosPuestoHoy.find(
                (t) => t.tipo_turno === "DESCANSO"
              );

              return (
                <div
                  key={puesto.puesto_id}
                  className="flex flex-col justify-between rounded-2xl border border-white/10 bg-slate-900/60 p-5 shadow-lg backdrop-blur-xl transition hover:border-cyan-500/30"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="rounded bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 font-mono text-xs font-bold text-cyan-300">
                          {puesto.codigo_puesto}
                        </span>
                        <h3 className="mt-2 text-base font-bold text-white leading-tight">
                          {puesto.nombre_puesto}
                        </h3>
                        <p className="text-xs text-slate-400 mt-0.5">
                          Cliente:{" "}
                          <strong className="text-slate-200">
                            {puesto.empresa_cliente}
                          </strong>
                        </p>
                      </div>

                      <span className="inline-flex items-center gap-1 rounded-full bg-white/5 px-2.5 py-1 text-[11px] text-slate-300 shrink-0">
                        <Shield className="h-3.5 w-3.5 text-emerald-400" />
                        {puesto.requiere_armamento ? "Indumil Armado" : "No Letal"}
                      </span>
                    </div>

                    <div className="mt-3 flex items-center gap-1 text-xs text-slate-400 border-b border-white/5 pb-3">
                      <MapPin className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                      <span>
                        {puesto.direccion_ubicacion} • {puesto.ciudad}
                      </span>
                    </div>

                    <div className="mt-4 space-y-2">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                        Guardas en Turno Hoy (12 Horas):
                      </span>

                      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-2.5 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Sun className="h-4 w-4 text-amber-400" />
                          <div>
                            <span className="text-[10px] font-bold uppercase text-amber-400 block">
                              Turno Día (06:00 - 18:00)
                            </span>
                            <span className="text-xs font-semibold text-white">
                              {guardiaDia
                                ? guardiaDia.nombre_operador
                                : "Sin asignar"}
                            </span>
                          </div>
                        </div>
                        {guardiaDia && (
                          <span className="font-mono text-xs text-amber-300">
                            {guardiaDia.codigo_placa_operador}
                          </span>
                        )}
                      </div>

                      <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-2.5 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Moon className="h-4 w-4 text-indigo-400" />
                          <div>
                            <span className="text-[10px] font-bold uppercase text-indigo-400 block">
                              Turno Noche (18:00 - 06:00)
                            </span>
                            <span className="text-xs font-semibold text-white">
                              {guardiaNoche
                                ? guardiaNoche.nombre_operador
                                : "Sin asignar"}
                            </span>
                          </div>
                        </div>
                        {guardiaNoche && (
                          <span className="font-mono text-xs text-indigo-300">
                            {guardiaNoche.codigo_placa_operador}
                          </span>
                        )}
                      </div>

                      <div className="rounded-xl border border-slate-700 bg-slate-950/40 p-2.5 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Coffee className="h-4 w-4 text-slate-400" />
                          <div>
                            <span className="text-[10px] font-bold uppercase text-slate-400 block">
                              Franco Compensatorio (24h)
                            </span>
                            <span className="text-xs font-medium text-slate-300">
                              {guardiaDescanso
                                ? guardiaDescanso.nombre_operador
                                : "Sin asignar"}
                            </span>
                          </div>
                        </div>
                        {guardiaDescanso && (
                          <span className="font-mono text-xs text-slate-400">
                            {guardiaDescanso.codigo_placa_operador}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Escuadra con Semáforo SuperVigilancia */}
                    <div className="mt-4 pt-3 border-t border-white/5">
                      <span className="text-[11px] font-semibold text-slate-400">
                        Acreditación SuperVigilancia de la Escuadra (
                        {guardiasDelPuesto.length}):
                      </span>
                      <div className="mt-2 space-y-1.5">
                        {guardiasDelPuesto.map((g) => {
                          const sem = evaluarSemaforoCredencialSv(
                            g.fecha_vencimiento_credencial,
                            g.excepcion_credencial_autorizada
                          );
                          return (
                            <div
                              key={g.usuario_id}
                              className="flex items-center justify-between rounded-lg bg-slate-950/70 border border-white/5 px-2.5 py-1.5 text-[11px]"
                            >
                              <span className="text-slate-200 font-medium truncate">
                                <strong className="font-mono text-emerald-400">
                                  {g.codigo_placa}
                                </strong>{" "}
                                • {g.nombre_completo}
                              </span>
                              <span
                                className={`rounded border px-1.5 py-0.5 text-[9px] font-bold shrink-0 ${sem.claseColor}`}
                              >
                                {sem.etiqueta}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 grid grid-cols-2 gap-2 pt-3 border-t border-white/10">
                    {!esCliente ? (
                      <Link
                        to="/turnos-2x2"
                        className="rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-center text-xs font-semibold text-slate-200 transition hover:bg-emerald-500 hover:text-slate-950"
                      >
                        Turnos & Relevos
                      </Link>
                    ) : (
                      <Link
                        to="/rondas-y-reportes"
                        className="rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-center text-xs font-semibold text-slate-200 transition hover:bg-emerald-500 hover:text-slate-950"
                      >
                        SLA Rondas QR
                      </Link>
                    )}
                    <Link
                      to="/minuta-en-vivo"
                      className="rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-center text-xs font-semibold text-slate-200 transition hover:bg-cyan-500 hover:text-slate-950"
                    >
                      {esCliente ? "Minuta Pública" : "Ver Minuta"}
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* SECCIÓN INFERIOR: MINUTA EN TIEMPO REAL & ACTAS SHA-256 RECIENTES */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <section className="lg:col-span-7 rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-2.5">
              <Radio className="h-5 w-5 text-emerald-400 animate-pulse" />
              <div>
                <h2 className="text-base font-bold text-white">
                  {esCliente
                    ? "Minuta Corporativa Filtrada para Cliente (PUBLICA_CLIENTE)"
                    : "Minuta Digital en Tiempo Real (Visibilidad Dual)"}
                </h2>
                <p className="text-xs text-slate-400">
                  {esCliente
                    ? "Eventos públicos verificados en su instalación contratada"
                    : "Transmisión en vivo WebSocket con filtro de visibilidad público/interno"}
                </p>
              </div>
            </div>

            <Link
              to="/minuta-en-vivo"
              className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:text-emerald-300"
            >
              <span>Abrir Bitácora</span>
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-4 space-y-3">
            {ultimosRegistros.map((registro) => (
              <div
                key={registro.registro_id}
                className="rounded-xl border border-white/5 bg-slate-950/60 p-3.5 transition hover:border-white/15"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold ${
                        registro.nivel_prioridad === "CRITICA"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                          : registro.nivel_prioridad === "ALTA"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                            : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      }`}
                    >
                      {registro.nivel_prioridad}
                    </span>
                    <span className="rounded bg-white/10 px-2 py-0.5 font-mono text-[10px] text-cyan-300">
                      {registro.visibilidad ?? "PUBLICA_CLIENTE"}
                    </span>
                    <span className="font-semibold text-sm text-white">
                      {registro.titulo_evento}
                    </span>
                  </div>

                  <span className="text-xs font-mono text-slate-400">
                    {format(new Date(registro.fecha_registro), "HH:mm • dd MMM", {
                      locale: es,
                    })}
                  </span>
                </div>

                <p className="mt-1.5 text-xs text-slate-300 leading-relaxed">
                  {registro.descripcion_detallada}
                </p>

                <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 border-t border-white/5 pt-2 text-[11px] text-slate-400">
                  <span className="text-cyan-300 font-medium">
                    {registro.codigo_puesto} - {registro.nombre_puesto}
                  </span>
                  <span>
                    Guarda:{" "}
                    <strong className="text-slate-200">
                      {registro.nombre_operador}
                    </strong>{" "}
                    ({registro.codigo_placa_operador})
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Historial Reciente de Actas de Entrega y Recibo de Puesto (Indumil SHA-256) */}
        <section className="lg:col-span-5 rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 border-b border-white/10 pb-3">
              <ClipboardCheck className="h-5 w-5 text-cyan-400" />
              <div>
                <h2 className="text-base font-bold text-white">
                  Actas de Relevo & Armamento Indumil (SHA-256)
                </h2>
                <p className="text-xs text-slate-400">
                  Verificaciones de dotación y munición en cambios de turno
                </p>
              </div>
            </div>

            <div className="mt-4 space-y-3">
              {actasRelevo.map((acta) => (
                <div
                  key={acta.acta_id}
                  className="rounded-xl border border-white/10 bg-slate-950/80 p-3 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">
                      {acta.codigo_puesto} • Acta #{acta.acta_id}
                    </span>
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                        acta.alerta_disparada
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                          : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      }`}
                    >
                      {acta.alerta_disparada
                        ? "NOVEDAD / ALERTA"
                        : "ARMAMENTO ÓPTIMO"}
                    </span>
                  </div>
                  <p className="mt-1 text-slate-300">
                    Arma: <strong>{acta.estado_armamento}</strong> • Munición:{" "}
                    <strong className="font-mono text-amber-300">
                      {acta.municion_verificada} cartuchos
                    </strong>{" "}
                    • Chaleco: {acta.estado_chaleco}
                  </p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    Entrega: {acta.nombre_operador_saliente}
                    {acta.nombre_operador_entrante
                      ? ` → Recibe: ${acta.nombre_operador_entrante}`
                      : ""}
                  </p>
                  <p className="mt-1 font-mono text-[10px] text-cyan-400 truncate">
                    SHA-256: {acta.sello_sha256}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-3.5 text-xs">
            <span className="font-bold text-emerald-300 block">
              Normativa Colombiana Release V2.0 Activa
            </span>
            <p className="mt-1 text-slate-400">
              SuperVigilancia • Ley 1920 de 2018 • Ley 2101 de 2021 (42h/sem) •
              Control Indumil y Cadena de Custodia SHA-256.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}

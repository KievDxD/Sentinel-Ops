/**
 * Fases 5, 6 y 7 (Enterprise V2.0):
 * - Fase 5: Control de Rondas con Checkpoints QR/GPS y Cola de Sincronización Offline-First.
 * - Fase 6: Exportación de Prenómina Laboral Colombiana Ley 2101 (42h) + Ausentismos (ADMINISTRADOR y RRHH)
 *   y Libro Foliado Oficial SHA-256 (ADMINISTRADOR, SUPERVISOR y CLIENTE).
 * - Fase 7: Auditoría en Tiempo Real de Cobertura de Puestos y Alertas de Relevo.
 */

import { useCallback, useEffect, useState, type ReactElement } from "react";
import { useForm } from "react-hook-form";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  QrCode,
  MapPin,
  WifiOff,
  CloudUpload,
  FileSpreadsheet,
  FileCheck2,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import {
  extraerMensajeError,
  servicioAbrirLibroFoliadoOficial,
  servicioAuditarCoberturaPuestos,
  servicioDescargarPrenominaCsv,
  servicioListarMarcacionesRonda,
  servicioListarPuntosControl,
  servicioRegistrarMarcacionRonda,
  servicioSincronizarColaOffline,
} from "../servicios/cliente_api";
import { usarAlmacenAutenticacion } from "../estado/almacen_autenticacion";
import type {
  AlertaCoberturaPuesto,
  MarcacionRonda,
  PuntoControlRonda,
  RegistrarMarcacionRondaFormulario,
} from "../tipos/tipos_sistema";

const CLAVE_COLA_OFFLINE = "sentinel_ops_cola_rondas_offline_v1";

function leerColaOfflineLocal(): RegistrarMarcacionRondaFormulario[] {
  try {
    const crudo = localStorage.getItem(CLAVE_COLA_OFFLINE);
    if (!crudo) return [];
    return JSON.parse(crudo) as RegistrarMarcacionRondaFormulario[];
  } catch {
    return [];
  }
}

export function ModuloRondasYReportes(): ReactElement {
  const usuarioActual = usarAlmacenAutenticacion(
    (estado) => estado.usuarioActual
  );
  const rol = usuarioActual?.rol ?? "OPERADOR";
  const esOperador = rol === "OPERADOR";
  const esCliente = rol === "CLIENTE";
  const puedeDescargarPrenomina = rol === "ADMINISTRADOR" || rol === "RRHH";
  const puedeAbrirFolio =
    rol === "ADMINISTRADOR" || rol === "SUPERVISOR" || rol === "CLIENTE";

  const [puntos, setPuntos] = useState<PuntoControlRonda[]>([]);
  const [marcaciones, setMarcaciones] = useState<MarcacionRonda[]>([]);
  const [alertasCobertura, setAlertasCobertura] = useState<
    AlertaCoberturaPuesto[]
  >([]);
  const [colaOffline, setColaOffline] = useState<
    RegistrarMarcacionRondaFormulario[]
  >(leerColaOfflineLocal);
  const [modoSinSenalSimulado, setModoSinSenalSimulado] =
    useState<boolean>(false);
  const [mensajeExito, setMensajeExito] = useState<string | null>(null);
  const [mensajeError, setMensajeError] = useState<string | null>(null);

  const { register, handleSubmit, setValue, reset } =
    useForm<RegistrarMarcacionRondaFormulario>({
      defaultValues: {
        punto_id: 1,
        latitud_capturada: 4.66122,
        longitud_capturada: -74.05349,
        observacion_ronda:
          "Lectura QR en punto táctico verificada. Perímetro asegurado.",
      },
    });

  const cargarTodo = useCallback(async (): Promise<void> => {
    try {
      const [listaPuntos, listaMarcaciones, listaAlertas] = await Promise.all([
        servicioListarPuntosControl(),
        servicioListarMarcacionesRonda(),
        servicioAuditarCoberturaPuestos(),
      ]);
      setPuntos(listaPuntos);
      setMarcaciones(listaMarcaciones);
      setAlertasCobertura(
        esCliente && usuarioActual?.puesto_base_id
          ? listaAlertas.filter(
              (a) => a.puesto_id === usuarioActual.puesto_base_id
            )
          : listaAlertas
      );
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    }
  }, [esCliente, usuarioActual?.puesto_base_id]);

  useEffect((): void => {
    void cargarTodo();
  }, [cargarTodo]);

  const seleccionarCoordenadasDePunto = (puntoId: number): void => {
    const encontrado = puntos.find((p) => p.punto_id === puntoId);
    if (encontrado) {
      setValue("latitud_capturada", encontrado.latitud_gps);
      setValue("longitud_capturada", encontrado.longitud_gps);
    }
  };

  const procesarMarcacion = async (
    datos: RegistrarMarcacionRondaFormulario
  ): Promise<void> => {
    setMensajeError(null);
    setMensajeExito(null);

    const carga: RegistrarMarcacionRondaFormulario = {
      punto_id: Number(datos.punto_id),
      latitud_capturada: Number(datos.latitud_capturada),
      longitud_capturada: Number(datos.longitud_capturada),
      observacion_ronda: datos.observacion_ronda,
    };

    if (modoSinSenalSimulado || !navigator.onLine) {
      const nuevaCola = [...colaOffline, carga];
      setColaOffline(nuevaCola);
      localStorage.setItem(CLAVE_COLA_OFFLINE, JSON.stringify(nuevaCola));
      setMensajeExito(
        "Sin conexión en sótano/campo: La marcación QR/GPS se guardó en la Cola Offline-First local para sincronización posterior."
      );
      return;
    }

    try {
      const creada = await servicioRegistrarMarcacionRonda(carga);
      setMarcaciones((previas) => [creada, ...previas]);
      await cargarTodo();
      reset({
        ...carga,
        observacion_ronda: "Verificación de checkpoint sin novedad.",
      });
      setMensajeExito(
        `Marcación QR/GPS registrada (${creada.distancia_calculada_metros}m del punto - ${creada.dentro_de_geocerca ? "DENTRO DE GEOCERCA" : "FUERA DE RANGO"}) y emitida en vivo a Minuta.`
      );
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    }
  };

  const sincronizarColaPendiente = async (): Promise<void> => {
    if (colaOffline.length === 0) return;
    setMensajeError(null);
    setMensajeExito(null);
    try {
      const sincronizadas = await servicioSincronizarColaOffline(colaOffline);
      localStorage.removeItem(CLAVE_COLA_OFFLINE);
      setColaOffline([]);
      await cargarTodo();
      setMensajeExito(
        `Se sincronizaron exitosamente ${sincronizadas.length} marcaciones retenidas en modo Offline-First.`
      );
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    }
  };

  return (
    <div className="space-y-6">
      {!esOperador && (
        <section className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-emerald-500/30 bg-slate-900/70 p-6 backdrop-blur-xl">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
              Fase 6 // Cumplimiento Normativo Colombiano (Ley 2101 &
              SuperVigilancia)
            </span>
            <h2 className="mt-1 text-lg font-bold text-white">
              {puedeDescargarPrenomina
                ? "Exportación Contable de Prenómina Ley 2101 (42h) y Libro Foliado SHA-256"
                : "Expedición del Libro Foliado Oficial con Sello Criptográfico SHA-256"}
            </h2>
            <p className="text-xs text-slate-400">
              {puedeDescargarPrenomina
                ? "Incluye descuento automático por ausentismos (EPS/ARL/Licencia) para Siigo/Novasoft."
                : "Auditoría criptográfica de cadena de custodia SHA-256."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {puedeDescargarPrenomina && (
              <button
                type="button"
                onClick={(): void => {
                  void servicioDescargarPrenominaCsv();
                }}
                className="boton-tactico-campo inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-xs font-bold text-slate-950 shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-400"
              >
                <FileSpreadsheet className="h-4 w-4" />
                <span>Descargar Prenómina Ley 2101 (.CSV / Excel)</span>
              </button>
            )}

            {puedeAbrirFolio && (
              <button
                type="button"
                onClick={(): void => {
                  void servicioAbrirLibroFoliadoOficial();
                }}
                className="boton-tactico-campo inline-flex items-center gap-2 rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-4 py-2.5 text-xs font-bold text-cyan-300 transition hover:bg-cyan-500/20"
              >
                <FileCheck2 className="h-4 w-4" />
                <span>Abrir Libro Foliado Oficial SHA-256 (PDF)</span>
              </button>
            )}
          </div>
        </section>
      )}

      {mensajeExito && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-4 text-sm text-emerald-200">
          <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
          <span>{mensajeExito}</span>
        </div>
      )}

      {mensajeError && (
        <div className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-sm text-rose-200">
          <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0" />
          <span>{mensajeError}</span>
        </div>
      )}

      {!esOperador && (
        <section className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex items-center gap-2.5 border-b border-white/10 pb-4">
            <ShieldAlert className="h-5 w-5 text-amber-400" />
            <h2 className="text-lg font-bold text-white">
              Auditoría SLA de Cobertura y Rondas QR/GPS (Fase 7)
            </h2>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
            {alertasCobertura.map((alerta) => (
              <div
                key={alerta.puesto_id}
                className={`rounded-xl border p-4 ${
                  alerta.nivel_alerta === "CRITICA"
                    ? "border-rose-500/40 bg-rose-950/25"
                    : alerta.nivel_alerta === "MEDIA"
                      ? "border-amber-500/40 bg-amber-950/20"
                      : "border-emerald-500/30 bg-emerald-950/20"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-cyan-300">
                    {alerta.codigo_puesto}
                  </span>
                  <span className="rounded px-2 py-0.5 text-[10px] font-bold uppercase bg-black/40 text-white">
                    {alerta.estado_cobertura}
                  </span>
                </div>
                <h3 className="mt-2 font-bold text-white">
                  {alerta.nombre_puesto}
                </h3>
                <p className="mt-1 text-xs text-slate-300">
                  Guarda:{" "}
                  <strong className="text-white">
                    {alerta.operador_en_turno}
                  </strong>
                </p>
                <p className="mt-2 text-xs text-slate-400">
                  {alerta.detalle_operativo}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        {!esCliente && (
          <section className="xl:col-span-5 rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl h-fit">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center gap-2.5">
                <QrCode className="h-5 w-5 text-emerald-400" />
                <h2 className="text-lg font-bold text-white">
                  Escáner de Rondas QR / GPS
                </h2>
              </div>

              <button
                type="button"
                onClick={(): void =>
                  setModoSinSenalSimulado((previo) => !previo)
                }
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold transition ${
                  modoSinSenalSimulado
                    ? "border-amber-500/50 bg-amber-500/20 text-amber-300"
                    : "border-white/10 bg-white/5 text-slate-300"
                }`}
              >
                <WifiOff className="h-3.5 w-3.5" />
                <span>
                  {modoSinSenalSimulado
                    ? "Modo Sótano (Offline Activo)"
                    : "Simular Modo Offline"}
                </span>
              </button>
            </div>

            {colaOffline.length > 0 && (
              <div className="mt-4 flex items-center justify-between rounded-xl border border-amber-500/40 bg-amber-950/30 p-3.5">
                <span className="text-xs font-semibold text-amber-200">
                  {colaOffline.length} marcaciones en Cola Offline local
                </span>
                <button
                  type="button"
                  onClick={(): void => {
                    void sincronizarColaPendiente();
                  }}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-amber-400 px-3 py-1.5 text-xs font-bold text-slate-950 hover:bg-amber-300"
                >
                  <CloudUpload className="h-3.5 w-3.5" />
                  <span>Sincronizar Ahora</span>
                </button>
              </div>
            )}

            <form
              onSubmit={(e): void => {
                void handleSubmit(procesarMarcacion)(e);
              }}
              className="mt-5 space-y-4"
            >
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
                  Punto de Control (Checkpoint QR)
                </label>
                <select
                  {...register("punto_id", {
                    required: true,
                    onChange: (ev: { target: { value: string } }): void => {
                      seleccionarCoordenadasDePunto(Number(ev.target.value));
                    },
                  })}
                  className="w-full rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2.5 text-xs text-white"
                >
                  {puntos.map((p) => (
                    <option key={p.punto_id} value={p.punto_id}>
                      {p.codigo_qr_hash} — {p.nombre_punto} (Tolerancia{" "}
                      {p.radio_tolerancia_metros}m)
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Latitud GPS Capturada
                  </label>
                  <input
                    type="number"
                    step="any"
                    {...register("latitud_capturada", { required: true })}
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm font-mono text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Longitud GPS Capturada
                  </label>
                  <input
                    type="number"
                    step="any"
                    {...register("longitud_capturada", { required: true })}
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm font-mono text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
                  Observación de Ronda
                </label>
                <textarea
                  rows={2}
                  {...register("observacion_ronda", { required: true })}
                  className="w-full rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
              </div>

              <button
                type="submit"
                className="boton-tactico-campo w-full rounded-xl bg-emerald-500 py-3 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:bg-emerald-400"
              >
                {modoSinSenalSimulado
                  ? "Guardar Marcación en Cola Offline Local"
                  : "Validar Geocerca GPS y Registrar Lectura QR"}
              </button>
            </form>
          </section>
        )}

        <section
          className={`${
            esCliente ? "xl:col-span-12" : "xl:col-span-7"
          } rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl`}
        >
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-2.5">
              <MapPin className="h-5 w-5 text-cyan-400" />
              <h2 className="text-lg font-bold text-white">
                Bitácora Geodésica de Marcaciones QR / GPS (Haversine)
              </h2>
            </div>
            <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300">
              {marcaciones.length} Verificaciones
            </span>
          </div>

          <div className="mt-4 space-y-3">
            {marcaciones.map((m) => (
              <div
                key={m.marcacion_id}
                className="rounded-xl border border-white/10 bg-slate-950/70 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 font-mono text-xs font-bold text-emerald-300">
                      {m.codigo_qr_hash}
                    </span>
                    <span className="font-semibold text-sm text-white">
                      {m.nombre_punto}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {m.sincronizado_desde_offline && (
                      <span className="rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-300">
                        SINCRONIZADO OFFLINE
                      </span>
                    )}
                    <span
                      className={`rounded-md border px-2 py-0.5 text-[11px] font-bold ${
                        m.dentro_de_geocerca
                          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                          : "border-rose-500/40 bg-rose-500/20 text-rose-300"
                      }`}
                    >
                      {m.dentro_de_geocerca
                        ? `En Geocerca (${m.distancia_calculada_metros}m)`
                        : `Fuera de Rango (${m.distancia_calculada_metros}m)`}
                    </span>
                  </div>
                </div>

                <p className="mt-2 text-xs text-slate-300">
                  {m.observacion_ronda}
                </p>

                <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                  <span>
                    Guarda:{" "}
                    <strong className="text-slate-200">
                      {m.nombre_operador}
                    </strong>{" "}
                    • GPS:{" "}
                    <span className="font-mono">
                      {m.latitud_capturada}, {m.longitud_capturada}
                    </span>
                  </span>
                  <span className="font-mono">
                    {format(new Date(m.fecha_marcacion), "dd MMM HH:mm:ss", {
                      locale: es,
                    })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

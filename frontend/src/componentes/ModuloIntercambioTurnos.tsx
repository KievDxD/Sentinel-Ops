/**
 * Módulo 4: Sistema de Intercambio de Turnos con Validación de Cruce de Horarios
 * y Tiempo Mínimo de Descanso Legal (>= 12 horas) antes de aprobación del Supervisor.
 */

import { useCallback, useEffect, useState, type ReactElement } from "react";
import { useForm } from "react-hook-form";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  ArrowLeftRight,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
} from "lucide-react";
import {
  extraerMensajeError,
  servicioConsultarTurnos,
  servicioCrearIntercambio,
  servicioListarIntercambios,
  servicioResolverIntercambio,
} from "../servicios/cliente_api";
import { usarAlmacenAutenticacion } from "../estado/almacen_autenticacion";
import type {
  CrearSolicitudIntercambioFormulario,
  SolicitudIntercambioTurno,
  TurnoOperativo,
} from "../tipos/tipos_sistema";

export function ModuloIntercambioTurnos(): ReactElement {
  const usuarioActual = usarAlmacenAutenticacion(
    (estado) => estado.usuarioActual
  );
  const [intercambios, setIntercambios] = useState<SolicitudIntercambioTurno[]>(
    []
  );
  const [turnosOperativos, setTurnosOperativos] = useState<TurnoOperativo[]>(
    []
  );
  const [mensajeExito, setMensajeExito] = useState<string | null>(null);
  const [mensajeError, setMensajeError] = useState<string | null>(null);
  const [cargando, setCargando] = useState<boolean>(true);

  const { register, handleSubmit, reset } =
    useForm<CrearSolicitudIntercambioFormulario>();

  const cargarDatosIntercambios = useCallback(async (): Promise<void> => {
    setCargando(true);
    try {
      const [listaSolicitudes, resumenTurnos] = await Promise.all([
        servicioListarIntercambios(),
        servicioConsultarTurnos(),
      ]);
      setIntercambios(listaSolicitudes);
      setTurnosOperativos(
        resumenTurnos.turnos.filter((t) => t.tipo_turno !== "DESCANSO")
      );
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect((): void => {
    void cargarDatosIntercambios();
  }, [cargarDatosIntercambios]);

  const enviarSolicitudIntercambio = async (
    datos: CrearSolicitudIntercambioFormulario
  ): Promise<void> => {
    setMensajeError(null);
    setMensajeExito(null);
    try {
      const nueva = await servicioCrearIntercambio({
        turno_origen_id: Number(datos.turno_origen_id),
        turno_destino_id: Number(datos.turno_destino_id),
        motivo_solicitud: datos.motivo_solicitud,
      });
      setIntercambios((previas) => [nueva, ...previas]);
      reset();
      setMensajeExito(
        `Solicitud #${nueva.intercambio_id} validada por el Motor de Turnos (${nueva.horas_descanso_minimo_calculadas}h de descanso mínimo verificado) y enviada al Supervisor.`
      );
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    }
  };

  const procesarResolucionSupervisor = async (
    intercambioId: number,
    aprobar: boolean
  ): Promise<void> => {
    setMensajeError(null);
    setMensajeExito(null);
    try {
      const actualizada = await servicioResolverIntercambio(intercambioId, {
        aprobar,
        comentario_supervisor: aprobar
          ? "Aprobado por Supervisión Táctica tras verificar cumplimiento de descanso legal (>= 12h) y ausencia de cruces."
          : "Rechazado por requerimiento operativo del puesto de vigilancia.",
      });
      setIntercambios((previas) =>
        previas.map((item) =>
          item.intercambio_id === intercambioId ? actualizada : item
        )
      );
      await cargarDatosIntercambios();
      setMensajeExito(
        aprobar
          ? `Intercambio #${intercambioId} APROBADO. Los operadores fueron permutados atómicamente en la programación.`
          : `Intercambio #${intercambioId} RECHAZADO por el supervisor.`
      );
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    }
  };

  const puedeResolverComoSupervisor =
    usuarioActual?.rol === "SUPERVISOR" ||
    usuarioActual?.rol === "ADMINISTRADOR";

  return (
    <div className="space-y-6">
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

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        {/* Formulario de Solicitud con Validación de Cruce y Descanso */}
        <section className="xl:col-span-5 rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl h-fit">
          <div className="flex items-center gap-2.5 border-b border-white/10 pb-4">
            <ArrowLeftRight className="h-5 w-5 text-emerald-400" />
            <div>
              <h2 className="text-lg font-bold text-white">
                Solicitar Intercambio de Turno
              </h2>
              <p className="text-xs text-slate-400">
                El backend bloquea cruces horarios y exige descanso &ge; 12h
              </p>
            </div>
          </div>

          <form
            onSubmit={(e): void => {
              void handleSubmit(enviarSolicitudIntercambio)(e);
            }}
            className="mt-5 space-y-4"
          >
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
                Turno Origen (Guardia Solicitante)
              </label>
              <select
                {...register("turno_origen_id", { required: true })}
                className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-xs text-white"
              >
                {turnosOperativos.map((t) => (
                  <option key={t.turno_id} value={t.turno_id}>
                    #{t.turno_id} • {t.nombre_operador} ({t.tipo_turno}) -{" "}
                    {format(new Date(t.fecha_inicio), "dd MMM HH:mm", {
                      locale: es,
                    })}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
                Turno Destino (Guardia Receptor para Permutar)
              </label>
              <select
                {...register("turno_destino_id", { required: true })}
                className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-xs text-white"
              >
                {turnosOperativos.map((t) => (
                  <option key={t.turno_id} value={t.turno_id}>
                    #{t.turno_id} • {t.nombre_operador} ({t.tipo_turno}) -{" "}
                    {format(new Date(t.fecha_inicio), "dd MMM HH:mm", {
                      locale: es,
                    })}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
                Justificación Operativa o Médica
              </label>
              <textarea
                rows={3}
                {...register("motivo_solicitud", { required: true })}
                placeholder="Explica el motivo del relevo/intercambio de turno..."
                className="w-full rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
              />
            </div>

            <button
              type="submit"
              className="w-full rounded-xl bg-emerald-500 py-3 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:bg-emerald-400"
            >
              Validar Horarios/Descanso y Enviar Solicitud
            </button>
          </form>
        </section>

        {/* Bandeja de Solicitudes y Panel de Aprobación del Supervisor */}
        <section className="xl:col-span-7 rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="h-5 w-5 text-cyan-400" />
              <h2 className="text-lg font-bold text-white">
                Bandeja de Auditoría y Aprobación de Intercambios
              </h2>
            </div>
            <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300">
              {intercambios.length} Solicitudes
            </span>
          </div>

          {cargando ? (
            <p className="py-10 text-center text-sm text-slate-400">
              Cargando historial de intercambios...
            </p>
          ) : (
            <div className="mt-4 space-y-4">
              {intercambios.map((item) => (
                <article
                  key={item.intercambio_id}
                  className="rounded-xl border border-white/10 bg-slate-950/70 p-5"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-xs font-bold text-emerald-400">
                      SOLICITUD #{item.intercambio_id}
                    </span>

                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-300">
                        <Clock className="h-3 w-3" />
                        Descanso Mínimo:{" "}
                        {item.horas_descanso_minimo_calculadas}h
                      </span>

                      <span
                        className={`rounded-md border px-2.5 py-0.5 text-xs font-bold ${
                          item.estado_solicitud === "APROBADA"
                            ? "border-emerald-500/40 bg-emerald-500/20 text-emerald-300"
                            : item.estado_solicitud === "RECHAZADA"
                              ? "border-rose-500/40 bg-rose-500/20 text-rose-300"
                              : "border-amber-500/40 bg-amber-500/20 text-amber-300"
                        }`}
                      >
                        {item.estado_solicitud}
                      </span>
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 rounded-xl border border-white/5 bg-slate-900/70 p-3 text-xs">
                    <div>
                      <span className="text-slate-400">
                        Solicitante ({item.nombre_solicitante}):
                      </span>
                      <p className="mt-0.5 font-semibold text-white">
                        {item.resumen_turno_origen}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-400">
                        Receptor ({item.nombre_receptor}):
                      </span>
                      <p className="mt-0.5 font-semibold text-cyan-300">
                        {item.resumen_turno_destino}
                      </p>
                    </div>
                  </div>

                  <p className="mt-3 text-xs text-slate-300">
                    <strong>Motivo:</strong> {item.motivo_solicitud}
                  </p>
                  <p className="mt-1 text-xs text-emerald-300/90">
                    <strong>Dictamen Técnico del Motor:</strong>{" "}
                    {item.detalle_validacion_motor}
                  </p>

                  {item.comentario_supervisor && (
                    <p className="mt-2 rounded-lg bg-white/5 p-2 text-xs text-slate-300">
                      <strong>Resolución Supervisión ({item.nombre_supervisor}):</strong>{" "}
                      {item.comentario_supervisor}
                    </p>
                  )}

                  {puedeResolverComoSupervisor &&
                    item.estado_solicitud === "PENDIENTE" && (
                      <div className="mt-4 flex items-center gap-3 border-t border-white/10 pt-3">
                        <button
                          type="button"
                          onClick={(): void => {
                            void procesarResolucionSupervisor(
                              item.intercambio_id,
                              true
                            );
                          }}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3.5 py-2 text-xs font-bold text-slate-950 transition hover:bg-emerald-400"
                        >
                          <CheckCircle2 className="h-4 w-4" />
                          Aprobar y Permutar Turnos
                        </button>

                        <button
                          type="button"
                          onClick={(): void => {
                            void procesarResolucionSupervisor(
                              item.intercambio_id,
                              false
                            );
                          }}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3.5 py-2 text-xs font-bold text-rose-300 transition hover:bg-rose-500/20"
                        >
                          <XCircle className="h-4 w-4" />
                          Rechazar Solicitud
                        </button>
                      </div>
                    )}
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}


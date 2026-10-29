import React, { useState, useEffect } from "react";
import {
  servicioObtenerTelemetriaMapa,
  servicioSugerirPatrullaCercana,
  servicioDespacharPatrulla,
  servicioRegistrarLlegadaPatrulla,
  servicioFinalizarDespachoCad,
  servicioListarAlertasSos,
  extraerMensajeError,
} from "../servicios/cliente_api";
import type {
  ResumenMapaTactico,
  AlertaPanicoSos,
  CandidatoSupervisorCercano,
  DespachoPatrulla,
} from "../tipos/tipos_sistema";

export function ModuloDespachoCAD(): React.ReactElement {
  const [telemetria, setTelemetria] = useState<ResumenMapaTactico | null>(null);
  const [alertasSos, setAlertasSos] = useState<AlertaPanicoSos[]>([]);
  const [alertaSeleccionadaId, setAlertaSeleccionadaId] = useState<number | null>(
    null
  );
  const [candidatos, setCandidatos] = useState<CandidatoSupervisorCercano[]>([]);
  const [calculandoCandidatos, setCalculandoCandidatos] =
    useState<boolean>(false);

  // Despacho activo
  const [despachoActivo, setDespachoActivo] = useState<DespachoPatrulla | null>(
    null
  );
  const [informeCierre, setInformeCierre] = useState<string>("");
  const [procesando, setProcesando] = useState<boolean>(false);
  const [mensaje, setMensaje] = useState<{
    tipo: "exito" | "error";
    texto: string;
  } | null>(null);

  useEffect(() => {
    cargarDatosCAD();
    const intervalo = setInterval(cargarDatosCAD, 10000); // Polling cada 10s para el mapa
    return () => clearInterval(intervalo);
  }, []);

  async function cargarDatosCAD() {
    try {
      const [resTelemetria, resAlertas] = await Promise.all([
        servicioObtenerTelemetriaMapa(),
        servicioListarAlertasSos(true), // Solo activas
      ]);
      setTelemetria(resTelemetria);
      setAlertasSos(resAlertas);
    } catch (err) {
      console.error("Error al cargar telemetría CAD:", err);
    }
  }

  async function handleAnalizarAlerta(alertaId: number) {
    setAlertaSeleccionadaId(alertaId);
    setCalculandoCandidatos(true);
    try {
      const lista = await servicioSugerirPatrullaCercana(alertaId);
      setCandidatos(lista);
    } catch (err) {
      setMensaje({
        tipo: "error",
        texto: `Fallo al calcular cercanía: ${extraerMensajeError(err)}`,
      });
    } finally {
      setCalculandoCandidatos(false);
    }
  }

  async function handleDespachar(supervisorId: number) {
    if (!alertaSeleccionadaId) return;
    setProcesando(true);
    try {
      const despacho = await servicioDespacharPatrulla(
        alertaSeleccionadaId,
        supervisorId
      );
      setDespachoActivo(despacho);
      setMensaje({
        tipo: "exito",
        texto: `Patrulla ${despacho.codigo_placa_supervisor} despachada hacia ${despacho.nombre_puesto}. ETA: ${despacho.eta_minutos_estimado} min.`,
      });
      cargarDatosCAD();
    } catch (err) {
      setMensaje({
        tipo: "error",
        texto: `Error al despachar patrulla: ${extraerMensajeError(err)}`,
      });
    } finally {
      setProcesando(false);
    }
  }

  async function handleRegistrarLlegada() {
    if (!despachoActivo) return;
    setProcesando(true);
    try {
      const actualizado = await servicioRegistrarLlegadaPatrulla(
        despachoActivo.despacho_id
      );
      setDespachoActivo(actualizado);
      setMensaje({
        tipo: "exito",
        texto: `Arribo confirmado en sitio en ${actualizado.tiempo_arribo_segundos} segundos.`,
      });
    } catch (err) {
      setMensaje({
        tipo: "error",
        texto: `Error al registrar llegada: ${extraerMensajeError(err)}`,
      });
    } finally {
      setProcesando(false);
    }
  }

  async function handleFinalizarDespacho() {
    if (!despachoActivo || !informeCierre) return;
    setProcesando(true);
    try {
      await servicioFinalizarDespachoCad(
        despachoActivo.despacho_id,
        informeCierre
      );
      setMensaje({
        tipo: "exito",
        texto: "Incidente cerrado formalmente y acta táctica archivada.",
      });
      setDespachoActivo(null);
      setAlertaSeleccionadaId(null);
      setCandidatos([]);
      setInformeCierre("");
      cargarDatosCAD();
    } catch (err) {
      setMensaje({
        tipo: "error",
        texto: `Error al finalizar despacho: ${extraerMensajeError(err)}`,
      });
    } finally {
      setProcesando(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="bg-slate-900 border border-emerald-500/30 rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full">
                FASE 11 • CONSOLA CAD
              </span>
              <span className="text-xs text-slate-400 font-mono">
                DESPACHO ASISTIDO • MONITOREO GPS EN VIVO
              </span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span className="text-emerald-400">📡</span> Centro de Despacho Táctico & GPS Patrullas
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Geolocalización en tiempo real, detección de la patrulla más cercana mediante distancia Haversine, cálculo de ETA y certificación de tiempos de respuesta.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-xs font-mono text-emerald-300 font-bold">
              RADAR ACTIVO
            </span>
          </div>
        </div>
      </div>

      {mensaje && (
        <div
          className={`p-4 rounded-lg border text-sm font-medium flex items-center justify-between ${
            mensaje.tipo === "exito"
              ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300"
              : "bg-rose-950/40 border-rose-500/40 text-rose-300"
          }`}
        >
          <span>{mensaje.texto}</span>
          <button
            onClick={() => setMensaje(null)}
            className="text-xs underline hover:no-underline ml-4"
          >
            Cerrar
          </button>
        </div>
      )}

      {/* Cuadrícula Principal: Mapa Radar a la izquierda, Consola de Despacho a la derecha */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Radar Cartográfico Satelital (7 columnas) */}
        <div className="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="flex justify-between items-center border-b border-slate-800 pb-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-sky-400" />
              Mapa Táctico de Jurisdicción (Bogotá / Medellín)
            </h3>
            <span className="text-xs font-mono text-slate-400">
              {telemetria?.puestos.length ?? 0} Puestos • {telemetria?.supervisores.length ?? 0} Patrullas
            </span>
          </div>

          {/* Lienzo del Radar Táctico */}
          <div className="relative h-96 bg-slate-950 rounded-xl border border-slate-800 overflow-hidden flex items-center justify-center p-4">
            {/* Cuadrícula táctica de fondo */}
            <div
              className="absolute inset-0 opacity-15"
              style={{
                backgroundImage:
                  "radial-gradient(#10b981 1px, transparent 1px), radial-gradient(#10b981 1px, #020617 1px)",
                backgroundSize: "30px 30px",
                backgroundPosition: "0 0, 15px 15px",
              }}
            />

            {/* Círculos concéntricos de radar */}
            <div className="absolute w-72 h-72 border border-emerald-500/20 rounded-full pointer-events-none" />
            <div className="absolute w-44 h-44 border border-emerald-500/20 rounded-full pointer-events-none" />

            {/* Puntos de Vigilancia Representados */}
            <div className="relative z-10 w-full h-full flex flex-col justify-around">
              <div className="flex justify-between px-6">
                {telemetria?.puestos.slice(0, 2).map((p) => (
                  <div
                    key={p.puesto_id}
                    className={`p-2.5 rounded-lg border text-left shadow-lg backdrop-blur-md max-w-[200px] ${
                      p.estado_seguridad === "ALERTA_SOS"
                        ? "bg-rose-950/80 border-rose-500 text-rose-200 animate-pulse"
                        : "bg-slate-900/90 border-slate-700 text-slate-200"
                    }`}
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          p.estado_seguridad === "ALERTA_SOS"
                            ? "bg-rose-400"
                            : "bg-emerald-400"
                        }`}
                      />
                      <span className="text-[10px] font-mono font-bold">
                        {p.codigo_puesto}
                      </span>
                    </div>
                    <div className="text-xs font-bold truncate">
                      {p.nombre_puesto}
                    </div>
                    <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                      GPS: {p.latitud_gps.toFixed(3)}, {p.longitud_gps.toFixed(3)}
                    </div>
                  </div>
                ))}
              </div>

              {/* Patrullas Motorizadas en Tránsito */}
              <div className="flex justify-center gap-6">
                {telemetria?.supervisores.map((s) => (
                  <div
                    key={s.supervisor_id}
                    className="p-2.5 bg-sky-950/80 border border-sky-500/50 rounded-lg text-left shadow-lg text-sky-200 max-w-[180px]"
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-xs">🏍️</span>
                      <span className="text-[10px] font-mono font-bold text-sky-400">
                        {s.codigo_placa}
                      </span>
                    </div>
                    <div className="text-xs font-bold truncate">
                      {s.nombre_supervisor}
                    </div>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 bg-sky-500/20 rounded text-sky-300">
                      {s.estado_disponibilidad}
                    </span>
                  </div>
                ))}
              </div>

              <div className="flex justify-end px-12">
                {telemetria?.puestos.slice(2).map((p) => (
                  <div
                    key={p.puesto_id}
                    className="p-2.5 rounded-lg border bg-slate-900/90 border-slate-700 text-slate-200 max-w-[200px]"
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="w-2 h-2 rounded-full bg-emerald-400" />
                      <span className="text-[10px] font-mono font-bold">
                        {p.codigo_puesto}
                      </span>
                    </div>
                    <div className="text-xs font-bold truncate">
                      {p.nombre_puesto}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Consola de Despacho y Asignación Automática (5 columnas) */}
        <div className="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-400" />
                Alertas SOS Activas ({alertasSos.length})
              </span>
            </h3>
          </div>

          {alertasSos.length === 0 ? (
            <div className="p-8 text-center text-slate-500 border border-dashed border-slate-800 rounded-lg text-xs font-mono">
              ✓ Jurisdicción despejada. No hay emergencias SOS activas.
            </div>
          ) : (
            <div className="space-y-2.5">
              {alertasSos.map((a) => (
                <div
                  key={a.alerta_id}
                  className={`p-3 rounded-lg border text-xs cursor-pointer transition ${
                    alertaSeleccionadaId === a.alerta_id
                      ? "bg-rose-950/60 border-rose-500"
                      : "bg-slate-950/80 border-slate-800 hover:border-slate-700"
                  }`}
                  onClick={() => handleAnalizarAlerta(a.alerta_id)}
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-bold text-rose-400">
                      🚨 PÁNICO SOS #{a.alerta_id}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      {new Date(a.fecha_activacion).toLocaleTimeString("es-CO")}
                    </span>
                  </div>
                  <div className="font-semibold text-white">
                    {a.nombre_puesto}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Operador: {a.nombre_operador} ({a.codigo_placa_operador})
                  </div>
                  <button
                    type="button"
                    className="mt-2 text-xs font-bold text-sky-400 hover:underline"
                  >
                    {calculandoCandidatos && alertaSeleccionadaId === a.alerta_id
                      ? "Calculando geocercas..."
                      : "Calcular Patrullas Más Cercanas →"}
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Patrullas Recomendadas por Distancia Haversine y ETA */}
          {candidatos.length > 0 && !despachoActivo && (
            <div className="mt-4 pt-4 border-t border-slate-800 space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-sky-400">
                Patrullas Ordenadas por Proximidad (Haversine):
              </h4>

              {candidatos.map((c) => (
                <div
                  key={c.supervisor_id}
                  className={`p-3 rounded-lg border flex justify-between items-center text-xs ${
                    c.recomendado
                      ? "bg-emerald-950/30 border-emerald-500/50 text-emerald-200"
                      : "bg-slate-950 border-slate-800 text-slate-300"
                  }`}
                >
                  <div>
                    <div className="font-bold flex items-center gap-1.5">
                      <span>{c.nombre_supervisor}</span>
                      <span className="font-mono text-[10px] px-1 bg-white/10 rounded">
                        {c.codigo_placa}
                      </span>
                      {c.recomendado && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                          MÁS CERCANA
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] font-mono opacity-80 mt-1">
                      Distancia: <strong>{c.distancia_km} km</strong> • ETA: <strong>{c.eta_minutos} min</strong>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDespachar(c.supervisor_id)}
                    disabled={procesando}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-slate-950 font-bold rounded text-xs transition"
                  >
                    Despachar
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Despacho en Curso */}
          {despachoActivo && (
            <div className="mt-4 p-4 rounded-xl border border-sky-500/40 bg-sky-950/30 space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-sky-400 uppercase font-mono">
                  ORDEN DE DESPACHO EN CURSO
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-500/20 text-sky-300">
                  {despachoActivo.estado_despacho}
                </span>
              </div>

              <div className="text-xs text-slate-200">
                Patrulla: <strong>{despachoActivo.nombre_supervisor}</strong> ({despachoActivo.codigo_placa_supervisor})
                <br />
                Destino: <strong>{despachoActivo.nombre_puesto}</strong>
              </div>

              {despachoActivo.estado_despacho === "EN_RUTA" ? (
                <button
                  onClick={handleRegistrarLlegada}
                  disabled={procesando}
                  className="w-full py-2 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-lg transition"
                >
                  Confirmar Llegada en Sitio (Parar Cronómetro)
                </button>
              ) : (
                <div className="space-y-2">
                  <div className="text-[11px] text-emerald-400 font-mono">
                    ✓ Arribo confirmado en {despachoActivo.tiempo_arribo_segundos} segundos.
                  </div>
                  <textarea
                    rows={2}
                    placeholder="Informe táctico de cierre del supervisor..."
                    value={informeCierre}
                    onChange={(e) => setInformeCierre(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-white"
                  />
                  <button
                    onClick={handleFinalizarDespacho}
                    disabled={procesando || !informeCierre}
                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-lg transition"
                  >
                    Finalizar y Archivar Incidente
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

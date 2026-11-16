import React, { useEffect, useState } from "react";
import {
  Shield,
  Truck,
  Dog,
  Cpu,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Navigation,
  Plus,
  HeartPulse,
  Zap,
  Lock,
  Activity,
} from "lucide-react";
import {
  servicioListarEscoltasBasc,
  servicioCrearEscoltaBasc,
  servicioVerificarCorredorEscolta,
  servicioListarBinomiosK9,
  servicioRegistrarDescansoK9,
  servicioListarMediosTecnologicos,
} from "../servicios/cliente_api";
import type {
  MisionEscoltaBasc,
  BinomioCaninoK9,
  MedioTecnologicoPuesto,
} from "../tipos/tipos_sistema";

type PestanaActiva = "ESCOLTAS_BASC" | "BINOMIOS_K9" | "MEDIOS_TECNOLOGICOS";

export const OperacionesEspecialesK9: React.FC = () => {
  const [pestana, setPestana] = useState<PestanaActiva>("ESCOLTAS_BASC");
  const [escoltas, setEscoltas] = useState<MisionEscoltaBasc[]>([]);
  const [binomios, setBinomios] = useState<BinomioCaninoK9[]>([]);
  const [medios, setMedios] = useState<MedioTecnologicoPuesto[]>([]);
  const [cargando, setCargando] = useState<boolean>(true);
  const [mensajeOperativo, setMensajeOperativo] = useState<string | null>(null);
  const [alertaCritica, setAlertaCritica] = useState<string | null>(null);

  // Formulario nuevo despacho BASC
  const [mostrarFormEscolta, setMostrarFormEscolta] = useState<boolean>(false);
  const [tipoMision, setTipoMision] = useState<string>("CONVOY_CARGA_CRITICA_BASC");
  const [descripcionRuta, setDescripcionRuta] = useState<string>(
    "Convoy Zona Franca Siberia -> Terminal Carga El Dorado"
  );
  const [corredorVial, setCorredorVial] = useState<string>(
    "Autopista Medellín (Calle 80) -> Av. Cali -> Calle 26"
  );
  const [vehiculoPlaca, setVehiculoPlaca] = useState<string>(
    "WXY-942 (Furgón BASC + Patrulla Blindada)"
  );
  const [nivelBlindaje, setNivelBlindaje] = useState<"NIVEL_IIIA" | "NIVEL_IV" | "NIVEL_V">(
    "NIVEL_IV"
  );
  const [serialArma, setSerialArma] = useState<string>("IM-9MM-301988");

  const cargarDatos = async () => {
    setCargando(true);
    try {
      const [resEscoltas, resK9, resMedios] = await Promise.all([
        servicioListarEscoltasBasc(),
        servicioListarBinomiosK9(),
        servicioListarMediosTecnologicos(),
      ]);
      setEscoltas(resEscoltas);
      setBinomios(resK9);
      setMedios(resMedios);
    } catch {
      setAlertaCritica("Error sincronizando telemetría de Operaciones Especiales V5.0.");
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    void cargarDatos();
  }, []);

  const manejarCrearEscolta = async (e: React.FormEvent) => {
    e.preventDefault();
    setMensajeOperativo(null);
    setAlertaCritica(null);
    try {
      const nueva = await servicioCrearEscoltaBasc({
        tipo_mision: tipoMision,
        descripcion_ruta: descripcionRuta,
        corredor_vial: corredorVial,
        vehiculo_placa: vehiculoPlaca,
        nivel_blindaje: nivelBlindaje,
        serial_arma_indumil: serialArma,
        lat_origen: 4.739,
        lon_origen: -74.128,
        lat_destino: 4.696,
        lon_destino: -74.1415,
        umbral_desvio_metros: 220,
      });
      setMensajeOperativo(
        `Despacho BASC ${nueva.codigo_mision} creado (${nueva.distancia_ruta_km} km). Sello SHA-256: ${nueva.sello_manifiesto_sha256.slice(0, 16)}...`
      );
      setMostrarFormEscolta(false);
      await cargarDatos();
    } catch {
      setAlertaCritica("No fue posible registrar el nuevo despacho de escolta BASC.");
    }
  };

  const manejarSimularDesvio = async (mision: MisionEscoltaBasc, forzarDesvio: boolean) => {
    setMensajeOperativo(null);
    setAlertaCritica(null);
    try {
      const resultado = await servicioVerificarCorredorEscolta(
        mision.mision_id,
        forzarDesvio ? 4.612 : mision.lat_origen || 4.696,
        forzarDesvio ? -74.245 : mision.lon_origen || -74.1415,
        forzarDesvio ? 685.0 : 18.5
      );
      if (resultado.alerta_desvio_disparada) {
        setAlertaCritica(resultado.mensaje_tactico);
      } else {
        setMensajeOperativo(resultado.mensaje_tactico);
      }
      await cargarDatos();
    } catch {
      setAlertaCritica("Error al verificar geocerca de corredor vial BASC.");
    }
  };

  const manejarDescansoK9 = async (k9: BinomioCaninoK9) => {
    setMensajeOperativo(null);
    setAlertaCritica(null);
    try {
      const res = await servicioRegistrarDescansoK9(k9.k9_id, 45);
      setMensajeOperativo(res.mensaje);
      await cargarDatos();
    } catch {
      setAlertaCritica("No se pudo registrar el descanso normativo de la unidad K9.");
    }
  };

  return (
    <div className="space-y-6 text-slate-100">
      {/* Encabezado Táctico */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-slate-900/90 border border-emerald-500/30 rounded-xl p-5 shadow-lg">
        <div>
          <div className="flex items-center gap-2 text-emerald-400 text-xs font-mono uppercase tracking-widest">
            <Shield className="w-4 h-4" />
            <span>SENTINEL // OPS V5.0 — DIVISIÓN DE OPERACIONES ESPECIALES</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">
            Escoltas VIP BASC, Biodetección Canina K9 & Medios Tecnológicos
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Monitoreo geodésico ISO 28000 / BASC, control normativo de fatiga canina (Resolución SuperVigilancia máx. 6h) y cercas perimetrales en kV.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void cargarDatos()}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-600 text-xs font-mono text-emerald-300 transition"
          >
            <RefreshCw className={`w-4 h-4 ${cargando ? "animate-spin" : ""}`} />
            Sincronizar Telemetría
          </button>
        </div>
      </div>

      {/* Mensajes de retroalimentación */}
      {alertaCritica && (
        <div className="bg-red-950/80 border border-red-500 rounded-xl p-4 flex items-center justify-between text-red-200 text-sm">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
            <span className="font-mono">{alertaCritica}</span>
          </div>
          <button
            onClick={() => setAlertaCritica(null)}
            className="text-xs underline text-red-300 hover:text-white"
          >
            Cerrar
          </button>
        </div>
      )}

      {mensajeOperativo && (
        <div className="bg-emerald-950/80 border border-emerald-500/60 rounded-xl p-4 flex items-center justify-between text-emerald-200 text-sm">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <span className="font-mono">{mensajeOperativo}</span>
          </div>
          <button
            onClick={() => setMensajeOperativo(null)}
            className="text-xs underline text-emerald-300 hover:text-white"
          >
            Cerrar
          </button>
        </div>
      )}

      {/* Selector de Pestañas */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setPestana("ESCOLTAS_BASC")}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-mono uppercase tracking-wider transition ${
            pestana === "ESCOLTAS_BASC"
              ? "bg-emerald-600 text-white shadow-lg shadow-emerald-900/40"
              : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
          }`}
        >
          <Truck className="w-4 h-4" />
          Convoyes & Escoltas VIP BASC ({escoltas.length})
        </button>

        <button
          onClick={() => setPestana("BINOMIOS_K9")}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-mono uppercase tracking-wider transition ${
            pestana === "BINOMIOS_K9"
              ? "bg-emerald-600 text-white shadow-lg shadow-emerald-900/40"
              : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
          }`}
        >
          <Dog className="w-4 h-4" />
          Biodetección Canina K9 ({binomios.length})
        </button>

        <button
          onClick={() => setPestana("MEDIOS_TECNOLOGICOS")}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-mono uppercase tracking-wider transition ${
            pestana === "MEDIOS_TECNOLOGICOS"
              ? "bg-emerald-600 text-white shadow-lg shadow-emerald-900/40"
              : "bg-slate-900 text-slate-400 hover:text-white border border-slate-800"
          }`}
        >
          <Cpu className="w-4 h-4" />
          Medios Tecnológicos & Cercas ({medios.length})
        </button>
      </div>

      {/* PESTAÑA 1: CONVOYES & ESCOLTAS VIP BASC */}
      {pestana === "ESCOLTAS_BASC" && (
        <div className="space-y-5">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-emerald-400 font-mono">
              MISIONES DE ESCOLTA VEHICULAR & PROTECCIÓN EJECUTIVA (ISO 28000 / BASC)
            </h2>
            <button
              onClick={() => setMostrarFormEscolta(!mostrarFormEscolta)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-mono font-semibold text-white transition"
            >
              <Plus className="w-4 h-4" />
              {mostrarFormEscolta ? "Cancelar Despacho" : "Nuevo Despacho BASC"}
            </button>
          </div>

          {mostrarFormEscolta && (
            <form
              onSubmit={(e) => void manejarCrearEscolta(e)}
              className="bg-slate-900 border border-emerald-500/40 rounded-xl p-5 grid grid-cols-1 md:grid-cols-3 gap-4"
            >
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Modalidad de Misión
                </label>
                <select
                  value={tipoMision}
                  onChange={(e) => setTipoMision(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                >
                  <option value="CONVOY_CARGA_CRITICA_BASC">CONVOY CARGA CRÍTICA BASC</option>
                  <option value="PROTECCION_EJECUTIVA_VIP">PROTECCIÓN EJECUTIVA VIP</option>
                  <option value="CONVOY_AGROEXPORTACION_BASC">CONVOY AGROEXPORTACIÓN BASC</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Nivel de Blindaje (NIJ)
                </label>
                <select
                  value={nivelBlindaje}
                  onChange={(e) =>
                    setNivelBlindaje(e.target.value as "NIVEL_IIIA" | "NIVEL_IV" | "NIVEL_V")
                  }
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                >
                  <option value="NIVEL_IIIA">NIVEL IIIA (Subametralladora / 9mm)</option>
                  <option value="NIVEL_IV">NIVEL IV (Fusil 7.62x51mm OTAN)</option>
                  <option value="NIVEL_V">NIVEL V (Alta Seguridad Presidencial)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Serial Armamento Indumil en Misión
                </label>
                <input
                  type="text"
                  value={serialArma}
                  onChange={(e) => setSerialArma(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono"
                  required
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Descripción de Ruta Origen -&gt; Destino
                </label>
                <input
                  type="text"
                  value={descripcionRuta}
                  onChange={(e) => setDescripcionRuta(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Vehículo Escoltado / Placa RUNT
                </label>
                <input
                  type="text"
                  value={vehiculoPlaca}
                  onChange={(e) => setVehiculoPlaca(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono"
                  required
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Corredor Vial Autorizado
                </label>
                <input
                  type="text"
                  value={corredorVial}
                  onChange={(e) => setCorredorVial(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                  required
                />
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-bold rounded-lg uppercase tracking-wider"
                >
                  Emitir Manifiesto BASC SHA-256
                </button>
              </div>
            </form>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {escoltas.map((m) => {
              const enAlerta = m.estado_mision === "ALERTA_DESVIO_RUTA";
              const completada = m.estado_mision === "COMPLETADA";
              return (
                <div
                  key={m.mision_id}
                  className={`rounded-xl p-5 border transition ${
                    enAlerta
                      ? "bg-red-950/40 border-red-500 shadow-lg shadow-red-950/50"
                      : "bg-slate-900/90 border-slate-800"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-slate-800 text-emerald-400 border border-emerald-500/30">
                          {m.codigo_mision}
                        </span>
                        <span className="px-2.5 py-0.5 rounded text-xs font-mono bg-indigo-950 text-indigo-300 border border-indigo-500/40">
                          {m.nivel_blindaje}
                        </span>
                        <span
                          className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold ${
                            enAlerta
                              ? "bg-red-600 text-white animate-pulse"
                              : completada
                              ? "bg-slate-700 text-slate-200"
                              : "bg-emerald-950 text-emerald-300 border border-emerald-500/40"
                          }`}
                        >
                          {m.estado_mision}
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-white mt-2">
                        {m.descripcion_ruta}
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Corredor: <span className="text-slate-200">{m.corredor_vial}</span>
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4 text-xs bg-slate-950/70 p-3 rounded-lg border border-slate-800/80">
                    <div>
                      <span className="text-slate-500 block">Vehículo / Convoy</span>
                      <span className="font-mono text-slate-200">{m.vehiculo_placa}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Escolta Asignado</span>
                      <span className="font-mono text-emerald-300">
                        {m.escolta_nombre} ({m.escolta_codigo})
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Arma DCCA Indumil</span>
                      <span className="font-mono text-amber-300">{m.serial_arma_indumil}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Distancia Ruta</span>
                      <span className="font-mono text-white">{m.distancia_ruta_km} km</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Desviación Actual</span>
                      <span
                        className={`font-mono font-bold ${
                          m.desviacion_metros > m.umbral_desvio_metros
                            ? "text-red-400"
                            : "text-emerald-400"
                        }`}
                      >
                        {m.desviacion_metros}m / máx {m.umbral_desvio_metros}m
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Coordenadas GPS</span>
                      <span className="font-mono text-slate-300">
                        {m.lat_actual?.toFixed(4)}, {m.lon_actual?.toFixed(4)}
                      </span>
                    </div>
                  </div>

                  <div className="mt-3 pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5 truncate">
                      <Lock className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span>SHA-256 BASC: {m.sello_manifiesto_sha256.slice(0, 24)}...</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => void manejarSimularDesvio(m, true)}
                        className="px-3 py-1.5 rounded bg-red-900/70 hover:bg-red-700 text-red-100 border border-red-500/50 text-xs font-mono transition flex items-center gap-1.5"
                      >
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Simular Desvío de Ruta
                      </button>
                      {enAlerta && (
                        <button
                          onClick={() => void manejarSimularDesvio(m, false)}
                          className="px-3 py-1.5 rounded bg-emerald-800 hover:bg-emerald-700 text-white text-xs font-mono transition flex items-center gap-1.5"
                        >
                          <Navigation className="w-3.5 h-3.5" />
                          Restablecer Corredor
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* PESTAÑA 2: BIODETECCIÓN CANINA K9 */}
      {pestana === "BINOMIOS_K9" && (
        <div className="space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-mono font-bold text-emerald-400 uppercase">
                CONTROL DE UNIDADES BIODETECTORAS K9 — RESOLUCIÓN SUPERVIGILANCIA (TOPE 6 HORAS CONTINUAS)
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Monitoreo de fatiga olfativa, microchip ISO 11784, esquema de vacunación ICA y relevo en canil climatizado.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {binomios.map((k9) => {
              const esCritico = k9.horas_trabajadas_turno >= 5.5;
              return (
                <div
                  key={k9.k9_id}
                  className={`rounded-xl p-5 border ${
                    esCritico
                      ? "bg-amber-950/30 border-amber-500/60"
                      : "bg-slate-900 border-slate-800"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/30 text-xs font-mono font-bold">
                          {k9.codigo_unidad_k9}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-amber-300 text-xs font-mono">
                          {k9.especialidad}
                        </span>
                      </div>
                      <h3 className="text-lg font-bold text-white mt-1.5">
                        K9 {k9.nombre_canino} — <span className="text-slate-300 font-normal">{k9.raza}</span>
                      </h3>
                      <p className="text-xs text-slate-400">
                        Puesto asignado: <span className="text-slate-200 font-mono">{k9.puesto_codigo}</span> ({k9.puesto_nombre})
                      </p>
                    </div>
                    <span
                      className={`px-2.5 py-1 rounded text-xs font-mono font-bold ${
                        esCritico
                          ? "bg-amber-600 text-slate-950"
                          : "bg-emerald-900/70 text-emerald-300 border border-emerald-500/40"
                      }`}
                    >
                      {k9.semaforo_normativo_k9}
                    </span>
                  </div>

                  {/* Barra de fatiga K9 */}
                  <div className="mt-4">
                    <div className="flex justify-between text-xs font-mono mb-1">
                      <span className="text-slate-400">
                        Fatiga Operativa Turno Actual (Máx. {k9.max_horas_continuas_norma}h continuas)
                      </span>
                      <span className={esCritico ? "text-amber-400 font-bold" : "text-emerald-400"}>
                        {k9.horas_trabajadas_turno}h / {k9.max_horas_continuas_norma}h ({k9.porcentaje_fatiga}%)
                      </span>
                    </div>
                    <div className="w-full h-2.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className={`h-full transition-all ${
                          esCritico ? "bg-amber-500" : "bg-emerald-500"
                        }`}
                        style={{ width: `${Math.min(100, k9.porcentaje_fatiga)}%` }}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 mt-4 text-xs bg-slate-950/70 p-3 rounded-lg border border-slate-800">
                    <div>
                      <span className="text-slate-500 block">Guía Canino</span>
                      <span className="font-mono text-slate-200">
                        {k9.guia_nombre} ({k9.guia_codigo})
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Microchip ISO</span>
                      <span className="font-mono text-emerald-300">{k9.codigo_microchip}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Vacunación ICA</span>
                      <span className="font-mono text-slate-200">
                        Vigente hasta {k9.fecha_vencimiento_vacunas}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Estado Bienestar</span>
                      <span className="font-mono text-slate-300">{k9.estado_fatiga}</span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 mt-3 italic">
                    {k9.observaciones_veterinarias}
                  </p>

                  <div className="mt-4 pt-3 border-t border-slate-800 flex justify-end">
                    <button
                      onClick={() => void manejarDescansoK9(k9)}
                      className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-semibold transition"
                    >
                      <HeartPulse className="w-4 h-4" />
                      Registrar Descanso e Hidratación en Canil
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* PESTAÑA 3: MEDIOS TECNOLÓGICOS & CERCAS */}
      {pestana === "MEDIOS_TECNOLOGICOS" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {medios.map((disp) => {
              const enRespaldo = disp.estado_operativo !== "ONLINE";
              return (
                <div
                  key={disp.medio_id}
                  className={`rounded-xl p-4 border ${
                    enRespaldo
                      ? "bg-amber-950/30 border-amber-500/60"
                      : "bg-slate-900 border-slate-800"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-emerald-400">
                      {disp.codigo_dispositivo}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                        enRespaldo
                          ? "bg-amber-500 text-slate-950"
                          : "bg-emerald-950 text-emerald-300 border border-emerald-500/30"
                      }`}
                    >
                      {disp.estado_operativo}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-white mt-1.5">
                    {disp.ubicacion_detalle}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {disp.puesto_codigo} — {disp.puesto_nombre}
                  </p>
                  <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-800 text-xs font-mono">
                    <div>
                      <span className="text-slate-500 block text-[10px]">LATENCIA</span>
                      <span className="text-slate-200 flex items-center gap-1">
                        <Activity className="w-3 h-3 text-emerald-400" />
                        {disp.latencia_ms} ms
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">VOLTAJE CERCA</span>
                      <span className="text-amber-300 flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        {disp.voltaje_cerca_kv > 0 ? `${disp.voltaje_cerca_kv} kV` : "N/A"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">UPS BATERÍA</span>
                      <span className="text-emerald-300">{disp.bateria_respaldo_pct}%</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default OperacionesEspecialesK9;


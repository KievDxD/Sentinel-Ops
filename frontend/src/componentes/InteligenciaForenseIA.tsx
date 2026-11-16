import React, { useEffect, useState } from "react";
import {
  BrainCircuit,
  ShieldAlert,
  ShieldCheck,
  Flame,
  Wrench,
  Radar,
  Lock,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  FileSpreadsheet,
  Sparkles,
  Send,
  Cpu,
} from "lucide-react";
import {
  servicioGenerarBoletinRelevoIA,
  servicioAuditarAntifraudeRondas,
  servicioSimularSabotajeForense,
  servicioRepararCadenaForense,
  servicioObtenerKpisTiempoReal,
  servicioConsultarCopilotoTactico,
  extraerMensajeError,
} from "../servicios/cliente_api";
import type {
  BoletinRelevoIA,
  AuditoriaAntifraudeRondas,
  IntegridadBlockchainInfo,
  RespuestaCopilotoTactico,
} from "../tipos/tipos_sistema";

const CHIPS_CONSULTA_RAPIDA = [
  "Auditar integridad SHA-256",
  "Riesgos de credenciales y armamento",
  "Resumen táctico de turnos y SLA",
];

const CODIGOS_PUESTOS_SEDES = [
  { codigo: "PST-BOG-01", nombre: "Torre Financiera Chapinero (Bogotá)" },
  { codigo: "PST-OCC-02", nombre: "Parque Logístico Sabana (Madrid)" },
  { codigo: "PST-BOG-03", nombre: "Zona Franca Siberia (Cota / Calle 80)" },
  { codigo: "PST-FAC-04", nombre: "Planta Agroindustrial Los Andes (Facatativá)" },
  { codigo: "PST-BOG-05", nombre: "Complejo Reserva del Parque (Salitre)" },
  { codigo: "PST-BOG-06", nombre: "Centro de Datos Tier-IV (Puente Aranda)" },
];

export const InteligenciaForenseIA: React.FC = () => {
  const [puestoSeleccionado, setPuestoSeleccionado] = useState<string>("PST-BOG-03");
  const [boletin, setBoletin] = useState<BoletinRelevoIA | null>(null);
  const [auditoriaRondas, setAuditoriaRondas] =
    useState<AuditoriaAntifraudeRondas | null>(null);
  const [estadoBlockchain, setEstadoBlockchain] =
    useState<IntegridadBlockchainInfo | null>(null);
  const [detalleSabotaje, setDetalleSabotaje] = useState<{
    registro_id: number;
    texto_original_respaldado: string;
    texto_adulterado: string;
    sello_sha256_original: string;
  } | null>(null);
  const [cargando, setCargando] = useState<boolean>(true);
  const [procesandoForense, setProcesandoForense] = useState<boolean>(false);

  // Estado del Copiloto Táctico IA V5.1 (Zero-Trust Tool Calling)
  const [consultaCopiloto, setConsultaCopiloto] = useState<string>(
    "Auditar integridad SHA-256 y riesgos de vencimiento"
  );
  const [consultandoCopiloto, setConsultandoCopiloto] = useState<boolean>(false);
  const [respuestaCopiloto, setRespuestaCopiloto] =
    useState<RespuestaCopilotoTactico | null>(null);
  const [errorCopiloto, setErrorCopiloto] = useState<string | null>(null);

  const cargarTodo = async (codPuesto: string = puestoSeleccionado) => {
    setCargando(true);
    try {
      const [resBoletin, resAntifraude, resKpis] = await Promise.all([
        servicioGenerarBoletinRelevoIA(codPuesto),
        servicioAuditarAntifraudeRondas(),
        servicioObtenerKpisTiempoReal(),
      ]);
      setBoletin(resBoletin);
      setAuditoriaRondas(resAntifraude);
      setEstadoBlockchain(resKpis.integridad_blockchain);
      window.dispatchEvent(
        new CustomEvent("sentinel:estado-blockchain", {
          detail: resKpis.integridad_blockchain,
        })
      );
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    void cargarTodo(puestoSeleccionado);
  }, [puestoSeleccionado]);

  const manejarSimularSabotaje = async () => {
    setProcesandoForense(true);
    try {
      const res = await servicioSimularSabotajeForense(
        undefined,
        "[INTRUSIÓN SQL DETECTADA] Adulteración maliciosa de registro operativo en base de datos sin firma privada."
      );
      setDetalleSabotaje(res.detalle_sabotaje);
      setEstadoBlockchain(res.auditoria_resultante);
      window.dispatchEvent(
        new CustomEvent("sentinel:estado-blockchain", {
          detail: res.auditoria_resultante,
        })
      );
    } finally {
      setProcesandoForense(false);
    }
  };

  const manejarRepararCadena = async () => {
    setProcesandoForense(true);
    try {
      const res = await servicioRepararCadenaForense();
      setDetalleSabotaje(null);
      setEstadoBlockchain(res.auditoria_post_reparacion);
      window.dispatchEvent(
        new CustomEvent("sentinel:estado-blockchain", {
          detail: res.auditoria_post_reparacion,
        })
      );
    } finally {
      setProcesandoForense(false);
    }
  };

  const ejecutarConsultaCopiloto = async (texto?: string) => {
    const query = (texto ?? consultaCopiloto).trim();
    if (query.length < 3) return;
    if (texto) setConsultaCopiloto(texto);
    setConsultandoCopiloto(true);
    setErrorCopiloto(null);
    try {
      const res = await servicioConsultarCopilotoTactico({ consulta: query });
      setRespuestaCopiloto(res);
    } catch (err: unknown) {
      setErrorCopiloto(extraerMensajeError(err));
    } finally {
      setConsultandoCopiloto(false);
    }
  };

  const cadenaCorrupta = estadoBlockchain
    ? !estadoBlockchain.INTEGRIDAD_VERIFICADA
    : false;

  return (
    <div className="space-y-6 text-slate-100">
      {/* Encabezado */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-slate-900/90 border border-emerald-500/30 rounded-xl p-5 shadow-lg">
        <div>
          <div className="flex items-center gap-2 text-emerald-400 text-xs font-mono uppercase tracking-widest">
            <BrainCircuit className="w-4 h-4" />
            <span>SENTINEL // OPS V5.1 — COPILOTO IA ZERO-TRUST &amp; AUDITORÍA FORENSE</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">
            Copiloto Táctico IA, Boletín de Relevo &amp; Laboratorio SHA-256
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Tool calling vinculado al token JWT (aislamiento estricto por tenant y puesto), detección de velocidad imposible en rondas QR y simulador de ataque criptográfico.
          </p>
        </div>
        <button
          onClick={() => void cargarTodo(puestoSeleccionado)}
          className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-600 text-xs font-mono text-emerald-300 transition self-start md:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${cargando ? "animate-spin" : ""}`} />
          Recalcular Inteligencia
        </button>
      </div>

      {/* SECCIÓN 0 (V5.1): CONSOLA DEL COPILOTO TÁCTICO IA CON TOOL CALLING ZERO-TRUST */}
      <div className="rounded-xl border border-cyan-500/40 bg-gradient-to-br from-slate-900/95 via-slate-950/90 to-emerald-950/20 p-6 shadow-2xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-wider">
              <Sparkles className="w-4 h-4" />
              <span>ASISTENTE TÁCTICO DE MANDO — ZERO-TRUST TOOL CALLING</span>
            </div>
            <h2 className="text-lg font-bold text-white mt-1">
              Consola del Copiloto Táctico IA
            </h2>
          </div>
          <span className="px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-[11px] font-mono text-cyan-300 self-start sm:self-auto">
            {respuestaCopiloto?.modo_motor === "LLM_TOOL_CALLING"
              ? "Motor: LLM + Tools Activo"
              : "Motor: Fallback Determinístico SQL"}
          </span>
        </div>

        {/* Chips de consulta rápida */}
        <div className="flex flex-wrap gap-2">
          {CHIPS_CONSULTA_RAPIDA.map((chip) => (
            <button
              key={chip}
              type="button"
              disabled={consultandoCopiloto}
              onClick={() => void ejecutarConsultaCopiloto(chip)}
              className="px-3 py-1.5 rounded-full border border-emerald-500/35 bg-emerald-950/40 hover:bg-emerald-500/20 hover:border-emerald-400 text-xs font-mono text-emerald-200 transition disabled:opacity-50"
            >
              ⚡ {chip}
            </button>
          ))}
        </div>

        {/* Barra de entrada */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void ejecutarConsultaCopiloto();
          }}
          className="flex flex-col sm:flex-row gap-2"
        >
          <input
            type="text"
            value={consultaCopiloto}
            onChange={(e) => setConsultaCopiloto(e.target.value)}
            placeholder="Ej: Analiza riesgos de credenciales SuperVigilancia, anomalías Haversine y estado SHA-256..."
            className="flex-1 rounded-xl border border-slate-700 bg-slate-950/90 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
          />
          <button
            type="submit"
            disabled={consultandoCopiloto}
            className="flex items-center justify-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 px-5 py-2.5 text-xs font-mono font-bold uppercase tracking-wider text-slate-950 transition disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
            <span>{consultandoCopiloto ? "Analizando..." : "Consultar Copiloto"}</span>
          </button>
        </form>

        {/* Estado de carga tipo esqueleto / pulso táctico */}
        {consultandoCopiloto && (
          <div className="rounded-xl border border-cyan-500/30 bg-slate-950/80 p-4 space-y-2.5 animate-pulse">
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-300">
              <Cpu className="w-4 h-4 animate-spin" />
              <span>Invocando herramientas de solo lectura vinculadas al token JWT...</span>
            </div>
            <div className="h-3 w-3/4 rounded bg-slate-800" />
            <div className="h-3 w-1/2 rounded bg-slate-800" />
          </div>
        )}

        {errorCopiloto && (
          <div className="rounded-xl border border-rose-500/50 bg-rose-950/50 p-3.5 text-xs font-mono text-rose-200 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorCopiloto}</span>
          </div>
        )}

        {!consultandoCopiloto && respuestaCopiloto && (
          <div className="rounded-xl border border-slate-800 bg-slate-950/85 p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold ${
                    respuestaCopiloto.nivel_riesgo === "CRITICO"
                      ? "bg-red-600 text-white"
                      : respuestaCopiloto.nivel_riesgo === "ALTO"
                      ? "bg-amber-500 text-slate-950"
                      : respuestaCopiloto.nivel_riesgo === "MODERADO"
                      ? "bg-yellow-500/90 text-slate-950"
                      : "bg-emerald-600 text-white"
                  }`}
                >
                  RIESGO: {respuestaCopiloto.nivel_riesgo}
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 text-[11px] font-mono">
                  Tenant: {respuestaCopiloto.tenant_id_aislado}
                </span>
                {respuestaCopiloto.intento_inyeccion_detectado && (
                  <span className="px-2 py-0.5 rounded bg-rose-600 text-white text-[11px] font-mono font-bold">
                    PROMPT INJECTION BLOQUEADO
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-1">
                {respuestaCopiloto.herramientas_ejecutadas.map((tool) => (
                  <span
                    key={tool}
                    className="px-2 py-0.5 rounded border border-emerald-500/30 bg-emerald-950/40 text-[10px] font-mono text-emerald-300"
                  >
                    tool:{tool}
                  </span>
                ))}
              </div>
            </div>

            <p className="text-sm text-slate-100 leading-relaxed">
              {respuestaCopiloto.respuesta_ejecutiva}
            </p>

            {respuestaCopiloto.hashes_sha256_citados.length > 0 && (
              <div className="pt-2 border-t border-slate-800/80 space-y-1">
                <span className="text-[11px] font-mono text-slate-400 uppercase block">
                  Evidencia Criptográfica SHA-256 Citada:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {respuestaCopiloto.hashes_sha256_citados.map((hash) => (
                    <span
                      key={hash}
                      className="inline-flex items-center gap-1 rounded bg-slate-900 border border-slate-700 px-2 py-0.5 text-[11px] font-mono text-emerald-400"
                    >
                      <Lock className="w-3 h-3 shrink-0" />
                      {hash.slice(0, 22)}...
                    </span>
                  ))}
                </div>
              </div>
            )}

            {respuestaCopiloto.recomendaciones_tacticas.length > 0 && (
              <div className="pt-2 border-t border-slate-800/80">
                <span className="text-[11px] font-mono text-cyan-400 uppercase block mb-1">
                  Acciones Tácticas Sugeridas:
                </span>
                <ul className="space-y-1 text-xs text-slate-300">
                  {respuestaCopiloto.recomendaciones_tacticas.map((rec, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* SECCIÓN 1: LABORATORIO INTERACTIVO DE SABOTAJE Y AUTO-REPARACIÓN SHA-256 */}
      <div
        className={`rounded-xl p-6 border-2 transition-all ${
          cadenaCorrupta
            ? "bg-red-950/60 border-red-500 shadow-2xl shadow-red-950/80"
            : "bg-slate-900/95 border-emerald-500/50 shadow-xl"
        }`}
      >
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              {cadenaCorrupta ? (
                <span className="px-3 py-1 rounded bg-red-600 text-white text-xs font-mono font-bold animate-pulse flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4" />
                  ALERTA FORENSE: CADENA CORRUPTA DETECTADA EN BLOQUE #
                  {estadoBlockchain?.bloque_corrupto_id}
                </span>
              ) : (
                <span className="px-3 py-1 rounded bg-emerald-600 text-white text-xs font-mono font-bold flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4" />
                  INTEGRIDAD VERIFICADA (100% ESLABONES SHA-256 VÁLIDOS)
                </span>
              )}
              <span className="text-xs font-mono text-slate-400">
                Total Bloques Auditados: {estadoBlockchain?.total_bloques_auditados ?? 0}
              </span>
            </div>
            <h2 className="text-lg font-bold text-white mt-2">
              Laboratorio Interactivo de Sabotaje y Auto-Reparación Criptográfica SHA-256
            </h2>
            <p className="text-xs text-slate-300">
              Demostración técnica en vivo: altere intencionalmente un registro histórico en la base de datos SQL para comprobar cómo el motor SHA-256 detecta el eslabón corrupto en tiempo real, y luego restaure la cadena desde el respaldo forense.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              disabled={procesandoForense}
              onClick={() => void manejarSimularSabotaje()}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-mono text-xs font-bold shadow-lg shadow-red-950/60 transition"
            >
              <Flame className="w-4 h-4" />
              💥 Simular Ataque / Adulteración de Minuta en BD
            </button>
            <button
              disabled={procesandoForense}
              onClick={() => void manejarRepararCadena()}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-mono text-xs font-bold shadow-lg shadow-emerald-950/60 transition"
            >
              <Wrench className="w-4 h-4" />
              🛡️ Ejecutar Auto-Reparación Forense SHA-256
            </button>
          </div>
        </div>

        {/* Árbol visual de bloques y comparativa de hashes */}
        {estadoBlockchain && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-5 text-xs font-mono">
            <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3">
              <span className="text-slate-400 block text-[10px]">GÉNESIS DE REFERENCIA</span>
              <span className="text-emerald-400 truncate block mt-1">
                {estadoBlockchain.hash_genesis_referencia.slice(0, 28)}...
              </span>
            </div>
            <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3">
              <span className="text-slate-400 block text-[10px]">
                ESLABONES (MINUTA / ACTAS / KARDEX)
              </span>
              <span className="text-white font-bold block mt-1">
                {estadoBlockchain.bloques_minuta} / {estadoBlockchain.bloques_actas_relevo} /{" "}
                {estadoBlockchain.bloques_kardex_balistico} bloques
              </span>
            </div>
            <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3">
              <span className="text-slate-400 block text-[10px]">BLOQUES CORRUPTOS</span>
              <span
                className={`font-bold block mt-1 ${
                  cadenaCorrupta ? "text-red-400" : "text-emerald-400"
                }`}
              >
                {estadoBlockchain.bloques_corruptos} detectados
              </span>
            </div>
            <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3">
              <span className="text-slate-400 block text-[10px]">RAÍZ MERKLE ACTUAL</span>
              <span className="text-indigo-300 truncate block mt-1">
                {estadoBlockchain.hash_raiz_merkle.slice(0, 28)}...
              </span>
            </div>
          </div>
        )}

        {cadenaCorrupta && (
          <div className="mt-4 bg-slate-950/90 border border-red-500/80 rounded-xl p-4 space-y-2 text-xs font-mono">
            <div className="text-red-400 font-bold flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              EVIDENCIA CRIPTOGRÁFICA DE ADULTERACIÓN EN BLOQUE #
              {estadoBlockchain?.bloque_corrupto_id}
            </div>
            {detalleSabotaje && (
              <div className="text-slate-300 space-y-1">
                <div>
                  <span className="text-slate-500">Contenido Original Respaldado: </span>
                  <span className="text-emerald-300">
                    {detalleSabotaje.texto_original_respaldado}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Contenido Adulterado en BD: </span>
                  <span className="text-red-300">{detalleSabotaje.texto_adulterado}</span>
                </div>
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2 border-t border-slate-800">
              <div>
                <span className="text-slate-500 block">Hash Esperado (Cadena Legítima):</span>
                <span className="text-emerald-400 break-all">
                  {estadoBlockchain?.hash_esperado}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Hash Calculado (Bloque Corrupto):</span>
                <span className="text-red-400 break-all">
                  {estadoBlockchain?.hash_calculado}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* SECCIÓN 2: GENERADOR DE BOLETÍN TÁCTICO DE RELEVO (SHIFT HANDOVER BRIEFING) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-base font-bold font-mono text-emerald-400 flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5" />
              BOLETÍN TÁCTICO DE RELEVO IA (SHIFT HANDOVER BRIEFING — ÚLTIMAS 12 HORAS)
            </h2>
            <p className="text-xs text-slate-400">
              Selecciona una sede operativa para sintetizar novedades críticas, placas recurrentes, armamento Indumil y directivas de entrega de puesto.
            </p>
          </div>
          <select
            value={puestoSeleccionado}
            onChange={(e) => setPuestoSeleccionado(e.target.value)}
            className="bg-slate-950 border border-emerald-500/50 rounded-lg px-3 py-2 text-xs font-mono text-white"
          >
            {CODIGOS_PUESTOS_SEDES.map((p) => (
              <option key={p.codigo} value={p.codigo}>
                {p.codigo} — {p.nombre}
              </option>
            ))}
          </select>
        </div>

        {boletin && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-7 bg-slate-950/70 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs font-mono text-emerald-400 font-bold">
                    {boletin.puesto_codigo} • {boletin.ciudad}
                  </span>
                  <h3 className="text-base font-bold text-white">{boletin.puesto_nombre}</h3>
                </div>
                <span
                  className={`px-3 py-1 rounded text-xs font-mono font-bold ${
                    boletin.nivel_amenaza === "CRITICO"
                      ? "bg-red-600 text-white"
                      : boletin.nivel_amenaza === "ALTO"
                      ? "bg-amber-500 text-slate-950"
                      : "bg-emerald-600 text-white"
                  }`}
                >
                  AMENAZA: {boletin.nivel_amenaza}
                </span>
              </div>

              <div>
                <h4 className="text-xs font-mono uppercase text-slate-400 mb-1.5">
                  Hallazgos Clave Sintetizados ({boletin.total_eventos_analizados} eventos):
                </h4>
                <ul className="space-y-1.5 text-xs text-slate-200">
                  {boletin.hallazgos_clave.map((h, i) => (
                    <li
                      key={i}
                      className="bg-slate-900/90 border border-slate-800 rounded px-3 py-2 font-mono"
                    >
                      {h}
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="text-xs font-mono uppercase text-emerald-400 mb-1.5">
                  Directivas Tácticas para el Guarda Entrante:
                </h4>
                <ul className="space-y-1 text-xs text-slate-300">
                  {boletin.recomendaciones_tacticas.map((rec, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="lg:col-span-5 bg-slate-950/70 border border-slate-800 rounded-xl p-4 space-y-3 text-xs font-mono">
              <h4 className="text-xs font-bold uppercase text-amber-400">
                ESTADO DE ARMAMENTO INDUMIL &amp; GARITA EN RELEVO
              </h4>
              <div className="grid grid-cols-2 gap-2 bg-slate-900 p-3 rounded-lg border border-slate-800">
                <div>
                  <span className="text-slate-500 block">Serial Armamento</span>
                  <span className="text-white font-bold">
                    {boletin.estado_dotacion.serial_armamento}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Munición Verificada</span>
                  <span className="text-emerald-400 font-bold">
                    {boletin.estado_dotacion.municion_verificada_ultimo_relevo} /{" "}
                    {boletin.estado_dotacion.municion_reglamentaria} cartuchos
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Visitantes DENTRO</span>
                  <span className="text-amber-300 font-bold">
                    {boletin.visitantes_activos_en_recinto} activos
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Estado Dotación</span>
                  <span className="text-slate-200">
                    {boletin.estado_dotacion.estado_armamento}
                  </span>
                </div>
              </div>

              <div>
                <span className="text-slate-400 block mb-1">
                  Placas RUNT Recurrentes en el Turno:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {boletin.placas_recurrentes.map((placa) => (
                    <span
                      key={placa}
                      className="px-2 py-0.5 rounded bg-slate-800 text-amber-300 border border-amber-500/30 text-xs font-bold"
                    >
                      {placa}
                    </span>
                  ))}
                </div>
              </div>

              <p className="text-slate-400 italic font-sans">
                {boletin.estado_dotacion.observacion_relevo}
              </p>

              <div className="pt-2 border-t border-slate-800 flex items-center gap-1.5 text-[11px] text-emerald-400 truncate">
                <Lock className="w-3.5 h-3.5 shrink-0" />
                <span>SELLO BRIEFING SHA-256: {boletin.sello_boletin_sha256.slice(0, 26)}...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* SECCIÓN 3: AUDITORÍA ANTIFRAUDE DE RONDAS GPS/QR */}
      {auditoriaRondas && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <h2 className="text-base font-bold font-mono text-emerald-400 flex items-center gap-2">
                <Radar className="w-5 h-5" />
                AUDITOR ANTIFRAUDE DE RONDAS GPS / QR (DETECCIÓN DE VELOCIDAD HUMANA IMPOSIBLE)
              </h2>
              <p className="text-xs text-slate-400">
                Índice de Confiabilidad Geodésica: {auditoriaRondas.indice_confiabilidad_rondas_pct}% ({auditoriaRondas.marcaciones_conformes_geocerca}/{auditoriaRondas.total_marcaciones_auditadas} marcaciones dentro de geocerca).
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="py-2 pr-3">ID Anomalía</th>
                  <th className="py-2 pr-3">Puesto / Checkpoint</th>
                  <th className="py-2 pr-3">Guarda</th>
                  <th className="py-2 pr-3">Patrón Detectado</th>
                  <th className="py-2 pr-3">Velocidad / Distancia</th>
                  <th className="py-2">Diagnóstico Forense</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {auditoriaRondas.anomalias.map((a) => (
                  <tr key={a.anomalia_id}>
                    <td className="py-2.5 pr-3 font-bold text-red-400">{a.anomalia_id}</td>
                    <td className="py-2.5 pr-3 text-white">
                      {a.puesto_codigo} — {a.punto_nombre}
                    </td>
                    <td className="py-2.5 pr-3 text-slate-300">{a.operador_nombre}</td>
                    <td className="py-2.5 pr-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          a.severidad === "CRITICA"
                            ? "bg-red-600 text-white"
                            : "bg-amber-500 text-slate-950"
                        }`}
                      >
                        {a.tipo_anomalia}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-amber-300 font-bold">
                      {a.velocidad_estimada_kmh} km/h ({a.distancia_detectada_metros}m)
                    </td>
                    <td className="py-2.5 text-slate-300 font-sans">{a.diagnostico_forense}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default InteligenciaForenseIA;


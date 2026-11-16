import React, { useEffect, useState } from "react";
import {
  FileCheck2,
  ShieldAlert,
  HeartPulse,
  Search,
  CheckCircle2,
  AlertOctagon,
  UserCheck,
  Lock,
  RefreshCw,
  Clock,
  Shield,
} from "lucide-react";
import {
  servicioConsultarSarlaft,
  servicioListarHistorialSarlaft,
  servicioConsultarSemaforoChalecosKevlar,
  servicioRegistrarCheckAptitudSst,
  servicioListarMonitoresHombreCaido,
  servicioRegistrarLatidoHombreCaido,
} from "../servicios/cliente_api";
import type {
  CertificadoSarlaft,
  SemaforoChalecoKevlar,
  MonitorHombreCaido,
  RespuestaCheckAptitudSst,
} from "../tipos/tipos_sistema";

export const CumplimientoSarlaftSST: React.FC = () => {
  const [historialSarlaft, setHistorialSarlaft] = useState<CertificadoSarlaft[]>([]);
  const [certificadoReciente, setCertificadoReciente] = useState<CertificadoSarlaft | null>(
    null
  );
  const [chalecos, setChalecos] = useState<SemaforoChalecoKevlar[]>([]);
  const [monitores, setMonitores] = useState<MonitorHombreCaido[]>([]);
  const [cargando, setCargando] = useState<boolean>(true);
  const [mensajeSst, setMensajeSst] = useState<string | null>(null);

  // Estado formulario SARLAFT
  const [documento, setDocumento] = useState<string>("1032489120");
  const [nombreCompleto, setNombreCompleto] = useState<string>(
    "Andrés Felipe Castellanos Gómez"
  );
  const [tipoTercero, setTipoTercero] = useState<
    "ASPIRANTE_GUARDA" | "CLIENTE_B2B" | "VISITANTE_CRITICO"
  >("ASPIRANTE_GUARDA");

  // Estado formulario Check-in SST Decreto 1072
  const [puestoSstId, setPuestoSstId] = useState<number>(1);
  const [horasSueno, setHorasSueno] = useState<number>(7.5);
  const [ceroAlcohol, setCeroAlcohol] = useState<boolean>(true);
  const [chalecoVerificado, setChalecoVerificado] = useState<boolean>(true);
  const [resultadoCheckSst, setResultadoCheckSst] =
    useState<RespuestaCheckAptitudSst | null>(null);

  const cargarDatos = async () => {
    setCargando(true);
    try {
      const [resHist, resChalecos, resMonitores] = await Promise.all([
        servicioListarHistorialSarlaft(),
        servicioConsultarSemaforoChalecosKevlar(),
        servicioListarMonitoresHombreCaido(),
      ]);
      setHistorialSarlaft(resHist);
      if (resHist.length > 0 && !certificadoReciente) {
        setCertificadoReciente(resHist[0]);
      }
      setChalecos(resChalecos);
      setMonitores(resMonitores);
      if (resChalecos.length > 0 && puestoSstId === 1) {
        setPuestoSstId(resChalecos[0].puesto_id);
      }
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => {
    void cargarDatos();
  }, []);

  const ejecutarConsultaSarlaft = async (
    docParam?: string,
    nomParam?: string,
    tipoParam?: "ASPIRANTE_GUARDA" | "CLIENTE_B2B" | "VISITANTE_CRITICO"
  ) => {
    const docFinal = docParam ?? documento;
    const nomFinal = nomParam ?? nombreCompleto;
    const tipoFinal = tipoParam ?? tipoTercero;
    setDocumento(docFinal);
    setNombreCompleto(nomFinal);
    setTipoTercero(tipoFinal);

    const cert = await servicioConsultarSarlaft({
      documento: docFinal,
      nombre_completo: nomFinal,
      tipo_tercero: tipoFinal,
    });
    setCertificadoReciente(cert);
    const actualizado = await servicioListarHistorialSarlaft();
    setHistorialSarlaft(actualizado);
  };

  const manejarCheckAptitud = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await servicioRegistrarCheckAptitudSst({
      puesto_id: puestoSstId,
      horas_sueno_reportadas: horasSueno,
      cero_alcohol_fatiga: ceroAlcohol,
      chaleco_kevlar_verificado: chalecoVerificado,
      serial_chaleco_asignado: "KEV-IIIA-2024-108",
      observaciones_sst: "Check-in psicofísico Decreto 1072 registrado en consola.",
    });
    setResultadoCheckSst(res);
  };

  const manejarLatidoHombreCaido = async (puestoId: number, simularAlerta: boolean) => {
    const res = await servicioRegistrarLatidoHombreCaido(puestoId, simularAlerta);
    setMensajeSst(res.mensaje);
    const actualizados = await servicioListarMonitoresHombreCaido();
    setMonitores(actualizados);
  };

  return (
    <div className="space-y-6 text-slate-100">
      {/* Encabezado */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-slate-900/90 border border-emerald-500/30 rounded-xl p-5 shadow-lg">
        <div>
          <div className="flex items-center gap-2 text-emerald-400 text-xs font-mono uppercase tracking-widest">
            <FileCheck2 className="w-4 h-4" />
            <span>SENTINEL // OPS V5.0 — CUMPLIMIENTO LEGAL & RIESGO OPERATIVO</span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">
            SARLAFT 2.0 (Listas Restrictivas), SG-SST Decreto 1072 & Hombre Caído
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Debida diligencia instantánea OFAC/ONU/INTERPOL/PONAL con firma SHA-256, aptitud psicofísica ARL Nivel V y vida útil Kevlar (5 años).
          </p>
        </div>
        <button
          onClick={() => void cargarDatos()}
          className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-600 text-xs font-mono text-emerald-300 transition self-start md:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${cargando ? "animate-spin" : ""}`} />
          Actualizar Matrices
        </button>
      </div>

      {/* SECCIÓN 1: VALIDADOR SARLAFT 2.0 CON PRESETS DE 1 CLIC */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-6 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold font-mono text-emerald-400 flex items-center gap-2">
              <Search className="w-4 h-4" />
              CRUCE INSTANTÁNEO DE LISTAS RESTRICTIVAS SARLAFT 2.0
            </h2>
          </div>

          {/* Presets de demostración en 1 clic */}
          <div className="space-y-1.5">
            <span className="text-[11px] font-mono text-slate-400 uppercase block">
              Presets de Simulación Normativa (1 Clic):
            </span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() =>
                  void ejecutarConsultaSarlaft(
                    "1032489120",
                    "Andrés Felipe Castellanos Gómez",
                    "ASPIRANTE_GUARDA"
                  )
                }
                className="px-2.5 py-1.5 rounded bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-500/40 text-xs font-mono transition"
              >
                ✓ Probar Ciudadano Limpio
              </button>
              <button
                type="button"
                onClick={() =>
                  void ejecutarConsultaSarlaft(
                    "79884120",
                    "Dr. Gustavo Adolfo Mendoza (Ex-Ministro PEP)",
                    "CLIENTE_B2B"
                  )
                }
                className="px-2.5 py-1.5 rounded bg-amber-950/80 hover:bg-amber-900 text-amber-300 border border-amber-500/40 text-xs font-mono transition"
              >
                ⚠ Probar Persona Expuesta Políticamente (PEP)
              </button>
              <button
                type="button"
                onClick={() =>
                  void ejecutarConsultaSarlaft(
                    "80666999",
                    "Inversiones Fantasma del Caribe OFAC Ltda.",
                    "VISITANTE_CRITICO"
                  )
                }
                className="px-2.5 py-1.5 rounded bg-red-950/80 hover:bg-red-900 text-red-200 border border-red-500/40 text-xs font-mono transition"
              >
                ⛔ Probar Coincidencia Lista Restrictiva OFAC/INTERPOL
              </button>
            </div>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              void ejecutarConsultaSarlaft();
            }}
            className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2"
          >
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">
                Cédula / NIT / Pasaporte
              </label>
              <input
                type="text"
                value={documento}
                onChange={(e) => setDocumento(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">
                Tipo de Contraparte / Tercero
              </label>
              <select
                value={tipoTercero}
                onChange={(e) =>
                  setTipoTercero(
                    e.target.value as
                      | "ASPIRANTE_GUARDA"
                      | "CLIENTE_B2B"
                      | "VISITANTE_CRITICO"
                  )
                }
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              >
                <option value="ASPIRANTE_GUARDA">ASPIRANTE A GUARDA OPERATIVO</option>
                <option value="CLIENTE_B2B">CLIENTE CORPORATIVO B2B</option>
                <option value="VISITANTE_CRITICO">VISITANTE ÁREA CRÍTICA / PROVEEDOR</option>
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-mono text-slate-400 mb-1">
                Nombre Completo o Razón Social
              </label>
              <input
                type="text"
                value={nombreCompleto}
                onChange={(e) => setNombreCompleto(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                required
              />
            </div>
            <div className="sm:col-span-2">
              <button
                type="submit"
                className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-bold uppercase tracking-wider transition"
              >
                Ejecutar Cruce SARLAFT &amp; Emitir Certificado SHA-256
              </button>
            </div>
          </form>
        </div>

        {/* Certificado SARLAFT emitido */}
        <div className="lg:col-span-6 bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h2 className="text-base font-bold font-mono text-slate-200 mb-3">
            CERTIFICADO DE DEBIDA DILIGENCIA SARLAFT (CIRCULAR EXTERNA SUPERVIGILANCIA)
          </h2>
          {certificadoReciente ? (
            <div
              className={`rounded-xl p-4 border space-y-3 ${
                certificadoReciente.nivel_riesgo === "BLOQUEO_LISTA_RESTRICTIVA"
                  ? "bg-red-950/40 border-red-500"
                  : certificadoReciente.nivel_riesgo === "RIESGO_MEDIO_PEP"
                  ? "bg-amber-950/30 border-amber-500"
                  : "bg-emerald-950/30 border-emerald-500/50"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold px-2.5 py-1 rounded bg-slate-950 text-emerald-300 border border-slate-700">
                  {certificadoReciente.codigo_certificado}
                </span>
                <span
                  className={`font-mono text-xs font-bold px-3 py-1 rounded ${
                    certificadoReciente.nivel_riesgo === "BLOQUEO_LISTA_RESTRICTIVA"
                      ? "bg-red-600 text-white"
                      : certificadoReciente.nivel_riesgo === "RIESGO_MEDIO_PEP"
                      ? "bg-amber-500 text-slate-950"
                      : "bg-emerald-600 text-white"
                  }`}
                >
                  {certificadoReciente.nivel_riesgo}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-slate-400 block">Tercero Evaluado:</span>
                  <span className="font-bold text-white">
                    {certificadoReciente.nombre_consultado}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Documento / NIT:</span>
                  <span className="font-mono text-slate-200">
                    {certificadoReciente.documento_consultado} ({certificadoReciente.tipo_tercero})
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-200 bg-slate-950/70 p-3 rounded-lg border border-slate-800">
                {certificadoReciente.detalle_validacion}
              </p>

              <div className="text-[11px] font-mono text-slate-400 space-y-1">
                <div>
                  Listas Auditadas:{" "}
                  <span className="text-slate-300">
                    {certificadoReciente.listas_evaluadas.join(" • ")}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-emerald-400 truncate">
                  <Lock className="w-3.5 h-3.5 shrink-0" />
                  <span>SELLO SHA-256: {certificadoReciente.sello_auditoria_sha256}</span>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-400">Seleccione un preset o consulte un documento.</p>
          )}
        </div>
      </div>

      {/* SECCIÓN 2: MONITOR DE HOMBRE CAÍDO (DEAD MAN'S SWITCH) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h2 className="text-base font-bold font-mono text-emerald-400 flex items-center gap-2">
              <HeartPulse className="w-5 h-5" />
              MONITOR DE SUPERVIVENCIA &quot;HOMBRE CAÍDO&quot; (DEAD MAN&apos;S SWITCH — PUESTOS 24/7)
            </h2>
            <p className="text-xs text-slate-400">
              Temporizador de pulso de vida cada 15 minutos en turno nocturno. Si no hay confirmación, escala pre-alerta silenciosa al CAD.
            </p>
          </div>
          {mensajeSst && (
            <span className="px-3 py-1.5 rounded-lg bg-emerald-950 border border-emerald-500/50 text-xs font-mono text-emerald-300">
              {mensajeSst}
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {monitores.map((m) => {
            const enAlerta = m.estado_supervivencia !== "ACTIVO_NORMAL";
            return (
              <div
                key={m.monitoreo_id}
                className={`rounded-xl p-4 border ${
                  enAlerta
                    ? "bg-red-950/35 border-red-500/80"
                    : "bg-slate-950/80 border-slate-800"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-emerald-400">
                    {m.puesto_codigo}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                      enAlerta
                        ? "bg-red-600 text-white animate-pulse"
                        : "bg-emerald-950 text-emerald-300 border border-emerald-500/40"
                    }`}
                  >
                    {m.estado_supervivencia}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-white mt-1">{m.puesto_nombre}</h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  Guarda: {m.operador_nombre} ({m.operador_codigo})
                </p>

                <div className="flex items-center justify-between text-xs font-mono mt-3 pt-2 border-t border-slate-800">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-amber-400" />
                    Ventana: {Math.floor(m.segundos_restantes_ventana / 60)}m{" "}
                    {m.segundos_restantes_ventana % 60}s
                  </span>
                  <span className="text-emerald-300">
                    {m.latidos_consecutivos_exitosos} pulsos OK
                  </span>
                </div>

                <div className="flex items-center gap-2 mt-3">
                  <button
                    onClick={() => void manejarLatidoHombreCaido(m.puesto_id, false)}
                    className="flex-1 py-1.5 px-2.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-semibold transition"
                  >
                    Enviar Pulso de Vida
                  </button>
                  <button
                    onClick={() => void manejarLatidoHombreCaido(m.puesto_id, true)}
                    className="py-1.5 px-2.5 rounded bg-red-900/70 hover:bg-red-800 text-red-200 border border-red-500/40 text-xs font-mono transition"
                    title="Simular Inactividad Crítica"
                  >
                    Simular Caída
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* SECCIÓN 3: CHECK-IN DE APTITUD PSICOFÍSICA PRE-TURNO & SEMÁFORO DE CHALECOS KEVLAR */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h2 className="text-base font-bold font-mono text-emerald-400 flex items-center gap-2">
            <UserCheck className="w-4 h-4" />
            CHECK-IN PSICOFÍSICO PRE-TURNO (DECRETO 1072 / ARL NIVEL V)
          </h2>
          <form onSubmit={(e) => void manejarCheckAptitud(e)} className="space-y-3">
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">
                Puesto Operativo a Recibir
              </label>
              <select
                value={puestoSstId}
                onChange={(e) => setPuestoSstId(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              >
                {chalecos.map((c) => (
                  <option key={c.puesto_id} value={c.puesto_id}>
                    {c.puesto_codigo} — {c.puesto_nombre}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">
                Horas de Sueño Reparador (Últimas 24h) — Mínimo Legal: 5.0h
              </label>
              <input
                type="number"
                step="0.5"
                min="0"
                max="14"
                value={horasSueno}
                onChange={(e) => setHorasSueno(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono"
              />
            </div>
            <div className="flex items-center gap-4 text-xs font-mono">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={ceroAlcohol}
                  onChange={(e) => setCeroAlcohol(e.target.checked)}
                />
                <span>Cero Alcohol / Fatiga</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={chalecoVerificado}
                  onChange={(e) => setChalecoVerificado(e.target.checked)}
                />
                <span>Chaleco Kevlar IIIA Verificado</span>
              </label>
            </div>
            <button
              type="submit"
              className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-bold uppercase tracking-wider transition"
            >
              Validar Aptitud Psicofísica SG-SST
            </button>
          </form>

          {resultadoCheckSst && (
            <div
              className={`rounded-lg p-3 border text-xs font-mono ${
                resultadoCheckSst.apto_operacion
                  ? "bg-emerald-950/50 border-emerald-500/60 text-emerald-200"
                  : "bg-red-950/60 border-red-500 text-red-200"
              }`}
            >
              <div className="font-bold flex items-center gap-1.5">
                {resultadoCheckSst.apto_operacion ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <AlertOctagon className="w-4 h-4 text-red-400" />
                )}
                <span>Resultado: {resultadoCheckSst.estado_evaluacion}</span>
              </div>
              <div className="mt-1 text-[11px] text-slate-300">
                Sueño declarado: {resultadoCheckSst.horas_sueno_reportadas}h | Sello SHA-256:{" "}
                {resultadoCheckSst.sello_sst_sha256.slice(0, 20)}...
              </div>
            </div>
          )}
        </div>

        {/* Semáforo de Vida Útil de Chalecos Kevlar (5 años) */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
          <h2 className="text-base font-bold font-mono text-emerald-400 flex items-center gap-2">
            <Shield className="w-4 h-4" />
            SEMÁFORO DE VIDA ÚTIL DE PANELES BALÍSTICOS KEVLAR (NIVEL IIIA — NORMA 5 AÑOS)
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="py-2 pr-3">Puesto</th>
                  <th className="py-2 pr-3">Lote Kevlar NIJ</th>
                  <th className="py-2 pr-3">Vencimiento (5 Años)</th>
                  <th className="py-2 pr-3">Días Restantes</th>
                  <th className="py-2">Estado Normativo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {chalecos.map((c) => {
                  const vencido = c.semaforo_kevlar === "VENCIDO_REEMPLAZO_INMEDIATO";
                  return (
                    <tr key={c.puesto_id}>
                      <td className="py-2.5 pr-3 font-bold text-white">{c.puesto_codigo}</td>
                      <td className="py-2.5 pr-3 text-slate-300">
                        {c.serial_lote_kevlar} ({c.unidades_en_puesto} uds)
                      </td>
                      <td className="py-2.5 pr-3 text-slate-300">{c.fecha_vencimiento_5_anos}</td>
                      <td
                        className={`py-2.5 pr-3 font-bold ${
                          vencido ? "text-red-400" : "text-emerald-400"
                        }`}
                      >
                        {c.dias_restantes_vida_util} días
                      </td>
                      <td className="py-2.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            vencido
                              ? "bg-red-600 text-white"
                              : "bg-emerald-950 text-emerald-300 border border-emerald-500/40"
                          }`}
                        >
                          {c.semaforo_kevlar}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Historial Auditable SARLAFT */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-bold font-mono text-slate-300 mb-3 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-emerald-400" />
          HISTORIAL AUDITABLE DE CERTIFICADOS SARLAFT 2.0 ENCADENADOS ({historialSarlaft.length})
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2 pr-3">Certificado</th>
                <th className="py-2 pr-3">Documento / NIT</th>
                <th className="py-2 pr-3">Nombre / Razón Social</th>
                <th className="py-2 pr-3">Nivel de Riesgo</th>
                <th className="py-2">Sello SHA-256</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {historialSarlaft.slice(0, 8).map((item) => (
                <tr key={item.certificado_id}>
                  <td className="py-2 pr-3 text-emerald-400 font-bold">
                    {item.codigo_certificado}
                  </td>
                  <td className="py-2 pr-3 text-slate-200">{item.documento_consultado}</td>
                  <td className="py-2 pr-3 text-white font-sans">{item.nombre_consultado}</td>
                  <td className="py-2 pr-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        item.nivel_riesgo === "BLOQUEO_LISTA_RESTRICTIVA"
                          ? "bg-red-600 text-white"
                          : item.nivel_riesgo === "RIESGO_MEDIO_PEP"
                          ? "bg-amber-500 text-slate-950"
                          : "bg-emerald-950 text-emerald-300 border border-emerald-500/40"
                      }`}
                    >
                      {item.nivel_riesgo}
                    </span>
                  </td>
                  <td className="py-2 text-slate-400">
                    {item.sello_auditoria_sha256.slice(0, 22)}...
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default CumplimientoSarlaftSST;


import React, { useState, useEffect } from "react";
import {
  servicioConsultarSemaforoSalvoconductos,
  servicioConsultarKardexBalistico,
  servicioRegistrarMovimientoBalistico,
  servicioListarCertificadosPoligono,
  servicioRegistrarCertificadoPoligono,
  servicioListarPuestos,
  servicioListarUsuarios,
  extraerMensajeError,
} from "../servicios/cliente_api";
import { usarAlmacenAutenticacion } from "../estado/almacen_autenticacion";
import type {
  SemaforoSalvoconducto,
  MovimientoBalistico,
  TipoMovimientoBalistico,
  CertificadoPoligono,
  PuestoVigilancia,
  UsuarioSistema,
} from "../tipos/tipos_sistema";

export function ModuloLibroBalistico(): React.ReactElement {
  const { usuarioActual } = usarAlmacenAutenticacion();
  const esAdminOSuper =
    usuarioActual?.rol === "ADMINISTRADOR" ||
    usuarioActual?.rol === "SUPERVISOR";

  const [puestos, setPuestos] = useState<PuestoVigilancia[]>([]);
  const [puestoSeleccionadoId, setPuestoSeleccionadoId] = useState<number>(1);
  const [operadores, setOperadores] = useState<UsuarioSistema[]>([]);

  // Semáforo de salvoconductos
  const [salvoconductos, setSalvoconductos] = useState<SemaforoSalvoconducto[]>([]);
  const [cargandoSemaforo, setCargandoSemaforo] = useState<boolean>(false);

  // Kardex balístico
  const [kardex, setKardex] = useState<MovimientoBalistico[]>([]);
  const [cargandoKardex, setCargandoKardex] = useState<boolean>(false);

  // Certificados de Polígono
  const [certificados, setCertificados] = useState<CertificadoPoligono[]>([]);

  // Formulario movimiento balístico
  const [tipoMovimiento, setTipoMovimiento] =
    useState<TipoMovimientoBalistico>("CONSUMO_INCIDENTE");
  const [calibre, setCalibre] = useState<string>(".38 SPL");
  const [cantidadMunicion, setCantidadMunicion] = useState<number>(1);
  const [justificacion, setJustificacion] = useState<string>("");
  const [oficioDcca, setOficioDcca] = useState<string>("");
  const [registrandoMov, setRegistrandoMov] = useState<boolean>(false);

  // Formulario certificado polígono
  const [operadorCertId, setOperadorCertId] = useState<number>(0);
  const [academia, setAcademia] = useState<string>(
    "Academia Nacional de Seguridad Andina"
  );
  const [armaCalificada, setArmaCalificada] = useState<string>(
    "Revólver .38SPL / Escopeta 12GA"
  );
  const [puntaje, setPuntaje] = useState<number>(95);
  const [fechaPractica, setFechaPractica] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [registrandoCert, setRegistrandoCert] = useState<boolean>(false);

  const [mensaje, setMensaje] = useState<{
    tipo: "exito" | "error";
    texto: string;
  } | null>(null);

  useEffect(() => {
    cargarDatosGenerales();
  }, []);

  useEffect(() => {
    if (puestoSeleccionadoId > 0) {
      cargarKardex(puestoSeleccionadoId);
    }
  }, [puestoSeleccionadoId]);

  async function cargarDatosGenerales() {
    setCargandoSemaforo(true);
    try {
      const [listaPuestos, listaSalvo, listaCerts, todosUsuarios] =
        await Promise.all([
          servicioListarPuestos(),
          servicioConsultarSemaforoSalvoconductos(),
          servicioListarCertificadosPoligono(),
          servicioListarUsuarios(),
        ]);

      setPuestos(listaPuestos);
      setSalvoconductos(listaSalvo);
      setCertificados(listaCerts);

      const ops = todosUsuarios.filter((u) => u.rol === "OPERADOR");
      setOperadores(ops);
      if (ops.length > 0) {
        setOperadorCertId(ops[0].usuario_id);
      }
      if (listaPuestos.length > 0) {
        setPuestoSeleccionadoId(listaPuestos[0].puesto_id);
      }
    } catch (err) {
      console.error("Error al cargar datos balísticos:", err);
    } finally {
      setCargandoSemaforo(false);
    }
  }

  async function cargarKardex(puestoId: number) {
    setCargandoKardex(true);
    try {
      const movimientos = await servicioConsultarKardexBalistico(puestoId);
      setKardex(movimientos);
    } catch (err) {
      console.error("Error al cargar kardex:", err);
    } finally {
      setCargandoKardex(false);
    }
  }

  async function handleRegistrarMovimiento(e: React.FormEvent) {
    e.preventDefault();
    const dotacionDelPuesto = salvoconductos.find(
      (s) => s.puesto_id === puestoSeleccionadoId
    );

    if (!dotacionDelPuesto) {
      setMensaje({
        tipo: "error",
        texto: "El puesto seleccionado no cuenta con dotación de armas registrada.",
      });
      return;
    }

    setRegistrandoMov(true);
    try {
      const nuevo = await servicioRegistrarMovimientoBalistico({
        puesto_id: puestoSeleccionadoId,
        dotacion_id: dotacionDelPuesto.dotacion_id,
        tipo_movimiento: tipoMovimiento,
        calibre,
        cantidad_municion_afectada: cantidadMunicion,
        justificacion_novedad: justificacion,
        numero_oficio_dcca: oficioDcca || undefined,
      });

      setKardex([nuevo, ...kardex]);
      setMensaje({
        tipo: "exito",
        texto: `Movimiento foliado exitosamente con sello SHA-256. Nuevo saldo: ${nuevo.saldo_municion_resultante} cartuchos.`,
      });
      setJustificacion("");
      setOficioDcca("");
      // Recargar semáforo para actualizar stock
      const salvoActualizado = await servicioConsultarSemaforoSalvoconductos();
      setSalvoconductos(salvoActualizado);
    } catch (err) {
      setMensaje({
        tipo: "error",
        texto: `Fallo al registrar movimiento balístico: ${extraerMensajeError(err)}`,
      });
    } finally {
      setRegistrandoMov(false);
    }
  }

  async function handleRegistrarCertificado(e: React.FormEvent) {
    e.preventDefault();
    if (!operadorCertId) return;

    setRegistrandoCert(true);
    try {
      const nuevoCert = await servicioRegistrarCertificadoPoligono({
        operador_id: operadorCertId,
        academia_seguridad: academia,
        tipo_arma_calificada: armaCalificada,
        puntaje_precision: puntaje,
        aprobado: puntaje >= 70,
        fecha_practica: fechaPractica,
      });

      setCertificados([nuevoCert, ...certificados]);
      setMensaje({
        tipo: "exito",
        texto: `Certificado de tiro registrado para ${nuevoCert.nombre_operador}. Vence: ${nuevoCert.fecha_vencimiento_anual}.`,
      });
    } catch (err) {
      setMensaje({
        tipo: "error",
        texto: `Fallo al registrar certificado: ${extraerMensajeError(err)}`,
      });
    } finally {
      setRegistrandoCert(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="bg-slate-900 border border-amber-500/30 rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 text-xs font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-full">
                FASE 10 • TRAZABILIDAD DCCA INDUMIL
              </span>
              <span className="text-xs text-slate-400 font-mono">
                DECRETO 2535/1993 • CONTROL COMERCIO DE ARMAS
              </span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span className="text-amber-400">🛡️</span> Libro Balístico Digital & Salvoconductos
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Semáforo preventivo de vencimiento de salvoconductos (90/60/30 días), kardex de munición con firma SHA-256 y acreditación anual de polígono.
            </p>
          </div>

          <button
            onClick={cargarDatosGenerales}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-mono font-semibold transition"
          >
            ↻ Actualizar Auditoría
          </button>
        </div>
      </div>

      {mensaje && (
        <div
          className={`p-4 rounded-lg border text-sm font-medium flex items-center justify-between ${
            mensaje.tipo === "exito"
              ? "bg-amber-950/40 border-amber-500/40 text-amber-300"
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

      {/* 1. Semáforo Preventivo de Salvoconductos Indumil */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex justify-between items-center border-b border-slate-800 pb-3">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            Semáforo de Salvoconductos y Permisos Indumil ({salvoconductos.length} Armas)
          </h3>
          <span className="text-xs font-mono text-slate-400">
            Alertas: 90 / 60 / 30 Días
          </span>
        </div>

        {cargandoSemaforo ? (
          <div className="p-6 text-center text-slate-500 font-mono text-xs">
            Evaluando salvoconductos ante DCCA...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {salvoconductos.map((s) => (
              <div
                key={s.dotacion_id}
                className={`p-4 rounded-xl border flex flex-col justify-between ${
                  s.estado_semaforo === "VIGENTE_VERDE"
                    ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-200"
                    : s.estado_semaforo === "PREVENTIVO_AMARILLO"
                    ? "bg-amber-950/20 border-amber-500/30 text-amber-200"
                    : "bg-rose-950/20 border-rose-500/30 text-rose-200"
                }`}
              >
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-mono font-bold tracking-wider">
                      {s.serial_arma}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
                        s.estado_semaforo === "VIGENTE_VERDE"
                          ? "bg-emerald-500/20 text-emerald-400"
                          : s.estado_semaforo === "PREVENTIVO_AMARILLO"
                          ? "bg-amber-500/20 text-amber-400"
                          : "bg-rose-500/20 text-rose-400"
                      }`}
                    >
                      {s.estado_semaforo.replace("_", " ")}
                    </span>
                  </div>
                  <h4 className="font-bold text-sm text-white mb-1">
                    {s.tipo_arma}
                  </h4>
                  <p className="text-xs opacity-80">
                    Puesto: <strong>{s.nombre_puesto}</strong>
                  </p>
                  <p className="text-[11px] font-mono opacity-80 mt-1">
                    Salvoconducto N°: {s.numero_salvoconducto_indumil} ({s.tipo_salvoconducto})
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-white/10 flex justify-between items-center text-xs font-mono">
                  <span>
                    Vence: <strong>{s.fecha_vencimiento_salvoconducto}</strong>
                  </span>
                  <span className="font-bold">
                    {s.dias_restantes} Días
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 2. Kardex de Munición & Registro de Movimientos */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Formulario Registro Movimiento (5 columnas) */}
        {esAdminOSuper && (
          <div className="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2 border-b border-slate-800 pb-3">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              Asentar Movimiento Balístico
            </h3>

            <form onSubmit={handleRegistrarMovimiento} className="space-y-3">
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  PUESTO OPERATIVO
                </label>
                <select
                  value={puestoSeleccionadoId}
                  onChange={(e) =>
                    setPuestoSeleccionadoId(parseInt(e.target.value) || 1)
                  }
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                >
                  {puestos.map((p) => (
                    <option key={p.puesto_id} value={p.puesto_id}>
                      {p.nombre_puesto}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    TIPO MOVIMIENTO
                  </label>
                  <select
                    value={tipoMovimiento}
                    onChange={(e) =>
                      setTipoMovimiento(
                        e.target.value as TipoMovimientoBalistico
                      )
                    }
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                  >
                    <option value="CONSUMO_INCIDENTE">Consumo en Incidente</option>
                    <option value="PRACTICA_POLIGONO">Práctica Polígono</option>
                    <option value="REPOSICION_INDUMIL">Reposición Indumil</option>
                    <option value="MANTENIMIENTO_ARMERIA">Mantenimiento Armería</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    CANTIDAD CARTUCHOS
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={cantidadMunicion}
                    onChange={(e) =>
                      setCantidadMunicion(
                        Math.max(1, parseInt(e.target.value) || 1)
                      )
                    }
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    CALIBRE
                  </label>
                  <input
                    type="text"
                    value={calibre}
                    onChange={(e) => setCalibre(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    N° OFICIO / CASO DCCA
                  </label>
                  <input
                    type="text"
                    placeholder="Ej: OF-DCCA-2026-90"
                    value={oficioDcca}
                    onChange={(e) => setOficioDcca(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  JUSTIFICACIÓN Y NOVEDAD LEGAL *
                </label>
                <textarea
                  required
                  rows={2}
                  placeholder="Detalle del uso o ingreso de la munición..."
                  value={justificacion}
                  onChange={(e) => setJustificacion(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <button
                type="submit"
                disabled={registrandoMov}
                className="w-full py-2.5 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-800 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-lg transition shadow-md shadow-amber-950/50"
              >
                {registrandoMov ? "Firmando SHA-256..." : "Asentar en Libro Balístico (SHA-256)"}
              </button>
            </form>
          </div>
        )}

        {/* Historial Kardex Foliado (7 columnas) */}
        <div className="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
          <div className="flex justify-between items-center border-b border-slate-800 pb-3">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-sky-400" />
              Kardex de Munición del Puesto ({kardex.length} Registros)
            </h3>
            <span className="text-xs font-mono text-slate-400">
              Sello Criptográfico Inmutable
            </span>
          </div>

          {cargandoKardex ? (
            <div className="p-8 text-center text-slate-500 font-mono text-xs">
              Cargando historial balístico...
            </div>
          ) : kardex.length === 0 ? (
            <div className="p-12 text-center text-slate-500 border border-dashed border-slate-800 rounded-lg text-xs font-mono">
              No hay movimientos balísticos registrados en este puesto.
            </div>
          ) : (
            <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
              {kardex.map((k) => (
                <div
                  key={k.movimiento_id}
                  className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg text-xs font-mono"
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-bold text-amber-400">
                      {k.tipo_movimiento.replace("_", " ")}
                    </span>
                    <span className="text-slate-400 text-[10px]">
                      {new Date(k.fecha_movimiento).toLocaleString("es-CO")}
                    </span>
                  </div>

                  <div className="text-slate-200 font-sans mb-1.5">
                    {k.justificacion_novedad}
                  </div>

                  <div className="flex justify-between items-center text-[11px] text-slate-400 pt-1.5 border-t border-slate-800/80">
                    <span>
                      Cant: <strong className="text-white">{k.cantidad_municion_afectada}</strong> {k.calibre}
                    </span>
                    <span>
                      Saldo: <strong className="text-emerald-400">{k.saldo_municion_resultante}</strong> cartuchos
                    </span>
                    <span className="text-slate-500 truncate max-w-[140px]" title={k.firma_digital_sha256}>
                      SHA: {k.firma_digital_sha256.substring(0, 10)}...
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 3. Registro y Listado de Pruebas de Polígono Anuales (SuperVigilancia) */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex justify-between items-center border-b border-slate-800 pb-3">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Acreditación de Pruebas de Tiro y Polígono Anual ({certificados.length} Certificados)
          </h3>
          <span className="text-xs font-mono text-slate-400">
            Vigencia: 365 Días Reglamentarios
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {esAdminOSuper && (
            <form
              onSubmit={handleRegistrarCertificado}
              className="lg:col-span-5 bg-slate-950/80 p-4 rounded-xl border border-slate-800 space-y-3"
            >
              <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                Acreditar Nueva Calificación de Tiro
              </h4>

              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  VIGILANTE / OPERADOR EVALUADO
                </label>
                <select
                  value={operadorCertId}
                  onChange={(e) => setOperadorCertId(parseInt(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white"
                >
                  {operadores.map((op) => (
                    <option key={op.usuario_id} value={op.usuario_id}>
                      {op.nombre_completo} ({op.codigo_placa})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  ACADEMIA DE SEGURIDAD ACREDITADA
                </label>
                <input
                  type="text"
                  value={academia}
                  onChange={(e) => setAcademia(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono text-slate-400 mb-1">
                    ARMA CALIFICADA
                  </label>
                  <input
                    type="text"
                    value={armaCalificada}
                    onChange={(e) => setArmaCalificada(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white font-mono"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-mono text-slate-400 mb-1">
                    PUNTAJE (MÍN 70%)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={puntaje}
                    onChange={(e) => setPuntaje(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white font-mono font-bold"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  FECHA DE PRÁCTICA
                </label>
                <input
                  type="date"
                  value={fechaPractica}
                  onChange={(e) => setFechaPractica(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white font-mono"
                />
              </div>

              <button
                type="submit"
                disabled={registrandoCert}
                className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-lg transition"
              >
                {registrandoCert ? "Registrando..." : "Acreditar Certificado Oficial"}
              </button>
            </form>
          )}

          <div className={`${esAdminOSuper ? "lg:col-span-7" : "lg:col-span-12"} space-y-2`}>
            {certificados.length === 0 ? (
              <div className="p-8 text-center text-slate-500 border border-dashed border-slate-800 rounded-lg text-xs font-mono">
                No hay certificados de tiro cargados en el sistema.
              </div>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                {certificados.map((cert) => (
                  <div
                    key={cert.certificado_id}
                    className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg text-xs flex justify-between items-center"
                  >
                    <div>
                      <div className="font-bold text-white">
                        {cert.nombre_operador}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {cert.academia_seguridad} • Arma: {cert.tipo_arma_calificada}
                      </div>
                      <div className="text-[10px] font-mono text-slate-500 mt-0.5">
                        Practicado: {cert.fecha_practica} • Vence: <strong className="text-emerald-400">{cert.fecha_vencimiento_anual}</strong>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        {cert.puntaje_precision}% APROBADO
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

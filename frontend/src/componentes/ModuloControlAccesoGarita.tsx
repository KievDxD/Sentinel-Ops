import React, { useState, useEffect } from "react";
import {
  servicioDecodificarCedula,
  servicioRegistrarIngresoGarita,
  servicioRegistrarSalidaGarita,
  servicioListarActivosEnPuesto,
  servicioListarPuestos,
  extraerMensajeError,
} from "../servicios/cliente_api";
import type {
  RegistroAccesoGarita,
  TipoAccesoGarita,
  PuestoVigilancia,
  DatosCedulaColombiana,
} from "../tipos/tipos_sistema";

export function ModuloControlAccesoGarita(): React.ReactElement {
  const [puestos, setPuestos] = useState<PuestoVigilancia[]>([]);
  const [puestoSeleccionadoId, setPuestoSeleccionadoId] = useState<number>(1);
  const [visitantesActivos, setVisitantesActivos] = useState<
    RegistroAccesoGarita[]
  >([]);
  const [cargandoLista, setCargandoLista] = useState<boolean>(false);

  // Estados del escáner y formulario
  const [tramaEscaneada, setTramaEscaneada] = useState<string>("");
  const [decodificando, setDecodificando] = useState<boolean>(false);
  const [datosCedula, setDatosCedula] = useState<DatosCedulaColombiana | null>(
    null
  );

  const [tipoAcceso, setTipoAcceso] =
    useState<TipoAccesoGarita>("PEATONAL_VISITANTE");
  const [documento, setDocumento] = useState<string>("");
  const [nombres, setNombres] = useState<string>("");
  const [apellidos, setApellidos] = useState<string>("");
  const [rh, setRh] = useState<string>("O+");
  const [placaVehiculo, setPlacaVehiculo] = useState<string>("");
  const [empresaDestino, setEmpresaDestino] = useState<string>("");
  const [motivoIngreso, setMotivoIngreso] = useState<string>("");
  const [observaciones, setObservaciones] = useState<string>("");
  const [registrando, setRegistrando] = useState<boolean>(false);

  const [mensaje, setMensaje] = useState<{
    tipo: "exito" | "error";
    texto: string;
  } | null>(null);

  useEffect(() => {
    cargarPuestos();
  }, []);

  useEffect(() => {
    if (puestoSeleccionadoId > 0) {
      cargarActivos(puestoSeleccionadoId);
    }
  }, [puestoSeleccionadoId]);

  async function cargarPuestos() {
    try {
      const lista = await servicioListarPuestos();
      setPuestos(lista);
      if (lista.length > 0) {
        setPuestoSeleccionadoId(lista[0].puesto_id);
      }
    } catch (err) {
      console.error("Error al cargar puestos:", err);
    }
  }

  async function cargarActivos(puestoId: number) {
    setCargandoLista(true);
    try {
      const lista = await servicioListarActivosEnPuesto(puestoId);
      setVisitantesActivos(lista);
    } catch (err) {
      console.error("Error al cargar visitantes activos:", err);
    } finally {
      setCargandoLista(false);
    }
  }

  async function handleDecodificarTrama(cadena: string) {
    if (!cadena || cadena.length < 10) return;
    setDecodificando(true);
    try {
      const res = await servicioDecodificarCedula(cadena);
      setDatosCedula(res);
      if (res.es_valido) {
        setDocumento(res.documento_identidad);
        setNombres(
          `${res.primer_nombre} ${res.segundo_nombre}`.trim()
        );
        setApellidos(
          `${res.primer_apellido} ${res.segundo_apellido}`.trim()
        );
        setRh(res.grupo_sanguineo_rh);
        setMensaje({
          tipo: "exito",
          texto: `Cédula colombiana identificada: ${res.nombre_completo} (CC ${res.documento_identidad})`,
        });
      }
    } catch (err) {
      setMensaje({
        tipo: "error",
        texto: `No se pudo decodificar la trama: ${extraerMensajeError(err)}`,
      });
    } finally {
      setDecodificando(false);
    }
  }

  async function handleRegistrarIngreso(e: React.FormEvent) {
    e.preventDefault();
    if (!documento || !nombres || !apellidos || !empresaDestino || !motivoIngreso) {
      setMensaje({
        tipo: "error",
        texto: "Complete todos los campos obligatorios del ingreso.",
      });
      return;
    }

    setRegistrando(true);
    try {
      const nuevo = await servicioRegistrarIngresoGarita({
        puesto_id: puestoSeleccionadoId,
        tipo_acceso: tipoAcceso,
        documento_identidad: documento,
        nombres,
        apellidos,
        tipo_sangre_rh: rh,
        placa_vehiculo: placaVehiculo || undefined,
        empresa_o_destino: empresaDestino,
        motivo_ingreso: motivoIngreso,
        observaciones: observaciones || undefined,
      });

      setVisitantesActivos([nuevo, ...visitantesActivos]);
      setMensaje({
        tipo: "exito",
        texto: `Ingreso autorizado: ${nuevo.nombre_completo} registrado en garita.`,
      });

      // Limpiar formulario
      setTramaEscaneada("");
      setDocumento("");
      setNombres("");
      setApellidos("");
      setPlacaVehiculo("");
      setEmpresaDestino("");
      setMotivoIngreso("");
      setObservaciones("");
      setDatosCedula(null);
    } catch (err) {
      setMensaje({
        tipo: "error",
        texto: `Fallo al registrar ingreso: ${extraerMensajeError(err)}`,
      });
    } finally {
      setRegistrando(false);
    }
  }

  async function handleRegistrarSalida(accesoId: number) {
    try {
      await servicioRegistrarSalidaGarita(accesoId);
      setVisitantesActivos(
        visitantesActivos.filter((v) => v.acceso_id !== accesoId)
      );
      setMensaje({
        tipo: "exito",
        texto: "Salida registrada exitosamente.",
      });
    } catch (err) {
      setMensaje({
        tipo: "error",
        texto: `Fallo al registrar salida: ${extraerMensajeError(err)}`,
      });
    }
  }

  return (
    <div className="space-y-6">
      {/* Encabezado */}
      <div className="bg-slate-900 border border-sky-500/30 rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 text-xs font-mono font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/30 rounded-full">
                FASE 9 • PWA OPERATIVA
              </span>
              <span className="text-xs text-slate-400 font-mono">
                REGISTRADURÍA NACIONAL • ESTÁNDAR PDF417
              </span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span className="text-sky-400">⚡</span> Control de Acceso Garita & Escáner de Cédulas
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Lectura y decodificación automática del código de barras 2D de la cédula colombiana, registro vehicular y control de aforo en tiempo real.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <label className="text-xs font-mono text-slate-400">PUESTO:</label>
            <select
              value={puestoSeleccionadoId}
              onChange={(e) => setPuestoSeleccionadoId(parseInt(e.target.value) || 1)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              {puestos.map((p) => (
                <option key={p.puesto_id} value={p.puesto_id}>
                  {p.nombre_puesto}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Alerta de notificación */}
      {mensaje && (
        <div
          className={`p-4 rounded-lg border text-sm font-medium flex items-center justify-between ${
            mensaje.tipo === "exito"
              ? "bg-sky-950/40 border-sky-500/40 text-sky-300"
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

      {/* Cuadrícula: Escáner / Formulario a la izquierda y Personas adentro a la derecha */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Formulario de Entrada y Lector 2D (6 columnas) */}
        <div className="lg:col-span-6 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center justify-between border-b border-slate-800 pb-3">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-sky-400" />
              Lector PDF417 de Cédula de Ciudadanía
            </span>
            <span className="text-[11px] font-mono text-sky-400">
              Cámara / Pistola USB 2D
            </span>
          </h3>

          {/* Caja de Escaneo Rápido */}
          <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800">
            <label className="block text-xs font-mono text-slate-400 mb-1">
              APUNTE EL ESCÁNER 2D AL REVERSO DE LA CÉDULA
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Pistola USB o pegue trama PDF417: PubDSK_1 0010203040..."
                value={tramaEscaneada}
                onChange={(e) => {
                  setTramaEscaneada(e.target.value);
                  if (e.target.value.length > 20) {
                    handleDecodificarTrama(e.target.value);
                  }
                }}
                className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
              />
              <button
                type="button"
                onClick={() =>
                  handleDecodificarTrama(
                    "PubDSK_1 0010203040 VARGAS RESTREPO ALEJANDRO JOSE M 19880415 O+ 00000000"
                  )
                }
                className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-sky-300 border border-slate-700 rounded-lg text-xs font-mono transition"
              >
                Cédula Demo
              </button>
            </div>
            {decodificando && (
              <span className="text-[11px] text-sky-400 font-mono mt-1 block animate-pulse">
                Procesando trama de Registraduría...
              </span>
            )}
            {datosCedula && (
              <div className="mt-2 p-2 rounded bg-sky-950/40 border border-sky-500/30 text-[11px] text-sky-300 font-mono flex justify-between">
                <span>Registraduría: {datosCedula.nombre_completo}</span>
                <span>RH: {datosCedula.grupo_sanguineo_rh}</span>
              </div>
            )}
          </div>

          {/* Formulario de Ingreso */}
          <form onSubmit={handleRegistrarIngreso} className="space-y-3 pt-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  TIPO DE ACCESO
                </label>
                <select
                  value={tipoAcceso}
                  onChange={(e) =>
                    setTipoAcceso(e.target.value as TipoAccesoGarita)
                  }
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                >
                  <option value="PEATONAL_VISITANTE">Peatonal Visitante</option>
                  <option value="VEHICULAR">Vehicular / Conductor</option>
                  <option value="CONTRATISTA">Contratista / Proveedor</option>
                  <option value="EMPLEADO">Empleado / Funcionario</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  N° CÉDULA / DOC *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ej: 10203040"
                  value={documento}
                  onChange={(e) => setDocumento(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500 font-mono font-bold"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  NOMBRES *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ej: Alejandro José"
                  value={nombres}
                  onChange={(e) => setNombres(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  APELLIDOS *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ej: Vargas Restrepo"
                  value={apellidos}
                  onChange={(e) => setApellidos(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  GRUPO SANGUÍNEO / RH
                </label>
                <input
                  type="text"
                  placeholder="Ej: O+, A+, AB-"
                  value={rh}
                  onChange={(e) => setRh(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  PLACA VEHÍCULO (SI APLICA)
                </label>
                <input
                  type="text"
                  placeholder="Ej: HXZ-889"
                  value={placaVehiculo}
                  onChange={(e) => setPlacaVehiculo(e.target.value.toUpperCase())}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500 font-mono uppercase"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  EMPRESA / OFICINA DESTINO *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ej: Apto 402 / Piso 8"
                  value={empresaDestino}
                  onChange={(e) => setEmpresaDestino(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-400 mb-1">
                  MOTIVO INGRESO *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ej: Entrega de correspondencia"
                  value={motivoIngreso}
                  onChange={(e) => setMotivoIngreso(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-mono text-slate-400 mb-1">
                OBSERVACIONES DE GARITA
              </label>
              <input
                type="text"
                placeholder="Equipos ingresados (Laptop serial...), acompañantes..."
                value={observaciones}
                onChange={(e) => setObservaciones(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
              />
            </div>

            <button
              type="submit"
              disabled={registrando}
              className="w-full py-2.5 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 text-white font-bold text-xs uppercase tracking-wider rounded-lg transition shadow-md shadow-sky-950/50 mt-2"
            >
              {registrando ? "Registrando..." : "Autorizar Ingreso y Abrir Barrera"}
            </button>
          </form>
        </div>

        {/* Visitantes Actualmente en Sitio (6 columnas) */}
        <div className="lg:col-span-6 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center border-b border-slate-800 pb-3 mb-4">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                Personas / Vehículos Adentro ({visitantesActivos.length})
              </h3>
              <button
                onClick={() => cargarActivos(puestoSeleccionadoId)}
                className="text-xs text-sky-400 font-mono hover:underline"
              >
                ↻ Refrescar Aforo
              </button>
            </div>

            {cargandoLista ? (
              <div className="p-8 text-center text-slate-500 text-xs font-mono">
                Cargando aforo del puesto...
              </div>
            ) : visitantesActivos.length === 0 ? (
              <div className="p-12 text-center text-slate-500 border border-dashed border-slate-800 rounded-lg text-xs font-mono">
                No hay visitantes o vehículos activos dentro de las instalaciones.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
                {visitantesActivos.map((v) => (
                  <div
                    key={v.acceso_id}
                    className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg flex justify-between items-center hover:border-slate-700 transition"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-200 text-xs">
                          {v.nombre_completo}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-sky-500/10 text-sky-400 border border-sky-500/30">
                          CC {v.documento_identidad}
                        </span>
                        {v.placa_vehiculo && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/30">
                            🚗 {v.placa_vehiculo}
                          </span>
                        )}
                        {v.tipo_sangre_rh && (
                          <span className="text-[10px] font-mono text-slate-400">
                            RH {v.tipo_sangre_rh}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1">
                        Destino: <strong className="text-slate-300">{v.empresa_o_destino}</strong> • Motivo: {v.motivo_ingreso}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                        Ingreso: {new Date(v.fecha_ingreso).toLocaleTimeString("es-CO")} • Operador: {v.nombre_operador}
                      </div>
                    </div>

                    <button
                      onClick={() => handleRegistrarSalida(v.acceso_id)}
                      className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded text-xs font-semibold transition shrink-0 ml-3"
                    >
                      Registrar Salida
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-500 flex items-center justify-between">
            <span>Cumplimiento Ley 1581/2012 (Habeas Data & Protección de Datos Personales).</span>
            <span className="text-sky-400 font-mono">PWA OFFLINE-READY</span>
          </div>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from "react";
import {
  servicioCotizarTarifa,
  servicioListarPrefacturas,
  servicioGenerarPrefactura,
  servicioAbrirPrefacturaHtml,
  servicioListarUsuarios,
  servicioListarPuestos,
  extraerMensajeError,
} from "../servicios/cliente_api";
import { usarAlmacenAutenticacion } from "../estado/almacen_autenticacion";
import type {
  ModalidadServicioTarifa,
  RespuestaDesgloseCotizacion,
  PrefacturaB2B,
  UsuarioSistema,
  PuestoVigilancia,
} from "../tipos/tipos_sistema";

export function ModuloTarificadorB2B(): React.ReactElement {
  const { usuarioActual } = usarAlmacenAutenticacion();
  const esAdminORrhh =
    usuarioActual?.rol === "ADMINISTRADOR" || usuarioActual?.rol === "RRHH";

  // Estados del cotizador
  const [modalidad, setModalidad] = useState<ModalidadServicioTarifa>(
    "VIGILANCIA_24H_ARMADA"
  );
  const [cantidadPuestos, setCantidadPuestos] = useState<number>(1);
  const [porcentajeAdmin, setPorcentajeAdmin] = useState<number>(10);
  const [cotizacionActual, setCotizacionActual] =
    useState<RespuestaDesgloseCotizacion | null>(null);
  const [cargandoCotizacion, setCargandoCotizacion] = useState<boolean>(false);

  // Estados para emisión de prefactura
  const [clientes, setClientes] = useState<UsuarioSistema[]>([]);
  const [puestos, setPuestos] = useState<PuestoVigilancia[]>([]);
  const [clienteSeleccionadoId, setClienteSeleccionadoId] = useState<number>(0);
  const [puestoSeleccionadoId, setPuestoSeleccionadoId] = useState<number>(0);
  const [mesServicio, setMesServicio] = useState<string>("2026-10");
  const [notasComerciales, setNotasComerciales] = useState<string>("");
  const [emitirCargando, setEmitirCargando] = useState<boolean>(false);

  // Lista de prefacturas
  const [prefacturas, setPrefacturas] = useState<PrefacturaB2B[]>([]);
  const [cargandoLista, setCargandoLista] = useState<boolean>(false);
  const [mensajeEstado, setMensajeEstado] = useState<{
    tipo: "exito" | "error";
    texto: string;
  } | null>(null);

  // Cargar simulación inicial
  useEffect(() => {
    ejecutarSimulacion(modalidad, cantidadPuestos, porcentajeAdmin);
  }, [modalidad, cantidadPuestos, porcentajeAdmin]);

  // Cargar clientes, puestos y prefacturas
  useEffect(() => {
    cargarDatosIniciales();
  }, []);

  async function ejecutarSimulacion(
    mod: ModalidadServicioTarifa,
    cant: number,
    pct: number
  ) {
    setCargandoCotizacion(true);
    try {
      const resultado = await servicioCotizarTarifa({
        modalidad_servicio: mod,
        cantidad_puestos: cant,
        porcentaje_administracion: pct / 100,
      });
      setCotizacionActual(resultado);
    } catch (err) {
      console.error("Error al cotizar tarifa:", err);
    } finally {
      setCargandoCotizacion(false);
    }
  }

  async function cargarDatosIniciales() {
    setCargandoLista(true);
    try {
      const [listaPrefacturas, listaPuestos] = await Promise.all([
        servicioListarPrefacturas(),
        servicioListarPuestos(),
      ]);
      setPrefacturas(listaPrefacturas);
      setPuestos(listaPuestos);

      if (esAdminORrhh) {
        const todosUsuarios = await servicioListarUsuarios();
        const soloClientes = todosUsuarios.filter((u) => u.rol === "CLIENTE");
        setClientes(soloClientes);
        if (soloClientes.length > 0) {
          setClienteSeleccionadoId(soloClientes[0].usuario_id);
        }
      }
    } catch (err) {
      console.error("Error al cargar datos de facturación:", err);
    } finally {
      setCargandoLista(false);
    }
  }

  async function handleEmitirPrefactura(e: React.FormEvent) {
    e.preventDefault();
    if (!clienteSeleccionadoId) {
      setMensajeEstado({
        tipo: "error",
        texto: "Debe seleccionar un cliente destinatario.",
      });
      return;
    }

    setEmitirCargando(true);
    setMensajeEstado(null);
    try {
      const nueva = await servicioGenerarPrefactura({
        cliente_id: clienteSeleccionadoId,
        puesto_id: puestoSeleccionadoId > 0 ? puestoSeleccionadoId : null,
        mes_servicio: mesServicio,
        modalidad_servicio: modalidad,
        cantidad_puestos: cantidadPuestos,
        porcentaje_administracion: porcentajeAdmin / 100,
        notas_comerciales: notasComerciales || undefined,
      });

      setPrefacturas([nueva, ...prefacturas]);
      setMensajeEstado({
        tipo: "exito",
        texto: `Prefactura ${nueva.codigo_factura} emitida exitosamente con sello SHA-256.`,
      });
    } catch (err) {
      setMensajeEstado({
        tipo: "error",
        texto: `Fallo al emitir prefactura: ${extraerMensajeError(err)}`,
      });
    } finally {
      setEmitirCargando(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Encabezado Táctico */}
      <div className="bg-slate-900 border border-emerald-500/30 rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full">
                FASE 8 • ENTERPRISE V3.0
              </span>
              <span className="text-xs text-slate-400 font-mono">
                REGULACIÓN SUPERVIGILANCIA COLOMBIA
              </span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span className="text-emerald-400">§</span> Tarificación Legal & Facturación B2B
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Motor de tarifas mínimas obligatorias según circular SuperVigilancia, Ley 1920/2018 (Vigilante), Ley 2101/2021 (42h) y DIAN Art. 462-1.
            </p>
          </div>
          <button
            onClick={cargarDatosIniciales}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-mono font-semibold transition"
          >
            ↻ Actualizar Historial
          </button>
        </div>
      </div>

      {/* Alerta de notificación */}
      {mensajeEstado && (
        <div
          className={`p-4 rounded-lg border text-sm font-medium flex items-center justify-between ${
            mensajeEstado.tipo === "exito"
              ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300"
              : "bg-rose-950/40 border-rose-500/40 text-rose-300"
          }`}
        >
          <span>{mensajeEstado.texto}</span>
          <button
            onClick={() => setMensajeEstado(null)}
            className="text-xs underline hover:no-underline ml-4"
          >
            Cerrar
          </button>
        </div>
      )}

      {/* Panel Principal: Simulador Tarifario vs Resumen */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Columna Izquierda: Parámetros del Cotizador (5 columnas) */}
        <div className="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2 border-b border-slate-800 pb-3">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Parámetros del Puesto Regulado
          </h3>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1.5">
              MODALIDAD DE SERVICIO
            </label>
            <select
              value={modalidad}
              onChange={(e) =>
                setModalidad(e.target.value as ModalidadServicioTarifa)
              }
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="VIGILANCIA_24H_ARMADA">
                Vigilancia 24 Horas Armada (4 Guardas 2x2)
              </option>
              <option value="VIGILANCIA_24H_SIN_ARMA">
                Vigilancia 24 Horas Sin Arma (4 Guardas 2x2)
              </option>
              <option value="VIGILANCIA_12H_DIURNA">
                Vigilancia 12 Horas Diurna (2 Guardas)
              </option>
              <option value="VIGILANCIA_12H_NOCTURNA">
                Vigilancia 12 Horas Nocturna (2 Guardas)
              </option>
              <option value="SUPERVISION_MOTORIZADA">
                Supervisión Móvil / Patrulla (1 Supervisor)
              </option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1.5">
                CANTIDAD PUESTOS
              </label>
              <input
                type="number"
                min={1}
                max={50}
                value={cantidadPuestos}
                onChange={(e) =>
                  setCantidadPuestos(Math.max(1, parseInt(e.target.value) || 1))
                }
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1.5">
                % AIU ADMIN (MÍN 8%-10%)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={8}
                  max={25}
                  value={porcentajeAdmin}
                  onChange={(e) =>
                    setPorcentajeAdmin(
                      Math.max(8, parseInt(e.target.value) || 10)
                    )
                  }
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                />
                <span className="text-xs text-slate-400 font-mono">%</span>
              </div>
            </div>
          </div>

          {/* Formulario de Emisión B2B (Solo Administrador / RRHH) */}
          {esAdminORrhh && (
            <form
              onSubmit={handleEmitirPrefactura}
              className="mt-6 pt-5 border-t border-slate-800 space-y-3"
            >
              <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                Emitir Prefactura Oficial al Cliente
              </h4>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  CLIENTE DESTINATARIO
                </label>
                <select
                  value={clienteSeleccionadoId}
                  onChange={(e) =>
                    setClienteSeleccionadoId(parseInt(e.target.value) || 0)
                  }
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  {clientes.map((c) => (
                    <option key={c.usuario_id} value={c.usuario_id}>
                      {c.nombre_completo} (NIT/CC: {c.documento_identidad})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    PUESTO ESPECÍFICO
                  </label>
                  <select
                    value={puestoSeleccionadoId}
                    onChange={(e) =>
                      setPuestoSeleccionadoId(parseInt(e.target.value) || 0)
                    }
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value={0}>Todos / Consolidado</option>
                    {puestos.map((p) => (
                      <option key={p.puesto_id} value={p.puesto_id}>
                        {p.nombre_puesto}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    MES SERVICIO
                  </label>
                  <input
                    type="month"
                    value={mesServicio}
                    onChange={(e) => setMesServicio(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  NOTAS / ACUERDOS COMERCIALES
                </label>
                <input
                  type="text"
                  placeholder="Ej: Facturación con dotación balística y canina"
                  value={notasComerciales}
                  onChange={(e) => setNotasComerciales(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <button
                type="submit"
                disabled={emitirCargando}
                className="w-full mt-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-lg transition shadow-md shadow-emerald-950/50"
              >
                {emitirCargando ? "Generando..." : "Emitir Prefactura B2B (SHA-256)"}
              </button>
            </form>
          )}
        </div>

        {/* Columna Derecha: Tarjeta de Liquidación Visual y Rubros Legales (7 columnas) */}
        <div className="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center border-b border-slate-800 pb-3 mb-4">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-sky-400" />
                Desglose Analítico Regulado (SuperVigilancia)
              </h3>
              {cargandoCotizacion && (
                <span className="text-xs text-emerald-400 font-mono animate-pulse">
                  Calculando...
                </span>
              )}
            </div>

            {cotizacionActual ? (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-3 bg-slate-950/60 p-3.5 rounded-lg border border-slate-800/80">
                  <div>
                    <span className="text-[10px] font-mono text-slate-400 uppercase block">
                      Dotación Cuadrilla
                    </span>
                    <span className="text-base font-bold text-slate-100">
                      {cotizacionActual.guardas_por_puesto} Guardas / Puesto
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-slate-400 uppercase block">
                      Total Guardas
                    </span>
                    <span className="text-base font-bold text-emerald-400">
                      {cotizacionActual.total_guardas_requeridos} Efectivos
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] font-mono text-slate-400 uppercase block">
                      Costo Unitario Guarda
                    </span>
                    <span className="text-base font-bold text-sky-400">
                      ${cotizacionActual.costo_laboral_unitario_guarda.toLocaleString("es-CO", { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                    <span className="text-slate-400">
                      Mano de Obra (SMLMV + Auxilio + Prestaciones + ARL Riesgo V + Seguro Ley 1920):
                    </span>
                    <span className="font-mono text-slate-200 font-semibold">
                      ${cotizacionActual.costo_mano_obra_total.toLocaleString("es-CO", { minimumFractionDigits: 2 })} COP
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                    <span className="text-slate-400">
                      Armamento, Munición y Equipos Balísticos (Recargo Legal Indumil):
                    </span>
                    <span className="font-mono text-slate-200 font-semibold">
                      ${cotizacionActual.costo_armamento_y_equipos.toLocaleString("es-CO", { minimumFractionDigits: 2 })} COP
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                    <span className="text-slate-400">
                      Gastos de Administración e Intermediación (AIU {porcentajeAdmin}%):
                    </span>
                    <span className="font-mono text-slate-200 font-semibold">
                      ${cotizacionActual.costo_administracion_aiu.toLocaleString("es-CO", { minimumFractionDigits: 2 })} COP
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                    <span className="text-slate-400">
                      Subtotal Operativo Antes de Impuestos:
                    </span>
                    <span className="font-mono text-slate-200 font-semibold">
                      ${cotizacionActual.subtotal_antes_iva.toLocaleString("es-CO", { minimumFractionDigits: 2 })} COP
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                    <span className="text-slate-400">
                      IVA Especial DIAN (19% sobre base de AIU - Art. 462-1 E.T.):
                    </span>
                    <span className="font-mono text-sky-400 font-semibold">
                      ${cotizacionActual.iva_dian.toLocaleString("es-CO", { minimumFractionDigits: 2 })} COP
                    </span>
                  </div>
                </div>

                {/* Gran Total */}
                <div className="bg-emerald-950/20 border border-emerald-500/30 rounded-lg p-4 flex justify-between items-center">
                  <div>
                    <span className="text-xs font-mono text-emerald-400 uppercase tracking-wider block">
                      Tarifa Mensual Mínima Legal
                    </span>
                    <span className="text-xs text-slate-400">
                      Incluye nómina completa, armas, AIU e impuestos DIAN
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-bold font-mono text-emerald-300">
                      ${cotizacionActual.tarifa_total_factura_cop.toLocaleString("es-CO", { minimumFractionDigits: 2 })}
                    </span>
                    <span className="text-xs text-emerald-500 block font-mono">
                      COP / MES
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-slate-500 text-xs font-mono">
                Cargando desglose tarifario regulado...
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-500 flex items-center justify-between">
            <span>Base de cálculo: Jornada máxima 42 horas/semana (Ley 2101).</span>
            <span className="text-emerald-500 font-mono">✓ VIGILADO SUPERVIGILANCIA</span>
          </div>
        </div>
      </div>

      {/* Historial de Prefacturas Emitidas */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex justify-between items-center border-b border-slate-800 pb-3">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-400" />
            Registro y Auditoría de Prefacturas B2B
          </h3>
          <span className="text-xs font-mono text-slate-400">
            Total Emitidas: {prefacturas.length}
          </span>
        </div>

        {cargandoLista ? (
          <div className="p-6 text-center text-slate-500 font-mono text-xs">
            Cargando historial de prefacturación...
          </div>
        ) : prefacturas.length === 0 ? (
          <div className="p-8 text-center text-slate-500 border border-dashed border-slate-800 rounded-lg text-xs font-mono">
            No se han emitido prefacturas en el período seleccionado.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Código</th>
                  <th className="py-2.5 px-3">Cliente Contratante</th>
                  <th className="py-2.5 px-3">Puesto / Período</th>
                  <th className="py-2.5 px-3">Modalidad</th>
                  <th className="py-2.5 px-3 text-right">Subtotal</th>
                  <th className="py-2.5 px-3 text-right">Total Factura</th>
                  <th className="py-2.5 px-3 text-center">Estado</th>
                  <th className="py-2.5 px-3 text-center">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {prefacturas.map((pf) => (
                  <tr key={pf.prefactura_id} className="hover:bg-slate-800/40 transition">
                    <td className="py-2.5 px-3 font-bold text-sky-400">
                      {pf.codigo_factura}
                    </td>
                    <td className="py-2.5 px-3 font-sans text-slate-200">
                      {pf.nombre_cliente}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">
                      {pf.nombre_puesto ?? "Consolidado"} ({pf.mes_servicio})
                    </td>
                    <td className="py-2.5 px-3 text-slate-300">
                      {pf.modalidad_servicio.replace("VIGILANCIA_", "").replace("_", " ")}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-400">
                      ${pf.subtotal_cop.toLocaleString("es-CO", { maximumFractionDigits: 0 })}
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-emerald-400">
                      ${pf.total_factura_cop.toLocaleString("es-CO", { maximumFractionDigits: 0 })}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        {pf.estado_factura}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <button
                        onClick={() => servicioAbrirPrefacturaHtml(pf.prefactura_id)}
                        className="px-2.5 py-1 bg-sky-600 hover:bg-sky-500 text-white rounded text-[11px] font-sans font-semibold transition shadow"
                      >
                        📄 Foliado Oficial
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

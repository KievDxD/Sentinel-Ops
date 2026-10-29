/**
 * Módulo 3 (Enterprise V2.0): Minuta Digital en Tiempo Real (WebSockets) con Visibilidad Dual.
 * Soporta:
 * - Clasificación de visibilidad (`PUBLICA_CLIENTE` vs `INTERNA_OPERATIVA`).
 * - Modo de Solo Lectura Filtrado para el rol `CLIENTE` (vinculado a su puesto contratado).
 * - Visualización de eventos de Acta de Entrega/Recibo de Puesto (`ENTREGA_RECIBO_PUESTO`) y
 *   Alertas de Pánico SOS (`ALERTA_PANICO_SOS`).
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactElement,
} from "react";
import { useForm } from "react-hook-form";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  Radio,
  Send,
  Car,
  UserCheck,
  ShieldAlert,
  Footprints,
  Clock,
  AlertTriangle,
  Eye,
  EyeOff,
  ClipboardCheck,
  Siren,
  FileCheck2,
} from "lucide-react";
import {
  URL_WEBSOCKET_MINUTA,
  extraerMensajeError,
  servicioAbrirActaRelevoHtml,
  servicioAbrirLibroFoliadoOficial,
  servicioCrearRegistroMinuta,
  servicioListarMinuta,
  servicioListarPuestos,
} from "../servicios/cliente_api";
import { usarAlmacenAutenticacion } from "../estado/almacen_autenticacion";
import type {
  CrearRegistroMinutaFormulario,
  MensajeWebSocketMinuta,
  PuestoVigilancia,
  RegistroMinuta,
} from "../tipos/tipos_sistema";

export function ModuloMinutaTiempoReal(): ReactElement {
  const usuarioActual = usarAlmacenAutenticacion(
    (estado) => estado.usuarioActual
  );
  const [registros, setRegistros] = useState<RegistroMinuta[]>([]);
  const [puestos, setPuestos] = useState<PuestoVigilancia[]>([]);
  const [wsConectado, setWsConectado] = useState<boolean>(false);
  const [mensajeError, setMensajeError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState<boolean>(false);
  const socketRef = useRef<WebSocket | null>(null);

  const esCliente = usuarioActual?.rol === "CLIENTE";

  const { register, handleSubmit, reset, watch, setValue } =
    useForm<CrearRegistroMinutaFormulario>({
      defaultValues: {
        tipo_registro: "INGRESO_VISITANTE",
        visibilidad: "PUBLICA_CLIENTE",
        nivel_prioridad: "MEDIA",
        puesto_id: usuarioActual?.puesto_base_id ?? undefined,
      },
    });

  const tipoSeleccionado = watch("tipo_registro");

  const cargarDatosIniciales = useCallback(async (): Promise<void> => {
    try {
      const [listaMinuta, listaPuestos] = await Promise.all([
        servicioListarMinuta(
          esCliente && usuarioActual?.puesto_base_id
            ? usuarioActual.puesto_base_id
            : undefined
        ),
        servicioListarPuestos(),
      ]);
      setRegistros(listaMinuta);
      setPuestos(listaPuestos);

      if (usuarioActual?.puesto_base_id) {
        setValue("puesto_id", usuarioActual.puesto_base_id);
      } else if (listaPuestos.length > 0) {
        setValue("puesto_id", listaPuestos[0].puesto_id);
      }
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    }
  }, [esCliente, usuarioActual?.puesto_base_id, setValue]);

  useEffect((): (() => void) => {
    void cargarDatosIniciales();

    const socket = new WebSocket(URL_WEBSOCKET_MINUTA);
    socketRef.current = socket;

    socket.onopen = (): void => {
      setWsConectado(true);
    };

    socket.onmessage = (evento: MessageEvent<string>): void => {
      try {
        const datos = JSON.parse(evento.data) as MensajeWebSocketMinuta;
        if (
          (datos.tipo_mensaje === "NUEVO_REGISTRO_MINUTA" ||
            datos.tipo_mensaje === "ALERTA_PANICO_SOS" ||
            datos.tipo_mensaje === "SOS_ATENDIDO") &&
          datos.registro !== undefined
        ) {
          const nuevo = datos.registro;
          if (esCliente) {
            if (nuevo.visibilidad === "INTERNA_OPERATIVA") return;
            if (
              usuarioActual?.puesto_base_id &&
              nuevo.puesto_id !== usuarioActual.puesto_base_id
            ) {
              return;
            }
          }
          setRegistros((previos) => {
            if (previos.some((r) => r.registro_id === nuevo.registro_id)) {
              return previos;
            }
            return [nuevo, ...previos];
          });
        }
      } catch {
        // Ignorar tramas no válidas
      }
    };

    socket.onclose = (): void => {
      setWsConectado(false);
    };

    socket.onerror = (): void => {
      setWsConectado(false);
    };

    const intervaloLatido = window.setInterval((): void => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send("LATIDO");
      }
    }, 25000);

    return (): void => {
      window.clearInterval(intervaloLatido);
      socket.close();
    };
  }, [cargarDatosIniciales, esCliente, usuarioActual?.puesto_base_id]);

  const registrarEnMinuta = async (
    datos: CrearRegistroMinutaFormulario
  ): Promise<void> => {
    setEnviando(true);
    setMensajeError(null);
    try {
      const creado = await servicioCrearRegistroMinuta({
        ...datos,
        puesto_id: Number(datos.puesto_id),
      });
      setRegistros((previos) => {
        if (previos.some((r) => r.registro_id === creado.registro_id)) {
          return previos;
        }
        return [creado, ...previos];
      });
      reset({
        puesto_id: Number(datos.puesto_id),
        tipo_registro: datos.tipo_registro,
        visibilidad: datos.visibilidad ?? "PUBLICA_CLIENTE",
        nivel_prioridad: "MEDIA",
        titulo_evento: "",
        descripcion_detallada: "",
        nombre_visitante: "",
        documento_visitante: "",
        placa_vehiculo: "",
      });
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
      {/* Formulario de Registro Táctico (Oculto para CLIENTE por ser Consola Solo Lectura) */}
      {!esCliente && (
        <section className="xl:col-span-5 rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl h-fit">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-2.5">
              <Send className="h-5 w-5 text-emerald-400" />
              <h2 className="text-lg font-bold text-white">
                Asentar Anotación en Minuta
              </h2>
            </div>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${
                wsConectado
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : "border-amber-500/40 bg-amber-500/10 text-amber-300"
              }`}
            >
              <Radio
                className={`h-3.5 w-3.5 ${wsConectado ? "animate-pulse" : ""}`}
              />
              {wsConectado ? "WebSocket En Vivo" : "Modo REST Activo"}
            </span>
          </div>

          {mensajeError && (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-200">
              <AlertTriangle className="h-4 w-4 text-rose-400 shrink-0" />
              <span>{mensajeError}</span>
            </div>
          )}

          <form
            onSubmit={(e): void => {
              void handleSubmit(registrarEnMinuta)(e);
            }}
            className="mt-5 space-y-4"
          >
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
                Puesto de Vigilancia
              </label>
              <select
                {...register("puesto_id", { required: true })}
                className="w-full rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
              >
                {puestos.map((p) => (
                  <option key={p.puesto_id} value={p.puesto_id}>
                    {p.codigo_puesto} - {p.nombre_puesto}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
                  Categoría del Evento
                </label>
                <select
                  {...register("tipo_registro", { required: true })}
                  className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-white"
                >
                  <option value="INGRESO_VISITANTE">Ingreso de Visitante</option>
                  <option value="INGRESO_VEHICULO">Ingreso de Vehículo</option>
                  <option value="RONDA_CONTROL">Ronda de Control</option>
                  <option value="NOVEDAD_INCIDENTE">Novedad / Incidente</option>
                  <option value="RELEVO_TURNO">Relevo de Turno</option>
                  <option value="ENTREGA_RECIBO_PUESTO">
                    Entrega / Recibo de Puesto
                  </option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
                  Nivel de Prioridad
                </label>
                <select
                  {...register("nivel_prioridad", { required: true })}
                  className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-white"
                >
                  <option value="BAJA">BAJA (Rutinario)</option>
                  <option value="MEDIA">MEDIA (Seguimiento)</option>
                  <option value="ALTA">ALTA (Atención Inmediata)</option>
                  <option value="CRITICA">CRÍTICA (Alerta Táctica)</option>
                </select>
              </div>
            </div>

            {/* Selector de Visibilidad Dual (3.4) */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-cyan-300 mb-1">
                Visibilidad de la Anotación (RBAC Cliente)
              </label>
              <select
                {...register("visibilidad", { required: true })}
                className="w-full rounded-xl border border-cyan-500/30 bg-slate-950 px-3 py-2.5 text-xs font-bold text-white"
              >
                <option value="PUBLICA_CLIENTE">
                  PUBLICA_CLIENTE — Visible en Consola del Cliente Contratante
                </option>
                <option value="INTERNA_OPERATIVA">
                  INTERNA_OPERATIVA — Confidencial (Solo Supervisores / Admin / RRHH)
                </option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
                Título / Resumen de la Novedad
              </label>
              <input
                {...register("titulo_evento", { required: true })}
                placeholder="Ej. Ingreso de proveedor técnico / Ronda perimetral"
                className="w-full rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
              />
            </div>

            {(tipoSeleccionado === "INGRESO_VISITANTE" ||
              tipoSeleccionado === "INGRESO_VEHICULO") && (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 rounded-xl border border-white/10 bg-slate-950/60 p-3">
                <input
                  {...register("nombre_visitante")}
                  placeholder="Nombre visitante"
                  className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white"
                />
                <input
                  {...register("documento_visitante")}
                  placeholder="Cédula / NIT"
                  className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white"
                />
                <input
                  {...register("placa_vehiculo")}
                  placeholder="Placa (ej. KLM-890)"
                  className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white uppercase"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
                Descripción Detallada en Libro Digital
              </label>
              <textarea
                rows={3}
                {...register("descripcion_detallada", { required: true })}
                placeholder="Describe detalladamente la novedad, elementos verificados o autorización..."
                className="w-full rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2.5 text-sm text-white"
              />
            </div>

            <button
              type="submit"
              disabled={enviando}
              className="boton-tactico-campo w-full rounded-xl bg-emerald-500 py-3 text-xs font-bold uppercase tracking-wider text-slate-950 shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-400 disabled:opacity-50"
            >
              {enviando
                ? "Transmitiendo Evento..."
                : "Registrar y Transmitir en Vivo"}
            </button>
          </form>
        </section>
      )}

      {/* Flujo en Tiempo Real de la Minuta Digital */}
      <section
        className={`${
          esCliente ? "xl:col-span-12" : "xl:col-span-7"
        } rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl`}
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
          <div>
            <h2 className="text-lg font-bold text-white">
              {esCliente
                ? "Bitácora Corporativa de Minuta (Filtrada para Cliente)"
                : "Bitácora de Minuta Digital en Vivo (Visibilidad Dual)"}
            </h2>
            <p className="text-xs text-slate-400">
              {esCliente
                ? "Visualización en tiempo real de eventos públicos de su puesto contratado"
                : "Actualización instantánea vía WebSocket con clasificación PUBLICA_CLIENTE / INTERNA_OPERATIVA"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {esCliente && (
              <button
                type="button"
                onClick={(): void => {
                  void servicioAbrirLibroFoliadoOficial();
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500 px-3 py-1.5 text-xs font-bold text-slate-950"
              >
                <FileCheck2 className="h-4 w-4" />
                <span>Exportar Libro Foliado SHA-256</span>
              </button>
            )}
            <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300">
              {registros.length} Folios
            </span>
          </div>
        </div>

        <div className="mt-4 space-y-4 max-h-[620px] overflow-y-auto pr-1">
          {registros.map((item) => (
            <article
              key={item.registro_id}
              className="rounded-xl border border-white/10 bg-slate-950/70 p-4 transition hover:border-emerald-500/30"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {item.tipo_registro === "INGRESO_VEHICULO" && (
                    <Car className="h-4 w-4 text-cyan-400" />
                  )}
                  {item.tipo_registro === "INGRESO_VISITANTE" && (
                    <UserCheck className="h-4 w-4 text-emerald-400" />
                  )}
                  {item.tipo_registro === "RONDA_CONTROL" && (
                    <Footprints className="h-4 w-4 text-amber-400" />
                  )}
                  {item.tipo_registro === "NOVEDAD_INCIDENTE" && (
                    <ShieldAlert className="h-4 w-4 text-rose-400" />
                  )}
                  {item.tipo_registro === "RELEVO_TURNO" && (
                    <Clock className="h-4 w-4 text-indigo-400" />
                  )}
                  {item.tipo_registro === "ENTREGA_RECIBO_PUESTO" && (
                    <ClipboardCheck className="h-4 w-4 text-emerald-400" />
                  )}
                  {item.tipo_registro === "ALERTA_PANICO_SOS" && (
                    <Siren className="h-4 w-4 text-rose-500 animate-bounce" />
                  )}
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    {item.tipo_registro.replace(/_/g, " ")}
                  </span>
                  <span className="rounded bg-white/10 px-2 py-0.5 font-mono text-[11px] text-cyan-300">
                    {item.codigo_puesto}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] font-bold ${
                      item.visibilidad === "INTERNA_OPERATIVA"
                        ? "border-purple-500/40 bg-purple-500/15 text-purple-300"
                        : "border-sky-500/40 bg-sky-500/15 text-sky-300"
                    }`}
                  >
                    {item.visibilidad === "INTERNA_OPERATIVA" ? (
                      <EyeOff className="h-3 w-3" />
                    ) : (
                      <Eye className="h-3 w-3" />
                    )}
                    {item.visibilidad ?? "PUBLICA_CLIENTE"}
                  </span>

                  <span
                    className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase ${
                      item.nivel_prioridad === "CRITICA"
                        ? "border-rose-500/50 bg-rose-500/20 text-rose-200"
                        : item.nivel_prioridad === "ALTA"
                          ? "border-amber-500/50 bg-amber-500/20 text-amber-200"
                          : item.nivel_prioridad === "MEDIA"
                            ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-300"
                            : "border-slate-600 bg-slate-800 text-slate-300"
                    }`}
                  >
                    {item.nivel_prioridad}
                  </span>
                  <span className="font-mono text-xs text-slate-400">
                    {format(new Date(item.fecha_registro), "dd MMM HH:mm:ss", {
                      locale: es,
                    })}
                  </span>
                </div>
              </div>

              <h3 className="mt-2 text-base font-bold text-white">
                {item.titulo_evento}
              </h3>
              <p className="mt-1 text-sm text-slate-300">
                {item.descripcion_detallada}
              </p>

              {(item.nombre_visitante ||
                item.documento_visitante ||
                item.placa_vehiculo) && (
                <div className="mt-3 flex flex-wrap gap-3 rounded-lg border border-white/5 bg-slate-900/80 px-3 py-2 text-xs text-slate-300">
                  {item.nombre_visitante && (
                    <span>
                      Visitante:{" "}
                      <strong className="text-white">
                        {item.nombre_visitante}
                      </strong>
                    </span>
                  )}
                  {item.documento_visitante && (
                    <span>
                      Doc:{" "}
                      <strong className="font-mono text-white">
                        {item.documento_visitante}
                      </strong>
                    </span>
                  )}
                  {item.placa_vehiculo && (
                    <span>
                      Placa:{" "}
                      <strong className="rounded bg-amber-500/20 px-1.5 py-0.5 font-mono text-amber-300">
                        {item.placa_vehiculo}
                      </strong>
                    </span>
                  )}
                </div>
              )}

              <div className="mt-3 flex items-center justify-between border-t border-white/5 pt-2 text-xs text-slate-400">
                <span>
                  Reportado por:{" "}
                  <strong className="text-slate-200">
                    {item.nombre_operador}
                  </strong>{" "}
                  ({item.codigo_placa_operador})
                </span>
                <div className="flex items-center gap-2">
                  <span>{item.nombre_puesto}</span>
                  {item.tipo_registro === "ENTREGA_RECIBO_PUESTO" && (
                    <button
                      type="button"
                      onClick={(): void => {
                        void servicioAbrirActaRelevoHtml(1);
                      }}
                      className="inline-flex items-center gap-1 rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-300 hover:bg-emerald-500/20"
                    >
                      <FileCheck2 className="h-3 w-3" />
                      <span>Acta Foliada</span>
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

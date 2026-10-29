/**
 * Módulo 2 (Enterprise V2.0): Motor Inteligente de Turnos 2x2 (2 Día, 2 Noche, 2 Descanso)
 * con Liquidación Automática según Ley 2101 de 2021 (Tope 42h semanales en 2026),
 * Motor de Ausentismos (EPS/ARL/Licencia/Falta) con descuento automático en nómina,
 * y Motor Inteligente de Sugerencia de Relevos ("Relevantes") en 1 Clic.
 */

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactElement,
} from "react";
import { useForm } from "react-hook-form";
import { format, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import {
  CalendarClock,
  Sun,
  Moon,
  Coffee,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Building2,
  Shield,
  Users,
  Grid3X3,
  ListFilter,
  UserMinus,
  UserCheck,
} from "lucide-react";
import {
  extraerMensajeError,
  servicioAsignarRelevanteTurno,
  servicioConsultarTurnos,
  servicioGenerarCoberturaPuesto2x2,
  servicioGenerarRotacion2x2,
  servicioListarAusentismos,
  servicioListarPuestos,
  servicioListarUsuarios,
  servicioRegistrarAusentismo,
  servicioSugerirRelevantesTurno,
} from "../servicios/cliente_api";
import { usarAlmacenAutenticacion } from "../estado/almacen_autenticacion";
import type {
  AusentismoPersonal,
  CandidatoRelevanteSugerido,
  PuestoVigilancia,
  RegistrarAusentismoFormulario,
  ResumenLiquidacionTurnos,
  SolicitudGenerarRotacion2x2,
  TipoAusentismo,
  TurnoOperativo,
  UsuarioSistema,
} from "../tipos/tipos_sistema";

function formatearPesosColombianos(valor: number): string {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(valor);
}

export function ModuloMotorTurnos(): ReactElement {
  const usuarioActual = usarAlmacenAutenticacion(
    (estado) => estado.usuarioActual
  );
  const [resumenTurnos, setResumenTurnos] =
    useState<ResumenLiquidacionTurnos | null>(null);
  const [operadores, setOperadores] = useState<UsuarioSistema[]>([]);
  const [puestos, setPuestos] = useState<PuestoVigilancia[]>([]);
  const [ausentismos, setAusentismos] = useState<AusentismoPersonal[]>([]);
  const [filtroOperadorId, setFiltroOperadorId] = useState<number>(0);
  const [filtroPuestoId, setFiltroPuestoId] = useState<number>(0);
  const [cargando, setCargando] = useState<boolean>(true);
  const [mensajeExito, setMensajeExito] = useState<string | null>(null);
  const [mensajeError, setMensajeError] = useState<string | null>(null);

  const [pestanaActiva, setPestanaActiva] = useState<
    "MALLA_VISUAL" | "TABLA_DETALLE"
  >("MALLA_VISUAL");

  const [modoProgramacion, setModoProgramacion] = useState<
    "COBERTURA_PUESTO_24_7" | "INDIVIDUAL" | "AUSENTISMOS_Y_RELEVANTES"
  >("COBERTURA_PUESTO_24_7");

  const [puestoCoberturaId, setPuestoCoberturaId] = useState<number>(0);
  const [cuadrilla1Id, setCuadrilla1Id] = useState<number>(0);
  const [cuadrilla2Id, setCuadrilla2Id] = useState<number>(0);
  const [cuadrilla3Id, setCuadrilla3Id] = useState<number>(0);
  const [fechaInicioCobertura, setFechaInicioCobertura] = useState<string>(
    format(new Date(), "yyyy-MM-dd")
  );
  const [diasCobertura, setDiasCobertura] = useState<number>(30);
  const [generandoCobertura, setGenerandoCobertura] = useState<boolean>(false);

  // Estado para Ausentismos y Motor de Relevantes (3.3)
  const [operadorAusenteId, setOperadorAusenteId] = useState<number>(0);
  const [turnoAfectadoId, setTurnoAfectadoId] = useState<number>(0);
  const [tipoAusentismo, setTipoAusentismo] =
    useState<TipoAusentismo>("INCAPACIDAD_EPS");
  const [horasDescuento, setHorasDescuento] = useState<number>(12);
  const [soporteAusentismo, setSoporteAusentismo] = useState<string>(
    "Incapacidad médica EPS certificada por 12 horas de turno operativo."
  );
  const [registrandoAusentismo, setRegistrandoAusentismo] =
    useState<boolean>(false);

  const [turnoParaRelevoId, setTurnoParaRelevoId] = useState<number | null>(
    null
  );
  const [candidatosRelevantes, setCandidatosRelevantes] = useState<
    CandidatoRelevanteSugerido[]
  >([]);
  const [buscandoRelevantes, setBuscandoRelevantes] = useState<boolean>(false);
  const [asignandoRelevanteId, setAsignandoRelevanteId] = useState<
    number | null
  >(null);

  const hoyTexto = format(new Date(), "yyyy-MM-dd");

  const formularioIndividual = useForm<SolicitudGenerarRotacion2x2>({
    defaultValues: {
      fecha_inicio_ciclo: hoyTexto,
      cantidad_ciclos_6_dias: 2,
      reemplazar_existentes: true,
    },
  });

  const cargarDatosMotor = useCallback(
    async (operadorFiltro: number, puestoFiltro: number): Promise<void> => {
      setCargando(true);
      try {
        const idOperadorEfectivo =
          usuarioActual?.rol === "OPERADOR"
            ? usuarioActual.usuario_id
            : operadorFiltro > 0
              ? operadorFiltro
              : undefined;

        const [datosTurnos, listaUsuarios, listaPuestos, listaAusentismos] =
          await Promise.all([
            servicioConsultarTurnos(
              idOperadorEfectivo,
              puestoFiltro > 0 ? puestoFiltro : undefined
            ),
            servicioListarUsuarios(),
            servicioListarPuestos(),
            servicioListarAusentismos(),
          ]);
        setResumenTurnos(datosTurnos);
        const listaOperadores = listaUsuarios.filter(
          (u) => u.rol === "OPERADOR"
        );
        setOperadores(listaOperadores);
        setPuestos(listaPuestos);
        setAusentismos(listaAusentismos);

        if (listaOperadores.length > 0 && operadorAusenteId === 0) {
          setOperadorAusenteId(listaOperadores[0].usuario_id);
        }

        if (
          listaPuestos.length > 0 &&
          puestoFiltro === 0 &&
          puestoCoberturaId === 0
        ) {
          const primerPuesto = listaPuestos[0];
          setPuestoCoberturaId(primerPuesto.puesto_id);

          const guardiasPuesto = listaOperadores.filter(
            (o) => o.puesto_base_id === primerPuesto.puesto_id
          );
          if (guardiasPuesto.length >= 3) {
            setCuadrilla1Id(guardiasPuesto[0].usuario_id);
            setCuadrilla2Id(guardiasPuesto[1].usuario_id);
            setCuadrilla3Id(guardiasPuesto[2].usuario_id);
          } else if (listaOperadores.length >= 3) {
            setCuadrilla1Id(listaOperadores[0].usuario_id);
            setCuadrilla2Id(listaOperadores[1].usuario_id);
            setCuadrilla3Id(listaOperadores[2].usuario_id);
          }
        }
      } catch (errorCapturado: unknown) {
        setMensajeError(extraerMensajeError(errorCapturado));
      } finally {
        setCargando(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [usuarioActual?.rol, usuarioActual?.usuario_id]
  );

  useEffect((): void => {
    void cargarDatosMotor(filtroOperadorId, filtroPuestoId);
  }, [cargarDatosMotor, filtroOperadorId, filtroPuestoId]);

  const manejarCambioPuestoCobertura = (puestoId: number): void => {
    setPuestoCoberturaId(puestoId);
    const guardiasPuesto = operadores.filter(
      (o) => o.puesto_base_id === puestoId
    );
    if (guardiasPuesto.length >= 3) {
      setCuadrilla1Id(guardiasPuesto[0].usuario_id);
      setCuadrilla2Id(guardiasPuesto[1].usuario_id);
      setCuadrilla3Id(guardiasPuesto[2].usuario_id);
    }
  };

  const ejecutarGenerarCoberturaContinua = async (
    e: React.FormEvent
  ): Promise<void> => {
    e.preventDefault();
    setMensajeError(null);
    setMensajeExito(null);

    if (!puestoCoberturaId) {
      setMensajeError("Debe seleccionar un puesto de vigilancia.");
      return;
    }

    const unicos = new Set([cuadrilla1Id, cuadrilla2Id, cuadrilla3Id]);
    if (unicos.size < 3 || !cuadrilla1Id || !cuadrilla2Id || !cuadrilla3Id) {
      setMensajeError(
        "Las 3 cuadrillas deben tener guardas diferentes con credencial SuperVigilancia vigente."
      );
      return;
    }

    setGenerandoCobertura(true);
    try {
      const resultado = await servicioGenerarCoberturaPuesto2x2({
        puesto_id: puestoCoberturaId,
        operadores_ids: [cuadrilla1Id, cuadrilla2Id, cuadrilla3Id],
        fecha_inicio_ciclo: fechaInicioCobertura,
        cantidad_dias: Number(diasCobertura),
        reemplazar_existentes: true,
      });
      setResumenTurnos(resultado);
      setFiltroPuestoId(puestoCoberturaId);
      const puestoObj = puestos.find((p) => p.puesto_id === puestoCoberturaId);
      setMensajeExito(
        `¡Cobertura 24/7 generada exitosamente para ${puestoObj?.codigo_puesto ?? "Puesto"} por ${diasCobertura} días con tope semanal de ${resultado.tope_horas_semanales_aplicado ?? 42}h (Ley 2101)!`
      );
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    } finally {
      setGenerandoCobertura(false);
    }
  };

  const ejecutarGenerador2x2Individual = async (
    datos: SolicitudGenerarRotacion2x2
  ): Promise<void> => {
    setMensajeError(null);
    setMensajeExito(null);
    try {
      const resultado = await servicioGenerarRotacion2x2({
        operador_id: Number(datos.operador_id),
        puesto_id: Number(datos.puesto_id),
        fecha_inicio_ciclo: datos.fecha_inicio_ciclo,
        cantidad_ciclos_6_dias: Number(datos.cantidad_ciclos_6_dias),
        reemplazar_existentes: Boolean(datos.reemplazar_existentes),
      });
      setResumenTurnos(resultado);
      setFiltroOperadorId(Number(datos.operador_id));
      setMensajeExito(
        `Se generó el esquema rotativo 2x2 individual con tope semanal de ${resultado.tope_horas_semanales_aplicado ?? 42}h (Ley 2101).`
      );
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    }
  };

  const manejarRegistrarAusentismo = async (
    e: React.FormEvent
  ): Promise<void> => {
    e.preventDefault();
    if (!operadorAusenteId) return;
    setRegistrandoAusentismo(true);
    setMensajeError(null);
    setMensajeExito(null);
    try {
      const payload: RegistrarAusentismoFormulario = {
        operador_id: operadorAusenteId,
        turno_afectado_id: turnoAfectadoId > 0 ? turnoAfectadoId : null,
        tipo_ausentismo: tipoAusentismo,
        fecha_inicio: hoyTexto,
        fecha_fin: hoyTexto,
        horas_descontadas: Number(horasDescuento),
        descripcion_soporte: soporteAusentismo,
      };
      const creado = await servicioRegistrarAusentismo(payload);
      setMensajeExito(
        `Ausentismo (${creado.tipo_ausentismo}) registrado para ${creado.nombre_operador}. Se descontaron ${creado.horas_descontadas}h de prenómina y el turno quedó en estado DESCUBIERTO_PARCIAL.`
      );
      await cargarDatosMotor(filtroOperadorId, filtroPuestoId);
      if (creado.turno_afectado_id) {
        await consultarCandidatosRelevantes(creado.turno_afectado_id);
      }
    } catch (err: unknown) {
      setMensajeError(extraerMensajeError(err));
    } finally {
      setRegistrandoAusentismo(false);
    }
  };

  const consultarCandidatosRelevantes = async (
    turnoId: number
  ): Promise<void> => {
    setTurnoParaRelevoId(turnoId);
    setBuscandoRelevantes(true);
    setMensajeError(null);
    try {
      const sugeridos = await servicioSugerirRelevantesTurno(turnoId);
      setCandidatosRelevantes(sugeridos);
    } catch (err: unknown) {
      setMensajeError(extraerMensajeError(err));
    } finally {
      setBuscandoRelevantes(false);
    }
  };

  const asignarRelevanteEnUnClic = async (
    turnoId: number,
    operadorReemplazoId: number
  ): Promise<void> => {
    setAsignandoRelevanteId(operadorReemplazoId);
    setMensajeError(null);
    setMensajeExito(null);
    try {
      const turnoActualizado = await servicioAsignarRelevanteTurno(turnoId, {
        operador_reemplazo_id: operadorReemplazoId,
        observacion_asignacion:
          "Reasignado en 1 clic por Motor Inteligente de Relevantes",
      });
      setMensajeExito(
        `¡Relevo exitoso en 1 clic! El Turno #${turnoActualizado.turno_id} ahora está cubierto por ${turnoActualizado.nombre_operador} (${turnoActualizado.codigo_placa_operador}) y se notificó en vivo por WebSocket.`
      );
      setTurnoParaRelevoId(null);
      setCandidatosRelevantes([]);
      await cargarDatosMotor(filtroOperadorId, filtroPuestoId);
    } catch (err: unknown) {
      setMensajeError(extraerMensajeError(err));
    } finally {
      setAsignandoRelevanteId(null);
    }
  };

  const puedeProgramar =
    usuarioActual?.rol === "ADMINISTRADOR" ||
    usuarioActual?.rol === "SUPERVISOR" ||
    usuarioActual?.rol === "RRHH";

  const turnosFiltrados = resumenTurnos?.turnos ?? [];

  const turnosOperativosDelOperadorAusente = useMemo(() => {
    return turnosFiltrados.filter(
      (t) =>
        t.operador_id === operadorAusenteId && t.tipo_turno !== "DESCANSO"
    );
  }, [operadorAusenteId, turnosFiltrados]);

  const diasUnicosMalla = useMemo(() => {
    const mapaFechas = new Map<string, Date>();
    for (const t of turnosFiltrados) {
      const claveFecha = format(new Date(t.fecha_inicio), "yyyy-MM-dd");
      if (!mapaFechas.has(claveFecha)) {
        mapaFechas.set(claveFecha, parseISO(claveFecha));
      }
    }
    return Array.from(mapaFechas.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([clave, fecha]) => ({ clave, fecha }));
  }, [turnosFiltrados]);

  const guardiasMalla = useMemo(() => {
    const mapaGuardias = new Map<
      number,
      { operador_id: number; nombre: string; placa: string }
    >();
    for (const t of turnosFiltrados) {
      if (!mapaGuardias.has(t.operador_id)) {
        mapaGuardias.set(t.operador_id, {
          operador_id: t.operador_id,
          nombre: t.nombre_operador,
          placa: t.codigo_placa_operador,
        });
      }
    }
    return Array.from(mapaGuardias.values());
  }, [turnosFiltrados]);

  const mapaTurnosMalla = useMemo(() => {
    const mapa = new Map<string, TurnoOperativo>();
    for (const t of turnosFiltrados) {
      const claveFecha = format(new Date(t.fecha_inicio), "yyyy-MM-dd");
      mapa.set(`${t.operador_id}_${claveFecha}`, t);
    }
    return mapa;
  }, [turnosFiltrados]);

  return (
    <div className="space-y-6">
      {/* Indicadores consolidados de Normativa Laboral Colombiana (Ley 2101 - 42h semanales) */}
      {resumenTurnos && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-4 backdrop-blur-xl">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Total Turnos (12h)
            </span>
            <p className="mt-1 text-2xl font-bold text-white">
              {resumenTurnos.total_turnos_operativos}
            </p>
            <span className="text-xs text-emerald-400">
              {resumenTurnos.suma_horas_trabajadas}h efectivas
            </span>
          </div>

          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-950/15 p-4 backdrop-blur-xl">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-300">
              Tope Ley 2101 (2026)
            </span>
            <p className="mt-1 text-2xl font-bold text-white">
              {resumenTurnos.tope_horas_semanales_aplicado ?? 42}h / sem
            </p>
            <span className="text-xs text-emerald-400">
              Ord: {resumenTurnos.suma_horas_ordinarias}h
            </span>
          </div>

          <div className="rounded-2xl border border-indigo-500/20 bg-indigo-950/20 p-4 backdrop-blur-xl">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-300">
              Recargo Nocturno (35%)
            </span>
            <p className="mt-1 text-2xl font-bold text-indigo-200">
              {resumenTurnos.suma_horas_recargo_nocturno}h
            </p>
            <span className="text-xs text-indigo-300/80">
              Franja 21:00 - 06:00
            </span>
          </div>

          <div className="rounded-2xl border border-amber-500/20 bg-amber-950/20 p-4 backdrop-blur-xl">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-300">
              Extras (+25% / +75%)
            </span>
            <p className="mt-1 text-2xl font-bold text-amber-200">
              {(
                resumenTurnos.suma_horas_extras_diurnas +
                resumenTurnos.suma_horas_extras_nocturnas
              ).toFixed(1)}
              h
            </p>
            <span className="text-xs text-amber-300/80">
              Diu: {resumenTurnos.suma_horas_extras_diurnas}h • Noc:{" "}
              {resumenTurnos.suma_horas_extras_nocturnas}h
            </span>
          </div>

          <div className="rounded-2xl border border-rose-500/20 bg-rose-950/20 p-4 backdrop-blur-xl">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-rose-300">
              Desc. Ausentismos
            </span>
            <p className="mt-1 text-2xl font-bold text-rose-200">
              {resumenTurnos.suma_horas_descuento_ausentismo ?? 0}h
            </p>
            <span className="text-xs text-rose-300/80">
              EPS / ARL / Licencias
            </span>
          </div>

          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/25 p-4 backdrop-blur-xl">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-300">
              Liquidación Nómina COP
            </span>
            <p className="mt-1 text-xl font-bold text-emerald-300">
              {formatearPesosColombianos(
                resumenTurnos.costo_total_estimado_cop
              )}
            </p>
            <span className="text-xs text-emerald-400/80">
              Dom/Fest: {resumenTurnos.suma_horas_dominicales_festivas}h
            </span>
          </div>
        </div>
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

      {/* Programador Automático 2x2 + Motor de Ausentismos y Relevantes (3.3) */}
      {puedeProgramar && (
        <section className="rounded-2xl border border-emerald-500/20 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-emerald-400">
              <Sparkles className="h-4 w-4" />
              <span>
                Motor Táctico 2x2, Ausentismos EPS/ARL y Sugerencia de Relevantes
              </span>
            </div>

            <div className="inline-flex flex-wrap rounded-xl bg-slate-950 p-1 border border-white/10 gap-1">
              <button
                type="button"
                onClick={(): void =>
                  setModoProgramacion("COBERTURA_PUESTO_24_7")
                }
                className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  modoProgramacion === "COBERTURA_PUESTO_24_7"
                    ? "bg-emerald-500 text-slate-950 shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Shield className="h-3.5 w-3.5" />
                Cobertura 24/7 Puesto
              </button>
              <button
                type="button"
                onClick={(): void => setModoProgramacion("INDIVIDUAL")}
                className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  modoProgramacion === "INDIVIDUAL"
                    ? "bg-emerald-500 text-slate-950 shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Users className="h-3.5 w-3.5" />
                Rotación Individual
              </button>
              <button
                type="button"
                onClick={(): void =>
                  setModoProgramacion("AUSENTISMOS_Y_RELEVANTES")
                }
                className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  modoProgramacion === "AUSENTISMOS_Y_RELEVANTES"
                    ? "bg-amber-400 text-slate-950 shadow"
                    : "text-amber-300 hover:text-white"
                }`}
              >
                <UserMinus className="h-3.5 w-3.5" />
                Ausentismos & Relevantes (1-Clic)
              </button>
            </div>
          </div>

          {modoProgramacion === "COBERTURA_PUESTO_24_7" && (
            <form
              onSubmit={(e): void => void ejecutarGenerarCoberturaContinua(e)}
              className="mt-5 space-y-4"
            >
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Puesto de Vigilancia a Proteger
                  </label>
                  <select
                    value={puestoCoberturaId}
                    onChange={(e): void =>
                      manejarCambioPuestoCobertura(Number(e.target.value))
                    }
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white"
                    required
                  >
                    {puestos.map((p) => (
                      <option key={p.puesto_id} value={p.puesto_id}>
                        {p.codigo_puesto} - {p.nombre_puesto}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Fecha de Inicio Cobertura
                  </label>
                  <input
                    type="date"
                    value={fechaInicioCobertura}
                    onChange={(e): void =>
                      setFechaInicioCobertura(e.target.value)
                    }
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Extensión de Cobertura
                  </label>
                  <select
                    value={diasCobertura}
                    onChange={(e): void =>
                      setDiasCobertura(Number(e.target.value))
                    }
                    className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white"
                  >
                    <option value={6}>6 Días (1 Ciclo Completo 2x2)</option>
                    <option value={12}>12 Días (2 Ciclos 2x2)</option>
                    <option value={30}>30 Días (Mes Operativo Completo)</option>
                  </select>
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Asignación de las 3 Cuadrillas (Valida Credencial SuperVigilancia):
                </span>
                <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
                  <div>
                    <label className="block text-[11px] text-amber-300 mb-1 font-medium">
                      Cuadrilla 1 (Inicia Día 1 Diurno)
                    </label>
                    <select
                      value={cuadrilla1Id}
                      onChange={(e): void =>
                        setCuadrilla1Id(Number(e.target.value))
                      }
                      className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white"
                      required
                    >
                      <option value={0}>-- Seleccionar Guarda 1 --</option>
                      {operadores.map((op) => (
                        <option key={op.usuario_id} value={op.usuario_id}>
                          {op.nombre_completo} ({op.codigo_placa})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] text-indigo-300 mb-1 font-medium">
                      Cuadrilla 2 (Inicia Día 3 Diurno)
                    </label>
                    <select
                      value={cuadrilla2Id}
                      onChange={(e): void =>
                        setCuadrilla2Id(Number(e.target.value))
                      }
                      className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white"
                      required
                    >
                      <option value={0}>-- Seleccionar Guarda 2 --</option>
                      {operadores.map((op) => (
                        <option key={op.usuario_id} value={op.usuario_id}>
                          {op.nombre_completo} ({op.codigo_placa})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] text-slate-300 mb-1 font-medium">
                      Cuadrilla 3 (Inicia Día 5 Diurno)
                    </label>
                    <select
                      value={cuadrilla3Id}
                      onChange={(e): void =>
                        setCuadrilla3Id(Number(e.target.value))
                      }
                      className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white"
                      required
                    >
                      <option value={0}>-- Seleccionar Guarda 3 --</option>
                      {operadores.map((op) => (
                        <option key={op.usuario_id} value={op.usuario_id}>
                          {op.nombre_completo} ({op.codigo_placa})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={generandoCobertura}
                className="boton-tactico-campo w-full rounded-xl bg-emerald-500 py-3 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:bg-emerald-400 disabled:opacity-50"
              >
                {generandoCobertura
                  ? "Verificando Credenciales SV y Calculando Matriz..."
                  : `Generar Cobertura Continua 24/7 (${diasCobertura} Días — Tope 42h Ley 2101)`}
              </button>
            </form>
          )}

          {modoProgramacion === "INDIVIDUAL" && (
            <form
              onSubmit={(e): void => {
                void formularioIndividual.handleSubmit(
                  ejecutarGenerador2x2Individual
                )(e);
              }}
              className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-5 items-end"
            >
              <div>
                <label className="block text-xs text-slate-400 mb-1">
                  Operador (Guarda)
                </label>
                <select
                  {...formularioIndividual.register("operador_id", {
                    required: true,
                  })}
                  className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-white"
                >
                  {operadores.map((op) => (
                    <option key={op.usuario_id} value={op.usuario_id}>
                      {op.nombre_completo} ({op.codigo_placa})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">
                  Puesto Asignado
                </label>
                <select
                  {...formularioIndividual.register("puesto_id", {
                    required: true,
                  })}
                  className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-white"
                >
                  {puestos.map((p) => (
                    <option key={p.puesto_id} value={p.puesto_id}>
                      {p.codigo_puesto} - {p.nombre_puesto}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">
                  Fecha Inicio Ciclo
                </label>
                <input
                  type="date"
                  {...formularioIndividual.register("fecha_inicio_ciclo", {
                    required: true,
                  })}
                  className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm text-white"
                />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">
                  Ciclos de 6 Días
                </label>
                <select
                  {...formularioIndividual.register("cantidad_ciclos_6_dias", {
                    required: true,
                  })}
                  className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2.5 text-sm text-white"
                >
                  <option value={1}>1 Ciclo (6 días)</option>
                  <option value={2}>2 Ciclos (12 días)</option>
                  <option value={5}>5 Ciclos (30 días - Mes)</option>
                </select>
              </div>

              <button
                type="submit"
                className="boton-tactico-campo rounded-xl bg-emerald-500 px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:bg-emerald-400"
              >
                Calcular y Programar
              </button>
            </form>
          )}

          {/* MODO 3: MOTOR DE AUSENTISMOS Y SUGERENCIA INTELIGENTE DE RELEVANTES (3.3) */}
          {modoProgramacion === "AUSENTISMOS_Y_RELEVANTES" && (
            <div className="mt-5 grid grid-cols-1 gap-6 lg:grid-cols-12">
              <form
                onSubmit={(e): void => void manejarRegistrarAusentismo(e)}
                className="lg:col-span-6 space-y-3 rounded-xl border border-amber-500/30 bg-slate-950/80 p-4"
              >
                <h3 className="text-xs font-black uppercase tracking-wider text-amber-300">
                  1. Registrar Ausentismo y Descontar de Prenómina
                </h3>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-300 mb-1">
                      Guarda Ausente
                    </label>
                    <select
                      value={operadorAusenteId}
                      onChange={(e): void => {
                        setOperadorAusenteId(Number(e.target.value));
                        setTurnoAfectadoId(0);
                      }}
                      className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white"
                    >
                      {operadores.map((op) => (
                        <option key={op.usuario_id} value={op.usuario_id}>
                          {op.nombre_completo} ({op.codigo_placa})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-300 mb-1">
                      Turno Afectado (Quedará DESCUBIERTO_PARCIAL)
                    </label>
                    <select
                      value={turnoAfectadoId}
                      onChange={(e): void =>
                        setTurnoAfectadoId(Number(e.target.value))
                      }
                      className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white"
                    >
                      <option value={0}>
                        -- Seleccionar Turno Operativo --
                      </option>
                      {turnosOperativosDelOperadorAusente
                        .slice(0, 15)
                        .map((t) => (
                          <option key={t.turno_id} value={t.turno_id}>
                            #{t.turno_id} • {t.tipo_turno} (
                            {format(new Date(t.fecha_inicio), "dd MMM HH:mm")})
                          </option>
                        ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-300 mb-1">
                      Tipo de Ausentismo
                    </label>
                    <select
                      value={tipoAusentismo}
                      onChange={(e): void =>
                        setTipoAusentismo(e.target.value as TipoAusentismo)
                      }
                      className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white"
                    >
                      <option value="INCAPACIDAD_EPS">Incapacidad EPS</option>
                      <option value="INCAPACIDAD_ARL">
                        Incapacidad ARL (Laboral)
                      </option>
                      <option value="LICENCIA_REMUNERADA">
                        Licencia / Calamidad
                      </option>
                      <option value="FALTA_INJUSTIFICADA">
                        Falta Injustificada
                      </option>
                      <option value="ABANDONO_PUESTO">
                        Abandono de Puesto
                      </option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-300 mb-1">
                      Horas a Descontar del Turno
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={12}
                      value={horasDescuento}
                      onChange={(e): void =>
                        setHorasDescuento(Number(e.target.value))
                      }
                      className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white font-mono"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">
                    Soporte Documental / Observación RRHH
                  </label>
                  <input
                    type="text"
                    value={soporteAusentismo}
                    onChange={(e): void => setSoporteAusentismo(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-xs text-white"
                  />
                </div>

                <button
                  type="submit"
                  disabled={registrandoAusentismo}
                  className="boton-tactico-campo w-full rounded-xl bg-amber-400 py-2.5 text-xs font-black uppercase text-slate-950 hover:bg-amber-300 transition"
                >
                  {registrandoAusentismo
                    ? "Procesando Descuento en Nómina..."
                    : "Registrar Ausentismo y Buscar Guardas Relevantes"}
                </button>
              </form>

              {/* Panel de Sugerencia Inteligente de Relevantes en 1 Clic */}
              <div className="lg:col-span-6 rounded-xl border border-cyan-500/30 bg-slate-950/80 p-4 flex flex-col justify-between">
                <div>
                  <h3 className="text-xs font-black uppercase tracking-wider text-cyan-300">
                    2. Motor Inteligente de Relevantes (Ordenado por Menor Carga
                    de Horas Extras)
                  </h3>
                  <p className="mt-1 text-[11px] text-slate-400">
                    Filtra guardas activos con credencial SuperVigilancia
                    vigente, en día de descanso (&gt;= 12h previas libres) y
                    menor costo de horas extras en la semana.
                  </p>

                  {buscandoRelevantes ? (
                    <p className="py-6 text-center text-xs text-cyan-300">
                      Analizando disponibilidad 2x2, descanso &gt;=12h y
                      credenciales SV...
                    </p>
                  ) : candidatosRelevantes.length > 0 && turnoParaRelevoId ? (
                    <div className="mt-3 space-y-2 max-h-56 overflow-y-auto">
                      {candidatosRelevantes.map((cand) => (
                        <div
                          key={cand.usuario_id}
                          className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-slate-900 p-2.5 text-xs"
                        >
                          <div>
                            <div className="font-bold text-white">
                              {cand.nombre_completo}{" "}
                              <span className="font-mono text-emerald-400">
                                ({cand.codigo_placa})
                              </span>
                            </div>
                            <div className="text-[11px] text-slate-400">
                              Extras semana:{" "}
                              <strong className="text-amber-300">
                                {cand.horas_extras_acumuladas_semana}h
                              </strong>{" "}
                              • Descanso previo: {cand.horas_descanso_previas}h
                            </div>
                            <span className="text-[10px] font-bold text-cyan-300">
                              {cand.puntaje_idoneidad}
                            </span>
                          </div>
                          <button
                            type="button"
                            disabled={asignandoRelevanteId === cand.usuario_id}
                            onClick={(): void => {
                              void asignarRelevanteEnUnClic(
                                turnoParaRelevoId,
                                cand.usuario_id
                              );
                            }}
                            className="inline-flex items-center gap-1 rounded-lg bg-emerald-500 px-3 py-1.5 text-[11px] font-black text-slate-950 hover:bg-emerald-400 shrink-0"
                          >
                            <UserCheck className="h-3.5 w-3.5" />
                            <span>Reasignar 1-Clic</span>
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-4 space-y-2">
                      <span className="text-[11px] font-bold text-slate-300 block">
                        Historial de Ausentismos Registrados (
                        {ausentismos.length}):
                      </span>
                      {ausentismos.slice(0, 3).map((aus) => (
                        <div
                          key={aus.ausentismo_id}
                          className="flex items-center justify-between rounded-lg border border-white/5 bg-slate-900/70 p-2 text-xs"
                        >
                          <div>
                            <strong className="text-white">
                              {aus.nombre_operador}
                            </strong>{" "}
                            •{" "}
                            <span className="text-rose-300 font-semibold">
                              {aus.tipo_ausentismo} (-{aus.horas_descontadas}h)
                            </span>
                          </div>
                          {aus.turno_afectado_id && (
                            <button
                              type="button"
                              onClick={(): void => {
                                void consultarCandidatosRelevantes(
                                  aus.turno_afectado_id as number
                                );
                              }}
                              className="rounded bg-cyan-500/20 border border-cyan-500/40 px-2 py-1 text-[10px] font-bold text-cyan-300 hover:bg-cyan-500/30"
                            >
                              Sugerir Relevantes Turno #{aus.turno_afectado_id}
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Programación Táctica: Malla Visual 2x2 y Tabla Detallada */}
      <section className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <CalendarClock className="h-5 w-5 text-emerald-400" />
            <div>
              <h2 className="text-lg font-bold text-white">
                {usuarioActual?.rol === "OPERADOR"
                  ? `Mi Programación Personal de Turnos 2x2 (${usuarioActual.nombre_completo})`
                  : "Programación Operativa de Turnos 2x2 (Ley 2101 — 42h Semanales)"}
              </h2>
              <p className="text-xs text-slate-400">
                Rotación: 2 Día (06:00-18:00) • 2 Noche (18:00-06:00) • 2
                Descanso (Franco 24h)
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {usuarioActual?.rol !== "OPERADOR" && (
              <>
                <div className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-slate-950 px-2.5 py-1">
                  <Building2 className="h-3.5 w-3.5 text-cyan-400" />
                  <select
                    value={filtroPuestoId}
                    onChange={(e): void =>
                      setFiltroPuestoId(Number(e.target.value))
                    }
                    className="bg-transparent text-xs text-slate-200 focus:outline-none"
                  >
                    <option value={0} className="bg-slate-950 text-white">
                      Todos los Puestos
                    </option>
                    {puestos.map((p) => (
                      <option
                        key={p.puesto_id}
                        value={p.puesto_id}
                        className="bg-slate-950 text-white"
                      >
                        Puesto: {p.codigo_puesto} - {p.nombre_puesto}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-slate-950 px-2.5 py-1">
                  <Users className="h-3.5 w-3.5 text-emerald-400" />
                  <select
                    value={filtroOperadorId}
                    onChange={(e): void =>
                      setFiltroOperadorId(Number(e.target.value))
                    }
                    className="bg-transparent text-xs text-slate-200 focus:outline-none"
                  >
                    <option value={0} className="bg-slate-950 text-white">
                      Todos los Guardas
                    </option>
                    {operadores.map((op) => (
                      <option
                        key={op.usuario_id}
                        value={op.usuario_id}
                        className="bg-slate-950 text-white"
                      >
                        {op.nombre_completo} ({op.codigo_placa})
                      </option>
                    ))}
                  </select>
                </div>
              </>
            )}

            <div className="inline-flex rounded-xl bg-slate-950 p-1 border border-white/10">
              <button
                type="button"
                onClick={(): void => setPestanaActiva("MALLA_VISUAL")}
                className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                  pestanaActiva === "MALLA_VISUAL"
                    ? "bg-cyan-500 text-slate-950"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Grid3X3 className="h-3.5 w-3.5" />
                Malla 2x2
              </button>
              <button
                type="button"
                onClick={(): void => setPestanaActiva("TABLA_DETALLE")}
                className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                  pestanaActiva === "TABLA_DETALLE"
                    ? "bg-cyan-500 text-slate-950"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <ListFilter className="h-3.5 w-3.5" />
                Detalle Legal & Relevos
              </button>
            </div>
          </div>
        </div>

        {cargando ? (
          <p className="py-10 text-center text-sm text-slate-400">
            Calculando matriz de turnos y recargos laborales...
          </p>
        ) : turnosFiltrados.length === 0 ? (
          <div className="py-12 text-center text-slate-400">
            <CalendarClock className="h-10 w-10 mx-auto text-slate-600 mb-2" />
            <p className="font-semibold text-slate-300">
              No hay turnos registrados con los filtros seleccionados.
            </p>
          </div>
        ) : pestanaActiva === "MALLA_VISUAL" ? (
          <div className="mt-5 space-y-4">
            <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-950/60">
              <table className="w-full text-left text-xs whitespace-nowrap">
                <thead>
                  <tr className="border-b border-white/10 bg-slate-900/80 text-slate-300 font-semibold">
                    <th className="py-3 px-3.5 sticky left-0 z-10 bg-slate-900 shadow-md min-w-[200px]">
                      Guarda Asignado
                    </th>
                    {diasUnicosMalla.slice(0, 30).map(({ clave, fecha }) => {
                      const esDomingo = fecha.getDay() === 0;
                      return (
                        <th
                          key={clave}
                          className={`py-2 px-2 text-center min-w-[58px] ${
                            esDomingo ? "bg-rose-950/30 text-rose-300" : ""
                          }`}
                        >
                          <div className="text-[10px] uppercase font-mono text-slate-400">
                            {format(fecha, "EEE", { locale: es })}
                          </div>
                          <div className="font-bold text-white text-xs">
                            {format(fecha, "dd MMM", { locale: es })}
                          </div>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {guardiasMalla.map((guardia) => (
                    <tr
                      key={guardia.operador_id}
                      className="hover:bg-white/[0.02]"
                    >
                      <td className="py-3 px-3.5 sticky left-0 z-10 bg-slate-950 font-medium text-white shadow-md">
                        <div>{guardia.nombre}</div>
                        <span className="font-mono text-[11px] text-emerald-400 font-normal">
                          {guardia.placa}
                        </span>
                      </td>

                      {diasUnicosMalla.slice(0, 30).map(({ clave, fecha }) => {
                        const turno = mapaTurnosMalla.get(
                          `${guardia.operador_id}_${clave}`
                        );
                        const esDomingo = fecha.getDay() === 0;

                        if (!turno) {
                          return (
                            <td
                              key={clave}
                              className={`py-2 px-2 text-center text-slate-600 ${
                                esDomingo ? "bg-rose-950/10" : ""
                              }`}
                            >
                              -
                            </td>
                          );
                        }

                        if (turno.estado_turno === "DESCUBIERTO_PARCIAL") {
                          return (
                            <td key={clave} className="py-2 px-2 text-center">
                              <button
                                type="button"
                                onClick={(): void => {
                                  setModoProgramacion(
                                    "AUSENTISMOS_Y_RELEVANTES"
                                  );
                                  void consultarCandidatosRelevantes(
                                    turno.turno_id
                                  );
                                }}
                                className="inline-flex flex-col items-center justify-center rounded-lg border border-rose-500 bg-rose-500/20 px-2 py-1 text-[10px] font-black text-rose-200"
                              >
                                <span>AUSENTE</span>
                                <span className="text-[9px]">Relevar</span>
                              </button>
                            </td>
                          );
                        }

                        if (turno.tipo_turno === "DIURNO") {
                          return (
                            <td
                              key={clave}
                              className={`py-2 px-2 text-center ${
                                esDomingo ? "bg-rose-950/10" : ""
                              }`}
                            >
                              <span className="inline-flex flex-col items-center justify-center rounded-lg border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[11px] font-bold text-amber-300">
                                <span>D (12h)</span>
                                <span className="text-[9px] font-mono opacity-80">
                                  06-18
                                </span>
                              </span>
                            </td>
                          );
                        }

                        if (turno.tipo_turno === "NOCTURNO") {
                          return (
                            <td
                              key={clave}
                              className={`py-2 px-2 text-center ${
                                esDomingo ? "bg-rose-950/10" : ""
                              }`}
                            >
                              <span className="inline-flex flex-col items-center justify-center rounded-lg border border-indigo-500/40 bg-indigo-500/10 px-2 py-1 text-[11px] font-bold text-indigo-300">
                                <span>N (12h)</span>
                                <span className="text-[9px] font-mono opacity-80">
                                  18-06
                                </span>
                              </span>
                            </td>
                          );
                        }

                        return (
                          <td
                            key={clave}
                            className={`py-2 px-2 text-center ${
                              esDomingo ? "bg-rose-950/10" : ""
                            }`}
                          >
                            <span className="inline-flex flex-col items-center justify-center rounded-lg border border-slate-700 bg-slate-800/80 px-2 py-1 text-[11px] font-semibold text-slate-400">
                              <span>X (24h)</span>
                              <span className="text-[9px] font-mono opacity-70">
                                Franco
                              </span>
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 uppercase">
                  <th className="py-3 px-3">ID / Esquema</th>
                  <th className="py-3 px-3">Operador</th>
                  <th className="py-3 px-3">Puesto</th>
                  <th className="py-3 px-3">Horario</th>
                  <th className="py-3 px-3 text-right">Ord. (42h)</th>
                  <th className="py-3 px-3 text-right">Rec. Noc.</th>
                  <th className="py-3 px-3 text-right">Ext. Diu/Noc</th>
                  <th className="py-3 px-3 text-right">Desc. Ausent.</th>
                  <th className="py-3 px-3 text-right">Costo COP</th>
                  {puedeProgramar && (
                    <th className="py-3 px-3 text-center">Acción Relevo</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {turnosFiltrados.map((turno) => (
                  <tr
                    key={turno.turno_id}
                    className="hover:bg-white/[0.02] transition"
                  >
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        {turno.tipo_turno === "DIURNO" && (
                          <span className="inline-flex items-center gap-1 rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 font-bold text-amber-300">
                            <Sun className="h-3.5 w-3.5" /> DIURNO
                          </span>
                        )}
                        {turno.tipo_turno === "NOCTURNO" && (
                          <span className="inline-flex items-center gap-1 rounded-md border border-indigo-500/40 bg-indigo-500/10 px-2 py-0.5 font-bold text-indigo-300">
                            <Moon className="h-3.5 w-3.5" /> NOCTURNO
                          </span>
                        )}
                        {turno.tipo_turno === "DESCANSO" && (
                          <span className="inline-flex items-center gap-1 rounded-md border border-slate-600 bg-slate-800 px-2 py-0.5 font-bold text-slate-300">
                            <Coffee className="h-3.5 w-3.5" /> FRANCO
                          </span>
                        )}
                        <span className="font-mono text-slate-500">
                          #{turno.turno_id}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-3 font-medium text-white">
                      {turno.nombre_operador}{" "}
                      <span className="font-mono text-emerald-400">
                        ({turno.codigo_placa_operador})
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-300">
                      <span className="font-mono text-cyan-300">
                        {turno.codigo_puesto}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-200">
                      {format(new Date(turno.fecha_inicio), "dd MMM HH:mm", {
                        locale: es,
                      })}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-slate-200">
                      {turno.tipo_turno === "DESCANSO"
                        ? "-"
                        : `${turno.horas_ordinarias}h`}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-indigo-300">
                      {turno.tipo_turno === "DESCANSO"
                        ? "-"
                        : `${turno.horas_recargo_nocturno}h`}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-amber-300">
                      {turno.tipo_turno === "DESCANSO"
                        ? "-"
                        : `${turno.horas_extras_diurnas + turno.horas_extras_nocturnas}h`}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-rose-300">
                      {turno.horas_descuento_ausentismo &&
                      turno.horas_descuento_ausentismo > 0
                        ? `-${turno.horas_descuento_ausentismo}h (${turno.motivo_ausentismo ?? "AUS"})`
                        : "0h"}
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-emerald-300">
                      {turno.tipo_turno === "DESCANSO"
                        ? "$0"
                        : formatearPesosColombianos(turno.costo_estimado_cop)}
                    </td>
                    {puedeProgramar && (
                      <td className="py-3 px-3 text-center">
                        {turno.tipo_turno !== "DESCANSO" && (
                          <button
                            type="button"
                            onClick={(): void => {
                              setModoProgramacion("AUSENTISMOS_Y_RELEVANTES");
                              void consultarCandidatosRelevantes(
                                turno.turno_id
                              );
                            }}
                            className="rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-2 py-1 text-[10px] font-bold text-cyan-300 hover:bg-cyan-500/20"
                          >
                            Buscar Relevante
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

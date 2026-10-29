/**
 * Portal Táctico de Autenticación y Registro de Usuarios Reales (Módulo 1 - RBAC 5 Niveles y JWT).
 * Permite:
 * 1. Acceso Demo en 1-Click para los 5 roles corporativos (Administrador, Supervisor, RRHH, Operador, Cliente).
 * 2. Iniciar sesión con cualquier usuario registrado.
 * 3. Registrar nuevos integrantes con credencial SuperVigilancia y puesto asignado.
 */

import { useEffect, useState, type ReactElement } from "react";
import { useForm } from "react-hook-form";
import {
  ShieldCheck,
  Lock,
  Mail,
  Activity,
  Database,
  AlertCircle,
  KeyRound,
  UserPlus,
  Phone,
  BadgeAlert,
  Building2,
  ChevronDown,
  ChevronUp,
  Award,
} from "lucide-react";
import {
  extraerMensajeError,
  servicioIniciarSesion,
  servicioListarPuestos,
  servicioRegistrarUsuarioReal,
} from "../servicios/cliente_api";
import { usarAlmacenAutenticacion } from "../estado/almacen_autenticacion";
import type {
  PuestoVigilancia,
  RegistroUsuarioRealFormulario,
  RespuestaEstadoServidor,
  SolicitudInicioSesion,
} from "../tipos/tipos_sistema";

interface PropiedadesVistaAcceso {
  datosEstado: RespuestaEstadoServidor | null;
  estadoConexion: "cargando" | "conectado" | "error";
  alReintentarConexion: () => void;
}

interface CredencialDemostracion {
  etiquetaRol: string;
  subtituloPrioridad: string;
  nombre: string;
  correo: string;
  contrasena: string;
  colorDistintivo: string;
}

const CUENTAS_DEMOSTRACION: CredencialDemostracion[] = [
  {
    etiquetaRol: "ADMINISTRADOR",
    subtituloPrioridad: "Prioridad 1 • Dirección",
    nombre: "Comandante Alejandro Vargas",
    correo: "admin@sentinelops.co",
    contrasena: "Sentinel2026*",
    colorDistintivo: "border-emerald-500/40 bg-emerald-500/15 text-emerald-300",
  },
  {
    etiquetaRol: "SUPERVISOR",
    subtituloPrioridad: "Prioridad 2 • Operaciones",
    nombre: "Capitán Valeria Mendoza",
    correo: "supervisor@sentinelops.co",
    contrasena: "Sentinel2026*",
    colorDistintivo: "border-cyan-500/40 bg-cyan-500/15 text-cyan-300",
  },
  {
    etiquetaRol: "RRHH & NÓMINA",
    subtituloPrioridad: "Prioridad 2.5 • Ley 2101",
    nombre: "Dra. Natalia Gómez (RRH-201)",
    correo: "rrhh@sentinelops.co",
    contrasena: "Sentinel2026*",
    colorDistintivo: "border-purple-500/40 bg-purple-500/15 text-purple-300",
  },
  {
    etiquetaRol: "OPERADOR",
    subtituloPrioridad: "Prioridad 3 • Guarda 2x2",
    nombre: "Guarda Carlos Ramírez (OPR-401)",
    correo: "operador1@sentinelops.co",
    contrasena: "Sentinel2026*",
    colorDistintivo: "border-amber-500/40 bg-amber-500/15 text-amber-300",
  },
  {
    etiquetaRol: "CLIENTE",
    subtituloPrioridad: "Prioridad 4 • PST-BOG-01",
    nombre: "Ing. Roberto Salazar (CLI-901)",
    correo: "cliente@sentinelops.co",
    contrasena: "Sentinel2026*",
    colorDistintivo: "border-sky-500/40 bg-sky-500/15 text-sky-300",
  },
];

type PestanaAcceso = "ingreso" | "registro";

export function VistaAccesoTactico({
  datosEstado,
  estadoConexion,
  alReintentarConexion,
}: PropiedadesVistaAcceso): ReactElement {
  const establecerSesion = usarAlmacenAutenticacion(
    (estado) => estado.establecerSesion
  );

  const [pestanaActiva, setPestanaActiva] = useState<PestanaAcceso>("ingreso");
  const [errorAutenticacion, setErrorAutenticacion] = useState<string | null>(
    null
  );
  const [procesando, setProcesando] = useState<boolean>(false);
  const [puestosDisponibles, setPuestosDisponibles] = useState<
    PuestoVigilancia[]
  >([]);
  const [mostrarDemoCuentas, setMostrarDemoCuentas] = useState<boolean>(true);

  const formularioIngreso = useForm<SolicitudInicioSesion>({
    defaultValues: {
      correo_electronico: "",
      contrasena: "",
    },
  });

  const formularioRegistro = useForm<RegistroUsuarioRealFormulario>({
    defaultValues: {
      rol: "OPERADOR",
      codigo_placa: "",
      nombre_completo: "",
      documento_identidad: "",
      correo_electronico: "",
      telefono: "",
      contrasena: "",
      numero_credencial_sv: "SV-2026-9901",
      fecha_vencimiento_credencial: "2027-08-15",
      nivel_curso: "FUNDAMENTACION",
    },
  });

  useEffect((): void => {
    async function cargarPuestos(): Promise<void> {
      try {
        const lista = await servicioListarPuestos();
        setPuestosDisponibles(lista);
      } catch {
        // Silencioso si el backend apenas está encendiendo
      }
    }
    void cargarPuestos();
  }, []);

  const procesarInicioSesion = async (
    credenciales: SolicitudInicioSesion
  ): Promise<void> => {
    setProcesando(true);
    setErrorAutenticacion(null);
    try {
      const respuesta = await servicioIniciarSesion(credenciales);
      establecerSesion(respuesta);
    } catch (errorCapturado: unknown) {
      setErrorAutenticacion(extraerMensajeError(errorCapturado));
    } finally {
      setProcesando(false);
    }
  };

  const procesarRegistroReal = async (
    datos: RegistroUsuarioRealFormulario
  ): Promise<void> => {
    setProcesando(true);
    setErrorAutenticacion(null);
    try {
      const payload: RegistroUsuarioRealFormulario = {
        ...datos,
        puesto_base_id: datos.puesto_base_id
          ? Number(datos.puesto_base_id)
          : undefined,
      };
      const respuesta = await servicioRegistrarUsuarioReal(payload);
      establecerSesion(respuesta);
    } catch (errorCapturado: unknown) {
      setErrorAutenticacion(extraerMensajeError(errorCapturado));
    } finally {
      setProcesando(false);
    }
  };

  const ingresarConCuentaDemo = async (
    cuenta: CredencialDemostracion
  ): Promise<void> => {
    formularioIngreso.setValue("correo_electronico", cuenta.correo);
    formularioIngreso.setValue("contrasena", cuenta.contrasena);
    setPestanaActiva("ingreso");
    await procesarInicioSesion({
      correo_electronico: cuenta.correo,
      contrasena: cuenta.contrasena,
    });
  };

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <div className="pointer-events-none absolute -top-32 -left-32 h-96 w-96 rounded-full bg-emerald-500/15 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-cyan-500/15 blur-3xl" />

      <div className="relative z-10 grid w-full max-w-6xl grid-cols-1 gap-8 lg:grid-cols-12 items-center">
        {/* Panel Izquierdo: Telemetría del Núcleo y Normativa Colombiana */}
        <section className="lg:col-span-5 flex flex-col justify-between rounded-2xl border border-white/10 bg-slate-900/60 p-8 shadow-2xl backdrop-blur-xl">
          <div>
            <div className="flex items-center justify-between border-b border-white/10 pb-5">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                  <ShieldCheck className="h-7 w-7" />
                </div>
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-[0.25em] text-emerald-400">
                    Enterprise V2.0 • SuperVigilancia
                  </span>
                  <h1 className="text-xl font-bold tracking-tight text-white">
                    SENTINEL <span className="text-emerald-400">//</span> OPS
                  </h1>
                </div>
              </div>

              <button
                type="button"
                onClick={alReintentarConexion}
                className="flex items-center gap-1.5 rounded-full border border-white/10 bg-slate-950/80 px-3 py-1 text-xs hover:border-emerald-500/40"
              >
                <span
                  className={`h-2 w-2 rounded-full ${
                    estadoConexion === "conectado"
                      ? "bg-emerald-400"
                      : estadoConexion === "cargando"
                        ? "bg-amber-400 animate-ping"
                        : "bg-rose-500"
                  }`}
                />
                <span className="text-[11px]">
                  {estadoConexion === "conectado" ? "En Línea" : "Reconectar"}
                </span>
              </button>
            </div>

            <div className="mt-5 space-y-3">
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-3.5">
                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-emerald-300">
                  <Activity className="h-3.5 w-3.5" />
                  <span>Estado del Servidor & Ley 2101</span>
                </div>
                <p className="mt-1 text-sm font-semibold text-white">
                  {datosEstado?.estado ?? "Verificando enlace con FastAPI..."} •{" "}
                  Tope {datosEstado?.tope_horas_semanales_ley_2101 ?? 42}h/sem
                </p>
              </div>

              <div className="rounded-xl border border-white/10 bg-slate-950/50 p-3.5">
                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-cyan-300">
                  <Database className="h-3.5 w-3.5" />
                  <span>Motor de Persistencia</span>
                </div>
                <p className="mt-1 text-xs font-medium text-slate-200">
                  {datosEstado?.motor_base_datos ??
                    "PostgreSQL 15 / SQLite Asíncrono"}
                </p>
              </div>

              <div className="rounded-xl border border-white/10 bg-slate-950/50 p-3.5">
                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-amber-300">
                  <Building2 className="h-3.5 w-3.5" />
                  <span>Puestos con Armamento Indumil</span>
                </div>
                <p className="mt-1 text-xs font-medium text-slate-200">
                  {puestosDisponibles.length > 0
                    ? `${puestosDisponibles.length} Instalaciones con Cobertura 24/7 y Acta SHA-256`
                    : "Cargando instalaciones..."}
                </p>
              </div>
            </div>

            {/* Cuentas de Demostración Colapsables (5 Roles) */}
            <div className="mt-6 border-t border-white/10 pt-4">
              <button
                type="button"
                onClick={(): void => setMostrarDemoCuentas((prev) => !prev)}
                className="flex w-full items-center justify-between text-xs font-semibold text-slate-400 hover:text-slate-200"
              >
                <span>Jerarquía RBAC de 5 Niveles (1-Click Demo)</span>
                {mostrarDemoCuentas ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </button>

              {mostrarDemoCuentas && (
                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {CUENTAS_DEMOSTRACION.map((cuenta) => (
                    <button
                      key={cuenta.correo}
                      type="button"
                      disabled={procesando}
                      onClick={(): void => {
                        void ingresarConCuentaDemo(cuenta);
                      }}
                      className="flex flex-col items-start rounded-lg border border-white/10 bg-slate-950/70 p-2.5 text-left hover:border-emerald-500/40 transition"
                    >
                      <div className="flex items-center justify-between w-full">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${cuenta.colorDistintivo}`}
                        >
                          {cuenta.etiquetaRol}
                        </span>
                        <span className="text-[9px] text-slate-400 font-mono">
                          {cuenta.subtituloPrioridad}
                        </span>
                      </div>
                      <span className="mt-1 text-xs font-semibold text-white truncate w-full">
                        {cuenta.nombre}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <p className="mt-5 border-t border-white/10 pt-3 text-[11px] text-slate-400">
            SENTINEL // OPS V2.0 • SuperVigilancia • Ley 1920 y Ley 2101 (42h) •
            Indumil • SOS WebSockets.
          </p>
        </section>

        {/* Panel Derecho: Selector Dinámico de Inicio de Sesión o Registro Real */}
        <section className="lg:col-span-7 rounded-2xl border border-white/10 bg-slate-900/60 p-8 shadow-2xl backdrop-blur-xl">
          <div className="flex border-b border-white/10 mb-6">
            <button
              type="button"
              onClick={(): void => {
                setPestanaActiva("ingreso");
                setErrorAutenticacion(null);
              }}
              className={`flex items-center gap-2 pb-3 text-sm font-bold transition border-b-2 mr-6 ${
                pestanaActiva === "ingreso"
                  ? "border-emerald-400 text-white"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <KeyRound className="h-4 w-4 text-emerald-400" />
              <span>Iniciar Sesión</span>
            </button>

            <button
              type="button"
              onClick={(): void => {
                setPestanaActiva("registro");
                setErrorAutenticacion(null);
              }}
              className={`flex items-center gap-2 pb-3 text-sm font-bold transition border-b-2 ${
                pestanaActiva === "registro"
                  ? "border-cyan-400 text-white"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <UserPlus className="h-4 w-4 text-cyan-400" />
              <span>Registrar Guarda / Integrante Real</span>
            </button>
          </div>

          {errorAutenticacion && (
            <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-950/30 p-3.5 text-xs text-rose-200">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{errorAutenticacion}</span>
            </div>
          )}

          {pestanaActiva === "ingreso" && (
            <div className="space-y-4">
              {/* Botones de Acceso Rápido Demo para los 5 Roles */}
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3.5">
                <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-300 block mb-2.5">
                  Acceso Rápido Demo (5 Roles RBAC — 1 Clic):
                </span>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                  {CUENTAS_DEMOSTRACION.map((cuenta) => (
                    <button
                      key={cuenta.correo}
                      type="button"
                      disabled={procesando}
                      onClick={(): void => {
                        void ingresarConCuentaDemo(cuenta);
                      }}
                      className="rounded-lg border border-white/10 bg-slate-950 p-2 text-center transition hover:border-emerald-400 hover:bg-emerald-500/10"
                    >
                      <span
                        className={`block rounded px-1 py-0.5 text-[9px] font-bold ${cuenta.colorDistintivo}`}
                      >
                        {cuenta.etiquetaRol}
                      </span>
                      <span className="text-[10px] font-semibold text-white block mt-1 truncate">
                        {cuenta.correo.split("@")[0]}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="relative flex py-1 items-center">
                <div className="flex-grow border-t border-white/10"></div>
                <span className="flex-shrink mx-3 text-[11px] uppercase tracking-wider text-slate-500">
                  O ingrese credenciales corporativas
                </span>
                <div className="flex-grow border-t border-white/10"></div>
              </div>

              <form
                onSubmit={(evento): void => {
                  void formularioIngreso.handleSubmit(procesarInicioSesion)(
                    evento
                  );
                }}
                className="space-y-4"
              >
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                    Correo Electrónico
                  </label>
                  <div className="relative mt-1.5">
                    <Mail className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
                    <input
                      type="email"
                      {...formularioIngreso.register("correo_electronico", {
                        required: "El correo es obligatorio",
                      })}
                      className="w-full rounded-xl border border-white/10 bg-slate-950/80 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                      placeholder="ejemplo@sentinelops.co"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                    Contraseña
                  </label>
                  <div className="relative mt-1.5">
                    <Lock className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
                    <input
                      type="password"
                      {...formularioIngreso.register("contrasena", {
                        required: "La contraseña es obligatoria",
                      })}
                      className="w-full rounded-xl border border-white/10 bg-slate-950/80 py-2.5 pl-10 pr-4 text-sm text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                      placeholder="••••••••••••"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={procesando}
                  className="mt-2 w-full rounded-xl bg-emerald-500 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-400 disabled:opacity-50"
                >
                  {procesando ? "Autenticando..." : "Ingresar a la Plataforma"}
                </button>
              </form>
            </div>
          )}

          {pestanaActiva === "registro" && (
            <form
              onSubmit={(evento): void => {
                void formularioRegistro.handleSubmit(procesarRegistroReal)(
                  evento
                );
              }}
              className="space-y-3"
            >
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    Nombres y Apellidos Reales
                  </label>
                  <input
                    {...formularioRegistro.register("nombre_completo", {
                      required: true,
                    })}
                    placeholder="Ej. Hernando Pardo Gómez"
                    className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950/80 px-3.5 py-2 text-xs text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    Cédula / Documento de Identidad
                  </label>
                  <input
                    {...formularioRegistro.register("documento_identidad", {
                      required: true,
                    })}
                    placeholder="Ej. CC-1014235890"
                    className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950/80 px-3.5 py-2 text-xs text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    Correo Electrónico
                  </label>
                  <div className="relative mt-1">
                    <Mail className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
                    <input
                      type="email"
                      {...formularioRegistro.register("correo_electronico", {
                        required: true,
                      })}
                      placeholder="guardia@sentinelops.co"
                      className="w-full rounded-xl border border-white/10 bg-slate-950/80 py-2 pl-9 pr-3 text-xs text-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    Teléfono Móvil
                  </label>
                  <div className="relative mt-1">
                    <Phone className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
                    <input
                      {...formularioRegistro.register("telefono", {
                        required: true,
                      })}
                      placeholder="+57 312 456 7890"
                      className="w-full rounded-xl border border-white/10 bg-slate-950/80 py-2 pl-9 pr-3 text-xs text-white"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    Código Placa
                  </label>
                  <div className="relative mt-1">
                    <BadgeAlert className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
                    <input
                      {...formularioRegistro.register("codigo_placa", {
                        required: true,
                      })}
                      placeholder="Ej. OPR-512"
                      className="w-full rounded-xl border border-white/10 bg-slate-950/80 py-2 pl-9 pr-3 text-xs text-white uppercase"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    Rol Corporativo (5 Niveles)
                  </label>
                  <select
                    {...formularioRegistro.register("rol", { required: true })}
                    className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-white"
                  >
                    <option value="OPERADOR">OPERADOR (Guarda)</option>
                    <option value="SUPERVISOR">SUPERVISOR</option>
                    <option value="RRHH">RRHH (Gestión Humana/Nómina)</option>
                    <option value="CLIENTE">CLIENTE (Director Puesto)</option>
                    <option value="ADMINISTRADOR">ADMINISTRADOR</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    Puesto Asignado
                  </label>
                  <select
                    {...formularioRegistro.register("puesto_base_id")}
                    className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-white"
                  >
                    <option value="">Sin Puesto Asignado</option>
                    {puestosDisponibles.map((puesto) => (
                      <option key={puesto.puesto_id} value={puesto.puesto_id}>
                        {puesto.codigo_puesto} - {puesto.nombre_puesto}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    Credencial SuperVigilancia
                  </label>
                  <div className="relative mt-1">
                    <Award className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-emerald-400" />
                    <input
                      {...formularioRegistro.register("numero_credencial_sv")}
                      placeholder="SV-2026-9901"
                      className="w-full rounded-xl border border-white/10 bg-slate-950/80 py-2 pl-9 pr-3 text-xs text-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    Vencimiento Credencial SV
                  </label>
                  <input
                    type="date"
                    {...formularioRegistro.register(
                      "fecha_vencimiento_credencial"
                    )}
                    className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    Nivel Curso SV
                  </label>
                  <select
                    {...formularioRegistro.register("nivel_curso")}
                    className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-white"
                  >
                    <option value="FUNDAMENTACION">FUNDAMENTACIÓN</option>
                    <option value="REENTRENAMIENTO">REENTRENAMIENTO</option>
                    <option value="ESPECIALIZACION">ESPECIALIZACIÓN</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300">
                  Contraseña de Acceso
                </label>
                <div className="relative mt-1">
                  <Lock className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
                  <input
                    type="password"
                    {...formularioRegistro.register("contrasena", {
                      required: true,
                      minLength: 6,
                    })}
                    placeholder="Mínimo 6 caracteres"
                    className="w-full rounded-xl border border-white/10 bg-slate-950/80 py-2 pl-9 pr-3 text-xs text-white"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={procesando}
                className="mt-2 w-full rounded-xl bg-cyan-500 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/20 transition hover:bg-cyan-400 disabled:opacity-50"
              >
                {procesando
                  ? "Registrando en Base de Datos..."
                  : "Crear Cuenta Real e Ingresar"}
              </button>
            </form>
          )}
        </section>
      </div>
    </div>
  );
}

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
  AlertCircle,
  KeyRound,
  UserPlus,
  Phone,
  BadgeAlert,
  Award,
  ArrowUpRight,
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
    etiquetaRol: "Administrador",
    subtituloPrioridad: "Nivel 1 • Global",
    nombre: "Comandante Alejandro Vargas",
    correo: "admin@sentinelops.co",
    contrasena: "Sentinel2026*",
    colorDistintivo: "border-white/[0.08] bg-[#18181B] text-[#FAFAFA]",
  },
  {
    etiquetaRol: "Supervisor CAD",
    subtituloPrioridad: "Nivel 2 • Dispatch",
    nombre: "Capitán Valeria Mendoza",
    correo: "supervisor@sentinelops.co",
    contrasena: "Sentinel2026*",
    colorDistintivo: "border-white/[0.08] bg-[#18181B] text-zinc-200",
  },
  {
    etiquetaRol: "RRHH",
    subtituloPrioridad: "Nivel 2.5 • Ley 2101",
    nombre: "Dra. Natalia Gómez (RRH-201)",
    correo: "rrhh@sentinelops.co",
    contrasena: "Sentinel2026*",
    colorDistintivo: "border-white/[0.08] bg-[#18181B] text-zinc-200",
  },
  {
    etiquetaRol: "Operador Garita",
    subtituloPrioridad: "Nivel 3 • Guarda 2x2",
    nombre: "Guarda Carlos Ramírez (OPR-401)",
    correo: "operador1@sentinelops.co",
    contrasena: "Sentinel2026*",
    colorDistintivo: "border-white/[0.08] bg-[#18181B] text-zinc-200",
  },
  {
    etiquetaRol: "Cliente B2B",
    subtituloPrioridad: "Nivel 4 • PST-BOG-01",
    nombre: "Ing. Roberto Salazar (CLI-901)",
    correo: "cliente@sentinelops.co",
    contrasena: "Sentinel2026*",
    colorDistintivo: "border-white/[0.08] bg-[#18181B] text-zinc-200",
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
    <div className="min-h-screen w-full bg-[#09090B] text-[#FAFAFA] flex items-center justify-center p-6 sm:p-10">
      <div className="grid w-full max-w-5xl grid-cols-1 gap-10 lg:grid-cols-12 items-start">
        {/* Columna Izquierda: Identidad Minimalista, Telemetría Viva & Command-Menu Demo */}
        <section className="lg:col-span-5 flex flex-col justify-between space-y-8 pt-2">
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/[0.08] bg-[#111113] text-[#FAFAFA] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)]">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold tracking-tight text-[#FAFAFA]">
                    SENTINEL <span className="text-zinc-600">//</span> OPS
                  </h1>
                  <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-zinc-500 block">
                    Command Infrastructure V5.1
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={alReintentarConexion}
                className="flex items-center gap-2 rounded-full border border-white/[0.07] bg-[#111113] px-2.5 py-1 text-[11px] font-mono text-zinc-300 hover:border-white/20 transition duration-150"
              >
                <span className="relative flex h-2 w-2">
                  {estadoConexion === "conectado" && (
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#10B981] opacity-75" />
                  )}
                  <span
                    className={`relative inline-flex rounded-full h-2 w-2 ${
                      estadoConexion === "conectado"
                        ? "bg-[#10B981]"
                        : estadoConexion === "cargando"
                          ? "bg-[#F59E0B]"
                          : "bg-[#EF4444]"
                    }`}
                  />
                </span>
                <span>
                  {estadoConexion === "conectado"
                    ? "API Live"
                    : estadoConexion === "cargando"
                      ? "Syncing"
                      : "Offline"}
                </span>
              </button>
            </div>

            {/* Resumen Compacto de Cumplimiento & Motor */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-mono text-zinc-400 border-y border-white/[0.07] py-3 tabular-nums">
              <span>Ley 2101 · {datosEstado?.tope_horas_semanales_ley_2101 ?? 42}h/sem</span>
              <span className="text-zinc-700">·</span>
              <span>SHA-256 Ledger</span>
              <span className="text-zinc-700">·</span>
              <span>
                {puestosDisponibles.length > 0
                  ? `${puestosDisponibles.length} Sedes`
                  : "PostgreSQL/SQLite"}
              </span>
            </div>

            {/* Selector de 5 Roles Demo tipo Command-Menu de Linear */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-zinc-500 px-1">
                <span>Acceso Demo Rápido (5 Roles RBAC)</span>
                <span>1-Click</span>
              </div>

              <div className="rounded-xl border border-white/[0.07] bg-[#111113] divide-y divide-white/[0.07] overflow-hidden shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)]">
                {CUENTAS_DEMOSTRACION.map((cuenta, indice) => (
                  <button
                    key={cuenta.correo}
                    type="button"
                    disabled={procesando}
                    onClick={(): void => {
                      void ingresarConCuentaDemo(cuenta);
                    }}
                    className="group w-full flex items-center justify-between gap-3 px-3.5 py-2.5 text-left transition duration-150 hover:bg-[#18181B] disabled:opacity-50"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-[#FAFAFA] group-hover:text-white">
                          {cuenta.etiquetaRol}
                        </span>
                        <span className="text-[11px] text-zinc-500 truncate hidden sm:inline">
                          {cuenta.nombre}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <kbd className="rounded border border-white/[0.08] bg-[#09090B] px-1.5 py-0.5 font-mono text-[10px] text-zinc-400 group-hover:text-zinc-200 tabular-nums">
                        {cuenta.subtituloPrioridad} · ⌘{indice + 1}
                      </kbd>
                      <ArrowUpRight className="h-3.5 w-3.5 text-zinc-600 group-hover:text-[#FAFAFA] transition" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <p className="text-[11px] font-mono text-zinc-600">
            {datosEstado?.motor_base_datos ?? "PostgreSQL 15 / Async SQLite"} ·
            Clave semilla: Sentinel2026*
          </p>
        </section>

        {/* Columna Derecha: Formulario Limpio de Acceso / Registro */}
        <section className="lg:col-span-7 rounded-2xl border border-white/[0.07] bg-[#111113] p-8 sm:p-10 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06)]">
          <div className="flex border-b border-white/[0.07] mb-7">
            <button
              type="button"
              onClick={(): void => {
                setPestanaActiva("ingreso");
                setErrorAutenticacion(null);
              }}
              className={`flex items-center gap-2 pb-3 text-sm font-medium transition duration-150 border-b-2 mr-6 ${
                pestanaActiva === "ingreso"
                  ? "border-[#FAFAFA] text-[#FAFAFA]"
                  : "border-transparent text-zinc-500 hover:text-zinc-200"
              }`}
            >
              <KeyRound className="h-4 w-4" />
              <span>Iniciar Sesión</span>
            </button>

            <button
              type="button"
              onClick={(): void => {
                setPestanaActiva("registro");
                setErrorAutenticacion(null);
              }}
              className={`flex items-center gap-2 pb-3 text-sm font-medium transition duration-150 border-b-2 ${
                pestanaActiva === "registro"
                  ? "border-[#FAFAFA] text-[#FAFAFA]"
                  : "border-transparent text-zinc-500 hover:text-zinc-200"
              }`}
            >
              <UserPlus className="h-4 w-4" />
              <span>Registrar Integrante</span>
            </button>
          </div>

          {errorAutenticacion && (
            <div className="mb-6 flex items-start gap-2.5 rounded-lg border border-[#EF4444]/40 bg-[#EF4444]/10 p-3.5 text-xs text-red-200">
              <AlertCircle className="h-4 w-4 shrink-0 text-[#EF4444] mt-0.5" />
              <span>{errorAutenticacion}</span>
            </div>
          )}

          {pestanaActiva === "ingreso" && (
            <form
              onSubmit={(evento): void => {
                void formularioIngreso.handleSubmit(procesarInicioSesion)(
                  evento
                );
              }}
              className="space-y-5"
            >
              <div>
                <h2 className="text-base font-semibold tracking-tight text-[#FAFAFA]">
                  Credenciales Corporativas
                </h2>
                <p className="text-xs text-zinc-400 mt-1">
                  Ingresa tu correo institucional o selecciona un rol en el panel lateral para acceso demo instantáneo.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300">
                  Correo Electrónico
                </label>
                <div className="relative mt-1.5">
                  <Mail className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-zinc-500" />
                  <input
                    type="email"
                    {...formularioIngreso.register("correo_electronico", {
                      required: "El correo es obligatorio",
                    })}
                    className="w-full rounded-lg border border-white/[0.08] bg-[#09090B] py-2.5 pl-10 pr-4 text-sm text-[#FAFAFA] placeholder-zinc-600 focus:border-white/30 focus:outline-none transition duration-150"
                    placeholder="operador@sentinelops.co"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300">
                  Contraseña
                </label>
                <div className="relative mt-1.5">
                  <Lock className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-zinc-500" />
                  <input
                    type="password"
                    {...formularioIngreso.register("contrasena", {
                      required: "La contraseña es obligatoria",
                    })}
                    className="w-full rounded-lg border border-white/[0.08] bg-[#09090B] py-2.5 pl-10 pr-4 text-sm text-[#FAFAFA] placeholder-zinc-600 focus:border-white/30 focus:outline-none transition duration-150"
                    placeholder="••••••••••••"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={procesando}
                className="w-full rounded-lg bg-[#FAFAFA] py-2.5 text-sm font-semibold text-[#09090B] transition duration-150 hover:bg-zinc-200 disabled:opacity-50"
              >
                {procesando ? "Autenticando..." : "Ingresar a la Plataforma"}
              </button>
            </form>
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

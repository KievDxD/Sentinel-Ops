/**
 * Módulo 1 (Enterprise V2.0): Gestión de Personal (RBAC 5 Niveles), Control de Credenciales
 * SuperVigilancia + Examen Psicofísico (1.2) y Puestos de Vigilancia B2B.
 */

import { useCallback, useEffect, useState, type ReactElement } from "react";
import { useForm } from "react-hook-form";
import {
  Users,
  Building2,
  PlusCircle,
  Shield,
  CheckCircle2,
  AlertTriangle,
  MapPin,
  Award,
  FileSpreadsheet,
  Upload,
} from "lucide-react";
import {
  extraerMensajeError,
  servicioActualizarCredencialSv,
  servicioAsignarPuestoUsuario,
  servicioCrearPuesto,
  servicioCrearUsuario,
  servicioImportarUsuariosCsv,
  servicioListarPuestos,
  servicioListarUsuarios,
} from "../servicios/cliente_api";
import { usarAlmacenAutenticacion } from "../estado/almacen_autenticacion";
import { evaluarSemaforoCredencialSv } from "./CentroDeMandoDashboard";
import type {
  CrearPuestoFormulario,
  CrearUsuarioFormulario,
  NivelCursoVigilancia,
  PuestoVigilancia,
  UsuarioSistema,
} from "../tipos/tipos_sistema";

export function ModuloPersonalYPuestos(): ReactElement {
  const usuarioActual = usarAlmacenAutenticacion(
    (estado) => estado.usuarioActual
  );
  const [usuarios, setUsuarios] = useState<UsuarioSistema[]>([]);
  const [puestos, setPuestos] = useState<PuestoVigilancia[]>([]);
  const [cargando, setCargando] = useState<boolean>(true);
  const [mensajeExito, setMensajeExito] = useState<string | null>(null);
  const [mensajeError, setMensajeError] = useState<string | null>(null);

  // Estado para edición rápida de credencial SuperVigilancia
  const [usuarioEditandoSv, setUsuarioEditandoSv] =
    useState<UsuarioSistema | null>(null);
  const [credencialSvInput, setCredencialSvInput] = useState<string>("");
  const [vencimientoSvInput, setVencimientoSvInput] = useState<string>("");
  const [vencimientoPsicoInput, setVencimientoPsicoInput] =
    useState<string>("");
  const [nivelCursoInput, setNivelCursoInput] =
    useState<NivelCursoVigilancia>("FUNDAMENTACION");
  const [excepcionAdminInput, setExcepcionAdminInput] =
    useState<boolean>(false);
  const [motivoExcepcionInput, setMotivoExcepcionInput] = useState<string>("");

  // Estado para modal de importación masiva CSV
  const [mostrarModalCsv, setMostrarModalCsv] = useState<boolean>(false);
  const [contenidoCsvInput, setContenidoCsvInput] = useState<string>("");
  const [procesandoCsv, setProcesandoCsv] = useState<boolean>(false);
  const [resumenCsv, setResumenCsv] = useState<{
    total: number;
    creados: number;
    omitidos: number;
    errores: string[];
  } | null>(null);

  const formularioUsuario = useForm<CrearUsuarioFormulario>({
    defaultValues: {
      rol: "OPERADOR",
      codigo_placa: "OPR-410",
      numero_credencial_sv: "SV-2026-8840",
      fecha_vencimiento_credencial: "2027-06-30",
      fecha_vencimiento_psicofisico: "2027-04-30",
      nivel_curso: "FUNDAMENTACION",
    },
  });

  const formularioPuesto = useForm<CrearPuestoFormulario>({
    defaultValues: {
      ciudad: "Bogotá D.C.",
      requiere_armamento: true,
    },
  });

  const cargarDatosOrganizacion = useCallback(async (): Promise<void> => {
    setCargando(true);
    try {
      const [listaUsuarios, listaPuestos] = await Promise.all([
        servicioListarUsuarios(),
        servicioListarPuestos(),
      ]);
      setUsuarios(listaUsuarios);
      setPuestos(listaPuestos);
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect((): void => {
    void cargarDatosOrganizacion();
  }, [cargarDatosOrganizacion]);

  const abrirEditorCredencialSv = (u: UsuarioSistema): void => {
    setUsuarioEditandoSv(u);
    setCredencialSvInput(u.numero_credencial_sv ?? "SV-2026-9000");
    setVencimientoSvInput(u.fecha_vencimiento_credencial ?? "2027-05-20");
    setVencimientoPsicoInput(u.fecha_vencimiento_psicofisico ?? "2027-03-15");
    setNivelCursoInput(u.nivel_curso ?? "REENTRENAMIENTO");
    setExcepcionAdminInput(Boolean(u.excepcion_credencial_autorizada));
    setMotivoExcepcionInput(
      u.motivo_excepcion_credencial ??
        "Radicado de renovación en trámite ante SuperVigilancia"
    );
  };

  const guardarCredencialSv = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!usuarioEditandoSv) return;
    setMensajeError(null);
    setMensajeExito(null);
    try {
      const actualizado = await servicioActualizarCredencialSv(
        usuarioEditandoSv.usuario_id,
        {
          numero_credencial_sv: credencialSvInput || null,
          fecha_vencimiento_credencial: vencimientoSvInput || null,
          fecha_vencimiento_psicofisico: vencimientoPsicoInput || null,
          nivel_curso: nivelCursoInput,
          excepcion_credencial_autorizada: excepcionAdminInput,
          motivo_excepcion_credencial: motivoExcepcionInput || null,
        }
      );
      setUsuarios((prev) =>
        prev.map((item) =>
          item.usuario_id === actualizado.usuario_id ? actualizado : item
        )
      );
      setUsuarioEditandoSv(null);
      setMensajeExito(
        `Credencial SuperVigilancia actualizada para ${actualizado.nombre_completo}.`
      );
    } catch (err: unknown) {
      setMensajeError(extraerMensajeError(err));
    }
  };

  const manejarCrearUsuario = async (
    datos: CrearUsuarioFormulario
  ): Promise<void> => {
    setMensajeError(null);
    setMensajeExito(null);
    try {
      const payload: CrearUsuarioFormulario = {
        ...datos,
        puesto_base_id: datos.puesto_base_id
          ? Number(datos.puesto_base_id)
          : undefined,
      };
      const creado = await servicioCrearUsuario(payload);
      setUsuarios((previos) => [...previos, creado]);
      formularioUsuario.reset({ rol: "OPERADOR", codigo_placa: "OPR-411" });
      setMensajeExito(
        `Integrante ${creado.nombre_completo} (${creado.rol}) registrado correctamente.`
      );
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    }
  };

  const manejarCambioPuestoUsuario = async (
    usuarioId: number,
    nuevoPuestoIdValor: string
  ): Promise<void> => {
    setMensajeError(null);
    setMensajeExito(null);
    try {
      const puestoId = nuevoPuestoIdValor ? Number(nuevoPuestoIdValor) : null;
      const actualizado = await servicioAsignarPuestoUsuario(
        usuarioId,
        puestoId
      );
      setUsuarios((previos) =>
        previos.map((u) => (u.usuario_id === usuarioId ? actualizado : u))
      );
      setMensajeExito(
        `Asignación de puesto actualizada para ${actualizado.nombre_completo}.`
      );
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    }
  };

  const manejarCrearPuesto = async (
    datos: CrearPuestoFormulario
  ): Promise<void> => {
    setMensajeError(null);
    setMensajeExito(null);
    try {
      const creado = await servicioCrearPuesto(datos);
      setPuestos((previos) => [...previos, creado]);
      formularioPuesto.reset({
        ciudad: "Bogotá D.C.",
        requiere_armamento: true,
      });
      setMensajeExito(
        `Puesto ${creado.codigo_puesto} - ${creado.nombre_puesto} registrado exitosamente.`
      );
    } catch (errorCapturado: unknown) {
      setMensajeError(extraerMensajeError(errorCapturado));
    }
  };

  const manejarCargaMasivaCsv = async (): Promise<void> => {
    if (!contenidoCsvInput.trim()) {
      setMensajeError("Pegue o cargue un archivo con contenido CSV.");
      return;
    }
    setProcesandoCsv(true);
    setMensajeError(null);
    setResumenCsv(null);
    try {
      const res = await servicioImportarUsuariosCsv(contenidoCsvInput);
      setResumenCsv({
        total: res.total_procesados,
        creados: res.creados,
        omitidos: res.omitidos,
        errores: res.errores,
      });
      setMensajeExito(
        `Importación completada: ${res.creados} nuevos usuarios creados, ${res.omitidos} omitidos.`
      );
      void cargarDatosOrganizacion();
    } catch (err: unknown) {
      setMensajeError(extraerMensajeError(err));
    } finally {
      setProcesandoCsv(false);
    }
  };

  const descargarPlantillaCsv = (): void => {
    const encabezados =
      "documento_identidad,nombre_completo,correo_electronico,telefono,rol,codigo_placa,numero_credencial_sv,fecha_vencimiento_credencial,nivel_curso\n1012345678,Pedro Vigilante,pedro@seguridad.co,3101234567,OPERADOR,GRD-101,SV-2026-101,2027-12-31,FUNDAMENTACION\n1087654321,Maria Supervisora,maria@seguridad.co,3159876543,SUPERVISOR,SUP-202,SV-2026-202,2027-10-15,ESPECIALIZACION";
    const blob = new Blob([encabezados], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "plantilla_personal_sentinel.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const esAdministrador = usuarioActual?.rol === "ADMINISTRADOR";
  const esRrhh = usuarioActual?.rol === "RRHH";
  const puedeCrearPersonal = esAdministrador || esRrhh;
  const puedeGestionarPuestos =
    esAdministrador || usuarioActual?.rol === "SUPERVISOR";

  return (
    <div className="space-y-6">
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

      {/* Modal / Panel de Edición Documental SuperVigilancia (1.2) */}
      {usuarioEditandoSv && (
        <form
          onSubmit={(e): void => void guardarCredencialSv(e)}
          className="rounded-2xl border-2 border-emerald-500/50 bg-slate-900 p-6 shadow-2xl space-y-4"
        >
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <Award className="h-5 w-5 text-emerald-400" />
              <h3 className="text-base font-bold text-white">
                Actualizar Acreditación SuperVigilancia:{" "}
                {usuarioEditandoSv.nombre_completo} (
                {usuarioEditandoSv.codigo_placa})
              </h3>
            </div>
            <button
              type="button"
              onClick={(): void => setUsuarioEditandoSv(null)}
              className="text-xs text-slate-400 hover:text-white"
            >
              Cerrar
            </button>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">
                N° Credencial SV
              </label>
              <input
                type="text"
                value={credencialSvInput}
                onChange={(e): void => setCredencialSvInput(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">
                Vencimiento Credencial SV
              </label>
              <input
                type="date"
                value={vencimientoSvInput}
                onChange={(e): void => setVencimientoSvInput(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">
                Vencimiento Psicofísico
              </label>
              <input
                type="date"
                value={vencimientoPsicoInput}
                onChange={(e): void => setVencimientoPsicoInput(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">
                Nivel Curso Vigilancia
              </label>
              <select
                value={nivelCursoInput}
                onChange={(e): void =>
                  setNivelCursoInput(e.target.value as NivelCursoVigilancia)
                }
                className="w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white"
              >
                <option value="FUNDAMENTACION">FUNDAMENTACIÓN</option>
                <option value="REENTRENAMIENTO">REENTRENAMIENTO</option>
                <option value="ESPECIALIZACION">ESPECIALIZACIÓN</option>
              </select>
            </div>
          </div>

          {esAdministrador && (
            <div className="rounded-xl border border-purple-500/30 bg-purple-950/20 p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <label className="flex items-center gap-2 text-xs font-bold text-purple-200">
                <input
                  type="checkbox"
                  checked={excepcionAdminInput}
                  onChange={(e): void =>
                    setExcepcionAdminInput(e.target.checked)
                  }
                />
                <span>
                  Autorizar Excepción Temporal de Credencial Vencida (Exclusivo
                  ADMINISTRADOR)
                </span>
              </label>
              <input
                type="text"
                value={motivoExcepcionInput}
                onChange={(e): void => setMotivoExcepcionInput(e.target.value)}
                placeholder="Justificación de excepción..."
                className="rounded-lg border border-purple-400/40 bg-slate-950 px-3 py-1.5 text-xs text-white min-w-[260px]"
              />
            </div>
          )}

          <button
            type="submit"
            className="rounded-xl bg-emerald-500 px-5 py-2.5 text-xs font-black uppercase text-slate-950 hover:bg-emerald-400"
          >
            Guardar Cambios de Acreditación SuperVigilancia
          </button>
        </form>
      )}

      {/* Modal / Panel de Carga Masiva CSV */}
      {mostrarModalCsv && (
        <div className="rounded-2xl border-2 border-sky-500/50 bg-slate-900 p-6 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5 text-sky-400" />
              <h3 className="text-base font-bold text-white">
                Carga Masiva de Personal y Credenciales SuperVigilancia (CSV)
              </h3>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={descargarPlantillaCsv}
                className="text-xs text-sky-300 hover:text-sky-200 underline"
              >
                📥 Descargar Plantilla CSV
              </button>
              <button
                type="button"
                onClick={(): void => setMostrarModalCsv(false)}
                className="text-xs text-slate-400 hover:text-white"
              >
                Cerrar
              </button>
            </div>
          </div>

          <p className="text-xs text-slate-400">
            Pegue a continuación las filas en formato CSV o cargue un archivo. Se admite delimitador por coma o punto y coma. Se encriptará la contraseña por defecto <code className="text-emerald-400">Sentinel2026*</code> para cada nuevo ingreso.
          </p>

          <textarea
            rows={5}
            value={contenidoCsvInput}
            onChange={(e): void => setContenidoCsvInput(e.target.value)}
            placeholder={`documento_identidad,nombre_completo,correo_electronico,telefono,rol,codigo_placa,numero_credencial_sv,fecha_vencimiento_credencial,nivel_curso\n1012345678,Pedro Vigilante,pedro@seguridad.co,3101234567,OPERADOR,GRD-101,SV-2026-101,2027-12-31,FUNDAMENTACION`}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 p-3 font-mono text-xs text-white focus:outline-none focus:border-sky-500"
          />

          <div className="flex flex-wrap items-center justify-between gap-3">
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e): void => {
                const archivo = e.target.files?.[0];
                if (archivo) {
                  const lector = new FileReader();
                  lector.onload = (evento): void => {
                    setContenidoCsvInput((evento.target?.result as string) || "");
                  };
                  lector.readAsText(archivo);
                }
              }}
              className="text-xs text-slate-400 file:mr-2 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-white/10 file:text-white hover:file:bg-white/20"
            />

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={(): void => {
                  setContenidoCsvInput("");
                  setResumenCsv(null);
                }}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
              >
                Limpiar
              </button>
              <button
                type="button"
                onClick={(): void => void manejarCargaMasivaCsv()}
                disabled={procesandoCsv || !contenidoCsvInput.trim()}
                className="flex items-center gap-1.5 rounded-xl bg-sky-500 px-5 py-2 text-xs font-black uppercase text-slate-950 hover:bg-sky-400 disabled:opacity-50"
              >
                <Upload className="h-4 w-4" />
                <span>{procesandoCsv ? "Procesando Lote..." : "Procesar Carga Masiva"}</span>
              </button>
            </div>
          </div>

          {resumenCsv && (
            <div className="rounded-xl border border-sky-500/30 bg-sky-950/30 p-3 text-xs space-y-1">
              <div className="font-bold text-sky-200">
                Resultado de Importación: {resumenCsv.creados} creados de {resumenCsv.total} registros ({resumenCsv.omitidos} omitidos por duplicidad).
              </div>
              {resumenCsv.errores.length > 0 && (
                <div className="text-rose-300 font-mono text-[11px] max-h-20 overflow-y-auto">
                  {resumenCsv.errores.map((err, i) => (
                    <div key={i}>• {err}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* Listado de Personal Operativo, Semáforo SV y RBAC */}
        <section className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-3">
              <Users className="h-5 w-5 text-emerald-400" />
              <h2 className="text-lg font-bold text-white">
                Personal Activo, Roles (5 Niveles) y Credenciales SV
              </h2>
            </div>
            <div className="flex items-center gap-2">
              {puedeCrearPersonal && (
                <button
                  type="button"
                  onClick={(): void => setMostrarModalCsv(true)}
                  className="flex items-center gap-1.5 rounded-lg border border-sky-500/40 bg-sky-500/10 px-3 py-1 text-xs font-bold text-sky-300 hover:bg-sky-500/20"
                >
                  <FileSpreadsheet className="h-3.5 w-3.5 text-sky-400" />
                  <span>Importar CSV</span>
                </button>
              )}
              <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300">
                {usuarios.length} Integrantes
              </span>
            </div>
          </div>

          {cargando ? (
            <p className="py-8 text-center text-sm text-slate-400">
              Cargando nómina de personal...
            </p>
          ) : (
            <div className="mt-4 space-y-3 max-h-[600px] overflow-y-auto pr-1">
              {usuarios.map((u) => {
                const puestoAsignado = puestos.find(
                  (p) => p.puesto_id === u.puesto_base_id
                );
                const sem = evaluarSemaforoCredencialSv(
                  u.fecha_vencimiento_credencial,
                  u.excepcion_credencial_autorizada
                );

                return (
                  <div
                    key={u.usuario_id}
                    className="rounded-xl border border-white/10 bg-slate-950/60 p-4 transition hover:border-white/20"
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold text-white">
                            {u.nombre_completo}
                          </span>
                          <span className="rounded bg-white/10 px-2 py-0.5 font-mono text-xs text-emerald-300">
                            {u.codigo_placa}
                          </span>
                          {u.rol === "OPERADOR" && (
                            <span
                              className={`rounded border px-2 py-0.5 text-[10px] font-bold ${sem.claseColor}`}
                            >
                              {sem.etiqueta}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-xs text-slate-400">
                          {u.documento_identidad} • {u.correo_electronico}
                        </p>
                        {u.numero_credencial_sv && (
                          <p className="mt-0.5 text-[11px] font-mono text-cyan-300">
                            SV: {u.numero_credencial_sv} • Vence:{" "}
                            {u.fecha_vencimiento_credencial ?? "N/A"} • Curso:{" "}
                            {u.nivel_curso ?? "FUNDAMENTACION"}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={(): void => abrirEditorCredencialSv(u)}
                          className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-bold text-emerald-300 hover:bg-emerald-500/20"
                        >
                          Editar SV
                        </button>
                        <span className="rounded-lg border border-white/15 bg-white/5 px-2.5 py-1 text-xs font-bold text-white">
                          {u.rol}
                        </span>
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-white/5 pt-2 text-xs">
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <MapPin className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                        <span>Puesto:</span>
                        {puestoAsignado ? (
                          <span className="font-medium text-cyan-300">
                            {puestoAsignado.codigo_puesto} -{" "}
                            {puestoAsignado.nombre_puesto}
                          </span>
                        ) : (
                          <span className="italic text-slate-500">
                            Sin puesto asignado
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <label
                          htmlFor={`puesto-select-${u.usuario_id}`}
                          className="text-[11px] text-slate-400"
                        >
                          Reasignar:
                        </label>
                        <select
                          id={`puesto-select-${u.usuario_id}`}
                          value={u.puesto_base_id ?? ""}
                          onChange={(e): void => {
                            void manejarCambioPuestoUsuario(
                              u.usuario_id,
                              e.target.value
                            );
                          }}
                          className="rounded-lg border border-white/10 bg-slate-900 px-2 py-1 text-xs text-white"
                        >
                          <option value="">-- Sin Asignar --</option>
                          {puestos.map((p) => (
                            <option key={p.puesto_id} value={p.puesto_id}>
                              {p.codigo_puesto} - {p.nombre_puesto}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Formulario de creación para ADMINISTRADOR y RRHH */}
          {puedeCrearPersonal && (
            <form
              onSubmit={(e): void => {
                void formularioUsuario.handleSubmit(manejarCrearUsuario)(e);
              }}
              className="mt-6 space-y-3 border-t border-white/10 pt-5"
            >
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400">
                <PlusCircle className="h-4 w-4" />
                <span>
                  Alta Documental de Nuevo Personal (ADMINISTRADOR y RRHH)
                </span>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <input
                  {...formularioUsuario.register("nombre_completo", {
                    required: true,
                  })}
                  placeholder="Nombre completo"
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
                <input
                  {...formularioUsuario.register("documento_identidad", {
                    required: true,
                  })}
                  placeholder="Documento (ej. CC-1020...)"
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
                <input
                  type="email"
                  {...formularioUsuario.register("correo_electronico", {
                    required: true,
                  })}
                  placeholder="correo@sentinelops.co"
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
                <input
                  {...formularioUsuario.register("telefono", {
                    required: true,
                  })}
                  placeholder="Teléfono móvil"
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
                <input
                  {...formularioUsuario.register("codigo_placa", {
                    required: true,
                  })}
                  placeholder="Código Placa (ej. OPR-410)"
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
                <select
                  {...formularioUsuario.register("rol", { required: true })}
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                >
                  <option value="OPERADOR">OPERADOR (Guarda)</option>
                  <option value="SUPERVISOR">SUPERVISOR</option>
                  <option value="RRHH">RRHH (Gestión Humana)</option>
                  <option value="CLIENTE">CLIENTE (Consola Puesto)</option>
                  {esAdministrador && (
                    <option value="ADMINISTRADOR">ADMINISTRADOR</option>
                  )}
                </select>
                <input
                  {...formularioUsuario.register("numero_credencial_sv")}
                  placeholder="Credencial SV (ej. SV-2026-8840)"
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
                <input
                  type="date"
                  {...formularioUsuario.register(
                    "fecha_vencimiento_credencial"
                  )}
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
                <select
                  {...formularioUsuario.register("puesto_base_id")}
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                >
                  <option value="">-- Puesto Base (Opcional) --</option>
                  {puestos.map((p) => (
                    <option key={p.puesto_id} value={p.puesto_id}>
                      {p.codigo_puesto} - {p.nombre_puesto}
                    </option>
                  ))}
                </select>
                <input
                  type="password"
                  {...formularioUsuario.register("contrasena", {
                    required: true,
                  })}
                  placeholder="Contraseña inicial (mín. 6 caracteres)"
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
              </div>
              <button
                type="submit"
                className="boton-tactico-campo w-full rounded-xl bg-emerald-500 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:bg-emerald-400"
              >
                Registrar Integrante con Acreditación SuperVigilancia
              </button>
            </form>
          )}
        </section>

        {/* Listado y Creación de Puestos de Vigilancia */}
        <section className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-3">
              <Building2 className="h-5 w-5 text-cyan-400" />
              <h2 className="text-lg font-bold text-white">
                Puestos de Vigilancia Protegidos
              </h2>
            </div>
            <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300">
              {puestos.length} Instalaciones
            </span>
          </div>

          <div className="mt-4 space-y-3">
            {puestos.map((p) => (
              <div
                key={p.puesto_id}
                className="rounded-xl border border-white/10 bg-slate-950/60 p-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 font-mono text-xs font-bold text-cyan-300">
                      {p.codigo_puesto}
                    </span>
                    <h3 className="font-semibold text-white">
                      {p.nombre_puesto}
                    </h3>
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-white/5 px-2.5 py-0.5 text-xs text-slate-300">
                    <Shield className="h-3.5 w-3.5 text-emerald-400" />
                    {p.requiere_armamento ? "Armado Indumil" : "No Letal"}
                  </span>
                </div>
                <p className="mt-1.5 text-xs text-slate-400">
                  Cliente:{" "}
                  <strong className="text-slate-200">{p.empresa_cliente}</strong>{" "}
                  • {p.direccion_ubicacion} ({p.ciudad})
                </p>
              </div>
            ))}
          </div>

          {puedeGestionarPuestos ? (
            <form
              onSubmit={(e): void => {
                void formularioPuesto.handleSubmit(manejarCrearPuesto)(e);
              }}
              className="mt-6 space-y-3 border-t border-white/10 pt-5"
            >
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
                <PlusCircle className="h-4 w-4" />
                <span>
                  Registrar Nuevo Puesto (Exclusivo Admin / Supervisor)
                </span>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <input
                  {...formularioPuesto.register("codigo_puesto", {
                    required: true,
                  })}
                  placeholder="Código (ej. PST-BOG-04)"
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
                <input
                  {...formularioPuesto.register("ciudad", { required: true })}
                  placeholder="Ciudad"
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
                <input
                  {...formularioPuesto.register("nombre_puesto", {
                    required: true,
                  })}
                  placeholder="Nombre del Puesto / Instalación"
                  className="sm:col-span-2 rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
                <input
                  {...formularioPuesto.register("empresa_cliente", {
                    required: true,
                  })}
                  placeholder="Empresa Cliente B2B"
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
                <input
                  {...formularioPuesto.register("direccion_ubicacion", {
                    required: true,
                  })}
                  placeholder="Dirección física"
                  className="rounded-xl border border-white/10 bg-slate-950 px-3.5 py-2 text-sm text-white"
                />
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-300">
                <input
                  type="checkbox"
                  {...formularioPuesto.register("requiere_armamento")}
                  className="rounded border-white/20 bg-slate-950 text-emerald-500"
                />
                <span>
                  El puesto requiere dotación de armamento Indumil autorizado
                </span>
              </label>
              <button
                type="submit"
                className="boton-tactico-campo w-full rounded-xl bg-cyan-500 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-950 transition hover:bg-cyan-400"
              >
                Dar de Alta Puesto Operativo
              </button>
            </form>
          ) : (
            <div className="mt-6 rounded-xl border border-white/10 bg-slate-950/60 p-4 text-xs text-slate-400">
              Restricción RBAC: El rol <strong>RRHH</strong> gestiona
              acreditación documental y nómina, pero no modifica geocercas ni
              crea puestos tácticos.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

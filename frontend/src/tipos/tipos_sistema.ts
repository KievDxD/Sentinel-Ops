/**
 * Definiciones de tipos e interfaces estrictas de TypeScript para SENTINEL // OPS (Release Enterprise V2.0).
 * Prohibido el uso de `any`. Todos los nombres están en español.
 */

export type RolUsuario =
  | "ADMINISTRADOR"
  | "SUPERVISOR"
  | "RRHH"
  | "OPERADOR"
  | "CLIENTE";

export type NivelCursoVigilancia =
  | "FUNDAMENTACION"
  | "REENTRENAMIENTO"
  | "ESPECIALIZACION";

export type TipoTurno = "DIURNO" | "NOCTURNO" | "DESCANSO";

export type EstadoTurno =
  | "PROGRAMADO"
  | "EN_CURSO"
  | "COMPLETADO"
  | "INTERCAMBIADO"
  | "DESCUBIERTO_PARCIAL";

export type TipoRegistroMinuta =
  | "INGRESO_VISITANTE"
  | "INGRESO_VEHICULO"
  | "RONDA_CONTROL"
  | "NOVEDAD_INCIDENTE"
  | "RELEVO_TURNO"
  | "ENTREGA_RECIBO_PUESTO"
  | "ALERTA_PANICO_SOS";

export type VisibilidadMinuta = "PUBLICA_CLIENTE" | "INTERNA_OPERATIVA";

export type NivelPrioridad = "BAJA" | "MEDIA" | "ALTA" | "CRITICA";

export type EstadoSolicitudIntercambio = "PENDIENTE" | "APROBADA" | "RECHAZADA";

export type EstadoItemDotacion = "OPTIMO" | "NOVEDAD" | "FALTANTE";

export type TipoAusentismo =
  | "INCAPACIDAD_EPS"
  | "INCAPACIDAD_ARL"
  | "LICENCIA_REMUNERADA"
  | "FALTA_INJUSTIFICADA"
  | "ABANDONO_PUESTO";

export type ModalidadServicioTarifa =
  | "VIGILANCIA_24H_ARMADA"
  | "VIGILANCIA_24H_SIN_ARMA"
  | "VIGILANCIA_12H_DIURNA"
  | "VIGILANCIA_12H_NOCTURNA"
  | "SUPERVISION_MOTORIZADA";

export type EstadoFactura = "BORRADOR" | "EMITIDA" | "PAGADA" | "ANULADA";

export type EstadoAlertaSos = "ACTIVA" | "ATENDIDA";

export type TipoAccesoGarita =
  | "PEATONAL_VISITANTE"
  | "VEHICULAR"
  | "CONTRATISTA"
  | "EMPLEADO";

export type EstadoAccesoGarita = "DENTRO" | "SALIO";

export type TipoMovimientoBalistico =
  | "DOTACION_INICIAL"
  | "CONSUMO_INCIDENTE"
  | "PRACTICA_POLIGONO"
  | "MANTENIMIENTO_ARMERIA"
  | "REPOSICION_INDUMIL";

export type EstadoDespachoPatrulla =
  | "PENDIENTE"
  | "EN_RUTA"
  | "EN_SITIO"
  | "FINALIZADO"
  | "CANCELADO";

export interface RespuestaEstadoServidor {
  estado: string;
  fecha: string;
  motor_base_datos: string;
  conexiones_websocket_activas: number;
  tope_horas_semanales_ley_2101?: number;
}

export interface UsuarioSistema {
  usuario_id: number;
  documento_identidad: string;
  nombre_completo: string;
  correo_electronico: string;
  telefono: string;
  rol: RolUsuario;
  codigo_placa: string;
  puesto_base_id?: number | null;
  numero_credencial_sv?: string | null;
  fecha_vencimiento_credencial?: string | null;
  fecha_vencimiento_psicofisico?: string | null;
  nivel_curso?: NivelCursoVigilancia | null;
  excepcion_credencial_autorizada?: boolean;
  motivo_excepcion_credencial?: string | null;
  activo: boolean;
  fecha_creacion: string;
}

export interface ActualizarCredencialUsuarioFormulario {
  numero_credencial_sv: string | null;
  fecha_vencimiento_credencial: string | null;
  fecha_vencimiento_psicofisico: string | null;
  nivel_curso: NivelCursoVigilancia | null;
  excepcion_credencial_autorizada: boolean;
  motivo_excepcion_credencial?: string | null;
}

export interface RespuestaTokensAutenticacion {
  token_acceso: string;
  token_refresco: string;
  tipo_esquema: string;
  usuario: UsuarioSistema;
}

export interface SolicitudInicioSesion {
  correo_electronico: string;
  contrasena: string;
}

export interface RegistroUsuarioRealFormulario {
  documento_identidad: string;
  nombre_completo: string;
  correo_electronico: string;
  telefono: string;
  contrasena: string;
  rol: RolUsuario;
  codigo_placa: string;
  puesto_base_id?: number;
  numero_credencial_sv?: string;
  fecha_vencimiento_credencial?: string;
  fecha_vencimiento_psicofisico?: string;
  nivel_curso?: NivelCursoVigilancia;
}

export interface CrearUsuarioFormulario {
  documento_identidad: string;
  nombre_completo: string;
  correo_electronico: string;
  telefono: string;
  contrasena: string;
  rol: RolUsuario;
  codigo_placa: string;
  puesto_base_id?: number;
  numero_credencial_sv?: string;
  fecha_vencimiento_credencial?: string;
  fecha_vencimiento_psicofisico?: string;
  nivel_curso?: NivelCursoVigilancia;
}

export interface PuestoVigilancia {
  puesto_id: number;
  codigo_puesto: string;
  nombre_puesto: string;
  empresa_cliente: string;
  direccion_ubicacion: string;
  ciudad: string;
  requiere_armamento: boolean;
  activo: boolean;
}

export interface CrearPuestoFormulario {
  codigo_puesto: string;
  nombre_puesto: string;
  empresa_cliente: string;
  direccion_ubicacion: string;
  ciudad: string;
  requiere_armamento: boolean;
}

export interface TurnoOperativo {
  turno_id: number;
  operador_id: number;
  nombre_operador: string;
  codigo_placa_operador: string;
  puesto_id: number;
  nombre_puesto: string;
  codigo_puesto: string;
  tipo_turno: TipoTurno;
  estado_turno: EstadoTurno;
  fecha_inicio: string;
  fecha_fin: string;
  horas_totales: number;
  horas_ordinarias: number;
  horas_recargo_nocturno: number;
  horas_extras_diurnas: number;
  horas_extras_nocturnas: number;
  horas_dominicales_festivas: number;
  horas_descuento_ausentismo?: number;
  motivo_ausentismo?: string | null;
  costo_estimado_cop: number;
  observaciones: string | null;
}

export interface ResumenLiquidacionTurnos {
  tope_horas_semanales_aplicado?: number;
  total_turnos_operativos: number;
  total_dias_descanso: number;
  suma_horas_trabajadas: number;
  suma_horas_ordinarias: number;
  suma_horas_recargo_nocturno: number;
  suma_horas_extras_diurnas: number;
  suma_horas_extras_nocturnas: number;
  suma_horas_dominicales_festivas: number;
  suma_horas_descuento_ausentismo?: number;
  costo_total_estimado_cop: number;
  turnos: TurnoOperativo[];
}

export interface SolicitudGenerarRotacion2x2 {
  operador_id: number;
  puesto_id: number;
  fecha_inicio_ciclo: string;
  cantidad_ciclos_6_dias: number;
  reemplazar_existentes: boolean;
}

export interface SolicitudGenerarCoberturaPuesto2x2 {
  puesto_id: number;
  operadores_ids?: number[];
  fecha_inicio_ciclo: string;
  cantidad_dias: number;
  reemplazar_existentes: boolean;
}

export interface CandidatoRelevanteSugerido {
  usuario_id: number;
  nombre_completo: string;
  codigo_placa: string;
  numero_credencial_sv: string | null;
  credencial_vigente: boolean;
  en_dia_descanso: boolean;
  horas_descanso_previas: number;
  horas_extras_acumuladas_semana: number;
  puntaje_idoneidad: string;
}

export interface AsignarRelevanteTurnoFormulario {
  operador_reemplazo_id: number;
  observacion_asignacion?: string;
}

export interface RegistroMinuta {
  registro_id: number;
  operador_id: number;
  nombre_operador: string;
  codigo_placa_operador: string;
  puesto_id: number;
  nombre_puesto: string;
  codigo_puesto: string;
  tipo_registro: TipoRegistroMinuta;
  visibilidad?: VisibilidadMinuta;
  nivel_prioridad: NivelPrioridad;
  titulo_evento: string;
  descripcion_detallada: string;
  nombre_visitante: string | null;
  documento_visitante: string | null;
  placa_vehiculo: string | null;
  fecha_registro: string;
}

export interface CrearRegistroMinutaFormulario {
  puesto_id: number;
  tipo_registro: TipoRegistroMinuta;
  visibilidad?: VisibilidadMinuta;
  nivel_prioridad: NivelPrioridad;
  titulo_evento: string;
  descripcion_detallada: string;
  nombre_visitante?: string;
  documento_visitante?: string;
  placa_vehiculo?: string;
}

export interface AlertaPanicoSos {
  alerta_id: number;
  operador_id: number;
  nombre_operador: string;
  codigo_placa_operador: string;
  puesto_id: number;
  nombre_puesto: string;
  codigo_puesto: string;
  latitud_gps: number;
  longitud_gps: number;
  estado_alerta: EstadoAlertaSos;
  fecha_activacion: string;
  atendida_por_id: number | null;
  nombre_supervisor_atendio: string | null;
  fecha_atencion: string | null;
  tiempo_reaccion_segundos: number | null;
  nota_reaccion: string | null;
}

export interface DispararAlertaSosFormulario {
  puesto_id: number;
  latitud_gps: number;
  longitud_gps: number;
}

export interface AtenderAlertaSosFormulario {
  nota_reaccion: string;
}

export interface MensajeWebSocketMinuta {
  tipo_mensaje:
    | "NUEVO_REGISTRO_MINUTA"
    | "ALERTA_PANICO_SOS"
    | "SOS_ATENDIDO"
    | "LATIDO_ACTIVO";
  registro?: RegistroMinuta;
  alerta_sos?: AlertaPanicoSos;
}

export interface DotacionPuesto {
  dotacion_id: number;
  puesto_id: number;
  tipo_arma: string;
  serial_arma: string;
  numero_salvoconducto_indumil: string;
  tipo_salvoconducto: string;
  fecha_vencimiento_salvoconducto: string;
  cantidad_municion_autorizada: number;
  serial_chaleco_balistico: string;
  serie_radio_comunicacion: string;
  celular_corporativo_imei: string;
  tiene_linterna_tactica: boolean;
  llaves_y_minutas_fisicas: boolean;
}

export interface CrearActaRelevoFormulario {
  puesto_id: number;
  operador_entrante_id?: number | null;
  estado_armamento: EstadoItemDotacion;
  municion_verificada: number;
  estado_chaleco: EstadoItemDotacion;
  estado_radio: EstadoItemDotacion;
  estado_linterna_y_llaves: EstadoItemDotacion;
  observaciones_relevo: string;
}

export interface ActaRelevoPuesto {
  acta_id: number;
  puesto_id: number;
  nombre_puesto: string;
  codigo_puesto: string;
  operador_saliente_id: number;
  nombre_operador_saliente: string;
  operador_entrante_id: number | null;
  nombre_operador_entrante: string | null;
  estado_armamento: EstadoItemDotacion;
  municion_verificada: number;
  estado_chaleco: EstadoItemDotacion;
  estado_radio: EstadoItemDotacion;
  estado_linterna_y_llaves: EstadoItemDotacion;
  observaciones_relevo: string;
  sello_sha256: string;
  alerta_disparada: boolean;
  fecha_acta: string;
}

export interface RegistrarAusentismoFormulario {
  operador_id: number;
  turno_afectado_id?: number | null;
  tipo_ausentismo: TipoAusentismo;
  fecha_inicio: string;
  fecha_fin: string;
  horas_descontadas: number;
  descripcion_soporte: string;
}

export interface AusentismoPersonal {
  ausentismo_id: number;
  operador_id: number;
  nombre_operador: string;
  codigo_placa: string;
  turno_afectado_id: number | null;
  tipo_ausentismo: TipoAusentismo;
  fecha_inicio: string;
  fecha_fin: string;
  horas_descontadas: number;
  descripcion_soporte: string;
  registrado_por_id: number;
  nombre_registrador: string;
  reemplazo_asignado_id: number | null;
  nombre_reemplazo: string | null;
  fecha_registro: string;
}

export interface SolicitudIntercambioTurno {
  intercambio_id: number;
  operador_solicitante_id: number;
  nombre_solicitante: string;
  operador_receptor_id: number;
  nombre_receptor: string;
  turno_origen_id: number;
  resumen_turno_origen: string;
  turno_destino_id: number;
  resumen_turno_destino: string;
  motivo_solicitud: string;
  estado_solicitud: EstadoSolicitudIntercambio;
  validacion_sin_cruces: boolean;
  horas_descanso_minimo_calculadas: number;
  detalle_validacion_motor: string;
  supervisor_validador_id: number | null;
  nombre_supervisor: string | null;
  comentario_supervisor: string | null;
  fecha_solicitud: string;
  fecha_resolucion: string | null;
}

export interface CrearSolicitudIntercambioFormulario {
  turno_origen_id: number;
  turno_destino_id: number;
  motivo_solicitud: string;
}

export interface ResolverIntercambioFormulario {
  aprobar: boolean;
  comentario_supervisor: string;
}

export interface PuntoControlRonda {
  punto_id: number;
  puesto_id: number;
  codigo_qr_hash: string;
  nombre_punto: string;
  latitud_gps: number;
  longitud_gps: number;
  radio_tolerancia_metros: number;
  orden_secuencia: number;
  activo: boolean;
}

export interface RegistrarMarcacionRondaFormulario {
  punto_id: number;
  latitud_capturada: number;
  longitud_capturada: number;
  observacion_ronda: string;
  sincronizado_desde_offline?: boolean;
}

export interface MarcacionRonda {
  marcacion_id: number;
  punto_id: number;
  nombre_punto: string;
  codigo_qr_hash: string;
  operador_id: number;
  nombre_operador: string;
  latitud_capturada: number;
  longitud_capturada: number;
  distancia_calculada_metros: number;
  dentro_de_geocerca: boolean;
  sincronizado_desde_offline: boolean;
  observacion_ronda: string;
  fecha_marcacion: string;
}

export interface AlertaCoberturaPuesto {
  puesto_id: number;
  codigo_puesto: string;
  nombre_puesto: string;
  estado_cobertura: string;
  nivel_alerta: NivelPrioridad;
  operador_en_turno: string;
  puntos_control_verificados: number;
  total_puntos_control: number;
  detalle_operativo: string;
}

export interface SolicitudCotizacionTarifa {
  modalidad_servicio: ModalidadServicioTarifa;
  cantidad_puestos: number;
  porcentaje_administracion: number;
  smlmv?: number;
  auxilio_transporte?: number;
}

export interface RespuestaDesgloseCotizacion {
  modalidad_servicio: ModalidadServicioTarifa;
  cantidad_puestos: number;
  guardas_por_puesto: number;
  total_guardas_requeridos: number;
  costo_laboral_unitario_guarda: number;
  costo_mano_obra_total: number;
  costo_armamento_y_equipos: number;
  costo_administracion_aiu: number;
  subtotal_antes_iva: number;
  iva_dian: number;
  tarifa_total_factura_cop: number;
  tarifa_minima_supervigilancia: number;
}

export interface SolicitudGenerarPrefactura {
  cliente_id: number;
  puesto_id?: number | null;
  mes_servicio: string;
  modalidad_servicio: ModalidadServicioTarifa;
  cantidad_puestos: number;
  porcentaje_administracion: number;
  notas_comerciales?: string;
}

export interface PrefacturaB2B {
  prefactura_id: number;
  codigo_factura: string;
  cliente_id: number;
  nombre_cliente: string;
  puesto_id: number | null;
  nombre_puesto: string | null;
  mes_servicio: string;
  modalidad_servicio: ModalidadServicioTarifa;
  cantidad_puestos: number;
  cantidad_guardas_requeridos: number;
  costo_mano_obra_cop: number;
  costo_armamento_cop: number;
  costo_administracion_cop: number;
  subtotal_cop: number;
  iva_cop: number;
  total_factura_cop: number;
  estado_factura: EstadoFactura;
  notas_comerciales: string | null;
  firma_digital_sha256: string;
  fecha_emision: string;
  fecha_vencimiento: string;
}

// ============================================================================
// FASE 9: CONTROL DE ACCESO GARITA Y ESCÁNER PDF417
// ============================================================================
export interface DatosCedulaColombiana {
  documento_identidad: string;
  primer_apellido: string;
  segundo_apellido: string;
  primer_nombre: string;
  segundo_nombre: string;
  nombre_completo: string;
  sexo: string;
  fecha_nacimiento?: string | null;
  grupo_sanguineo_rh: string;
  es_valido: boolean;
  mensaje_validacion: string;
}

export interface SolicitudRegistrarAccesoGarita {
  puesto_id: number;
  tipo_acceso: TipoAccesoGarita;
  documento_identidad: string;
  nombres: string;
  apellidos: string;
  tipo_sangre_rh?: string;
  placa_vehiculo?: string;
  empresa_o_destino: string;
  motivo_ingreso: string;
  observaciones?: string;
}

export interface RegistroAccesoGarita {
  acceso_id: number;
  puesto_id: number;
  nombre_puesto: string;
  operador_id: number;
  nombre_operador: string;
  tipo_acceso: TipoAccesoGarita;
  documento_identidad: string;
  nombres: string;
  apellidos: string;
  nombre_completo: string;
  tipo_sangre_rh: string | null;
  placa_vehiculo: string | null;
  empresa_o_destino: string;
  motivo_ingreso: string;
  es_sospechoso_alerta: boolean;
  estado_acceso: EstadoAccesoGarita;
  fecha_ingreso: string;
  fecha_salida: string | null;
  observaciones: string | null;
}

// ============================================================================
// FASE 10: LIBRO BALÍSTICO DIGITAL Y TRAZABILIDAD DCCA INDUMIL
// ============================================================================
export interface SemaforoSalvoconducto {
  dotacion_id: number;
  puesto_id: number;
  nombre_puesto: string;
  tipo_arma: string;
  serial_arma: string;
  numero_salvoconducto_indumil: string;
  tipo_salvoconducto: string;
  fecha_vencimiento_salvoconducto: string;
  dias_restantes: number;
  estado_semaforo: "VIGENTE_VERDE" | "PREVENTIVO_AMARILLO" | "CRITICO_ROJO" | "VENCIDO";
  requiere_tramite_dcca: boolean;
  cantidad_municion_actual: number;
}

export interface MovimientoBalistico {
  movimiento_id: number;
  puesto_id: number;
  nombre_puesto: string;
  dotacion_id: number;
  tipo_arma: string;
  serial_arma: string;
  operador_responsable_id: number;
  nombre_operador: string;
  tipo_movimiento: TipoMovimientoBalistico;
  calibre: string;
  cantidad_municion_afectada: number;
  saldo_municion_resultante: number;
  justificacion_novedad: string;
  numero_oficio_dcca: string | null;
  firma_digital_sha256: string;
  fecha_movimiento: string;
}

export interface SolicitudRegistrarMovimientoBalistico {
  puesto_id: number;
  dotacion_id: number;
  tipo_movimiento: TipoMovimientoBalistico;
  calibre: string;
  cantidad_municion_afectada: number;
  justificacion_novedad: string;
  numero_oficio_dcca?: string;
}

export interface CertificadoPoligono {
  certificado_id: number;
  operador_id: number;
  nombre_operador: string;
  academia_seguridad: string;
  tipo_arma_calificada: string;
  puntaje_precision: number;
  aprobado: boolean;
  fecha_practica: string;
  fecha_vencimiento_anual: string;
}

export interface SolicitudRegistrarCertificadoPoligono {
  operador_id: number;
  academia_seguridad: string;
  tipo_arma_calificada: string;
  puntaje_precision: number;
  aprobado: boolean;
  fecha_practica: string;
}

// ============================================================================
// FASE 11: CENTRO DE DESPACHO CAD Y MONITOREO GPS EN VIVO
// ============================================================================
export interface TelemetriaPuestoMapa {
  puesto_id: number;
  nombre_puesto: string;
  codigo_puesto: string;
  latitud_gps: number;
  longitud_gps: number;
  estado_seguridad: "NORMAL" | "ALERTA_SOS";
  requiere_armamento: boolean;
}

export interface TelemetriaSupervisorMapa {
  supervisor_id: number;
  nombre_supervisor: string;
  codigo_placa: string;
  latitud_actual: number;
  longitud_actual: number;
  estado_disponibilidad: "DISPONIBLE" | "EN_DESPACHO";
}

export interface ResumenMapaTactico {
  puestos: TelemetriaPuestoMapa[];
  supervisores: TelemetriaSupervisorMapa[];
  alertas_sos_activas_conteo: number;
}

export interface CandidatoSupervisorCercano {
  supervisor_id: number;
  nombre_supervisor: string;
  codigo_placa: string;
  distancia_km: number;
  eta_minutos: number;
  recomendado: boolean;
}

export interface DespachoPatrulla {
  despacho_id: number;
  alerta_sos_id: number;
  supervisor_id: number;
  nombre_supervisor: string;
  codigo_placa_supervisor: string;
  puesto_id: number;
  nombre_puesto: string;
  coordenadas_puesto: [number, number];
  distancia_km_calculada: number;
  eta_minutos_estimado: number;
  estado_despacho: EstadoDespachoPatrulla;
  fecha_despacho: string;
  fecha_llegada_sitio: string | null;
  tiempo_arribo_segundos: number | null;
  informe_tactico_cierre: string | null;
}

// ============================================================================
// MEJORAS TÁCTICAS V3.0: LPR, PONAL Y CARGA MASIVA CSV
// ============================================================================
export interface RespuestaEscanearPlaca {
  placa_normalizada: string;
  tipo_vehiculo: string;
  es_valida: boolean;
  mensaje: string;
}

export interface CuadrantePoliciaPuesto {
  puesto_id: number;
  cai_jurisdiccion: string;
  telefono_cuadrante: string;
  canal_radio_frecuencia: string;
}

export interface InfoRedApoyoPonal {
  linea_emergencia_nacional: string;
  red_apoyo_supervigilancia: string;
  cuadrantes: CuadrantePoliciaPuesto[];
}

export interface RespuestaImportacionUsuariosCsv {
  total_procesados: number;
  creados: number;
  omitidos: number;
  errores: string[];
  usuarios_creados: UsuarioSistema[];
}

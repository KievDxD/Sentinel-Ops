"""
Esquemas de validación estricta Pydantic v2 para SENTINEL // OPS (Release Enterprise V2.0).
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modelos.modelos_bd import (
    EstadoAccesoGarita,
    EstadoAlertaSos,
    EstadoDespachoPatrulla,
    EstadoFactura,
    EstadoItemDotacion,
    EstadoSolicitudIntercambio,
    EstadoTurno,
    ModalidadServicioTarifa,
    NivelCursoVigilancia,
    NivelPrioridad,
    RolUsuario,
    TipoAccesoGarita,
    TipoAusentismo,
    TipoMovimientoBalistico,
    TipoRegistroMinuta,
    TipoTurno,
    VisibilidadMinuta,
)


# ============================================================================
# ESQUEMAS DE DIAGNÓSTICO DEL SISTEMA
# ============================================================================
class RespuestaEstadoSistema(BaseModel):
    """Esquema de respuesta para el endpoint /api/estado."""

    estado: str
    fecha: str
    motor_base_datos: str = "PostgreSQL 15 (Docker)"
    conexiones_websocket_activas: int = 0
    tope_horas_semanales_ley_2101: int = 42


# ============================================================================
# MÓDULO 1: AUTENTICACIÓN, 5 ROLES (RBAC), CREDENCIALES SUPERVIGILANCIA Y PUESTOS
# ============================================================================
class SolicitudInicioSesion(BaseModel):
    """Credenciales de ingreso enviadas por el usuario."""

    correo_electronico: EmailStr
    contrasena: str = Field(..., min_length=4, max_length=128)


class SolicitudRefrescarToken(BaseModel):
    """Solicitud para renovar el token de acceso usando el token de refresco."""

    token_refresco: str


class RespuestaUsuario(BaseModel):
    """Representación pública y segura de un usuario del sistema con estado SuperVigilancia."""

    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    documento_identidad: str
    nombre_completo: str
    correo_electronico: EmailStr
    telefono: str
    rol: RolUsuario
    codigo_placa: str
    puesto_base_id: int | None = None
    numero_credencial_sv: str | None = None
    fecha_vencimiento_credencial: date | None = None
    fecha_vencimiento_psicofisico: date | None = None
    nivel_curso: NivelCursoVigilancia | None = NivelCursoVigilancia.FUNDAMENTACION
    excepcion_credencial_autorizada: bool = False
    activo: bool
    fecha_creacion: datetime


class RegistroUsuarioRealSolicitud(BaseModel):
    """Datos para registrar a un nuevo integrante en cualquiera de los 5 roles."""

    documento_identidad: str = Field(..., min_length=5, max_length=30)
    nombre_completo: str = Field(..., min_length=3, max_length=120)
    correo_electronico: EmailStr
    telefono: str = Field(..., min_length=7, max_length=30)
    contrasena: str = Field(..., min_length=6, max_length=128)
    rol: RolUsuario = Field(default=RolUsuario.OPERADOR)
    codigo_placa: str = Field(..., min_length=2, max_length=30)
    puesto_base_id: int | None = None
    numero_credencial_sv: str | None = None
    fecha_vencimiento_credencial: date | None = None
    fecha_vencimiento_psicofisico: date | None = None
    nivel_curso: NivelCursoVigilancia | None = NivelCursoVigilancia.FUNDAMENTACION


class CrearUsuarioSolicitud(BaseModel):
    """Datos requeridos por un Administrador o RRHH para dar de alta un nuevo integrante."""

    documento_identidad: str = Field(..., min_length=5, max_length=30)
    nombre_completo: str = Field(..., min_length=3, max_length=120)
    correo_electronico: EmailStr
    telefono: str = Field(..., min_length=7, max_length=30)
    contrasena: str = Field(..., min_length=6, max_length=128)
    rol: RolUsuario
    codigo_placa: str = Field(..., min_length=2, max_length=30)
    puesto_base_id: int | None = None
    numero_credencial_sv: str | None = None
    fecha_vencimiento_credencial: date | None = None
    fecha_vencimiento_psicofisico: date | None = None
    nivel_curso: NivelCursoVigilancia | None = NivelCursoVigilancia.FUNDAMENTACION


class ActualizarCredencialUsuarioSolicitud(BaseModel):
    """Actualización documental de SuperVigilancia y aptitud psicofísica (RRHH / Admin)."""

    numero_credencial_sv: str = Field(..., min_length=4, max_length=50)
    fecha_vencimiento_credencial: date
    fecha_vencimiento_psicofisico: date
    nivel_curso: NivelCursoVigilancia
    excepcion_credencial_autorizada: bool = False


class AsignarPuestoUsuarioSolicitud(BaseModel):
    """Solicitud para asignar o modificar el puesto base de vigilancia de un usuario."""

    puesto_base_id: int | None = None


class RespuestaTokensAutenticacion(BaseModel):
    """Respuesta completa tras autenticación exitosa con JWT Access y Refresh."""

    token_acceso: str
    token_refresco: str
    tipo_esquema: str = "Bearer"
    usuario: RespuestaUsuario


class RespuestaPuestoVigilancia(BaseModel):
    """Representación de un puesto de vigilancia o instalación cliente."""

    model_config = ConfigDict(from_attributes=True)

    puesto_id: int
    codigo_puesto: str
    nombre_puesto: str
    empresa_cliente: str
    direccion_ubicacion: str
    ciudad: str
    requiere_armamento: bool
    activo: bool


class CrearPuestoVigilanciaSolicitud(BaseModel):
    """Solicitud para registrar un nuevo puesto de vigilancia."""

    codigo_puesto: str = Field(..., min_length=3, max_length=30)
    nombre_puesto: str = Field(..., min_length=3, max_length=120)
    empresa_cliente: str = Field(..., min_length=3, max_length=120)
    direccion_ubicacion: str = Field(..., min_length=5, max_length=200)
    ciudad: str = Field(default="Bogotá D.C.", max_length=80)
    requiere_armamento: bool = False


# ============================================================================
# MÓDULO 2: MOTOR INTELIGENTE DE TURNOS 2X2 Y LEY 2101 DE 2021 (42H SEMANALES)
# ============================================================================
class DesgloseLaboralColombiano(BaseModel):
    """Resultado del cálculo de horas y recargos según Ley 2101 (42h) y CST."""

    horas_totales: float
    horas_ordinarias: float
    horas_recargo_nocturno: float
    horas_extras_diurnas: float
    horas_extras_nocturnas: float
    horas_dominicales_festivas: float
    horas_descuento_ausentismo: float = 0.0
    costo_estimado_cop: float


class SolicitudGenerarRotacion2x2(BaseModel):
    """Parámetros para programar automáticamente el esquema rotativo 2x2 individual."""

    operador_id: int
    puesto_id: int
    fecha_inicio_ciclo: date
    cantidad_ciclos_6_dias: int = Field(default=2, ge=1, le=6)
    reemplazar_existentes: bool = True


class SolicitudGenerarCoberturaPuesto2x2(BaseModel):
    """Parámetros para programar la rotación continua 24/7 de un puesto."""

    puesto_id: int
    operadores_ids: list[int] | None = None
    fecha_inicio_ciclo: date
    cantidad_dias: int = Field(default=30, ge=6, le=90)
    reemplazar_existentes: bool = True


class RespuestaTurno(BaseModel):
    """Representación detallada de un turno operativo con cálculos laborales y ausentismos."""

    turno_id: int
    operador_id: int
    nombre_operador: str
    codigo_placa_operador: str
    puesto_id: int
    nombre_puesto: str
    codigo_puesto: str
    tipo_turno: TipoTurno
    estado_turno: EstadoTurno
    fecha_inicio: datetime
    fecha_fin: datetime
    horas_totales: float
    horas_ordinarias: float
    horas_recargo_nocturno: float
    horas_extras_diurnas: float
    horas_extras_nocturnas: float
    horas_dominicales_festivas: float
    horas_descuento_ausentismo: float = 0.0
    motivo_ausentismo: str | None = None
    costo_estimado_cop: float
    observaciones: str | None = None


class ResumenLiquidacionTurnos(BaseModel):
    """Consolidado estadístico de horas, ausentismos y costos según Ley 2101 (42h semanales)."""

    tope_horas_semanales_aplicado: int = 42
    total_turnos_operativos: int
    total_dias_descanso: int
    suma_horas_trabajadas: float
    suma_horas_ordinarias: float
    suma_horas_recargo_nocturno: float
    suma_horas_extras_diurnas: float
    suma_horas_extras_nocturnas: float
    suma_horas_dominicales_festivas: float
    suma_horas_descuento_ausentismo: float = 0.0
    costo_total_estimado_cop: float
    turnos: list[RespuestaTurno]


class CandidatoRelevanteSugerido(BaseModel):
    """Guarda sugerido por el motor inteligente para cubrir un turno descubierto."""

    usuario_id: int
    nombre_completo: str
    codigo_placa: str
    numero_credencial_sv: str | None = None
    credencial_vigente: bool
    en_dia_descanso: bool
    horas_descanso_previas: float
    horas_extras_acumuladas_semana: float
    puntaje_idoneidad: str


class AsignarRelevanteTurnoSolicitud(BaseModel):
    """Solicitud para asignar en 1 clic a un guarda relevante en un turno descubierto."""

    operador_reemplazo_id: int
    observacion_asignacion: str = "Reemplazo asignado por motor inteligente de relevantes"


# ============================================================================
# MÓDULO 3: MINUTA DIGITAL EN TIEMPO REAL CON VISIBILIDAD DUAL
# ============================================================================
class CrearRegistroMinutaSolicitud(BaseModel):
    """Datos enviados por el operador o supervisor para asentar una anotación en minuta."""

    puesto_id: int
    tipo_registro: TipoRegistroMinuta
    visibilidad: VisibilidadMinuta = VisibilidadMinuta.PUBLICA_CLIENTE
    nivel_prioridad: NivelPrioridad = NivelPrioridad.MEDIA
    titulo_evento: str = Field(..., min_length=4, max_length=150)
    descripcion_detallada: str = Field(..., min_length=6, max_length=2000)
    nombre_visitante: str | None = Field(default=None, max_length=120)
    documento_visitante: str | None = Field(default=None, max_length=40)
    placa_vehiculo: str | None = Field(default=None, max_length=20)


class RespuestaRegistroMinuta(BaseModel):
    """Evento de minuta enriquecido con visibilidad dual y datos del operador/puesto."""

    registro_id: int
    operador_id: int
    nombre_operador: str
    codigo_placa_operador: str
    puesto_id: int
    nombre_puesto: str
    codigo_puesto: str
    tipo_registro: TipoRegistroMinuta
    visibilidad: VisibilidadMinuta = VisibilidadMinuta.PUBLICA_CLIENTE
    nivel_prioridad: NivelPrioridad
    titulo_evento: str
    descripcion_detallada: str
    nombre_visitante: str | None = None
    documento_visitante: str | None = None
    placa_vehiculo: str | None = None
    fecha_registro: datetime


# ============================================================================
# MÓDULO 4: SISTEMA DE INTERCAMBIO DE TURNOS
# ============================================================================
class CrearSolicitudIntercambio(BaseModel):
    """Petición de intercambio de turno entre dos guardias."""

    turno_origen_id: int
    turno_destino_id: int
    motivo_solicitud: str = Field(..., min_length=6, max_length=500)


class ResolverSolicitudIntercambio(BaseModel):
    """Decisión de un Supervisor o Administrador sobre una solicitud de intercambio."""

    aprobar: bool
    comentario_supervisor: str = Field(..., min_length=4, max_length=500)


class RespuestaSolicitudIntercambio(BaseModel):
    """Detalle completo de una solicitud de intercambio y su dictamen técnico."""

    intercambio_id: int
    operador_solicitante_id: int
    nombre_solicitante: str
    operador_receptor_id: int
    nombre_receptor: str
    turno_origen_id: int
    resumen_turno_origen: str
    turno_destino_id: int
    resumen_turno_destino: str
    motivo_solicitud: str
    estado_solicitud: EstadoSolicitudIntercambio
    validacion_sin_cruces: bool
    horas_descanso_minimo_calculadas: float
    detalle_validacion_motor: str
    supervisor_validador_id: int | None = None
    nombre_supervisor: str | None = None
    comentario_supervisor: str | None = None
    fecha_solicitud: datetime
    fecha_resolucion: datetime | None = None


# ============================================================================
# FASES 5, 6 Y 7: RONDAS QR/GPS, COLA OFFLINE, AUDITORÍA Y REPORTES
# ============================================================================
class RespuestaPuntoControlRonda(BaseModel):
    """Punto de control QR/GPS configurado en un puesto de vigilancia."""

    model_config = ConfigDict(from_attributes=True)

    punto_id: int
    puesto_id: int
    codigo_qr_hash: str
    nombre_punto: str
    latitud_gps: float
    longitud_gps: float
    radio_tolerancia_metros: float
    orden_secuencia: int
    activo: bool


class RegistrarMarcacionRondaSolicitud(BaseModel):
    """Datos enviados al escanear un checkpoint QR/GPS en campo o desde cola offline."""

    punto_id: int
    latitud_capturada: float
    longitud_capturada: float
    observacion_ronda: str = Field(..., min_length=4, max_length=500)
    sincronizado_desde_offline: bool = False


class SincronizarLoteOfflineSolicitud(BaseModel):
    """Lote de marcaciones almacenadas en IndexedDB/LocalStorage durante desconexión."""

    marcaciones: list[RegistrarMarcacionRondaSolicitud]


class RespuestaMarcacionRonda(BaseModel):
    """Resultado de una marcación de ronda con verificación geodésica Haversine."""

    marcacion_id: int
    punto_id: int
    nombre_punto: str
    codigo_qr_hash: str
    operador_id: int
    nombre_operador: str
    latitud_capturada: float
    longitud_capturada: float
    distancia_calculada_metros: float
    dentro_de_geocerca: bool
    sincronizado_desde_offline: bool
    observacion_ronda: str
    fecha_marcacion: datetime


class AlertaCoberturaPuesto(BaseModel):
    """Estado de cobertura y cumplimiento de relevo en un puesto de vigilancia."""

    puesto_id: int
    codigo_puesto: str
    nombre_puesto: str
    estado_cobertura: str
    nivel_alerta: NivelPrioridad
    operador_en_turno: str
    puntos_control_verificados: int
    total_puntos_control: int
    detalle_operativo: str


# ============================================================================
# RELEASE ENTERPRISE V2.0: ARMAMENTO INDUMIL, ACTA RELEVO, AUSENTISMOS Y SOS
# ============================================================================
class RespuestaDotacionPuesto(BaseModel):
    """Inventario oficial de armamento Indumil y elementos tácticos de un puesto."""

    model_config = ConfigDict(from_attributes=True)

    dotacion_id: int
    puesto_id: int
    tipo_arma: str
    serial_arma: str
    numero_salvoconducto_indumil: str
    tipo_salvoconducto: str
    fecha_vencimiento_salvoconducto: date
    cantidad_municion_autorizada: int
    serial_chaleco_balistico: str
    serie_radio_comunicacion: str
    celular_corporativo_imei: str
    tiene_linterna_tactica: bool
    llaves_y_minutas_fisicas: bool


class CrearActaRelevoSolicitud(BaseModel):
    """Checklist de entrega/recibo de puesto diligenciado en cambio de turno de 12h."""

    puesto_id: int
    operador_entrante_id: int | None = None
    estado_armamento: EstadoItemDotacion = EstadoItemDotacion.OPTIMO
    municion_verificada: int = Field(..., ge=0, le=200)
    estado_chaleco: EstadoItemDotacion = EstadoItemDotacion.OPTIMO
    estado_radio: EstadoItemDotacion = EstadoItemDotacion.OPTIMO
    estado_linterna_y_llaves: EstadoItemDotacion = EstadoItemDotacion.OPTIMO
    observaciones_relevo: str = Field(..., min_length=5, max_length=1000)


class RespuestaActaRelevo(BaseModel):
    """Acta firmada criptográficamente con SHA-256 tras verificación de puesto y armamento."""

    acta_id: int
    puesto_id: int
    nombre_puesto: str
    codigo_puesto: str
    operador_saliente_id: int
    nombre_operador_saliente: str
    operador_entrante_id: int | None = None
    nombre_operador_entrante: str | None = None
    estado_armamento: EstadoItemDotacion
    municion_verificada: int
    estado_chaleco: EstadoItemDotacion
    estado_radio: EstadoItemDotacion
    estado_linterna_y_llaves: EstadoItemDotacion
    observaciones_relevo: str
    sello_sha256: str
    alerta_disparada: bool
    fecha_acta: datetime


class RegistrarAusentismoSolicitud(BaseModel):
    """Registro de incapacidad EPS/ARL, licencia o falta por parte de RRHH o Supervisor."""

    operador_id: int
    turno_afectado_id: int | None = None
    tipo_ausentismo: TipoAusentismo
    fecha_inicio: date
    fecha_fin: date
    horas_descontadas: float = Field(default=12.0, ge=1.0, le=240.0)
    descripcion_soporte: str = Field(..., min_length=5, max_length=500)


class RespuestaAusentismo(BaseModel):
    """Representación enriquecida de un registro de ausentismo y su impacto en nómina."""

    ausentismo_id: int
    operador_id: int
    nombre_operador: str
    codigo_placa: str
    turno_afectado_id: int | None = None
    tipo_ausentismo: TipoAusentismo
    fecha_inicio: date
    fecha_fin: date
    horas_descontadas: float
    descripcion_soporte: str
    registrado_por_id: int
    nombre_registrador: str
    reemplazo_asignado_id: int | None = None
    nombre_reemplazo: str | None = None
    fecha_registro: datetime


class DispararAlertaSosSolicitud(BaseModel):
    """Datos enviados por el Botón de Pánico Táctico SOS desde el puesto de guardia."""

    puesto_id: int
    latitud_gps: float
    longitud_gps: float


class AtenderAlertaSosSolicitud(BaseModel):
    """Registro de reacción táctica del Supervisor o Administrador ante una alerta SOS."""

    nota_reaccion: str = Field(..., min_length=5, max_length=500)


class RespuestaAlertaSos(BaseModel):
    """Estado detallado de una Alerta de Pánico SOS y su tiempo de reacción."""

    alerta_id: int
    operador_id: int
    nombre_operador: str
    codigo_placa_operador: str
    puesto_id: int
    nombre_puesto: str
    codigo_puesto: str
    latitud_gps: float
    longitud_gps: float
    estado_alerta: EstadoAlertaSos
    fecha_activacion: datetime
    atendida_por_id: int | None = None
    nombre_supervisor_atendio: str | None = None
    fecha_atencion: datetime | None = None
    tiempo_reaccion_segundos: int | None = None
    nota_reaccion: str | None = None


# ============================================================================
# MÓDULO 8: TARIFICACIÓN LEGAL SUPERVIGILANCIA Y FACTURACIÓN B2B (V3.0)
# ============================================================================
class SolicitudCotizacionTarifa(BaseModel):
    """Parámetros para simulación tarifaria legal de un puesto."""

    modalidad_servicio: ModalidadServicioTarifa
    cantidad_puestos: int = Field(default=1, ge=1, le=100)
    porcentaje_administracion: float = Field(default=0.10, ge=0.08, le=0.30)
    smlmv: float = Field(default=1_423_500.0, ge=1_000_000.0)
    auxilio_transporte: float = Field(default=200_000.0, ge=0.0)


class RespuestaDesgloseCotizacion(BaseModel):
    """Desglose detallado de la cotización según regulación SuperVigilancia."""

    modalidad_servicio: ModalidadServicioTarifa
    cantidad_puestos: int
    guardas_por_puesto: int
    total_guardas_requeridos: int
    costo_laboral_unitario_guarda: float
    costo_mano_obra_total: float
    costo_armamento_y_equipos: float
    costo_administracion_aiu: float
    subtotal_antes_iva: float
    iva_dian: float
    tarifa_total_factura_cop: float
    tarifa_minima_supervigilancia: float


class SolicitudGenerarPrefactura(BaseModel):
    """Solicitud para emitir una prefactura legal B2B para un cliente."""

    cliente_id: int
    puesto_id: int | None = None
    mes_servicio: str = Field(..., pattern=r"^\d{4}-\d{2}$")  # Ej: "2026-10"
    modalidad_servicio: ModalidadServicioTarifa
    cantidad_puestos: int = Field(default=1, ge=1, le=100)
    porcentaje_administracion: float = Field(default=0.10, ge=0.08, le=0.30)
    notas_comerciales: str | None = Field(default=None, max_length=500)


class RespuestaPrefactura(BaseModel):
    """Detalle completo de una prefactura legal generada."""

    model_config = ConfigDict(from_attributes=True)

    prefactura_id: int
    codigo_factura: str
    cliente_id: int
    nombre_cliente: str
    puesto_id: int | None = None
    nombre_puesto: str | None = None
    mes_servicio: str
    modalidad_servicio: ModalidadServicioTarifa
    cantidad_puestos: int
    cantidad_guardas_requeridos: int
    costo_mano_obra_cop: float
    costo_armamento_cop: float
    costo_administracion_cop: float
    subtotal_cop: float
    iva_cop: float
    total_factura_cop: float
    estado_factura: EstadoFactura
    notas_comerciales: str | None = None
    firma_digital_sha256: str
    fecha_emision: datetime
    fecha_vencimiento: date


# ============================================================================
# MÓDULO 9: CONTROL DE ACCESO GARITA Y ESCÁNER CÉDULAS PDF417 (V3.0 FASE 9)
# ============================================================================
class SolicitudDecodificarCedula(BaseModel):
    """Trama cruda del código de barras PDF417 de la cédula colombiana."""

    trama_cruda: str = Field(..., min_length=10)


class RespuestaCedulaColombiana(BaseModel):
    """Datos estructurados obtenidos de la cédula colombiana."""

    documento_identidad: str
    primer_apellido: str
    segundo_apellido: str
    primer_nombre: str
    segundo_nombre: str
    nombre_completo: str
    sexo: str
    fecha_nacimiento: date | None = None
    grupo_sanguineo_rh: str
    es_valido: bool
    mensaje_validacion: str


class SolicitudRegistrarAccesoGarita(BaseModel):
    """Registro de ingreso de visitante, vehículo o contratista en garita."""

    puesto_id: int
    tipo_acceso: TipoAccesoGarita = TipoAccesoGarita.PEATONAL_VISITANTE
    documento_identidad: str = Field(..., min_length=5, max_length=30)
    nombres: str = Field(..., min_length=2, max_length=100)
    apellidos: str = Field(..., min_length=2, max_length=100)
    tipo_sangre_rh: str | None = Field(default=None, max_length=10)
    placa_vehiculo: str | None = Field(default=None, max_length=15)
    empresa_o_destino: str = Field(..., min_length=2, max_length=120)
    motivo_ingreso: str = Field(..., min_length=3, max_length=200)
    observaciones: str | None = Field(default=None, max_length=500)


class RespuestaAccesoGarita(BaseModel):
    """Representación enriquecida de un evento de acceso a las instalaciones."""

    model_config = ConfigDict(from_attributes=True)

    acceso_id: int
    puesto_id: int
    nombre_puesto: str
    operador_id: int
    nombre_operador: str
    tipo_acceso: TipoAccesoGarita
    documento_identidad: str
    nombres: str
    apellidos: str
    nombre_completo: str
    tipo_sangre_rh: str | None = None
    placa_vehiculo: str | None = None
    empresa_o_destino: str
    motivo_ingreso: str
    es_sospechoso_alerta: bool
    estado_acceso: EstadoAccesoGarita
    fecha_ingreso: datetime
    fecha_salida: datetime | None = None
    observaciones: str | None = None


# ============================================================================
# MÓDULO 10: LIBRO BALÍSTICO DIGITAL Y TRAZABILIDAD INDUMIL DCCA (V3.0 FASE 10)
# ============================================================================
class SolicitudRegistrarMovimientoBalistico(BaseModel):
    """Registro de consumo, práctica o reposición de munición y armamento."""

    puesto_id: int
    dotacion_id: int
    tipo_movimiento: TipoMovimientoBalistico
    calibre: str = Field(..., min_length=2, max_length=30)
    cantidad_municion_afectada: int = Field(..., ge=1, le=100)
    justificacion_novedad: str = Field(..., min_length=5, max_length=500)
    numero_oficio_dcca: str | None = Field(default=None, max_length=50)


class RespuestaMovimientoBalistico(BaseModel):
    """Detalle de movimiento en el Libro Balístico oficial."""

    model_config = ConfigDict(from_attributes=True)

    movimiento_id: int
    puesto_id: int
    nombre_puesto: str
    dotacion_id: int
    tipo_arma: str
    serial_arma: str
    operador_responsable_id: int
    nombre_operador: str
    tipo_movimiento: TipoMovimientoBalistico
    calibre: str
    cantidad_municion_afectada: int
    saldo_municion_resultante: int
    justificacion_novedad: str
    numero_oficio_dcca: str | None = None
    firma_digital_sha256: str
    fecha_movimiento: datetime


class SolicitudRegistrarCertificadoPoligono(BaseModel):
    """Registro de calificación de tiro reglamentario."""

    operador_id: int
    academia_seguridad: str = Field(..., min_length=3, max_length=120)
    tipo_arma_calificada: str = Field(..., min_length=3, max_length=50)
    puntaje_precision: float = Field(..., ge=0.0, le=100.0)
    aprobado: bool = True
    fecha_practica: date


class RespuestaCertificadoPoligono(BaseModel):
    """Detalle del certificado de tiro acreditado."""

    model_config = ConfigDict(from_attributes=True)

    certificado_id: int
    operador_id: int
    nombre_operador: str
    academia_seguridad: str
    tipo_arma_calificada: str
    puntaje_precision: float
    aprobado: bool
    fecha_practica: date
    fecha_vencimiento_anual: date


# ============================================================================
# MÓDULO 11: CENTRO DE DESPACHO CAD Y MONITOREO GPS EN VIVO (V3.0 FASE 11)
# ============================================================================
class SolicitudDespacharPatrulla(BaseModel):
    """Orden de despacho de una patrulla motorizada hacia una emergencia SOS."""

    alerta_sos_id: int
    supervisor_id: int
    nota_despacho: str | None = Field(default=None, max_length=300)


class SolicitudCierreDespacho(BaseModel):
    """Reporte táctico de arribo y cierre de la reacción motorizada."""

    informe_tactico_cierre: str = Field(..., min_length=5, max_length=1000)


class RespuestaDespachoPatrulla(BaseModel):
    """Telemetría y estado de una orden de despacho CAD."""

    model_config = ConfigDict(from_attributes=True)

    despacho_id: int
    alerta_sos_id: int
    supervisor_id: int
    nombre_supervisor: str
    codigo_placa_supervisor: str
    puesto_id: int
    nombre_puesto: str
    coordenadas_puesto: tuple[float, float]
    distancia_km_calculada: float
    eta_minutos_estimado: float
    estado_despacho: EstadoDespachoPatrulla
    fecha_despacho: datetime
    fecha_llegada_sitio: datetime | None = None
    tiempo_arribo_segundos: int | None = None
    informe_tactico_cierre: str | None = None



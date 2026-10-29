"""
Esquemas de validación estricta Pydantic v2 para SENTINEL // OPS (Release Enterprise V2.0).
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modelos.modelos_bd import (
    EstadoAlertaSos,
    EstadoItemDotacion,
    EstadoSolicitudIntercambio,
    EstadoTurno,
    NivelCursoVigilancia,
    NivelPrioridad,
    RolUsuario,
    TipoAusentismo,
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

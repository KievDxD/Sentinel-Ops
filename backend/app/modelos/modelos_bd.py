"""
Modelos relacionales SQLAlchemy 2.0 para SENTINEL // OPS (Release Enterprise V2.0).
Todas las tablas, columnas, enumeraciones y relaciones están 100% en español.
"""

from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.nucleo.base_datos import BaseModeloDeclarativo


def obtener_hora_utc() -> datetime:
    """Retorna la fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


class RolUsuario(str, Enum):
    """Roles del sistema para el Control de Acceso Basado en Roles (RBAC de 5 Niveles)."""

    ADMINISTRADOR = "ADMINISTRADOR"
    SUPERVISOR = "SUPERVISOR"
    RRHH = "RRHH"
    OPERADOR = "OPERADOR"
    CLIENTE = "CLIENTE"


class NivelCursoVigilancia(str, Enum):
    """Niveles de capacitación acreditados ante la SuperVigilancia."""

    FUNDAMENTACION = "FUNDAMENTACION"
    REENTRENAMIENTO = "REENTRENAMIENTO"
    ESPECIALIZACION = "ESPECIALIZACION"


class TipoTurno(str, Enum):
    """Tipos de turno dentro del esquema rotativo 2x2."""

    DIURNO = "DIURNO"
    NOCTURNO = "NOCTURNO"
    DESCANSO = "DESCANSO"


class EstadoTurno(str, Enum):
    """Estados operativos de un turno asignado."""

    PROGRAMADO = "PROGRAMADO"
    EN_CURSO = "EN_CURSO"
    COMPLETADO = "COMPLETADO"
    INTERCAMBIADO = "INTERCAMBIADO"
    DESCUBIERTO_PARCIAL = "DESCUBIERTO_PARCIAL"


class TipoRegistroMinuta(str, Enum):
    """Categorías operativas para la Minuta Digital en Tiempo Real."""

    INGRESO_VISITANTE = "INGRESO_VISITANTE"
    INGRESO_VEHICULO = "INGRESO_VEHICULO"
    RONDA_CONTROL = "RONDA_CONTROL"
    NOVEDAD_INCIDENTE = "NOVEDAD_INCIDENTE"
    RELEVO_TURNO = "RELEVO_TURNO"
    ENTREGA_RECIBO_PUESTO = "ENTREGA_RECIBO_PUESTO"
    ALERTA_PANICO_SOS = "ALERTA_PANICO_SOS"


class VisibilidadMinuta(str, Enum):
    """Control de visibilidad dual para eventos de la Minuta Digital."""

    PUBLICA_CLIENTE = "PUBLICA_CLIENTE"
    INTERNA_OPERATIVA = "INTERNA_OPERATIVA"


class NivelPrioridad(str, Enum):
    """Niveles de criticidad de los eventos registrados en la minuta digital."""

    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class EstadoSolicitudIntercambio(str, Enum):
    """Estados del flujo de intercambio de turnos entre operadores y supervisores."""

    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"


class EstadoItemDotacion(str, Enum):
    """Estados de verificación en el checklist de entrega/recibo de puesto."""

    OPTIMO = "OPTIMO"
    NOVEDAD = "NOVEDAD"
    FALTANTE = "FALTANTE"


class TipoAusentismo(str, Enum):
    """Categorías legales de ausentismo laboral en Colombia."""

    INCAPACIDAD_EPS = "INCAPACIDAD_EPS"
    INCAPACIDAD_ARL = "INCAPACIDAD_ARL"
    LICENCIA_REMUNERADA = "LICENCIA_REMUNERADA"
    FALTA_INJUSTIFICADA = "FALTA_INJUSTIFICADA"
    ABANDONO_PUESTO = "ABANDONO_PUESTO"


class EstadoAlertaSos(str, Enum):
    """Estados operativos de una alerta de pánico SOS."""

    ACTIVA = "ACTIVA"
    ATENDIDA = "ATENDIDA"


class ModeloUsuario(BaseModeloDeclarativo):
    """Tabla `usuarios` que almacena los 5 roles RBAC y sus credenciales SuperVigilancia."""

    __tablename__ = "usuarios"

    usuario_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    documento_identidad: Mapped[str] = mapped_column(
        String(30), unique=True, index=True, nullable=False
    )
    nombre_completo: Mapped[str] = mapped_column(String(120), nullable=False)
    correo_electronico: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    contrasena_encriptada: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(
        SqlEnum(RolUsuario, name="enum_rol_usuario"),
        nullable=False,
        default=RolUsuario.OPERADOR,
    )
    codigo_placa: Mapped[str] = mapped_column(String(30), nullable=False)
    puesto_base_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("puestos_vigilancia.puesto_id"), nullable=True
    )
    # Credenciales SuperVigilancia y Curso de Fundamentación (V2.0)
    numero_credencial_sv: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    fecha_vencimiento_credencial: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    fecha_vencimiento_psicofisico: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    nivel_curso: Mapped[NivelCursoVigilancia | None] = mapped_column(
        SqlEnum(NivelCursoVigilancia, name="enum_nivel_curso"),
        default=NivelCursoVigilancia.FUNDAMENTACION,
        nullable=True,
    )
    excepcion_credencial_autorizada: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=obtener_hora_utc, nullable=False
    )

    turnos_asignados: Mapped[list["ModeloTurno"]] = relationship(
        "ModeloTurno",
        back_populates="operador",
        cascade="all, delete-orphan",
    )
    registros_minuta: Mapped[list["ModeloRegistroMinuta"]] = relationship(
        "ModeloRegistroMinuta",
        back_populates="operador",
    )


class ModeloPuestoVigilancia(BaseModeloDeclarativo):
    """Tabla `puestos_vigilancia` que representa las sedes o instalaciones protegidas."""

    __tablename__ = "puestos_vigilancia"

    puesto_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    codigo_puesto: Mapped[str] = mapped_column(
        String(30), unique=True, index=True, nullable=False
    )
    nombre_puesto: Mapped[str] = mapped_column(String(120), nullable=False)
    empresa_cliente: Mapped[str] = mapped_column(String(120), nullable=False)
    direccion_ubicacion: Mapped[str] = mapped_column(String(200), nullable=False)
    ciudad: Mapped[str] = mapped_column(
        String(80), default="Bogotá D.C.", nullable=False
    )
    requiere_armamento: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    turnos: Mapped[list["ModeloTurno"]] = relationship(
        "ModeloTurno",
        back_populates="puesto_vigilancia",
    )
    registros_minuta: Mapped[list["ModeloRegistroMinuta"]] = relationship(
        "ModeloRegistroMinuta",
        back_populates="puesto_vigilancia",
    )


class ModeloTurno(BaseModeloDeclarativo):
    """
    Tabla `turnos` gestionada por el Motor Inteligente de Turnos 2x2.
    Almacena horarios y el desglose automático según Ley 2101 de 2021 (42h) y CST.
    """

    __tablename__ = "turnos"

    turno_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    operador_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), index=True, nullable=False
    )
    puesto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("puestos_vigilancia.puesto_id"), index=True, nullable=False
    )
    tipo_turno: Mapped[TipoTurno] = mapped_column(
        SqlEnum(TipoTurno, name="enum_tipo_turno"), nullable=False
    )
    estado_turno: Mapped[EstadoTurno] = mapped_column(
        SqlEnum(EstadoTurno, name="enum_estado_turno"),
        default=EstadoTurno.PROGRAMADO,
        nullable=False,
    )
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    fecha_fin: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    # Cálculos automáticos de normativa laboral colombiana
    horas_totales: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    horas_ordinarias: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    horas_recargo_nocturno: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    horas_extras_diurnas: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    horas_extras_nocturnas: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    horas_dominicales_festivas: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    horas_descuento_ausentismo: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    motivo_ausentismo: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    costo_estimado_cop: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    operador: Mapped["ModeloUsuario"] = relationship(
        "ModeloUsuario", back_populates="turnos_asignados"
    )
    puesto_vigilancia: Mapped["ModeloPuestoVigilancia"] = relationship(
        "ModeloPuestoVigilancia", back_populates="turnos"
    )


class ModeloRegistroMinuta(BaseModeloDeclarativo):
    """
    Tabla `registros_minuta` para la Minuta Digital en Tiempo Real con Visibilidad Dual.
    """

    __tablename__ = "registros_minuta"

    registro_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    operador_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), index=True, nullable=False
    )
    puesto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("puestos_vigilancia.puesto_id"), index=True, nullable=False
    )
    tipo_registro: Mapped[TipoRegistroMinuta] = mapped_column(
        SqlEnum(TipoRegistroMinuta, name="enum_tipo_registro_minuta"),
        nullable=False,
    )
    visibilidad: Mapped[VisibilidadMinuta] = mapped_column(
        SqlEnum(VisibilidadMinuta, name="enum_visibilidad_minuta"),
        default=VisibilidadMinuta.PUBLICA_CLIENTE,
        nullable=False,
    )
    nivel_prioridad: Mapped[NivelPrioridad] = mapped_column(
        SqlEnum(NivelPrioridad, name="enum_nivel_prioridad"),
        default=NivelPrioridad.MEDIA,
        nullable=False,
    )
    titulo_evento: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion_detallada: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_visitante: Mapped[str | None] = mapped_column(String(120), nullable=True)
    documento_visitante: Mapped[str | None] = mapped_column(String(40), nullable=True)
    placa_vehiculo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=obtener_hora_utc, index=True, nullable=False
    )

    operador: Mapped["ModeloUsuario"] = relationship(
        "ModeloUsuario", back_populates="registros_minuta"
    )
    puesto_vigilancia: Mapped["ModeloPuestoVigilancia"] = relationship(
        "ModeloPuestoVigilancia", back_populates="registros_minuta"
    )


class ModeloSolicitudIntercambio(BaseModeloDeclarativo):
    """
    Tabla `solicitudes_intercambio` para el Sistema de Intercambio de Turnos.
    """

    __tablename__ = "solicitudes_intercambio"

    intercambio_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    operador_solicitante_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), index=True, nullable=False
    )
    operador_receptor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), index=True, nullable=False
    )
    turno_origen_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("turnos.turno_id"), nullable=False
    )
    turno_destino_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("turnos.turno_id"), nullable=False
    )
    motivo_solicitud: Mapped[str] = mapped_column(Text, nullable=False)
    estado_solicitud: Mapped[EstadoSolicitudIntercambio] = mapped_column(
        SqlEnum(EstadoSolicitudIntercambio, name="enum_estado_intercambio"),
        default=EstadoSolicitudIntercambio.PENDIENTE,
        nullable=False,
    )
    validacion_sin_cruces: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    horas_descanso_minimo_calculadas: Mapped[float] = mapped_column(
        Float, default=12.0, nullable=False
    )
    detalle_validacion_motor: Mapped[str] = mapped_column(Text, nullable=False)
    supervisor_validador_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), nullable=True
    )
    comentario_supervisor: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_solicitud: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=obtener_hora_utc, nullable=False
    )
    fecha_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ModeloPuntoControlRonda(BaseModeloDeclarativo):
    """
    Tabla `puntos_control_ronda` (Fase 5) que almacena los checkpoints físicos QR/GPS.
    """

    __tablename__ = "puntos_control_ronda"

    punto_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    puesto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("puestos_vigilancia.puesto_id"), index=True, nullable=False
    )
    codigo_qr_hash: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    nombre_punto: Mapped[str] = mapped_column(String(120), nullable=False)
    latitud_gps: Mapped[float] = mapped_column(Float, nullable=False)
    longitud_gps: Mapped[float] = mapped_column(Float, nullable=False)
    radio_tolerancia_metros: Mapped[float] = mapped_column(
        Float, default=50.0, nullable=False
    )
    orden_secuencia: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ModeloMarcacionRonda(BaseModeloDeclarativo):
    """
    Tabla `marcaciones_ronda` (Fase 5) que registra cada verificación de punto QR/GPS.
    """

    __tablename__ = "marcaciones_ronda"

    marcacion_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    punto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("puntos_control_ronda.punto_id"),
        index=True,
        nullable=False,
    )
    operador_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), index=True, nullable=False
    )
    latitud_capturada: Mapped[float] = mapped_column(Float, nullable=False)
    longitud_capturada: Mapped[float] = mapped_column(Float, nullable=False)
    distancia_calculada_metros: Mapped[float] = mapped_column(Float, nullable=False)
    dentro_de_geocerca: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sincronizado_desde_offline: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    observacion_ronda: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_marcacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=obtener_hora_utc, index=True, nullable=False
    )


class ModeloDotacionPuesto(BaseModeloDeclarativo):
    """
    Tabla `dotacion_armamento_puesto` (V2.0): Inventario y Armamento Indumil de cada puesto.
    """

    __tablename__ = "dotacion_armamento_puesto"

    dotacion_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    puesto_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("puestos_vigilancia.puesto_id"),
        unique=True,
        index=True,
        nullable=False,
    )
    tipo_arma: Mapped[str] = mapped_column(String(80), nullable=False)
    serial_arma: Mapped[str] = mapped_column(String(60), nullable=False)
    numero_salvoconducto_indumil: Mapped[str] = mapped_column(
        String(60), nullable=False
    )
    tipo_salvoconducto: Mapped[str] = mapped_column(
        String(30), default="TENENCIA", nullable=False
    )
    fecha_vencimiento_salvoconducto: Mapped[date] = mapped_column(
        Date, nullable=False
    )
    cantidad_municion_autorizada: Mapped[int] = mapped_column(
        Integer, default=18, nullable=False
    )
    serial_chaleco_balistico: Mapped[str] = mapped_column(
        String(60), nullable=False
    )
    serie_radio_comunicacion: Mapped[str] = mapped_column(
        String(60), nullable=False
    )
    celular_corporativo_imei: Mapped[str] = mapped_column(
        String(60), nullable=False
    )
    tiene_linterna_tactica: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    llaves_y_minutas_fisicas: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )


class ModeloActaRelevoPuesto(BaseModeloDeclarativo):
    """
    Tabla `actas_entrega_puesto` (V2.0): Checklist criptográfico SHA-256 de Entrega y Recibo de Puesto.
    """

    __tablename__ = "actas_entrega_puesto"

    acta_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    puesto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("puestos_vigilancia.puesto_id"), index=True, nullable=False
    )
    operador_saliente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), index=True, nullable=False
    )
    operador_entrante_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), nullable=True
    )
    estado_armamento: Mapped[EstadoItemDotacion] = mapped_column(
        SqlEnum(EstadoItemDotacion, name="enum_estado_item_dotacion"),
        default=EstadoItemDotacion.OPTIMO,
        nullable=False,
    )
    municion_verificada: Mapped[int] = mapped_column(Integer, nullable=False)
    estado_chaleco: Mapped[EstadoItemDotacion] = mapped_column(
        SqlEnum(EstadoItemDotacion, name="enum_estado_chaleco"),
        default=EstadoItemDotacion.OPTIMO,
        nullable=False,
    )
    estado_radio: Mapped[EstadoItemDotacion] = mapped_column(
        SqlEnum(EstadoItemDotacion, name="enum_estado_radio"),
        default=EstadoItemDotacion.OPTIMO,
        nullable=False,
    )
    estado_linterna_y_llaves: Mapped[EstadoItemDotacion] = mapped_column(
        SqlEnum(EstadoItemDotacion, name="enum_estado_linterna"),
        default=EstadoItemDotacion.OPTIMO,
        nullable=False,
    )
    observaciones_relevo: Mapped[str] = mapped_column(Text, nullable=False)
    sello_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    alerta_disparada: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    fecha_acta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=obtener_hora_utc, index=True, nullable=False
    )


class ModeloAusentismo(BaseModeloDeclarativo):
    """
    Tabla `ausentismos_personal` (V2.0): Registro de incapacidades EPS/ARL, licencias y faltas.
    """

    __tablename__ = "ausentismos_personal"

    ausentismo_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    operador_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), index=True, nullable=False
    )
    turno_afectado_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("turnos.turno_id"), nullable=True
    )
    tipo_ausentismo: Mapped[TipoAusentismo] = mapped_column(
        SqlEnum(TipoAusentismo, name="enum_tipo_ausentismo"),
        nullable=False,
    )
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    horas_descontadas: Mapped[float] = mapped_column(
        Float, default=12.0, nullable=False
    )
    descripcion_soporte: Mapped[str] = mapped_column(Text, nullable=False)
    registrado_por_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), nullable=False
    )
    reemplazo_asignado_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), nullable=True
    )
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=obtener_hora_utc, index=True, nullable=False
    )


class ModeloAlertaPanicoSos(BaseModeloDeclarativo):
    """
    Tabla `alertas_panico_sos` (V2.0): Eventos críticos de Botón de Pánico Táctico SOS.
    """

    __tablename__ = "alertas_panico_sos"

    alerta_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    operador_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), index=True, nullable=False
    )
    puesto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("puestos_vigilancia.puesto_id"), index=True, nullable=False
    )
    latitud_gps: Mapped[float] = mapped_column(Float, nullable=False)
    longitud_gps: Mapped[float] = mapped_column(Float, nullable=False)
    estado_alerta: Mapped[EstadoAlertaSos] = mapped_column(
        SqlEnum(EstadoAlertaSos, name="enum_estado_alerta_sos"),
        default=EstadoAlertaSos.ACTIVA,
        nullable=False,
    )
    fecha_activacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=obtener_hora_utc, index=True, nullable=False
    )
    atendida_por_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.usuario_id"), nullable=True
    )
    fecha_atencion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tiempo_reaccion_segundos: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    nota_reaccion: Mapped[str | None] = mapped_column(Text, nullable=True)

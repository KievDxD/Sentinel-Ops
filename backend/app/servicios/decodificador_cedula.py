"""
Servicio especializado en el procesamiento y decodificación del código de barras
bidimensional PDF417 de la Cédula de Ciudadanía Colombiana (Registraduría Nacional).

Formato de trama estándar de la cédula colombiana:
Trama cruda con longitud variable o fija que contiene:
- Documento de identidad (8 a 10 dígitos)
- Primer apellido
- Segundo apellido
- Primer nombre
- Segundo nombre (opcional)
- Sexo (M / F)
- Fecha de nacimiento (AAAAMMDD)
- Factor RH y grupo sanguíneo (O+, O-, A+, A-, B+, B-, AB+, AB-)
"""

from dataclasses import dataclass
from datetime import date
import re
from typing import Any


@dataclass
class DatosCedulaColombiana:
    """Información extraída del código de barras PDF417 de una cédula de ciudadanía."""

    documento_identidad: str
    primer_apellido: str
    segundo_apellido: str
    primer_nombre: str
    segundo_nombre: str
    nombre_completo: str
    sexo: str
    fecha_nacimiento: date | None
    grupo_sanguineo_rh: str
    es_valido: bool
    mensaje_validacion: str


def decodificar_trama_pdf417_colombia(trama_cruda: str) -> DatosCedulaColombiana:
    """
    Decodifica la cadena alfanumérica obtenida por el escáner 2D PDF417 de la cédula colombiana.
    Soporta tramas estándar de cédula física amarilla con hologramas y cédula digital.
    """
    if not trama_cruda or len(trama_cruda.strip()) < 15:
        return DatosCedulaColombiana(
            documento_identidad="",
            primer_apellido="",
            segundo_apellido="",
            primer_nombre="",
            segundo_nombre="",
            nombre_completo="",
            sexo="",
            fecha_nacimiento=None,
            grupo_sanguineo_rh="",
            es_valido=False,
            mensaje_validacion="Trama de código de barras vacía o insuficiente.",
        )

    trama_limpia = trama_cruda.replace("\x00", " ").strip()

    # Patrón 1: Trama típica extraída por pistola 2D USB o escáner móvil:
    # Bloque alfanumérico que contiene la secuencia de cédula, apellidos, nombres, sexo y fecha
    # Ejemplo estándar:
    # "PubDSK_1 0010203040 VARGAS RESTREPO ALEJANDRO JOSE M 19880415 0+"
    # o formato con delimitadores de espacio / tabulación / punto y coma
    partes = re.split(r"[\s\t|;]+", trama_limpia)
    partes = [p.strip() for p in partes if p.strip()]

    # Buscar número de cédula (secuencia de 7 a 10 dígitos)
    numero_cedula = ""
    indice_cedula = -1

    for idx, token in enumerate(partes):
        # A veces viene con ceros a la izquierda (ej: 0010203040)
        token_numerico = re.sub(r"\D", "", token)
        if 7 <= len(token_numerico) <= 10:
            numero_cedula = str(int(token_numerico))  # Quitar ceros a la izquierda
            indice_cedula = idx
            break

    # Si no se encontró por tokens, intentar con regex global en la trama
    if not numero_cedula:
        coincidencias = re.findall(r"\b\d{7,10}\b", trama_limpia)
        if coincidencias:
            numero_cedula = str(int(coincidencias[0]))

    primer_apellido = ""
    segundo_apellido = ""
    primer_nombre = ""
    segundo_nombre = ""
    sexo = "M"
    fecha_nacimiento: date | None = None
    rh = "O+"

    # Detección de Sexo (M o F)
    for t in partes:
        if t.upper() in ("M", "F", "MASCULINO", "FEMENINO"):
            sexo = "M" if t.upper().startswith("M") else "F"
            break

    # Detección de Grupo Sanguíneo y Factor RH (O+, O-, A+, A-, B+, B-, AB+, AB-)
    patron_rh = re.search(r"\b(O|A|B|AB)[\+\-]\b", trama_limpia, re.IGNORECASE)
    if patron_rh:
        rh = patron_rh.group(0).upper()

    # Detección de Fecha de Nacimiento (AAAAMMDD entre 1930 y 2015)
    patron_fecha = re.search(r"\b(19\d{2}|20[0-1]\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\b", trama_limpia)
    if patron_fecha:
        ano = int(patron_fecha.group(1))
        mes = int(patron_fecha.group(2))
        dia = int(patron_fecha.group(3))
        try:
            fecha_nacimiento = date(ano, mes, dia)
        except ValueError:
            fecha_nacimiento = None

    # Palabras a excluir de nombres/apellidos (encabezados de tarjetas, sexo, RH, etc.)
    palabras_reservadas = {"PUBDSK", "PUBDSK_1", "COL", "M", "F", "O", "A", "B", "AB"}

    # Extracción de nombres y apellidos omitiendo identificadores de control y sexo
    tokens_nombre = [
        t for t in partes
        if t.isalpha() and t.upper() not in palabras_reservadas and len(t) > 1
    ]

    if len(tokens_nombre) >= 2:
        primer_apellido = tokens_nombre[0].upper()
        if len(tokens_nombre) >= 3:
            segundo_apellido = tokens_nombre[1].upper()
            primer_nombre = tokens_nombre[2].upper()
            if len(tokens_nombre) >= 4:
                segundo_nombre = " ".join(tokens_nombre[3:]).upper()
        else:
            primer_nombre = tokens_nombre[1].upper()
    elif len(tokens_nombre) == 1:
        primer_nombre = tokens_nombre[0].upper()

    nombres = f"{primer_nombre} {segundo_nombre}".strip()
    apellidos = f"{primer_apellido} {segundo_apellido}".strip()
    nombre_completo = f"{nombres} {apellidos}".strip()

    es_valido = bool(numero_cedula and (primer_nombre or primer_apellido))

    return DatosCedulaColombiana(
        documento_identidad=numero_cedula,
        primer_apellido=primer_apellido,
        segundo_apellido=segundo_apellido,
        primer_nombre=primer_nombre,
        segundo_nombre=segundo_nombre,
        nombre_completo=nombre_completo if nombre_completo else f"Ciudadano CC {numero_cedula}",
        sexo=sexo,
        fecha_nacimiento=fecha_nacimiento,
        grupo_sanguineo_rh=rh,
        es_valido=es_valido,
        mensaje_validacion="Cédula colombiana decodificada correctamente." if es_valido else "Datos incompletos en la trama.",
    )

# SENTINEL // OPS (Release Enterprise V3.0) — Plataforma SaaS B2B para Empresas de Seguridad Privada en Colombia

Plataforma empresarial integral de nivel de producción diseñada para gestionar la operación táctica, armamento Indumil, credenciales SuperVigilancia, turnos rotativos 2x2 de 12 horas, minuta digital con visibilidad dual, alertas de pánico SOS en tiempo real, rondas QR/GPS con soporte Offline-First, tarificación legal SuperVigilancia con facturación B2B, escáner de cédulas PDF417 en garita, libro balístico digital DCCA Indumil, centro de despacho asistido por computadora (CAD) con radar GPS y arquitectura SaaS Multi-Tenant conforme a la legislación colombiana (**Superintendencia de Vigilancia y Seguridad Privada**, **Ley 1920 de 2018**, **Ley 2101 de 2021** de reducción de jornada a 42 horas semanales, **Decreto 2535/1993**, **Art. 462-1 E.T. DIAN** y **Código Sustantivo del Trabajo**).

---

## 1. Módulos Operativos y Regulatorios Enterprise V3.0

### 1.1. Tarificación Legal SuperVigilancia & Facturación B2B (Fase 8)
- **Motor de Tarifas Mínimas Reguladas:** Computa el piso legal mensual por puesto 24/7 (cuadrilla de 4 guardas rotando 2x2 sin exceder la jornada máxima de 42h/semana Ley 2101).
- **Rubros de Ley:** SMLMV + Auxilio de transporte + Factor Prestacional (Cesantías, Prima, Vacaciones 21.83%) + Seguridad Social y Parafiscales (Salud, Pensión, ARL Riesgo V 4.35%, CCF 28.85%) + Dotación y Seguro Colectivo de Vida Ley 1920.
- **Recargo por Armamento Indumil:** 10% adicional regulado sobre el componente de mano de obra en puestos armados.
- **AIU e IVA DIAN:** Margen de Administración e Intermediación regulado (mínimo 10%) e IVA especial del 19% sobre la base de AIU (Art. 462-1 Estatuto Tributario).
- **Prefacturación B2B Foliada:** Generador de prefacturas oficiales con firma criptográfica inmutable SHA-256 y vista HTML lista para imprimir o exportar a PDF.

### 1.2. Control de Acceso en Garita & Escáner de Cédulas PDF417 (Fase 9)
- **Decodificador Nativo PDF417:** Lee la trama alfanumérica bidimensional del reverso de la cédula de ciudadanía colombiana (estándar Registraduría Nacional).
- **Extracción Inmediata:** Extrae documento de identidad, primer apellido, segundo apellido, primer nombre, segundo nombre, sexo, fecha de nacimiento y factor RH/grupo sanguíneo.
- **Gestión de Garita:** Registro de ingresos peatonales y vehiculares (placa), empresa/oficina de destino, motivo y salida con 1 clic.
- **PWA Offline-Ready:** Soporte para funcionamiento en garitas remotas sin conectividad (`manifest.json` y sincronización local).

### 1.3. Libro Balístico Digital & Trazabilidad Indumil DCCA (Fase 10)
- **Semáforo Preventivo de Salvoconductos:** Diagnóstico anticipado de vencimientos ante el Departamento de Control Comercio de Armas (DCCA):
  - `Verde`: > 90 días de vigencia.
  - `Amarillo Preventivo`: 30 a 90 días.
  - `Rojo Crítico`: < 30 días (alerta inmediata para trámite de renovación).
  - `Vencido`: Trámite urgente y bloqueo automático de asignación de arma.
- **Kardex Inmutable de Munición:** Registro de consumo por incidentes, pruebas de polígono y reposiciones con saldo dinámico y firma SHA-256.
- **Acreditación de Pruebas de Tiro:** Registro de certificados de polígono expedidos por academias de seguridad acreditadas con vigencia anual reglamentaria (365 días).

### 1.4. Centro de Despacho CAD & Monitoreo GPS de Patrullas en Vivo (Fase 11)
- **Radar Táctico Cartográfico:** Visualización satelital en tiempo real de puestos fijos y patrullas motorizadas con telemetría GPS.
- **Detección Automática de Proximidad:** Al dispararse un botón de pánico SOS, el motor calcula la distancia geodésica Haversine de todos los supervisores y ordena por cercanía.
- **Cálculo de ETA en Minutos:** Tiempo estimado de arribo calculado en base a velocidad urbana motorizada de emergencia.
- **Flujo de Reacción Certificada:** Despacho formal de la unidad $\rightarrow$ Registro de arribo en sitio con cronómetro en segundos $\rightarrow$ Informe táctico de cierre del incidente.

### 1.5. Arquitectura SaaS Multi-Empresa & Despliegue Cloud (Fase 12)
- **Soporte Multi-Tenant:** Segregación de información por empresa de seguridad privada (`tenant_id`).
- **Respaldo Forense Criptográfico:** Endpoint `/api/reportes/respaldo-forense-cifrado` que consolida minutas, actas, kardex balístico y facturación en un paquete JSON con sello maestro SHA-256 para auditoría de la SuperVigilancia.
- **Despliegue Cloud:** `Dockerfile` multi-stage para producción (frontend Vite + backend FastAPI Uvicorn) listo para Google Cloud Run, AWS ECS o Docker Compose.

### 1.1. Motor Inteligente de Turnos 2x2 (12h) y Nómina Ley 2101 (42 Horas Semanales)
- **Ciclo Rotativo 2x2 (6 Días):** `2 Días (06:00-18:00) → 2 Noches (18:00-06:00) → 2 Descansos Compensatorios (24h Libres)`.
- **Cobertura Continua 24/7 por Puesto (3 Cuadrillas):** Cada puesto cuenta con una escuadra de 3 guardas rotando con desfase de 2 días para garantizar cobertura 24/7 sin puestos descubiertos.
- **Tope Semanal Dinámico Ley 2101 (`tope_horas_semanales = 42`):** El motor contabiliza las horas ordinarias acumuladas en la semana ISO y transiciona automáticamente a horas extras (`+25%` diurna, `+75%` nocturna) al alcanzar el tope de 42h semanales, manteniendo el recargo nocturno (`35%` de `21:00` a `06:00`) y dominical/festivo (`+75%`).
- **Descuento Automático por Ausentismos:** Registro de incapacidades EPS/ARL, licencias remuneradas y faltas con deducción automática en la liquidación y en el CSV contable (Siigo/Novasoft).

### 1.2. Control de Credenciales SuperVigilancia y Curso de Vigilancia
- Semáforo visual de vigencia (`Vigente > 30 días`, `Por Vencer <= 30 días`, `Vencido < hoy`) para credencial SuperVigilancia y examen de aptitud psicofísica.
- **Bloqueo Operativo Automático:** El backend impide programar turnos o aprobar relevos a guardas con credencial vencida, salvo autorización expresa de excepción temporal por un `ADMINISTRADOR`.

### 1.3. Jerarquía RBAC de 5 Niveles
| Rol | Prioridad | Alcance Operativo y Permisos |
| :--- | :--- | :--- |
| **`ADMINISTRADOR`** | Prioridad 1 — Dirección General | Acceso total al Centro de Mando Ejecutivo, KPIs de flota, autorización de excepciones SuperVigilancia, atención de alertas SOS, exportación de Prenómina Ley 2101 y Libro Foliado SHA-256. |
| **`SUPERVISOR`** | Prioridad 2 — Oficial de Operaciones | Consola de Supervisión 24/7: programación 2x2, recepción de sirena y atención de Alertas SOS con tiempo de reacción certificado, motor de relevantes en 1 clic y Libro Foliado SHA-256. |
| **`RRHH`** | Prioridad 2.5 — Gestión Humana y Nómina | Alta y actualización documental de guardas (credenciales SV, exámenes psicofísicos, cursos), registro de ausentismos (EPS/ARL/Licencias) y descarga de Prenómina Contable CSV/Excel. |
| **`OPERADOR`** | Prioridad 3 — Guarda en Puesto | Consola Táctica con **Botón de Pánico SOS** (protección hold 2.5s / doble confirmación), **Acta Digital de Entrega/Recibo de Puesto con Armamento Indumil (SHA-256)**, minuta digital y escáner QR/GPS Offline-First. |
| **`CLIENTE`** | Prioridad 4 — Director del Puesto Contratado | Consola Corporativa de Solo Lectura vinculada exclusivamente a su puesto (`PST-BOG-01`): guarda en turno en tiempo real con vigencia SV, SLA de rondas QR/GPS, **Minuta Filtrada (`PUBLICA_CLIENTE`)** y descarga del Libro Foliado SHA-256 de su instalación (sin acceso a nómina ni costos salariales). |

### 1.4. Módulos Tácticos V2.0
- **Acta Digital de Entrega y Recibo de Puesto (Inventario + Armamento Indumil):** Verificación de arma de dotación (Revólver .38L / Escopeta Cal 12 / No Letal), serial, salvoconducto Indumil, munición exacta, chaleco balístico y radio, generando folio inmutable `SHA-256` en la categoría `ENTREGA_RECIBO_PUESTO`.
- **Botón de Pánico Táctico SOS (WebSockets + Web Audio API):** Emisión inmediata de coordenadas GPS por `/ws/minuta`, banner rojo pulsante con sirena sintetizada por Web Audio API en consolas de supervisión y registro del tiempo exacto de reacción en segundos.
- **Motor Inteligente de Relevantes en 1 Clic:** Sugiere guardas con credencial SV vigente, en día de descanso ($\ge 12\text{h}$ previas) y ordenados de menor a mayor carga de horas extras semanales.
- **Modo Táctico de Campo (Alto Contraste / Sunlight Ready):** Conmutador en el header persistido que transforma la interfaz a fondo negro puro, bordes ámbar de alto contraste y botones táctiles de mínimo `56px`.
- **Aislamiento de Sesión (`sessionStorage`):** Al abrir la aplicación en el navegador siempre se inicia en la pantalla de bienvenida y login (`VistaAccesoTactico`), eliminando autologins residuales.

---

## 2. Ejecución Local

### Opción A: Script Unificado para Git Bash (Recomendado)
```bash
cd "/c/Users/USER/Downloads/SENTINEL  OPS"
bash iniciar.sh
```
*Inicia automáticamente el backend en segundo plano y levanta el frontend en vivo.*

### Opción B: Ejecución Manual en Terminales Separadas

#### Terminal 1 — Backend (FastAPI + Uvicorn)
```bash
# En Git Bash:
cd "/c/Users/USER/Downloads/SENTINEL  OPS/backend"
source .venv/Scripts/activate
python -m uvicorn app.main:aplicacion --host 127.0.0.1 --port 8000 --reload

# En PowerShell:
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:aplicacion --host 127.0.0.1 --port 8000 --reload
```
*API:* `http://127.0.0.1:8000` | *Swagger UI:* `http://127.0.0.1:8000/docs`

#### Terminal 2 — Frontend (Vite + React)
```bash
cd frontend
npm run dev
```
*Aplicación:* `http://localhost:5173/`

---

## 3. Cuentas Semilla para Pruebas (Contraseña para todas: `Sentinel2026*`)

- **Administrador (Prioridad 1):** `admin@sentinelops.co` (`PL-001`)
- **Supervisor (Prioridad 2):** `supervisor@sentinelops.co` (`SUP-101`)
- **RRHH y Nómina (Prioridad 2.5):** `rrhh@sentinelops.co` (`RRH-201`)
- **Guarda Operador (Prioridad 3):** `operador1@sentinelops.co` (`OPR-1001`)
- **Cliente Corporativo (Prioridad 4 — Puesto `PST-BOG-01`):** `cliente@sentinelops.co` (`CLI-901`)

---

## 4. Pruebas y Control de Calidad

```bash
# Tests unitarios e integración (Pytest)
.\backend\.venv\Scripts\pytest.exe backend/tests -v

# Verificación de tipos TypeScript
npm --prefix frontend run build
```

---

## 5. Estado de Ejecución y Cobertura Integral (Release V3.0)
- [x] **Fase 1 a 7:** Autenticación RBAC 5 Niveles, Turnos 2x2, Minuta WebSockets, Relevos Indumil, Rondas QR/GPS y Prenómina Ley 2101 (42h).
- [x] **Fase 8:** Tarificación Mínima Legal SuperVigilancia (SMLMV + factor prestacional) y facturación electrónica B2B con firma SHA-256.
- [x] **Fase 9:** PWA móvil táctica con escaneo de código de barras de cédulas colombianas (PDF417) y control de garita en tiempo real.
- [x] **Fase 10:** Libro Balístico Digital DCCA Indumil, semáforo preventivo de salvoconductos y certificados anuales de tiro.
- [x] **Fase 11:** Centro de Despacho Táctico Asistido por Computadora (CAD) con radar GPS y algoritmo geodésico Haversine.
- [x] **Fase 12:** Arquitectura Cloud Multi-Tenant (`tenant_id`), volcado forense criptográfico y Dockerfile multi-stage de producción.

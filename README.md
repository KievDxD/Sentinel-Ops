# SENTINEL // OPS (Release Enterprise V3.0) — Plataforma SaaS B2B para Empresas de Seguridad Privada en Colombia

Plataforma empresarial integral de nivel de producción diseñada para gestionar la operación táctica, armamento Indumil, credenciales SuperVigilancia, turnos rotativos 2x2 de 12 horas, minuta digital con visibilidad dual, alertas de pánico SOS en tiempo real, rondas QR/GPS con soporte Offline-First, tarificación legal SuperVigilancia con facturación B2B, escáner de cédulas PDF417 en garita, reconocimiento óptico de placas vehiculares (LPR), libro balístico digital DCCA Indumil, centro de despacho asistido por computadora (CAD) con radar GPS, enlace a la Red de Apoyo de la Policía Nacional (PONAL) y arquitectura SaaS Multi-Tenant conforme a la legislación colombiana (**Superintendencia de Vigilancia y Seguridad Privada**, **Ley 1920 de 2018**, **Ley 2101 de 2021** de reducción de jornada a 42 horas semanales, **Decreto 2535/1993**, **Art. 462-1 E.T. DIAN** y **Código Sustantivo del Trabajo**).

---

## 1. Módulos Operativos y Regulatorios Enterprise V3.0

### 1.1. Motor Inteligente de Turnos 2x2 (12h) y Liquidación Laboral (Ley 2101 - 42 Horas Semanales)
- **Ciclo Rotativo 2x2 (6 Días):** `2 Días (06:00-18:00) → 2 Noches (18:00-06:00) → 2 Descansos Compensatorios (24h Libres)`.
- **Cobertura Continua 24/7 por Puesto:** Escuadras operativas sincronizadas para garantizar cobertura ininterrumpida sin puestos descubiertos.
- **Tope Semanal Dinámico Ley 2101 (`tope_horas_semanales = 42`):** El motor contabiliza las horas ordinarias acumuladas en la semana ISO y transiciona automáticamente a horas extras (`+25%` diurna, `+75%` nocturna) al alcanzar el tope de 42h semanales, manteniendo el recargo nocturno (`35%` de `21:00` a `06:00`) y dominical/festivo (`+75%`).
- **Descuento Automático por Ausentismos:** Deducción de incapacidades EPS/ARL, licencias y faltas con cómputo inmediato en la liquidación y en el archivo CSV de prenómina contable (Siigo/Novasoft).
- **Motor de Relevantes en 1 Clic:** Sugiere automáticamente guardas disponibles con credencial vigente, en descanso reglamentario ($\ge 12\text{h}$) y con menor acumulación de horas extras.

### 1.2. Gestión de Personal, Credenciales SuperVigilancia y Carga Masiva CSV
- **Semáforo Documental SuperVigilancia:** Control en tiempo real de vigencia de credenciales de vigilante y exámenes de aptitud psicofísica (`Vigente > 30 días`, `Preventivo <= 30 días`, `Vencido < hoy`).
- **Bloqueo Operativo Automático:** El backend bloquea la programación de turnos y aprobación de relevos a personal con credenciales vencidas, admitiendo excepciones auditadas solo por administradores.
- **Carga Masiva CSV (`POST /api/organizacion/usuarios/importar-csv`):** Importación en lote de nómina y credenciales con detección automática de delimitadores (`,` o `;`), descarga de plantilla oficial, encriptación segura por defecto (`Sentinel2026*`) y protección contra DoS (máx. 2 MB / 1,000 filas).

### 1.3. Minuta Digital en Tiempo Real, Visibilidad Dual y Botón de Pánico SOS
- **Visibilidad Dual:**
  - `PUBLICA_CLIENTE`: Accesible para auditores de la empresa cliente en su instalación (ingresos, novedades generales, relevos conformes).
  - `INTERNA_OPERATIVA`: Restringida a la central de seguridad (incidentes críticos, alertas de armamento y novedades disciplinarias).
- **WebSockets Bidireccionales (`/ws/minuta`):** Difusión instantánea de folios, relevos y alertas a todas las consolas conectadas.
- **Botón de Pánico Táctico SOS:** Activación inmediata con protección contra pulsaciones accidentales (hold 2.5s / confirmación táctil), disparo de sirena sintetizada con Web Audio API en consolas de supervisión y medición de tiempo de reacción certificado en segundos.

### 1.4. Actas Oficiales Foliadas de Relevo con Armamento Indumil (Sello SHA-256 e Impresión HTML/PDF)
- **Checklist Táctico de Dotación:** Inspección de revólveres .38L, escopetas calibre 12, salvoconductos DCCA, cartuchos reglamentarios, chalecos antibalas, radios y linternas.
- **Foliado Criptográfico:** Emisión de sello digital inmutable `SHA-256` que vincula puesto, operador saliente, operador entrante, inventario verificado e instante temporal.
- **Impresión Oficial HTML/PDF (`GET /api/minuta/actas-relevo/{acta_id}/html`):** Vista imprimible formal con firmas digitales, sellos de auditoría y protección estricta contra inyecciones XSS.

### 1.5. Control de Acceso en Garita, Escáner Cédulas PDF417 y Reconocimiento LPR
- **Decodificador Nativo PDF417:** Lectura instantánea de la trama bidimensional de la cédula de ciudadanía colombiana, extrayendo número de documento, nombres, apellidos, sexo, fecha de nacimiento y tipo sanguíneo/RH.
- **Reconocimiento Óptico y Normalización LPR de Placas (`POST /api/acceso/escanear-placa`):** Validación y formateo automático de matrículas bajo estándar RUNT (`ABC-123` para automóviles particulares/públicos y `ABC-12D` para motocicletas) con botón táctico en garita.
- **Gestión PWA Offline-First:** Registro local y sincronización garantizada para garitas perimetrales remotas.

### 1.6. Libro Balístico Digital DCCA Indumil y Semáforo de Salvoconductos
- **Semáforo Preventivo a 90/60/30 Días:** Diagnóstico anticipado de permisos de porte y tenencia de armas ante el Departamento de Control Comercio de Armas (DCCA):
  - `Verde`: > 90 días de vigencia legal.
  - `Amarillo Preventivo`: Entre 30 y 90 días (inicio de trámite de renovación).
  - `Rojo Crítico`: < 30 días (alerta máxima y restricción de asignación).
  - `Vencido`: Bloqueo inmediato de asignación del arma en dotación.
- **Kardex Inmutable de Munición:** Movimientos de dotación, consumo por incidentes, pruebas de polígono y reposiciones Indumil con firma SHA-256.
- **Acreditación de Pruebas de Tiro:** Control anual obligatorio (365 días) de certificados de polígono y puntaje de puntería emitidos por academias autorizadas.

### 1.7. Tarificación Legal SuperVigilancia y Facturación B2B
- **Costeo Laboral Riguroso:** SMLMV + auxilio de transporte + factor prestacional (21.83%) + seguridad social y parafiscales (ARL Riesgo V 4.35%, pensión, salud, CCF 28.85%) + dotación y póliza colectiva de vida Ley 1920.
- **Tarifa Mínima Legal Regulada:** Cálculo de base mensual por puesto 24/7 (cuadrilla de 4 guardas) con recargo del 10% por armamento Indumil en modalidades armadas.
- **Base AIU e IVA DIAN (Art. 462-1 E.T.):** AIU regulado (mínimo 10%) e IVA del 19% aplicado exclusivamente sobre la base de administración.
- **Prefacturación B2B Foliada:** Emisión de prefacturas comerciales foliadas con firma digital SHA-256 y visualización HTML imprimible.

### 1.8. Centro de Despacho Táctico (CAD), Radar GPS y Red de Apoyo PONAL (123)
- **Monitoreo Satelital en Tiempo Real:** Mapa cartográfico interactivo con telemetría de puestos fijos y patrullas motorizadas en servicio.
- **Algoritmo Geodésico Haversine:** Localización y ordenamiento automático de la patrulla más cercana ante alertas SOS activas con estimación de tiempo de arribo (ETA en minutos).
- **Trazabilidad de Reacción:** Cronometraje en segundos desde la orden de despacho hasta el arribo confirmado en sitio y acta de cierre del incidente.
- **Directorio Táctico Red de Apoyo PONAL (`GET /api/cad/red-apoyo-ponal`):** Enlace directo a la línea de emergencia 123, línea nacional de la SuperVigilancia y catálogo de cuadrantes policiales, CAI de jurisdicción y frecuencias de radio (VHF/UHF) por puesto vigilado.

### 1.9. Jerarquía RBAC de 5 Niveles y Aislamiento Multi-Tenant
| Rol | Prioridad | Alcance y Permisos Operativos |
| :--- | :--- | :--- |
| **`ADMINISTRADOR`** | Prioridad 1 | Dirección General: Centro de mando ejecutivo, excepciones de credencial, auditoría forense, prefacturación B2B y configuración global. |
| **`SUPERVISOR`** | Prioridad 2 | Operaciones y Patrullas: Despacho CAD, resolución de intercambios, atención de sirenas SOS, relevos 2x2 y libro foliado. |
| **`RRHH`** | Prioridad 2.5 | Gestión Humana: Acreditación documental SuperVigilancia, carga masiva CSV, gestión de ausentismos y exportación de nómina Ley 2101. |
| **`OPERADOR`** | Prioridad 3 | Guarda en Puesto: Garita (cédula PDF417 + LPR), checklist de dotación Indumil, botón de pánico SOS y rondas QR/GPS. |
| **`CLIENTE`** | Prioridad 4 | Contratante: Supervisión exclusiva de su instalación (`puesto_base_id`), guarda en turno, SLA de rondas y minutas públicas (sin acceso a costos salariales ni datos de otras sedes). |

### 1.10. Respaldo Forense Criptográfico y Despliegue en Contenedores (Docker)
- **Volcado Forense Maestro (`/api/reportes/respaldo-forense-cifrado`):** Consolidación estructurada de turnos, minutas, actas de armamento, movimientos balísticos y facturación bajo un hash de sellado único para auditorías externas de la Superintendencia.
- **Despliegue Multi-Stage:** `Dockerfile` optimizado que compila la SPA de React en Vite y monta el backend en FastAPI Uvicorn listo para entornos Cloud (Cloud Run, ECS, Kubernetes) o Docker Compose.

---

## 2. Blindaje de Seguridad y Control de Vulnerabilidades

- **Mitigación de Cross-Site Scripting (XSS):** Saneamiento estricto (`html.escape`) en todas las plantillas y vistas HTML renderizadas por el servidor (actas de relevo, libro foliado y prefacturas).
- **Aislamiento Multi-Tenant:** Validación estricta a nivel de base de datos; usuarios con rol `CLIENTE` tienen restringida la consulta a actas y minutas de puestos ajenos (código HTTP 403 Forbidden).
- **Protección contra Denegación de Servicio (DoS):** Límite estricto de 2 MB y 1,000 registros por lote en importaciones masivas CSV.
- **Criptografía Robusta:** Hashing de contraseñas mediante `bcrypt` con salteado dinámico; firmas de inalterabilidad mediante digestos `SHA-256`.
- **Aislamiento de Sesión:** Manejo de tokens JWT persistidos en `sessionStorage` por pestaña para impedir sesiones fantasma o autologins residuales tras reiniciar el navegador.

---

## 3. Puesta en Marcha y Ejecución Local

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
*API:* `http://127.0.0.1:8000` | *Documentación OpenAPI (Swagger):* `http://127.0.0.1:8000/docs`

#### Terminal 2 — Frontend (Vite + React)
```bash
cd frontend
npm run dev
```
*Aplicación:* `http://localhost:5173/`

---

## 4. Cuentas Semilla Oficiales (Contraseña: `Sentinel2026*`)

- **Administrador (Prioridad 1):** `admin@sentinelops.co` (`PL-001`)
- **Supervisor (Prioridad 2):** `supervisor@sentinelops.co` (`SUP-101`)
- **RRHH y Nómina (Prioridad 2.5):** `rrhh@sentinelops.co` (`RRH-201`)
- **Guarda Operador (Prioridad 3):** `operador1@sentinelops.co` (`OPR-1001`)
- **Cliente Corporativo (Prioridad 4 — Sede `PST-BOG-01`):** `cliente@sentinelops.co` (`CLI-901`)

---

## 5. Pruebas y Aseguramiento de Calidad

```bash
# Suite de pruebas automatizadas Pytest (16 tests unitarios y de integración)
.\backend\.venv\Scripts\pytest.exe backend/tests -v

# Verificación de compilación y tipado TypeScript estricto
npm --prefix frontend run build
```

---

## 6. Estado del Roadmap y Cobertura Integral (Release V3.0)

- [x] **Fases 1 a 7:** Control RBAC 5 Niveles, Turnos 2x2, Minuta WebSockets en tiempo real, Checklist Indumil, Rondas QR/GPS Offline-First y Prenómina Ley 2101 (42h).
- [x] **Fase 8:** Tarificación legal regulada SuperVigilancia (SMLMV + factor prestacional + recargo armas) y prefacturación B2B foliada SHA-256.
- [x] **Fase 9:** PWA móvil táctica con escáner de cédulas colombianas PDF417 y reconocimiento óptico de placas vehiculares (LPR).
- [x] **Fase 10:** Libro Balístico Digital DCCA Indumil, semáforo preventivo de salvoconductos (90/60/30 días) y control anual de polígono.
- [x] **Fase 11:** Centro de Despacho Táctico Asistido por Computadora (CAD), telemetría GPS en vivo, algoritmo geodésico Haversine y Red de Apoyo PONAL (123).
- [x] **Fase 12:** Arquitectura SaaS Multi-Tenant (`tenant_id`), volcado forense criptográfico y Dockerfile multi-stage de producción.
- [x] **Hardening:** Carga masiva CSV blindada contra DoS, actas foliadas HTML con prevención XSS y aislamiento estricto multi-tenant para clientes.

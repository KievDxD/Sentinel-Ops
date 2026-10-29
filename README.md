# SENTINEL // OPS (Release Enterprise V2.0) — Plataforma SaaS B2B para Empresas de Seguridad Privada en Colombia

Plataforma empresarial de nivel de producción diseñada para gestionar la operación táctica, armamento Indumil, credenciales SuperVigilancia, turnos rotativos 2x2 de 12 horas, minuta digital con visibilidad dual, alertas de pánico SOS en tiempo real, rondas QR/GPS con soporte Offline-First y prenómina laboral conforme a la legislación colombiana (**SuperVigilancia**, **Ley 1920 de 2018**, **Ley 2101 de 2021** de reducción de jornada a 42 horas semanales en 2026 y **Código Sustantivo del Trabajo**).

---

## 1. Arquitectura Normativa y Módulos Enterprise V2.0

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
| **`CLIENTE`** | Prioridad 4 — Director del Puesto Contratado | Consola Corporativa de Solo Lectura vinculada exclusivamente a su puesto (`PST-BOG-01`): guarda en turno en tiempo real con vigencia SV, SLA de rondas QR/GPS, **Minuta Filtrada (`PUBLICA_CLIENTE`)** y descarga del Libro Foliado SHA-256 de su instalación. |

### 1.4. Módulos Tácticos V2.0
- **Acta Digital de Entrega y Recibo de Puesto (Inventario + Armamento Indumil):** Verificación de arma de dotación (Revólver .38L / Escopeta Cal 12 / No Letal), serial, salvoconducto Indumil, munición exacta, chaleco balístico y radio, generando folio inmutable `SHA-256` en la categoría `ENTREGA_RECIBO_PUESTO`.
- **Botón de Pánico Táctico SOS (WebSockets + Web Audio API):** Emisión inmediata de coordenadas GPS por `/ws/minuta`, banner rojo pulsante con sirena sintetizada por Web Audio API en consolas de supervisión y registro del tiempo exacto de reacción en segundos.
- **Motor Inteligente de Relevantes en 1 Clic:** Sugiere guardas con credencial SV vigente, en día de descanso ($\ge 12\text{h}$ previas) y ordenados de menor a mayor carga de horas extras semanales.
- **Modo Táctico de Campo (Alto Contraste / Sunlight Ready):** Conmutador en el header persistido en `localStorage` que transforma la interfaz a fondo negro puro, bordes ámbar de alto contraste y botones táctiles de mínimo `56px`.

---

## 2. Ejecución Local y Credenciales Semilla (`Sentinel2026*`)

### Comandos de Arranque
```powershell
# Backend FastAPI (Puerto 8000)
cd backend
.\.venv\Scripts\uvicorn.exe app.main:aplicacion --host 127.0.0.1 --port 8000

# Frontend React + TypeScript + Vite (Puerto 5173)
npm --prefix frontend run dev
```

### Cuentas Demo (Contraseña para todas: `Sentinel2026*`)
- **Administrador (Prioridad 1):** `admin@sentinelops.co` (`ADM-001`)
- **Supervisor (Prioridad 2):** `supervisor@sentinelops.co` (`SUP-104`)
- **RRHH y Nómina (Prioridad 2.5):** `rrhh@sentinelops.co` (`RRH-201`)
- **Guarda Operador (Prioridad 3):** `operador1@sentinelops.co` (`OPR-401`)
- **Cliente Corporativo (Prioridad 4 — Puesto `PST-BOG-01`):** `cliente@sentinelops.co` (`CLI-901`)

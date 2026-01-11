# KPInfo_CNC v2.0  
**Sistema Web de Registro y Reporte de Producción CNC (MES ligero / Shop-Floor Reporting)**

KPInfo CNC v2.0 corresponde a la evolución del MVP original, incorporando una **arquitectura web de tres capas**, acceso multiusuario desde navegador (mobile-first), autenticación, control de privilegios y mecanismos básicos de seguridad orientados a un entorno productivo real.

Esta versión está diseñada para **uso operativo en planta** mediante smartphones u otros dispositivos con navegador web, manteniendo un stack liviano y sin frameworks.

---

## Stack tecnológico

- **Backend:** Python (servidor HTTP propio, sin frameworks)
- **Base de datos:** SQLite
- **Frontend:** HTML, CSS y JavaScript puro (vanilla)
- **Arquitectura:** 3 capas
  - Presentación (web)
  - Lógica de negocio (services)
  - Persistencia (SQLite)

---

## Diferencias clave respecto a v1.0 (Legacy)

La versión v1.0 estaba pensada para ejecución local/intranet en una terminal fija y **no incluía gestión de usuarios**.

La versión **v2.0 introduce**:

### Autenticación y usuarios (Capa 3)
- CRUD de usuarios (operador / administrador).
- Inicio de sesión con token (Bearer).
- Control de acceso por roles (RBAC).
- Administrador no puede deshabilitarse a sí mismo ni al último admin activo.

### Cambio de contraseña sin SMTP
- Solicitud de cambio desde el frontend.
- Aprobación o cancelación manual por un administrador.
- Respuestas genéricas para evitar enumeración de usuarios.
- Rate-limit específico (anti-abuso).

### Modo EXTRAS (operador avanzado)
- Activación mediante clave de extras.
- Emisión de token firmado con vigencia temporal.
- Permite acciones sensibles como:
  - Edición administrativa.
  - Acceso a registros archivados.
  - Purga controlada de datos.

### Operación y reporting
- Registro de pedidos de producción CNC.
- Registro y gestión de anomalías.
- Exportación de reportes en formato CSV.
- Envío del archivo por el medio que el usuario estime conveniente.

### Enfoque mobile-first
- Interfaz responsive.
- Pensado para uso desde smartphone en piso de planta.

### Seguridad práctica
- Validaciones server-side.
- Rate-limit por endpoint sensible (login, register, extras, export).
- Tokens con expiración.
- Separación clara entre flujos legacy y flujos autenticados.

---

## Estructura del proyecto

KPInfo_CNC_v2/
├─ server/
│ ├─ http/ # Handler, mixins, API GET/POST, rate limit
│ ├─ services/ # Lógica de negocio
│ ├─ utils/
│ ├─ db.py
│ ├─ server.py
│ └─ schema.sql
├─ web/
│ ├─ assets/
│ ├─ *.html
│ └─ favicon.ico
├─ docs/
├─ .gitignore
├─ README.md
└─ LICENSE


---

## Ejecutar en entorno local

### Requisitos
- Python 3.10+ (recomendado)
- Navegador web moderno

### Pasos
```bash
python -m server.server

---

### Abrir en navegador (entorno local)

http://127.0.0.1:8000/

---

### Licencia

GPL-3.0



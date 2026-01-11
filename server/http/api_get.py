# server/http/api_get.py
from urllib.parse import parse_qs

from server.services.catalogos_admin_service import CatalogosAdminService
from server.services.admin_usuarios_service import AdminUsuariosService
from server.services.clave_cambio_service import ClaveCambioService
from server.utils.http_utils import send_json, ok, err


class ApiGetMixin:
    def handle_api_get(self, parsed):
        # =========================
        # HEALTH
        # =========================
        if parsed.path == "/api/health":
            return send_json(self, 200, ok({"status": "ok"}))

        # =========================
        # CATÁLOGOS (público para formularios)
        # =========================
        if parsed.path == "/api/catalogos":
            try:
                data = self.catalogos.get_catalogos()
                return send_json(self, 200, ok(data))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al obtener catálogos."))

        # =========================
        # ADMIN: CATÁLOGOS (CRUD UI) - legacy (X-Admin-Key)
        # =========================
        if parsed.path == "/api/admin/catalogos":
            if not self._handle_admin_guard():
                return
            try:
                svc = CatalogosAdminService(self.db)
                data = svc.listar()
                return send_json(self, 200, ok(data))
            except ValueError as ve:
                code = str(ve)
                if code == "CATALOGO_INVALIDO":
                    return send_json(self, 400, err("VALIDATION_ERROR", "Catálogo inválido."))
                return send_json(self, 400, err("VALIDATION_ERROR", "Solicitud inválida."))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al obtener catálogos (admin)."))

        # =========================
        # ADMIN: Variaciones asignadas por material (tabla puente)
        # GET /api/admin/variaciones/asignadas?tipo_plancha_id=ID
        # =========================
        if parsed.path == "/api/admin/variaciones/asignadas":
            if not self._handle_admin_guard():
                return

            qs = parse_qs(parsed.query or "")
            tipo_plancha_id = (qs.get("tipo_plancha_id", [""])[0] or "").strip()

            if not tipo_plancha_id:
                return send_json(self, 400, err("VALIDATION_ERROR", "Debe indicar tipo_plancha_id."))

            try:
                svc = CatalogosAdminService(self.db)
                items = svc.listar_variaciones_asignadas(tipo_plancha_id)
                return send_json(self, 200, ok({"items": items}))
            except ValueError as ve:
                code = str(ve)
                if code == "ID_INVALIDO":
                    return send_json(self, 400, err("VALIDATION_ERROR", "tipo_plancha_id inválido."))
                if code in ("MATERIAL_NOT_FOUND", "NOT_FOUND"):
                    return send_json(self, 404, err("NOT_FOUND", "Material no encontrado."))
                return send_json(self, 400, err("VALIDATION_ERROR", "Solicitud inválida."))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al obtener variaciones asignadas."))

        # =========================
        # ADMIN: STATUS (legacy) - X-Admin-Key
        # GET /api/admin/status
        # =========================
        if parsed.path == "/api/admin/status":
            if not self._handle_admin_guard():
                return

            try:
                rid_extras = None
                try:
                    rid_extras = self._get_extras_rid_if_any()
                except Exception:
                    rid_extras = None

                extras_active = rid_extras is not None

                return send_json(
                    self,
                    200,
                    ok({"admin": True, "extras_active": extras_active, "extras_rid": rid_extras}),
                )
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al obtener estado administrativo."))

        # =========================
        # ADMIN (CAPA 2): USUARIOS - Bearer + RBAC
        # GET /api/admin/usuarios?q=...&rol=...&activos=0|1
        # =========================
        if parsed.path == "/api/admin/usuarios":
            if not self._handle_admin_user_guard():
                return

            qs = parse_qs(parsed.query or "")
            q = (qs.get("q") or [""])[0]
            rol = (qs.get("rol") or [""])[0]
            activos_raw = (qs.get("activos") or [""])[0]

            activos = None
            if activos_raw in ("0", "1"):
                activos = int(activos_raw)

            svc = getattr(self, "admin_usuarios", None) or AdminUsuariosService(self.db)
            data = svc.listar(q=q, activos=activos, rol=rol)
            return send_json(self, 200, ok({"items": data}))

        # =========================================================
        # ADMIN (CAPA 2): Password change requests (Variante 2)
        # GET /api/admin/usuarios/password-change/status?usuario_id=ID
        # GET /api/admin/usuarios/password-change/pending
        # =========================================================
        if parsed.path == "/api/admin/usuarios/password-change/status":
            if not self._handle_admin_user_guard():
                return

            qs = parse_qs(parsed.query or "")
            uid_raw = (qs.get("usuario_id") or qs.get("id") or [""])[0]
            try:
                usuario_id = int(uid_raw or 0)
                if usuario_id <= 0:
                    raise ValueError()
            except Exception:
                return send_json(self, 400, err("VALIDATION_ERROR", "usuario_id inválido."))

            try:
                svc = getattr(self, "clave_cambio", None) or ClaveCambioService(self.db)
                data = svc.get_status(usuario_id=usuario_id, history_limit=5)
                return send_json(self, 200, ok(data))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al obtener estado de solicitud de cambio de contraseña."))

        if parsed.path == "/api/admin/usuarios/password-change/pending":
            if not self._handle_admin_user_guard():
                return

            # Lista global de solicitudes PENDING vigentes con datos básicos del usuario
            try:
                rows = self.db.query_all(
                    """
                    SELECT
                      u.id AS usuario_id,
                      u.nombre,
                      u.apellido,
                      u.email,
                      u.username,
                      u.rol,
                      u.activo,
                      p.id AS request_id,
                      p.creado_en,
                      p.expira_en,
                      p.origen_ip
                    FROM password_change_request p
                    JOIN usuario u ON u.id = p.usuario_id
                    WHERE p.estado = 'PENDING'
                      AND p.expira_en >= datetime('now')
                    ORDER BY p.creado_en DESC;
                    """
                ) or []
                return send_json(self, 200, ok({"items": rows}))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al listar solicitudes pendientes."))

        # =========================
        # EXPORT (CSV)
        # =========================
        if parsed.path in ("/api/export/pedidos.csv", "/api/exportar/pedidos.csv"):
            qs = parse_qs(parsed.query or "")
            desde = (qs.get("desde", [""])[0] or "").strip()
            hasta = (qs.get("hasta", [""])[0] or "").strip()
            try:
                content, fname = self.export.export_pedidos_csv(desde=desde, hasta=hasta)
                return self._send_csv(content, fname)
            except ValueError as ve:
                if str(ve) == "DATE_RANGE_INVALID":
                    return send_json(self, 400, err("VALIDATION_ERROR", "Rango de fechas inválido (desde > hasta)."))
                return send_json(self, 400, err("VALIDATION_ERROR", "Parámetros inválidos para exportación."))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al exportar pedidos."))

        if parsed.path in ("/api/export/anomalias.csv", "/api/exportar/anomalias.csv"):
            qs = parse_qs(parsed.query or "")
            desde = (qs.get("desde", [""])[0] or "").strip()
            hasta = (qs.get("hasta", [""])[0] or "").strip()
            try:
                content, fname = self.export.export_anomalias_csv(desde=desde, hasta=hasta)
                return self._send_csv(content, fname)
            except ValueError as ve:
                if str(ve) == "DATE_RANGE_INVALID":
                    return send_json(self, 400, err("VALIDATION_ERROR", "Rango de fechas inválido (desde > hasta)."))
                return send_json(self, 400, err("VALIDATION_ERROR", "Parámetros inválidos para exportación."))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al exportar anomalías."))

        # =========================
        # PEDIDOS
        # =========================
        if parsed.path == "/api/pedidos":
            qs = parse_qs(parsed.query or "")
            estado = (qs.get("estado", ["general"])[0] or "general").strip()
            q = (qs.get("q", [""])[0] or "").strip()

            archivados_flag = (qs.get("archivados", ["0"])[0] or "0").strip()
            archivados_only = archivados_flag == "1"

            if archivados_only:
                rid = self._handle_extras_guard()
                if rid is None:
                    return
                estado = "archivado"

            try:
                items = self.pedidos.listar_pedidos(
                    estado=estado,
                    q=q if q else None,
                    incluir_archivados=archivados_only,
                )
                return send_json(self, 200, ok({"items": items}))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al listar pedidos."))

        if parsed.path.startswith("/api/pedidos/"):
            tail = parsed.path.split("/api/pedidos/", 1)[1].strip("/")
            if "/" in tail:
                return send_json(self, 404, err("NOT_FOUND", "Endpoint no encontrado."))

            try:
                pedido_id = self._parse_pos_int(tail)
            except ValueError:
                return send_json(self, 400, err("VALIDATION_ERROR", "ID de pedido inválido."))

            try:
                row = self.pedidos.obtener_pedido_detalle(pedido_id)
                if not row:
                    return send_json(self, 404, err("NOT_FOUND", "Pedido no encontrado."))
                return send_json(self, 200, ok(row))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al obtener detalle del pedido."))

        # =========================
        # ANOMALÍAS
        # =========================
        if parsed.path == "/api/anomalias":
            qs = parse_qs(parsed.query or "")
            estado = (qs.get("estado", ["todos"])[0] or "todos").strip()
            q = (qs.get("q", [""])[0] or "").strip()

            archivados_flag = (qs.get("archivados", ["0"])[0] or "0").strip()
            archivados_only = archivados_flag == "1"

            if archivados_only:
                rid = self._handle_extras_guard()
                if rid is None:
                    return
                estado = "archivado"

            try:
                items = self.anomalias.listar_anomalias(
                    estado=estado,
                    q=q if q else None,
                    incluir_archivados=archivados_only,
                )
                return send_json(self, 200, ok({"items": items}))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al listar anomalías."))

        if parsed.path.startswith("/api/anomalias/"):
            tail = parsed.path.split("/api/anomalias/", 1)[1].strip("/")
            if "/" in tail:
                return send_json(self, 404, err("NOT_FOUND", "Endpoint no encontrado."))

            try:
                anomalia_id = self._parse_pos_int(tail)
            except ValueError:
                return send_json(self, 400, err("VALIDATION_ERROR", "ID de anomalía inválido."))

            try:
                row = self.anomalias.obtener_anomalia_detalle(anomalia_id)
                if not row:
                    return send_json(self, 404, err("NOT_FOUND", "Anomalía no encontrada."))
                return send_json(self, 200, ok(row))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al obtener detalle de la anomalía."))

        return send_json(self, 404, err("NOT_FOUND", "Endpoint no encontrado."))

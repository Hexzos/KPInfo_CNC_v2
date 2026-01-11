# server/http/app_handler.py
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

from server.config import CONFIG
from server.db import Database

from server.services.catalogos_service import CatalogoService
from server.services.sesion_service import SesionService
from server.services.pedidos_service import PedidosService
from server.services.anomalias_service import AnomaliasService
from server.services.export_service import ExportService
from server.services.extras_service import ExtrasService

from server.services.auth_service import AuthService
from server.services.admin_usuarios_service import AdminUsuariosService

from server.http.mixins import HandlerHelpersMixin, ExtrasAuthMixin, AdminAuthMixin, UserAuthMixin
from server.http.api_get import ApiGetMixin
from server.http.api_post import ApiPostMixin
from server.utils.http_utils import send_json, err

# Rate limit (module dedicado)
from server.http.rate_limit import rate_limit_check, RateRule


class AppHandler(
    BaseHTTPRequestHandler,
    HandlerHelpersMixin,
    ExtrasAuthMixin,
    AdminAuthMixin,
    UserAuthMixin,
    ApiGetMixin,
    ApiPostMixin,
):
    db = Database(CONFIG.db_path)

    # Servicios existentes
    catalogos = CatalogoService(db)
    sesion = SesionService(db)
    pedidos = PedidosService(db)
    anomalias = AnomaliasService(db)
    export = ExportService(db)
    extras = ExtrasService(db)

    # Servicios capa 2
    auth = AuthService(db)
    admin_usuarios = AdminUsuariosService(db)

    # =========================
    # RATE LIMIT (políticas)
    # =========================
    # Reglas por prefijo/path para no tocar api_post (800+ líneas).
    # Pensado para uso real (móvil) sin bloquear uso normal.
    _RL_RULES = [
        # -------------------------
        # AUTH: login/register/reset
        # -------------------------
        ("POST", "/api/auth/login", RateRule(20, 10 * 60)),            # 20 / 10 min / IP (suave)
        ("POST", "/api/auth/register", RateRule(10, 10 * 60)),         # 10 / 10 min / IP
        ("POST", "/api/auth/logout", RateRule(60, 10 * 60)),           # 60 / 10 min / IP
        ("POST", "/api/auth/password/forgot", RateRule(20, 10 * 60)),  # 20 / 10 min / IP (además del 2/8h interno)
        ("POST", "/api/auth/password/reset", RateRule(10, 10 * 60)),   # si existiera

        # -------------------------
        # EXTRAS: elevate (sensible, pero debe permitir uso frecuente)
        # -------------------------
        # Suave para permitir activar/desactivar en iteraciones (móvil / operación).
        ("POST", "/api/extras/elevate", RateRule(60, 60)),             # 60 / min / IP
        ("POST", "/api/admin/elevate", RateRule(60, 60)),              # 60 / min / IP (alias legacy)

        # -------------------------
        # SESIÓN: iniciar turno (evitar spam accidental)
        # -------------------------
        ("POST", "/api/registro-turno/iniciar", RateRule(30, 60)),     # 30 / min / IP

        # -------------------------
        # ADMIN: prefijo completo (RBAC / Bearer)
        # -------------------------
        ("GET",  "/api/admin/", RateRule(180, 60)),                    # 180 / min / IP
        ("POST", "/api/admin/", RateRule(120, 60)),                    # 120 / min / IP

        # -------------------------
        # EXPORT CSV (GET): puede ser “caro”
        # -------------------------
        ("GET", "/api/export/", RateRule(30, 60)),                     # 30 / min / IP
        ("GET", "/api/exportar/", RateRule(30, 60)),                   # 30 / min / IP

        # -------------------------
        # CRUD operacional (móvil): listar/detalle y crear/actualizar
        # -------------------------
        ("GET",  "/api/pedidos", RateRule(240, 60)),
        ("POST", "/api/pedidos", RateRule(120, 60)),
        ("GET",  "/api/anomalias", RateRule(240, 60)),
        ("POST", "/api/anomalias", RateRule(120, 60)),
    ]

    def log_message(self, format, *args):
        return

    # -------------------------
    # Helper: responder 429 sin depender de send_json
    # -------------------------
    def _send_rate_limited(self, retry_after: int):
        payload = err("RATE_LIMIT", "Demasiadas solicitudes. Intenta nuevamente más tarde.")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(429)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Retry-After", str(int(retry_after or 1)))
        self.end_headers()
        self.wfile.write(body)

    def _apply_rate_limit(self, method: str, path: str) -> bool:
        """
        Aplica rate limit según reglas por prefijo/path.
        Retorna True si puede continuar, False si ya respondió 429.
        """
        for m, prefix, rule in self._RL_RULES:
            if m == method and path.startswith(prefix):
                allowed, retry = rate_limit_check(self, scope=f"{m}:{prefix}", rule=rule)
                if not allowed:
                    self._send_rate_limited(retry)
                    return False
                return True
        return True

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path.startswith("/api/"):
            if not self._apply_rate_limit("GET", parsed.path):
                return
            return self.handle_api_get(parsed)

        return self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path.startswith("/api/"):
            if not self._apply_rate_limit("POST", parsed.path):
                return
            return self.handle_api_post(parsed)

        return send_json(self, 404, err("NOT_FOUND", "Recurso no encontrado."))

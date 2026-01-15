# server/http/api_post.py
import sqlite3
from urllib.parse import parse_qs

from server.config import CONFIG
from server.http.security import verify_pbkdf2_password
from server.services.catalogos_admin_service import CatalogosAdminService
from server.services.auth_service import AuthService
from server.services.admin_usuarios_service import AdminUsuariosService
from server.services.clave_cambio_service import ClaveCambioService
from server.utils.http_utils import read_json, send_json, ok, err

from server.validators import (
    validate_registro_turno_iniciar,
    validate_pedido_crear,
    validate_pedido_actualizar_operador,
    validate_anomalia_crear,
    validate_anomalia_actualizar_operador,
)


class ApiPostMixin:
    def handle_api_post(self, parsed):

        # =========================================================
        # AUTH: Password change sin SMTP (Variante 2)
        # Mantiene endpoint /api/auth/password/forgot
        # Body: { identificador, password } o { email, password }
        # Respuesta: SIEMPRE genérica (no filtra existencia)
        # =========================================================
        if parsed.path == "/api/auth/password/forgot":
            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            identificador = (dto.get("identificador") or dto.get("email") or "").strip()
            new_password = dto.get("password") or dto.get("password_nueva") or ""

            if not identificador:
                return send_json(self, 400, err("VALIDATION_ERROR", "Ingrese email o username."))
            if len(new_password or "") < 8:
                return send_json(self, 400, err("VALIDATION_ERROR", "La contraseña debe tener al menos 8 caracteres."))

            origen_ip = None
            try:
                origen_ip = (self.client_address[0] if getattr(self, "client_address", None) else None)
            except Exception:
                origen_ip = None

            try:
                svc = getattr(self, "clave_cambio", None) or ClaveCambioService(self.db)
                svc.request_change(identificador=identificador, new_password=new_password, origen_ip=origen_ip)

                return send_json(
                    self,
                    200,
                    ok(
                        {
                            "message": (
                                "Si el usuario existe y está activo, se registró una solicitud de cambio de contraseña. "
                                "Un administrador debe aprobarla."
                            )
                        }
                    ),
                )
            except Exception:
                return send_json(
                    self,
                    200,
                    ok(
                        {
                            "message": (
                                "Si el usuario existe y está activo, se registró una solicitud de cambio de contraseña. "
                                "Un administrador debe aprobarla."
                            )
                        }
                    ),
                )

        # =========================================================
        # ADMIN: aprobar/cancelar solicitud de cambio de contraseña (Variante 2)
        # POST /api/admin/usuarios/password-change/approve  { usuario_id }
        # POST /api/admin/usuarios/password-change/cancel   { usuario_id }
        # =========================================================
        if parsed.path in (
            "/api/admin/usuarios/password-change/approve",
            "/api/admin/usuarios/password-change/cancel",
        ):
            if not self._handle_admin_user_guard():
                return

            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            try:
                usuario_id = int(dto.get("usuario_id") or dto.get("id") or 0)
                if usuario_id <= 0:
                    raise ValueError()
            except Exception:
                return send_json(self, 400, err("VALIDATION_ERROR", "usuario_id inválido."))

            try:
                me = self._require_admin_user()  # type: ignore
            except PermissionError:
                return

            admin_id = int(me.get("id") or 0)
            if admin_id <= 0:
                return send_json(self, 401, err("AUTH_REQUIRED", "Se requiere iniciar sesión."))

            svc = getattr(self, "clave_cambio", None) or ClaveCambioService(self.db)

            try:
                if parsed.path.endswith("/approve"):
                    svc.approve(usuario_id=usuario_id, admin_id=admin_id)
                    return send_json(self, 200, ok({"message": "Cambio de contraseña aprobado y aplicado."}))

                svc.cancel(usuario_id=usuario_id, admin_id=admin_id)
                return send_json(self, 200, ok({"message": "Solicitud de cambio de contraseña cancelada."}))

            except ValueError as ve:
                code = str(ve)
                if code == "NO_USER":
                    return send_json(self, 404, err("NOT_FOUND", "Usuario no existe."))
                if code == "USUARIO_INACTIVO":
                    return send_json(self, 400, err("VALIDATION_ERROR", "Usuario inactivo."))
                if code == "NO_PENDING":
                    return send_json(self, 400, err("VALIDATION_ERROR", "No hay solicitud pendiente vigente."))
                if code == "INVALID":
                    return send_json(self, 400, err("VALIDATION_ERROR", "Solicitud inválida."))
                return send_json(self, 400, err("VALIDATION_ERROR", "Solicitud inválida."))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al procesar la solicitud de cambio de contraseña."))

        # =========================================================
        # AUTH (CAPA 2): register/login/logout
        # =========================================================
        if parsed.path in ("/api/auth/register", "/api/auth/login", "/api/auth/logout"):
            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            svc = getattr(self, "auth", None) or AuthService(self.db)

            if parsed.path.endswith("/register"):
                try:
                    svc.register(
                        dto.get("nombre"),
                        dto.get("apellido"),
                        dto.get("email"),
                        dto.get("password"),
                        dto.get("username"),
                    )
                    return send_json(self, 200, ok({"message": "OK"}))
                except ValueError as ve:
                    code = str(ve)
                    msg = "Solicitud inválida."
                    if code == "EMAIL_YA_EXISTE":
                        msg = "El email ya está registrado."
                    elif code == "USERNAME_YA_EXISTE":
                        msg = "El username ya está en uso."
                    elif code == "PASSWORD_DEBIL":
                        msg = "La contraseña debe tener al menos 8 caracteres."
                    elif code == "EMAIL_INVALIDO":
                        msg = "Email inválido."
                    return send_json(self, 400, err("VALIDATION_ERROR", msg))

            if parsed.path.endswith("/login"):
                try:
                    data = svc.login(dto.get("identificador"), dto.get("password"))
                    return send_json(self, 200, ok(data))
                except ValueError:
                    return send_json(self, 400, err("VALIDATION_ERROR", "Credenciales requeridas."))
                except PermissionError as pe:
                    code = str(pe)
                    if code == "USUARIO_INACTIVO":
                        return send_json(self, 403, err("AUTH_DENIED", "Usuario desactivado."))
                    return send_json(self, 401, err("AUTH_INVALID", "Credenciales inválidas."))

            if parsed.path.endswith("/logout"):
                token = self._get_bearer_token() if hasattr(self, "_get_bearer_token") else ""
                if not token:
                    return send_json(self, 401, err("AUTH_REQUIRED", "Se requiere iniciar sesión."))
                svc.logout(token)
                return send_json(self, 200, ok({"message": "OK"}))

        # =========================================================
        # ADMIN (CAPA 2): Usuarios CRUD
        # =========================================================
        if parsed.path in (
            "/api/admin/usuarios/create",
            "/api/admin/usuarios/update",
            "/api/admin/usuarios/toggle",
        ):
            if not self._handle_admin_user_guard():
                return

            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            svc = getattr(self, "admin_usuarios", None) or AdminUsuariosService(self.db)

            if parsed.path.endswith("/create"):
                try:
                    uid = svc.crear(
                        dto.get("nombre"),
                        dto.get("apellido"),
                        dto.get("email"),
                        dto.get("password"),
                        dto.get("username"),
                        dto.get("rol") or "operador",
                        dto.get("activo", 1),
                    )
                    return send_json(self, 200, ok({"id": uid}))
                except ValueError as ve:
                    code = str(ve)
                    msg = "Solicitud inválida."
                    if code == "EMAIL_YA_EXISTE":
                        msg = "El email ya está registrado."
                    elif code == "USERNAME_YA_EXISTE":
                        msg = "El username ya está en uso."
                    elif code == "ROL_INVALIDO":
                        msg = "Rol inválido."
                    elif code == "PASSWORD_DEBIL":
                        msg = "La contraseña debe tener al menos 8 caracteres."
                    return send_json(self, 400, err("VALIDATION_ERROR", msg))

            if parsed.path.endswith("/update"):
                try:
                    uid = int(dto.get("id") or 0)
                    svc.actualizar(
                        uid,
                        dto.get("nombre"),
                        dto.get("apellido"),
                        dto.get("email"),
                        dto.get("username"),
                        dto.get("rol"),
                    )
                    return send_json(self, 200, ok({"message": "OK"}))
                except ValueError as ve:
                    code = str(ve)
                    msg = "Solicitud inválida."
                    if code == "NO_EXISTE":
                        msg = "Usuario no existe."
                    elif code == "EMAIL_YA_EXISTE":
                        msg = "El email ya está registrado."
                    elif code == "USERNAME_YA_EXISTE":
                        msg = "El username ya está en uso."
                    elif code == "ROL_INVALIDO":
                        msg = "Rol inválido."
                    elif code == "LAST_ADMIN":
                        msg = "No se puede quitar privilegios al último administrador activo."
                    return send_json(self, 400, err("VALIDATION_ERROR", msg))

            if parsed.path.endswith("/toggle"):
                try:
                    uid = int(dto.get("id") or 0)
                    activo = 1 if int(dto.get("activo") or 0) == 1 else 0
                    if uid <= 0:
                        raise ValueError("NO_EXISTE")

                    try:
                        me = self._require_admin_user()  # type: ignore
                    except PermissionError:
                        return

                    if int(me.get("id") or 0) == uid and activo == 0:
                        raise ValueError("SELF_DISABLE")

                    svc.toggle_activo(uid, activo)
                    return send_json(self, 200, ok({"message": "OK"}))
                except ValueError as ve:
                    code = str(ve)
                    msg = "Solicitud inválida."
                    if code == "NO_EXISTE":
                        msg = "Usuario no existe."
                    elif code == "LAST_ADMIN":
                        msg = "No se puede deshabilitar al último administrador activo."
                    elif code == "SELF_DISABLE":
                        msg = (
                            "Por seguridad, un administrador no puede deshabilitarse a sí mismo; "
                            "debe hacerlo otro administrador."
                        )
                    return send_json(self, 400, err("VALIDATION_ERROR", msg))

        # =========================
        # ADMIN: CATÁLOGOS (CRUD)
        # =========================
        if parsed.path in (
            "/api/admin/catalogos/create",
            "/api/admin/catalogos/update",
            "/api/admin/catalogos/delete",
        ):
            if not self._handle_admin_guard():
                return

            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            catalogo = (dto.get("catalogo") or "").strip().lower()
            svc = CatalogosAdminService(self.db)

            if parsed.path.endswith("/create"):
                nombre = (dto.get("nombre") or "").strip()
                if not catalogo or not nombre:
                    return send_json(self, 400, err("VALIDATION_ERROR", "Debe indicar catálogo y nombre."))

                try:
                    new_id = svc.crear(catalogo=catalogo, nombre=nombre)
                    return send_json(self, 201, ok({"id": new_id, "nombre": nombre}))
                except ValueError as ve:
                    code = str(ve)
                    if code == "CATALOGO_INVALIDO":
                        return send_json(self, 400, err("VALIDATION_ERROR", "Catálogo inválido."))
                    if code == "NOMBRE_INVALIDO":
                        return send_json(self, 400, err("VALIDATION_ERROR", "Nombre inválido."))
                    return send_json(self, 400, err("VALIDATION_ERROR", "Solicitud inválida."))
                except sqlite3.IntegrityError as ie:
                    msg = str(ie).lower()
                    if "unique" in msg:
                        return send_json(self, 409, err("DUPLICATE", "Ya existe un registro con ese nombre."))
                    return send_json(self, 409, err("CONSTRAINT", "No se pudo crear el registro por restricción."))
                except Exception:
                    return send_json(self, 500, err("DB_ERROR", "Error al crear registro del catálogo."))

            if parsed.path.endswith("/update"):
                try:
                    item_id = int(dto.get("id"))
                    if item_id <= 0:
                        raise ValueError()
                except Exception:
                    return send_json(self, 400, err("VALIDATION_ERROR", "ID inválido."))

                nombre = (dto.get("nombre") or "").strip()
                if not catalogo or not nombre:
                    return send_json(self, 400, err("VALIDATION_ERROR", "Debe indicar catálogo y nombre."))

                try:
                    svc.actualizar(catalogo=catalogo, item_id=item_id, nombre=nombre)
                    return send_json(self, 200, ok({"id": item_id, "nombre": nombre}))
                except ValueError as ve:
                    code = str(ve)
                    if code == "CATALOGO_INVALIDO":
                        return send_json(self, 400, err("VALIDATION_ERROR", "Catálogo inválido."))
                    if code == "NOMBRE_INVALIDO":
                        return send_json(self, 400, err("VALIDATION_ERROR", "Nombre inválido."))
                    if code == "NOT_FOUND":
                        return send_json(self, 404, err("NOT_FOUND", "Registro no encontrado."))
                    return send_json(self, 400, err("VALIDATION_ERROR", "Solicitud inválida."))
                except sqlite3.IntegrityError as ie:
                    msg = str(ie).lower()
                    if "unique" in msg:
                        return send_json(self, 409, err("DUPLICATE", "Ya existe un registro con ese nombre."))
                    return send_json(self, 409, err("CONSTRAINT", "No se pudo actualizar por restricción."))
                except Exception:
                    return send_json(self, 500, err("DB_ERROR", "Error al actualizar registro del catálogo."))

            if parsed.path.endswith("/delete"):
                try:
                    item_id = int(dto.get("id"))
                    if item_id <= 0:
                        raise ValueError()
                except Exception:
                    return send_json(self, 400, err("VALIDATION_ERROR", "ID inválido."))

                if not catalogo:
                    return send_json(self, 400, err("VALIDATION_ERROR", "Debe indicar catálogo."))

                try:
                    svc.eliminar(catalogo=catalogo, item_id=item_id)
                    return send_json(self, 200, ok({"deleted": True, "id": item_id}))
                except ValueError as ve:
                    code = str(ve)
                    if code == "CATALOGO_INVALIDO":
                        return send_json(self, 400, err("VALIDATION_ERROR", "Catálogo inválido."))
                    if code == "NOT_FOUND":
                        return send_json(self, 404, err("NOT_FOUND", "Registro no encontrado."))
                    if code == "REFERENCIADO":
                        return send_json(self, 409, err("IN_USE", "No se puede eliminar: el registro está referenciado."))
                    return send_json(self, 400, err("VALIDATION_ERROR", "Solicitud inválida."))
                except sqlite3.IntegrityError:
                    return send_json(
                        self, 409, err("IN_USE", "No se puede eliminar: el registro está en uso por otros datos (FK).")
                    )
                except Exception:
                    return send_json(self, 500, err("DB_ERROR", "Error al eliminar registro del catálogo."))

        # =========================================================
        # ADMIN: Variaciones por material (tabla puente)
        # =========================================================
        if parsed.path in ("/api/admin/variaciones/asignar", "/api/admin/variaciones/desasignar"):
            if not self._handle_admin_guard():
                return

            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            try:
                tipo_plancha_id = int(dto.get("tipo_plancha_id") or 0)
                variacion_material_id = int(dto.get("variacion_material_id") or dto.get("variacion_id") or 0)
                if tipo_plancha_id <= 0 or variacion_material_id <= 0:
                    raise ValueError()
            except Exception:
                return send_json(self, 400, err("VALIDATION_ERROR", "IDs inválidos."))

            try:
                if parsed.path.endswith("/asignar"):
                    try:
                        self.db.execute(
                            """
                            INSERT INTO tipo_plancha_variacion (tipo_plancha_id, variacion_material_id)
                            VALUES (?, ?);
                            """,
                            (tipo_plancha_id, variacion_material_id),
                        )
                    except sqlite3.IntegrityError:
                        pass
                    return send_json(self, 200, ok({"assigned": True}))

                self.db.execute(
                    """
                    DELETE FROM tipo_plancha_variacion
                    WHERE tipo_plancha_id = ? AND variacion_material_id = ?;
                    """,
                    (tipo_plancha_id, variacion_material_id),
                )
                return send_json(self, 200, ok({"unassigned": True}))

            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al actualizar variaciones asignadas."))

        # =========================================================
        # ADMIN: Purga archivados (requiere extras)
        # =========================================================
        if parsed.path in (
            "/api/admin/purge/pedidos/range",
            "/api/admin/purge/pedidos/all",
            "/api/admin/purge/anomalias/range",
            "/api/admin/purge/anomalias/all",
        ):
            if not self._handle_admin_guard():
                return
            rid_extras = self._handle_extras_guard()
            if rid_extras is None:
                return

            try:
                dto = read_json(self)
            except ValueError:
                dto = {}

            def _count_one(sql, params=()):
                row = self.db.query_one(sql, params) or {}
                for k in ("n", "count", "COUNT(*)"):
                    if k in row:
                        try:
                            return int(row[k] or 0)
                        except Exception:
                            pass
                try:
                    return int(list(row.values())[0])
                except Exception:
                    return 0

            try:
                tabla = "pedido" if "/pedidos/" in parsed.path else "anomalia"

                if parsed.path.endswith("/range"):
                    desde = (dto.get("desde") or "").strip()
                    hasta = (dto.get("hasta") or "").strip()

                    if not desde or not hasta:
                        return send_json(self, 400, err("VALIDATION_ERROR", "Debe indicar desde y hasta."))
                    if len(desde) != 10 or len(hasta) != 10 or desde > hasta:
                        return send_json(self, 400, err("VALIDATION_ERROR", "Rango de fechas inválido."))

                    n = _count_one(
                        f"""
                        SELECT COUNT(*) AS n
                        FROM {tabla}
                        WHERE es_archivado = 1
                          AND fecha_registro >= ?
                          AND fecha_registro <= ?;
                        """,
                        (desde, hasta),
                    )

                    self.db.execute(
                        f"""
                        DELETE FROM {tabla}
                        WHERE es_archivado = 1
                          AND fecha_registro >= ?
                          AND fecha_registro <= ?;
                        """,
                        (desde, hasta),
                    )

                    self._extras_audit(
                        rid_extras,
                        "PURGE_RANGE",
                        tabla,
                        None,
                        f"Purga por rango {desde}..{hasta}. Eliminados: {n}",
                    )
                    return send_json(self, 200, ok({"deleted": n}))

                n = _count_one(f"SELECT COUNT(*) AS n FROM {tabla} WHERE es_archivado = 1;")
                self.db.execute(f"DELETE FROM {tabla} WHERE es_archivado = 1;")

                self._extras_audit(
                    rid_extras,
                    "PURGE_ALL",
                    tabla,
                    None,
                    f"Purga completa. Eliminados: {n}",
                )
                return send_json(self, 200, ok({"deleted": n}))

            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al ejecutar purga."))

        # =========================================================
        # ADMIN: Rotar clave de extras (requiere extras)
        # =========================================================
        if parsed.path == "/api/admin/extras-key/rotate":
            if not self._handle_admin_guard():
                return
            rid_extras = self._handle_extras_guard()
            if rid_extras is None:
                return

            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            current = (dto.get("extras_key_current") or "").strip()
            newkey = (dto.get("extras_key_new") or "").strip()

            if not current or not newkey:
                return send_json(self, 400, err("VALIDATION_ERROR", "Debe indicar clave actual y nueva clave."))
            if len(newkey) < 8:
                return send_json(self, 400, err("VALIDATION_ERROR", "La nueva clave debe tener al menos 8 caracteres."))
            if current != CONFIG.extra_key:
                return send_json(self, 401, err("UNAUTHORIZED", "Clave actual incorrecta."))

            try:
                CONFIG.extra_key = newkey
                self._extras_audit(rid_extras, "ROTATE_EXTRAS_KEY", "config", None, "Rotación de clave extras (runtime).")
                return send_json(self, 200, ok({"message": "OK"}))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "No fue posible actualizar la clave."))

        # =========================
        # EXTRAS - elevate (principal + alias compat)
        # =========================
        if parsed.path in ("/api/extras/elevate", "/api/admin/elevate"):
            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            try:
                registro_turno_id = int(dto.get("registro_turno_id"))
                if registro_turno_id <= 0:
                    raise ValueError()
            except Exception:
                return send_json(self, 400, err("VALIDATION_ERROR", "registro_turno_id inválido."))

            svc_auth = getattr(self, "auth", None) or AuthService(self.db)
            u = None
            try:
                token = self._get_bearer_token() if hasattr(self, "_get_bearer_token") else ""
                if token:
                    u = svc_auth.get_usuario_by_token(token)
            except Exception:
                u = None

            is_admin = bool(u and u.get("rol") == "admin")

            if is_admin:
                try:
                    data = self.extras.elevate(registro_turno_id=registro_turno_id, extras_key=CONFIG.extra_key)
                    return send_json(self, 200, ok({"token": data["token"]}))
                except ValueError as ve:
                    if str(ve) == "RID_NOT_FOUND":
                        return send_json(self, 404, err("NOT_FOUND", "Registro de turno no encontrado."))
                    return send_json(self, 400, err("VALIDATION_ERROR", "Solicitud inválida."))
                except Exception:
                    return send_json(self, 500, err("DB_ERROR", "Error al activar modo extras."))

            extras_key = (dto.get("extras_key") or dto.get("key") or "").strip()
            if not extras_key:
                return send_json(self, 400, err("VALIDATION_ERROR", "Ingrese la clave de extras."))

            try:
                data = self.extras.elevate(registro_turno_id=registro_turno_id, extras_key=extras_key)
                return send_json(self, 200, ok({"token": data["token"]}))
            except ValueError as ve:
                code = str(ve)
                if code == "RID_NOT_FOUND":
                    return send_json(self, 404, err("NOT_FOUND", "Registro de turno no encontrado."))
                if code == "EXTRAS_KEY_INVALID":
                    return send_json(self, 401, err("UNAUTHORIZED", "Clave incorrecta, intente nuevamente."))
                return send_json(self, 400, err("VALIDATION_ERROR", "Solicitud inválida."))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al activar modo extras."))

        # =========================
        # SESIÓN: iniciar registro turno (operador/admin)
        # =========================
        if parsed.path == "/api/registro-turno/iniciar":
            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            valid, fields = validate_registro_turno_iniciar(dto)
            if not valid:
                return send_json(self, 400, err("VALIDATION_ERROR", "Hay campos inválidos.", fields))

            svc_auth = getattr(self, "auth", None) or AuthService(self.db)
            u = None
            try:
                token = self._get_bearer_token() if hasattr(self, "_get_bearer_token") else ""
                if token:
                    u = svc_auth.get_usuario_by_token(token)
            except Exception:
                u = None

            admin_username = (dto.get("admin_username") or "").strip()
            admin_password = dto.get("admin_password") or ""
            admin_key = (dto.get("admin_key") or "").strip()

            admin_by_bearer = bool(u and u.get("rol") == "admin")
            admin_attempt_legacy = bool(admin_username or admin_password or admin_key)

            if admin_by_bearer:
                rol = "admin"
            elif admin_attempt_legacy:
                if not admin_username or not admin_password or not admin_key:
                    return send_json(
                        self,
                        400,
                        err("VALIDATION_ERROR", "Para acceso administrador, ingrese usuario, contraseña y admin key."),
                    )
                if admin_key != CONFIG.admin_key:
                    return send_json(self, 401, err("UNAUTHORIZED", "Admin key incorrecta."))
                if admin_username != CONFIG.admin0_username:
                    return send_json(self, 401, err("UNAUTHORIZED", "Usuario administrador incorrecto."))
                if not verify_pbkdf2_password(admin_password, CONFIG.admin_password_hash):
                    return send_json(self, 401, err("UNAUTHORIZED", "Contraseña incorrecta."))
                rol = "admin"
            else:
                op_nombre = (dto.get("operador_nombre") or "").strip().lower()
                op_apellido = (dto.get("operador_apellido") or "").strip().lower()
                if op_nombre == "admin" and op_apellido == "cnc":
                    return send_json(
                        self,
                        400,
                        err("VALIDATION_ERROR", "Credenciales reservadas. Use el acceso administrador."),
                    )
                rol = "operador"

            try:
                data = self.sesion.iniciar_registro_turno(dto["operador_nombre"], dto["operador_apellido"])
                data["rol"] = rol
                if rol == "admin":
                    data["admin_key"] = CONFIG.admin_key
                return send_json(self, 201, ok(data))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al crear registro de turno."))

        # =========================
        # PEDIDOS: crear
        # =========================
        if parsed.path == "/api/pedidos":
            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            valid, fields = validate_pedido_crear(dto)
            if not valid:
                return send_json(self, 400, err("VALIDATION_ERROR", "Hay campos inválidos.", fields))

            try:
                data = self.pedidos.crear_pedido(dto)
                return send_json(self, 201, ok(data))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al crear pedido."))

        # =========================================================
        # ✅ ARCHIVAR/RESTAURAR (SQL directo, requiere extras)
        # POST /api/pedidos/<id>/archivar | /restaurar
        # POST /api/anomalias/<id>/archivar | /restaurar
        # =========================================================
        if parsed.path.startswith("/api/pedidos/") or parsed.path.startswith("/api/anomalias/"):
            is_pedido = parsed.path.startswith("/api/pedidos/")
            is_anom = parsed.path.startswith("/api/anomalias/")

            if (is_pedido or is_anom) and (parsed.path.endswith("/archivar") or parsed.path.endswith("/restaurar")):
                base = "/api/pedidos/" if is_pedido else "/api/anomalias/"
                tail = parsed.path.split(base, 1)[1].strip("/")
                parts = tail.split("/")

                if len(parts) != 2 or parts[1] not in ("archivar", "restaurar"):
                    return send_json(self, 404, err("NOT_FOUND", "Endpoint no encontrado."))

                try:
                    item_id = self._parse_pos_int(parts[0])
                except ValueError:
                    return send_json(self, 400, err("VALIDATION_ERROR", "ID inválido."))

                rid_extras = self._handle_extras_guard()
                if rid_extras is None:
                    return  # guard ya responde

                tabla = "pedido" if is_pedido else "anomalia"
                flag = 1 if parts[1] == "archivar" else 0

                try:
                    exists = self.db.query_one(f"SELECT id FROM {tabla} WHERE id = ?;", (item_id,))
                    if not exists:
                        return send_json(self, 404, err("NOT_FOUND", f"{'Pedido' if is_pedido else 'Anomalía'} no encontrada."))

                    self.db.execute(f"UPDATE {tabla} SET es_archivado = ? WHERE id = ?;", (flag, item_id))

                    self._extras_audit(
                        rid_extras,
                        "ARCHIVAR" if flag == 1 else "RESTAURAR",
                        tabla,
                        item_id,
                        f"{'Archivado' if flag == 1 else 'Restaurado'} via endpoint.",
                    )

                    return send_json(self, 200, ok({"id": item_id, "es_archivado": flag}))

                except Exception:
                    return send_json(
                        self,
                        500,
                        err(
                            "DB_ERROR",
                            f"Error al actualizar el estado de archivado de la {'pedido' if is_pedido else 'anomalia'}.",
                        ),
                    )

        # =========================
        # PEDIDOS: actualizar (extras/operador)
        # =========================
        if parsed.path.startswith("/api/pedidos/") and parsed.path.endswith("/actualizar"):
            tail = parsed.path.split("/api/pedidos/", 1)[1].strip("/")
            parts = tail.split("/")

            if len(parts) != 2 or parts[1] != "actualizar":
                return send_json(self, 404, err("NOT_FOUND", "Endpoint no encontrado."))

            try:
                pedido_id = self._parse_pos_int(parts[0])
            except ValueError:
                return send_json(self, 400, err("VALIDATION_ERROR", "ID de pedido inválido."))

            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            rid_extras = self._get_extras_rid_if_any()
            is_extras = rid_extras is not None

            try:
                if is_extras and hasattr(self.pedidos, "actualizar_pedido_admin"):
                    data = self.pedidos.actualizar_pedido_admin(pedido_id, dto)  # type: ignore
                    self._extras_audit(
                        rid_extras,
                        "ACTUALIZAR_PEDIDO_EXTRAS",
                        "pedido",
                        pedido_id,
                        "Actualización extras (edición completa/reapertura).",
                    )
                else:
                    valid, fields = validate_pedido_actualizar_operador(dto)
                    if not valid:
                        return send_json(self, 400, err("VALIDATION_ERROR", "Hay campos inválidos.", fields))
                    data = self.pedidos.actualizar_pedido_operador(pedido_id, dto)

                return send_json(self, 200, ok(data))

            except ValueError as ve:
                code = str(ve)
                if code == "NOT_FOUND":
                    return send_json(self, 404, err("NOT_FOUND", "Pedido no encontrado."))
                if code == "ARCHIVED":
                    return send_json(self, 400, err("VALIDATION_ERROR", "No se puede modificar un pedido archivado."))
                if code == "LOCKED":
                    return send_json(
                        self,
                        400,
                        err(
                            "VALIDATION_ERROR",
                            "El pedido ya fue cerrado (completado/cancelado) y no admite modificaciones.",
                        ),
                    )
                if code == "PLANCHAS_INVALID":
                    return send_json(self, 400, err("VALIDATION_ERROR", "Planchas asignadas inválidas."))
                if code == "ULTIMA_OUT_OF_RANGE":
                    return send_json(self, 400, err("VALIDATION_ERROR", "Última plancha fuera de rango."))
                if code == "CORTES_NEG":
                    return send_json(self, 400, err("VALIDATION_ERROR", "Cortes totales inválidos."))
                if code == "ESTADO_INVALIDO":
                    return send_json(self, 400, err("VALIDATION_ERROR", "Estado inválido."))
                if code == "NO_COMPLETABLE":
                    return send_json(
                        self,
                        400,
                        err("VALIDATION_ERROR", "No se puede completar si faltan planchas por trabajar."),
                    )
                return send_json(self, 400, err("VALIDATION_ERROR", "Solicitud inválida."))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al actualizar el pedido."))

        # =========================
        # ANOMALÍAS: crear
        # =========================
        if parsed.path == "/api/anomalias":
            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            valid, fields = validate_anomalia_crear(dto)
            if not valid:
                return send_json(self, 400, err("VALIDATION_ERROR", "Hay campos inválidos.", fields))

            try:
                data = self.anomalias.crear_anomalia(dto)
                return send_json(self, 201, ok(data))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al crear anomalía."))

        # =========================
        # ANOMALÍAS: actualizar (extras/operador)
        # =========================
        if parsed.path.startswith("/api/anomalias/") and parsed.path.endswith("/actualizar"):
            tail = parsed.path.split("/api/anomalias/", 1)[1].strip("/")
            parts = tail.split("/")

            if len(parts) != 2 or parts[1] != "actualizar":
                return send_json(self, 404, err("NOT_FOUND", "Endpoint no encontrado."))

            try:
                anomalia_id = self._parse_pos_int(parts[0])
            except ValueError:
                return send_json(self, 400, err("VALIDATION_ERROR", "ID de anomalía inválido."))

            try:
                dto = read_json(self)
            except ValueError as ex:
                return send_json(self, 400, err("VALIDATION_ERROR", str(ex)))

            rid_extras = self._get_extras_rid_if_any()
            is_extras = rid_extras is not None

            try:
                if is_extras and hasattr(self.anomalias, "actualizar_anomalia_admin"):
                    data = self.anomalias.actualizar_anomalia_admin(anomalia_id, dto)  # type: ignore
                    self._extras_audit(
                        rid_extras,
                        "ACTUALIZAR_ANOMALIA_EXTRAS",
                        "anomalia",
                        anomalia_id,
                        "Actualización extras (incluye reversión/edición completa).",
                    )
                else:
                    valid, fields = validate_anomalia_actualizar_operador(dto)
                    if not valid:
                        return send_json(self, 400, err("VALIDATION_ERROR", "Hay campos inválidos.", fields))
                    data = self.anomalias.actualizar_anomalia_operador(anomalia_id, dto)

                return send_json(self, 200, ok(data))

            except ValueError as ve:
                code = str(ve)
                if code == "NOT_FOUND":
                    return send_json(self, 404, err("NOT_FOUND", "Anomalía no encontrada."))
                if code == "ARCHIVED":
                    return send_json(
                        self, 400, err("VALIDATION_ERROR", "No se puede modificar una anomalía archivada.")
                    )
                if code == "LOCKED":
                    return send_json(
                        self,
                        400,
                        err(
                            "VALIDATION_ERROR",
                            "La anomalía ya fue cerrada (solucionada) y no admite modificaciones.",
                        ),
                    )
                if code == "ESTADO_INVALIDO":
                    return send_json(self, 400, err("VALIDATION_ERROR", "Estado inválido."))
                if code == "SOLUCION_REQUERIDA":
                    return send_json(
                        self,
                        400,
                        err("VALIDATION_ERROR", "La solución es obligatoria (mínimo 10 caracteres)."),
                    )
                return send_json(self, 400, err("VALIDATION_ERROR", "Solicitud inválida."))
            except Exception:
                return send_json(self, 500, err("DB_ERROR", "Error al actualizar la anomalía."))

        return send_json(self, 404, err("NOT_FOUND", "Endpoint no encontrado."))

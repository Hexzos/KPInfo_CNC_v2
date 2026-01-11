# server/services/auth_service.py
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from server.config import CONFIG
from server.http.security import hash_pbkdf2_password, verify_pbkdf2_password


class AuthService:
    SESSION_HOURS = 8

    def __init__(self, db):
        self.db = db

    def _now(self) -> datetime:
        # UTC naive; en SQLite datetime('now') también es UTC.
        return datetime.utcnow()

    def _token_hash(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _expira_en(self) -> str:
        return (self._now() + timedelta(hours=self.SESSION_HOURS)).strftime("%Y-%m-%d %H:%M:%S")

    # ==========================================================
    # "Usuario 0" (bootstrap admin) - compat con tu esquema actual
    # ==========================================================
    def _bootstrap_username(self) -> str:
        return (getattr(CONFIG, "admin_username", "") or "").strip()

    def _bootstrap_email(self) -> str:
        """
        Mantiene compatibilidad:
        - Si en CONFIG agregas admin_email, se usa.
        - Si no existe, se construye uno estable (admin@local).
        """
        cfg_email = (getattr(CONFIG, "admin_email", "") or "").strip()
        if cfg_email:
            return cfg_email
        u = self._bootstrap_username() or "admin"
        # email "técnico" para cumplir constraints/índices (no se expone al usuario final)
        return f"{u}@local"

    def _bootstrap_pwd_hash(self) -> str:
        return (getattr(CONFIG, "admin_password_hash", "") or "").strip()

    def _bootstrap_row(self) -> Optional[Dict[str, Any]]:
        """
        Identifica al usuario 0 por (username==CONFIG.admin_username) y/o (email==bootstrap_email).
        """
        u = self._bootstrap_username()
        e = self._bootstrap_email()
        if not u and not e:
            return None
        return self.db.query_one(
            """
            SELECT id, nombre, apellido, email, username, password_hash, rol, activo
            FROM usuario
            WHERE (username = ? COLLATE NOCASE)
               OR (email = ? COLLATE NOCASE)
            LIMIT 1;
            """,
            (u, e),
        )

    def ensure_bootstrap_admin(self) -> None:
        """
        Usuario 0 (failsafe):
        - Existe aunque ya haya usuarios.
        - Solo se re-habilita automáticamente si NO hay otro admin activo.
        - Si no existe, se crea.
        """
        username = self._bootstrap_username()
        email = self._bootstrap_email()
        pwd_hash = self._bootstrap_pwd_hash()

        # defensivo
        if not username or not pwd_hash:
            return

        row0 = self._bootstrap_row()

        # Si no existe, crearlo (activo)
        if not row0:
            self.db.execute(
                """
                INSERT INTO usuario (nombre, apellido, email, username, password_hash, rol, activo)
                VALUES ('Admin', 'Sistema', ?, ?, ?, 'admin', 1);
                """,
                (email, username, pwd_hash),
            )
            return

        # Si existe pero quedó inactivo, re-habilitar SOLO si no hay otro admin activo
        if int(row0.get("activo") or 0) != 1:
            other_admin = self.db.query_one(
                """
                SELECT id
                FROM usuario
                WHERE rol = 'admin'
                  AND activo = 1
                  AND id <> ?
                LIMIT 1;
                """,
                (row0["id"],),
            )
            if not other_admin:
                self.db.execute(
                    "UPDATE usuario SET activo = 1, actualizado_en = datetime('now') WHERE id = ?;",
                    (row0["id"],),
                )

        # Asegurar que mantenga rol admin (por si alguien lo cambió)
        if (row0.get("rol") or "") != "admin":
            self.db.execute(
                "UPDATE usuario SET rol = 'admin', actualizado_en = datetime('now') WHERE id = ?;",
                (row0["id"],),
            )

    # ==========================================================
    # API pública Auth
    # ==========================================================
    def register(
        self,
        nombre: str,
        apellido: str,
        email: str,
        password: str,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        nombre = (nombre or "").strip()
        apellido = (apellido or "").strip()
        email = (email or "").strip()
        username = (username or "").strip() or None

        if len(nombre) < 2 or len(apellido) < 2:
            raise ValueError("NOMBRE_APELLIDO_INVALIDO")
        if "@" not in email or len(email) < 6:
            raise ValueError("EMAIL_INVALIDO")
        if len(password or "") < 8:
            raise ValueError("PASSWORD_DEBIL")
        if username and len(username) < 3:
            raise ValueError("USERNAME_INVALIDO")

        if self.db.query_one("SELECT id FROM usuario WHERE email = ? COLLATE NOCASE;", (email,)):
            raise ValueError("EMAIL_YA_EXISTE")
        if username and self.db.query_one("SELECT id FROM usuario WHERE username = ? COLLATE NOCASE;", (username,)):
            raise ValueError("USERNAME_YA_EXISTE")

        pwd_hash = hash_pbkdf2_password(password)

        uid = self.db.execute(
            """
            INSERT INTO usuario (nombre, apellido, email, username, password_hash, rol, activo)
            VALUES (?, ?, ?, ?, ?, 'operador', 1);
            """,
            (nombre, apellido, email, username, pwd_hash),
        )
        return {"id": uid}

    def login(self, identificador: str, password: str) -> Dict[str, Any]:
        # Asegura existencia del "usuario 0" antes de autenticar
        self.ensure_bootstrap_admin()

        ident = (identificador or "").strip()
        password = password or ""
        if not ident or not password:
            raise ValueError("CREDENCIALES_REQUERIDAS")

        row = self.db.query_one(
            """
            SELECT id, nombre, apellido, email, username, password_hash, rol, activo
            FROM usuario
            WHERE email = ? COLLATE NOCASE
               OR username = ? COLLATE NOCASE
            LIMIT 1;
            """,
            (ident, ident),
        )
        if not row:
            raise PermissionError("LOGIN_INVALIDO")
        if int(row["activo"]) != 1:
            raise PermissionError("USUARIO_INACTIVO")
        if not verify_pbkdf2_password(password, row["password_hash"]):
            raise PermissionError("LOGIN_INVALIDO")

        token = secrets.token_urlsafe(32)
        th = self._token_hash(token)
        exp = self._expira_en()

        self.db.execute(
            """
            INSERT INTO auth_sesion (usuario_id, token_hash, expira_en, revocado)
            VALUES (?, ?, ?, 0);
            """,
            (row["id"], th, exp),
        )
        self.db.execute(
            "UPDATE usuario SET ultimo_login_en = datetime('now') WHERE id = ?;",
            (row["id"],),
        )

        return {
            "token": token,
            "expira_en": exp,
            "usuario": {
                "id": row["id"],
                "nombre": row["nombre"],
                "apellido": row["apellido"],
                "email": row["email"],
                "username": row["username"],
                "rol": row["rol"],
            },
        }

    def logout(self, token: str) -> None:
        t = (token or "").strip()
        if not t:
            return
        th = self._token_hash(t)
        self.db.execute("UPDATE auth_sesion SET revocado = 1 WHERE token_hash = ?;", (th,))

    def get_usuario_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        t = (token or "").strip()
        if not t:
            return None
        th = self._token_hash(t)

        row = self.db.query_one(
            """
            SELECT u.id, u.nombre, u.apellido, u.email, u.username, u.rol, u.activo,
                   s.expira_en, s.revocado
            FROM auth_sesion s
            JOIN usuario u ON u.id = s.usuario_id
            WHERE s.token_hash = ?
            LIMIT 1;
            """,
            (th,),
        )
        if not row:
            return None
        if int(row["revocado"]) == 1 or int(row["activo"]) != 1:
            return None

        try:
            exp = datetime.strptime(row["expira_en"], "%Y-%m-%d %H:%M:%S")
            if exp < self._now():
                return None
        except Exception:
            return None

        try:
            self.db.execute(
                "UPDATE auth_sesion SET ultimo_uso_en = datetime('now') WHERE token_hash = ?;",
                (th,),
            )
        except Exception:
            pass

        return {
            "id": row["id"],
            "nombre": row["nombre"],
            "apellido": row["apellido"],
            "email": row["email"],
            "username": row["username"],
            "rol": row["rol"],
        }

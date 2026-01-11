# server/services/admin_usuarios_service.py
from typing import Any, Dict, List, Optional

from server.config import CONFIG
from server.http.security import hash_pbkdf2_password


class AdminUsuariosService:
    def __init__(self, db):
        self.db = db

    def _norm(self, s) -> str:
        return (s or "").strip()

    def _email_ok(self, email: str) -> bool:
        # validación mínima (el resto en frontend si quieres)
        return ("@" in email) and (len(email) >= 6) and (" " not in email)

    def _is_admin0(self, email: str, username: Optional[str]) -> bool:
        e = (email or "").strip().lower()
        u = (username or "").strip().lower()
        return (e == (CONFIG.admin0_email or "").strip().lower()) or (u == (CONFIG.admin0_username or "").strip().lower())

    def _count_other_active_admins(self, exclude_uid: int) -> int:
        row = self.db.query_one(
            """
            SELECT COUNT(1) AS c
            FROM usuario
            WHERE rol='admin' AND activo=1 AND id <> ?;
            """,
            (exclude_uid,),
        )
        return int(row["c"]) if row and row.get("c") is not None else 0

    def listar(self, q: str = "", activos: Optional[int] = None, rol: str = "") -> List[Dict[str, Any]]:
        q = self._norm(q)
        rol = self._norm(rol)

        where = []
        params = []

        if q:
            where.append("(nombre LIKE ? OR apellido LIKE ? OR email LIKE ? OR username LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like, like, like])

        if activos in (0, 1):
            where.append("activo = ?")
            params.append(int(activos))

        if rol in ("operador", "admin"):
            where.append("rol = ?")
            params.append(rol)

        w = (" WHERE " + " AND ".join(where)) if where else ""
        sql = f"""
        SELECT id, nombre, apellido, email, username, rol, activo, creado_en, ultimo_login_en
        FROM usuario
        {w}
        ORDER BY id DESC;
        """
        return self.db.query_all(sql, tuple(params))

    def crear(self, nombre, apellido, email, password, username=None, rol="operador", activo=1) -> int:
        nombre = self._norm(nombre)
        apellido = self._norm(apellido)
        email = self._norm(email)
        username = self._norm(username) or None

        if len(nombre) < 2 or len(apellido) < 2:
            raise ValueError("NOMBRE_APELLIDO_INVALIDO")
        if not self._email_ok(email):
            raise ValueError("EMAIL_INVALIDO")

        if username and len(username) < 3:
            raise ValueError("USERNAME_INVALIDO")

        if rol not in ("operador", "admin"):
            raise ValueError("ROL_INVALIDO")

        if len(password or "") < 8:
            raise ValueError("PASSWORD_DEBIL")

        activo_i = 1 if int(activo or 0) == 1 else 0

        if self.db.query_one("SELECT id FROM usuario WHERE email = ? COLLATE NOCASE;", (email,)):
            raise ValueError("EMAIL_YA_EXISTE")
        if username and self.db.query_one("SELECT id FROM usuario WHERE username = ? COLLATE NOCASE;", (username,)):
            raise ValueError("USERNAME_YA_EXISTE")

        pwd_hash = hash_pbkdf2_password(password)
        uid = self.db.execute(
            """
            INSERT INTO usuario (nombre, apellido, email, username, password_hash, rol, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (nombre, apellido, email, username, pwd_hash, rol, activo_i),
        )
        return uid

    def actualizar(self, uid: int, nombre, apellido, email, username=None, rol=None) -> None:
        uid = int(uid or 0)
        if uid <= 0:
            raise ValueError("NO_EXISTE")

        nombre = self._norm(nombre)
        apellido = self._norm(apellido)
        email = self._norm(email)
        username = self._norm(username) or None

        if len(nombre) < 2 or len(apellido) < 2:
            raise ValueError("NOMBRE_APELLIDO_INVALIDO")
        if not self._email_ok(email):
            raise ValueError("EMAIL_INVALIDO")
        if username and len(username) < 3:
            raise ValueError("USERNAME_INVALIDO")

        current = self.db.query_one("SELECT id, rol, activo, email, username FROM usuario WHERE id = ?;", (uid,))
        if not current:
            raise ValueError("NO_EXISTE")

        if self.db.query_one("SELECT id FROM usuario WHERE email = ? COLLATE NOCASE AND id <> ?;", (email, uid)):
            raise ValueError("EMAIL_YA_EXISTE")
        if username and self.db.query_one(
            "SELECT id FROM usuario WHERE username = ? COLLATE NOCASE AND id <> ?;",
            (username, uid),
        ):
            raise ValueError("USERNAME_YA_EXISTE")

        # validar rol (si viene)
        if rol is not None and rol != "":
            if rol not in ("operador", "admin"):
                raise ValueError("ROL_INVALIDO")
        else:
            rol = None

        # Regla: no permitir “quitar admin” al último admin activo (incluye admin0 si está activo)
        if rol == "operador" and (current.get("rol") == "admin") and int(current.get("activo") or 0) == 1:
            other_admins = self._count_other_active_admins(uid)
            if other_admins <= 0:
                raise ValueError("LAST_ADMIN")

        self.db.execute(
            """
            UPDATE usuario
            SET nombre = ?, apellido = ?, email = ?, username = ?,
                rol = COALESCE(?, rol),
                actualizado_en = datetime('now')
            WHERE id = ?;
            """,
            (nombre, apellido, email, username, rol, uid),
        )

    def toggle_activo(self, uid: int, activo: int) -> None:
        uid = int(uid or 0)
        if uid <= 0:
            raise ValueError("NO_EXISTE")

        row = self.db.query_one("SELECT id, rol, activo, email, username FROM usuario WHERE id = ?;", (uid,))
        if not row:
            raise ValueError("NO_EXISTE")

        activo_i = 1 if int(activo or 0) == 1 else 0
        rol = (row.get("rol") or "").strip()

        # Regla principal: si vas a desactivar un admin, no puedes dejar 0 admins activos.
        if rol == "admin" and activo_i == 0 and int(row.get("activo") or 0) == 1:
            other_admins = self._count_other_active_admins(uid)
            if other_admins <= 0:
                raise ValueError("LAST_ADMIN")

        self.db.execute(
            "UPDATE usuario SET activo = ?, actualizado_en = datetime('now') WHERE id = ?;",
            (activo_i, uid),
        )

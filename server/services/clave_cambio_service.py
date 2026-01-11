# server/services/clave_cambio_service.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from server.http.security import hash_pbkdf2_password


class ClaveCambioService:
    """
    Variante 2 (sin SMTP):
    - Operador solicita cambio ingresando nueva contraseña (se guarda SOLO hash).
    - Admin aprueba/cancela desde panel.
    - Reglas:
      - 1 solicitud activa (PENDING) a la vez.
      - Expira en 2 horas.
      - Rate limit: máximo 2 solicitudes cada 8 horas por usuario.
      - No filtrar existencia de usuario (eso se maneja en el endpoint).
    """

    TTL_HOURS = 2
    WINDOW_HOURS = 8
    MAX_REQ_PER_WINDOW = 2

    def __init__(self, db):
        self.db = db

    def _now(self) -> datetime:
        return datetime.utcnow()

    def _ts(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _expire_pending_for_user(self, usuario_id: int) -> None:
        now = self._ts(self._now())
        # Marca como EXPIRED cualquier PENDING vencida
        self.db.execute(
            """
            UPDATE password_change_request
               SET estado = 'EXPIRED',
                   resuelto_en = datetime('now')
             WHERE usuario_id = ?
               AND estado = 'PENDING'
               AND expira_en < ?;
            """,
            (usuario_id, now),
        )

    def _get_user_by_ident(self, ident: str) -> Optional[Dict[str, Any]]:
        ident = (ident or "").strip()
        if not ident:
            return None
        return self.db.query_one(
            """
            SELECT id, activo, rol
              FROM usuario
             WHERE email = ? COLLATE NOCASE
                OR username = ? COLLATE NOCASE
             LIMIT 1;
            """,
            (ident, ident),
        )

    def request_change(self, identificador: str, new_password: str, origen_ip: Optional[str] = None) -> None:
        """
        Crea solicitud PENDING con hash PBKDF2, respetando rate limit y 1-activa.
        Si el usuario no existe o está inactivo, NO crea nada (pero el endpoint responde OK genérico).
        """
        u = self._get_user_by_ident(identificador)
        if not u:
            return
        uid = int(u.get("id") or 0)
        if uid <= 0:
            return
        if int(u.get("activo") or 0) != 1:
            # usuario inactivo: no crear solicitud (silencioso)
            return

        self._expire_pending_for_user(uid)

        now_dt = self._now()
        now = self._ts(now_dt)

        # 1) Si hay una PENDING vigente, no crear otra
        pending = self.db.query_one(
            """
            SELECT id
              FROM password_change_request
             WHERE usuario_id = ?
               AND estado = 'PENDING'
               AND expira_en >= ?
             ORDER BY creado_en DESC
             LIMIT 1;
            """,
            (uid, now),
        )
        if pending:
            return

        # 2) Rate limit: máximo 2 solicitudes en últimas 8 horas
        window_start = self._ts(now_dt - timedelta(hours=self.WINDOW_HOURS))
        row = self.db.query_one(
            """
            SELECT COUNT(*) AS n
              FROM password_change_request
             WHERE usuario_id = ?
               AND creado_en >= ?;
            """,
            (uid, window_start),
        ) or {}
        try:
            n = int(row.get("n") or 0)
        except Exception:
            n = 0

        if n >= self.MAX_REQ_PER_WINDOW:
            return

        # 3) Crear solicitud
        if len(new_password or "") < 8:
            # La validación fuerte se hace en el endpoint; aquí solo defensivo.
            return

        pwd_hash = hash_pbkdf2_password(new_password)
        expira_en = self._ts(now_dt + timedelta(hours=self.TTL_HOURS))

        self.db.execute(
            """
            INSERT INTO password_change_request (
              usuario_id, estado, pending_password_hash,
              creado_en, expira_en,
              origen_ip
            )
            VALUES (?, 'PENDING', ?, datetime('now'), ?, ?);
            """,
            (uid, pwd_hash, expira_en, (origen_ip or None)),
        )

    def get_status(self, usuario_id: int, history_limit: int = 5) -> Dict[str, Any]:
        """
        Devuelve:
          - active: solicitud PENDING vigente o null
          - history: últimas N solicitudes no activas (APPROVED/CANCELLED/EXPIRED)
        """
        uid = int(usuario_id or 0)
        if uid <= 0:
            return {"active": None, "history": []}

        self._expire_pending_for_user(uid)
        now = self._ts(self._now())

        active = self.db.query_one(
            """
            SELECT id, creado_en, expira_en, origen_ip
              FROM password_change_request
             WHERE usuario_id = ?
               AND estado = 'PENDING'
               AND expira_en >= ?
             ORDER BY creado_en DESC
             LIMIT 1;
            """,
            (uid, now),
        )

        history: List[Dict[str, Any]] = self.db.query_all(
            """
            SELECT id, estado, creado_en, expira_en, resuelto_en, resuelto_por, origen_ip
              FROM password_change_request
             WHERE usuario_id = ?
               AND estado <> 'PENDING'
             ORDER BY creado_en DESC
             LIMIT ?;
            """,
            (uid, int(history_limit)),
        ) or []

        return {"active": active, "history": history}

    def approve(self, usuario_id: int, admin_id: int) -> None:
        uid = int(usuario_id or 0)
        aid = int(admin_id or 0)
        if uid <= 0 or aid <= 0:
            raise ValueError("INVALID")

        # usuario debe estar activo (si está inactivo, no aplicar cambios)
        u = self.db.query_one("SELECT id, activo FROM usuario WHERE id = ? LIMIT 1;", (uid,))
        if not u:
            raise ValueError("NO_USER")
        if int(u.get("activo") or 0) != 1:
            raise ValueError("USUARIO_INACTIVO")

        self._expire_pending_for_user(uid)
        now = self._ts(self._now())

        req = self.db.query_one(
            """
            SELECT id, pending_password_hash, expira_en
              FROM password_change_request
             WHERE usuario_id = ?
               AND estado = 'PENDING'
               AND expira_en >= ?
             ORDER BY creado_en DESC
             LIMIT 1;
            """,
            (uid, now),
        )
        if not req:
            raise ValueError("NO_PENDING")

        # 1) aplicar password
        self.db.execute(
            "UPDATE usuario SET password_hash = ?, actualizado_en = datetime('now') WHERE id = ?;",
            (req["pending_password_hash"], uid),
        )

        # 2) revocar sesiones del usuario (logout forzado)
        self.db.execute(
            "UPDATE auth_sesion SET revocado = 1 WHERE usuario_id = ?;",
            (uid,),
        )

        # 3) cerrar solicitud
        self.db.execute(
            """
            UPDATE password_change_request
               SET estado = 'APPROVED',
                   resuelto_en = datetime('now'),
                   resuelto_por = ?
             WHERE id = ?;
            """,
            (aid, req["id"]),
        )

    def cancel(self, usuario_id: int, admin_id: int) -> None:
        uid = int(usuario_id or 0)
        aid = int(admin_id or 0)
        if uid <= 0 or aid <= 0:
            raise ValueError("INVALID")

        self._expire_pending_for_user(uid)
        now = self._ts(self._now())

        req = self.db.query_one(
            """
            SELECT id
              FROM password_change_request
             WHERE usuario_id = ?
               AND estado = 'PENDING'
               AND expira_en >= ?
             ORDER BY creado_en DESC
             LIMIT 1;
            """,
            (uid, now),
        )
        if not req:
            raise ValueError("NO_PENDING")

        self.db.execute(
            """
            UPDATE password_change_request
               SET estado = 'CANCELLED',
                   resuelto_en = datetime('now'),
                   resuelto_por = ?
             WHERE id = ?;
            """,
            (aid, req["id"]),
        )

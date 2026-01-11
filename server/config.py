# server/config.py
import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=False)  # permitir rotar claves en runtime si lo necesitas
class Config:
    # ==========================================================
    # Runtime (local vs Fly)
    # - Fly requiere escuchar en 0.0.0.0
    # - Fly expone el puerto por env (típicamente PORT=8080)
    # ==========================================================
    host: str = os.getenv("APP_HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", os.getenv("APP_PORT", "8000")))

    # ==========================================================
    # Paths
    # - En Fly, DB_PATH debería apuntar a un volumen montado (ej: /data/cnc.sqlite3)
    # - Si no existe DB_PATH, se mantiene el comportamiento local (data/cnc.sqlite3)
    # ==========================================================
    db_path: Path = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "cnc.sqlite3")))
    schema_path: Path = BASE_DIR / "server" / "schema.sql"
    web_root: Path = BASE_DIR / "web"

    # ==========================================================
    # EXTRAS (legacy funcional)
    # - Mantiene compatibilidad: se sigue usando CONFIG.extra_key
    # - En Fly: definir EXTRA_KEY como secret para no hardcodear
    # ==========================================================
    extra_key: str = os.getenv("EXTRA_KEY", "operadorCNC.1234")

    # ==========================================================
    # ADMIN 0 (failsafe / hardcodeado)
    # - Bootstrap para poder entrar y crear admins reales.
    # ==========================================================
    admin0_email: str = os.getenv("ADMIN0_EMAIL", "admin@kpinfo.local")
    admin0_username: str = os.getenv("ADMIN0_USERNAME", "admin")

    # ==========================================================
    # ADMIN (panel legacy) - compat con código existente
    # - api_post.py y mixins.py hoy usan estos nombres.
    # - Mantenerlos evita tocar más archivos por ahora.
    # ==========================================================
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")  # alias compat (legacy)
    admin_key: str = os.getenv("ADMIN_KEY", "AdminPanel.2026")

    # Hash PBKDF2 (sha256) formato:
    # pbkdf2_sha256$<iters>$<salt_hex>$<hash_hex>
    # Password por defecto para este hash: adminCNC.1234
    admin_password_hash: str = os.getenv(
        "ADMIN_PASSWORD_HASH",
        "pbkdf2_sha256$200000$01010101010101010101010101010101$"
        "7227409565b7b96510ec33e91ee8fed9ce1aaa25edd0fc9ae79f0b70df189e6e",
    )

    def __post_init__(self) -> None:
        """
        Ajuste sutil:
        Mantener consistencia entre admin0_username y admin_username
        (compatibilidad con el flujo legacy que aún compara admin_username).
        """
        if not getattr(self, "admin_username", "") and getattr(self, "admin0_username", ""):
            self.admin_username = self.admin0_username
        if not getattr(self, "admin0_username", "") and getattr(self, "admin_username", ""):
            self.admin0_username = self.admin_username


CONFIG = Config()

# server/http/security.py
import os
import binascii
import hashlib
import hmac

PBKDF2_ITERS_DEFAULT = 200_000
PBKDF2_SALT_BYTES = 16


def hash_pbkdf2_password(plain: str, iters: int = PBKDF2_ITERS_DEFAULT) -> str:
    """
    Return format:
      pbkdf2_sha256$<iters>$<salt_hex>$<hash_hex>
    """
    if plain is None:
        raise ValueError("password requerido")
    plain = str(plain)
    if not plain:
        raise ValueError("password requerido")

    salt = os.urandom(PBKDF2_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, int(iters))
    return "pbkdf2_sha256$%d$%s$%s" % (
        int(iters),
        binascii.hexlify(salt).decode("ascii"),
        binascii.hexlify(dk).decode("ascii"),
    )


def verify_pbkdf2_password(plain: str, stored: str) -> bool:
    """
    stored format:
      pbkdf2_sha256$<iters>$<salt_hex>$<hash_hex>
    """
    try:
        parts = stored.split("$")
        if len(parts) != 4:
            return False
        algo, iters_s, salt_hex, hash_hex = parts
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = binascii.unhexlify(salt_hex.encode("ascii"))
        expected = binascii.unhexlify(hash_hex.encode("ascii"))

        dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, iters)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False

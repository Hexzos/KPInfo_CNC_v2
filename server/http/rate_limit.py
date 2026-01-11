# server/http/rate_limit.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass(frozen=True)
class RateRule:
    limit: int
    window_seconds: int


# Memoria en proceso:
# key -> lista de timestamps (epoch seconds)
_BUCKETS: Dict[str, List[float]] = {}


def _client_ip(handler) -> str:
    try:
        return (handler.client_address[0] if getattr(handler, "client_address", None) else "unknown") or "unknown"
    except Exception:
        return "unknown"


def rate_limit_check(handler, *, scope: str, rule: RateRule) -> Tuple[bool, int]:
    """
    Rate limit en memoria (por proceso), clave por IP + scope.
    - Retorna (allowed, retry_after_seconds).
    - 'scope' sirve para agrupar por endpoint/prefijo/método.

    Limitación conocida: si ejecutas múltiples instancias/procesos, el contador no se comparte.
    Para Fly con 1 instancia es suficiente; para multi-instancia habría que centralizar.
    """
    ip = _client_ip(handler)
    key = f"{ip}:{scope}"

    now = time.time()
    window_start = now - float(rule.window_seconds)

    hits = _BUCKETS.get(key)
    if hits is None:
        hits = []
        _BUCKETS[key] = hits

    # limpiar eventos fuera de ventana
    while hits and hits[0] < window_start:
        hits.pop(0)

    if len(hits) >= int(rule.limit):
        # calcular retry_after: cuando salga el primer hit de la ventana
        oldest = hits[0] if hits else now
        retry_after = int((oldest + rule.window_seconds) - now)
        if retry_after < 1:
            retry_after = 1
        return False, retry_after

    hits.append(now)
    return True, 0

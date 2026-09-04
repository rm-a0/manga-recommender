"""Response models for the liveness and readiness probes."""

from typing import Literal

from pydantic import BaseModel


class Health(BaseModel):
    """Liveness response. Answered without touching any dependency."""

    status: Literal["ok"] = "ok"


class Readiness(BaseModel):
    """Readiness response, with one entry per checked dependency.

    `status` is "ready" only when every check passed.
    """

    status: Literal["ready", "degraded"]
    checks: dict[str, bool]

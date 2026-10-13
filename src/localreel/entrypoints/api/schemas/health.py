from typing import Literal

from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: Literal["ok", "unavailable"]
    db: Literal["ok", "down"]

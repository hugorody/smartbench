"""Common request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class APIMessage(BaseModel):
    message: str


class AuditStamp(BaseModel):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

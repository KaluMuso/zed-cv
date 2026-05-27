"""Legacy save/unsave response model."""

from pydantic import BaseModel


class SaveJobResponse(BaseModel):
    saved: bool = True

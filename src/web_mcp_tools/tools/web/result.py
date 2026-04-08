from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

PayloadT = TypeVar("PayloadT")


class Result(BaseModel, Generic[PayloadT]):
    """Structured result envelope for tool callers."""

    model_config = ConfigDict(extra="forbid")

    payload: PayloadT | None = Field(
        default=None, description="A valid payload object, None if invalid."
    )
    ok: bool = Field(description="request status")
    error_message: str | None = Field(
        default=None, description="error message when request fails"
    )

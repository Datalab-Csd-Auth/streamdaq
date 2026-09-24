from enum import StrEnum
from typing import Any, Literal

from fastapi import HTTPException, status
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

from streamdaq.api.adapters import validate_coerce_params
from streamdaq.api.registries import (
    INSTANT_CHECK_REGISTRY,
    MEASURE_REGISTRY,
    SINK_REGISTRY,
    SOURCE_REGISTRY,
    WINDOW_REGISTRY,
)
from streamdaq.translators.string_to_callable import resolve_must_be


class InputConfig(BaseModel):
    type: str = Field(
        ..., description="The type of input source (e.g., 'markdown_table', 'kafka')."
    )
    params: dict[str, Any] = Field(
        default_factory=dict, description="Configuration parameters for the input."
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in SOURCE_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input type must be one of {list(SOURCE_REGISTRY.keys())}",
            )
        return v


class OutputConfig(BaseModel):
    type: str = Field(..., description="The type of output sink (e.g., 'jsonlines').")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Configuration parameters for the output."
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in SINK_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Output type must be one of {list(SINK_REGISTRY.keys())}",
            )
        return v

    # TODO: Add a model_validator to validate the params against the output class's
    # expected parameters for each output type.


class InstantCheckConfig(BaseModel):
    name: str = Field(..., description="Human-readable name for the instant check.")
    check_class: str = Field(..., description="The class name of the check (e.g., 'InRange').")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the check instance."
    )

    @field_validator("check_class")
    @classmethod
    def validate_check_class(cls, v: str) -> str:
        if v not in INSTANT_CHECK_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Check class must be one of {list(INSTANT_CHECK_REGISTRY.keys())}",
            )
        return v

    @model_validator(mode="after")
    def validate_params(self) -> "InstantCheckConfig":
        check_cls = INSTANT_CHECK_REGISTRY.get(self.check_class)
        if check_cls:
            self.params = validate_coerce_params(
                check_cls,
                self.params,
                inject={"name": self.name},
                drop=("name",),
                label=self.check_class,
            )
        return self


class MeasureConfig(BaseModel):
    type: str = Field(..., description="The measure type (e.g., 'Mean', 'InRangeCount').")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters for the measure.")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in MEASURE_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Measure type must be one of {list(MEASURE_REGISTRY.keys())}",
            )
        return v

    @model_validator(mode="after")
    def validate_params(self) -> "MeasureConfig":
        measure_cls = MEASURE_REGISTRY.get(self.type)
        if measure_cls:
            self.params = validate_coerce_params(measure_cls, self.params, label=self.type)
        return self


class WindowCheckConfig(BaseModel):
    name: str = Field(..., description="Human-readable name for the window check.")
    measure: MeasureConfig
    must_be: str | None = Field(
        default=None, description="Condition that the measure must satisfy (e.g., '[1, 4]', '>=2')."
    )

    @field_validator("must_be")
    @classmethod
    def validate_must_be(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            resolve_must_be(value)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        return value


class WindowConfig(BaseModel):
    type: str = Field(..., description="The type of window (e.g., 'sliding', 'tumbling').")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters for the window.")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in WINDOW_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Window type must be one of {list(WINDOW_REGISTRY.keys())}",
            )
        return v


class WindowChecksConfig(BaseModel):
    window: WindowConfig
    checks: list[WindowCheckConfig]


class TaskStatus(StrEnum):
    """Lifecycle status of a task."""

    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class TaskConfig(BaseModel):
    name: str = Field(..., description="Name of the task.")
    windowby_column: str | None = Field(None, description="Column to window by.")
    input: InputConfig | None = Field(None, description="Input source configuration.")
    output: OutputConfig | None = Field(None, description="Output sink configuration.")
    instant_checks: list[InstantCheckConfig] = Field(default_factory=list)
    window_checks_config: WindowChecksConfig | None = None
    status: TaskStatus = Field(default=TaskStatus.RUNNING, description="Current lifecycle status.")


class SessionStatus(BaseModel):
    status: Literal["running", "stopped", "failed"]
    active_tasks_count: int
    version: str


class APIHeartbeat(BaseModel):
    status: Literal["OK"] = "OK"
    service: Literal["streamdaq"] = "streamdaq"

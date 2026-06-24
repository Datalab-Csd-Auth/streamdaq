from enum import Enum, StrEnum
from typing import Any, Literal

from fastapi import HTTPException, status
from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from streamdaq.api.registries import (
    INPUT_REGISTRY,
    INSTANT_CHECK_REGISTRY,
    MEASURE_REGISTRY,
    OUTPUT_REGISTRY,
    WINDOW_REGISTRY,
)


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
        if v not in INPUT_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input type must be one of {list(INPUT_REGISTRY.keys())}",
            )
        return v

    # TODO: Add a model_validator to validate the params against the input class's expected parameters for each input type.


class OutputConfig(BaseModel):
    type: str = Field(..., description="The type of output sink (e.g., 'jsonlines').")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Configuration parameters for the output."
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in OUTPUT_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Output type must be one of {list(OUTPUT_REGISTRY.keys())}",
            )
        return v

    # TODO: Add a model_validator to validate the params against the output class's expected parameters for each output type.


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
            try:
                validated_instance = TypeAdapter(check_cls).validate_python(
                    {"name": self.name, **self.params}
                )
                import dataclasses

                if dataclasses.is_dataclass(validated_instance):
                    coerced_params = dataclasses.asdict(validated_instance)
                    coerced_params.pop("name", None)
                    self.params = coerced_params
            except ValidationError as e:
                errors = []
                for err in e.errors():
                    loc = ".".join(map(str, err.get("loc", [])))
                    errors.append(f"{loc}: {err.get('msg', 'Invalid')}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid params for {self.check_class}: {'; '.join(errors)}",
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
            try:
                validated_instance = TypeAdapter(measure_cls).validate_python(self.params)
                import dataclasses

                if dataclasses.is_dataclass(validated_instance):
                    coerced_params = dataclasses.asdict(validated_instance)
                    self.params = coerced_params
            except ValidationError as e:
                errors = []
                for err in e.errors():
                    loc = ".".join(map(str, err.get("loc", [])))
                    errors.append(f"{loc}: {err.get('msg', 'Invalid')}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid params for {self.type}: {'; '.join(errors)}",
                )
        return self


class WindowCheckConfig(BaseModel):
    name: str = Field(..., description="Human-readable name for the window check.")
    measure: MeasureConfig
    must_be: str = Field(
        ..., description="Condition that the measure must satisfy (e.g., '[1, 4]', '>=2')."
    )

    # TODO: Add a model_validator to validate the must_be condition.


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

    DRAFT = "draft"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class TaskDynamicCreate(BaseModel):
    """Payload to create or update a draft task dynamically."""

    task_name: str = Field(..., description="Name of the task.")
    window_type: str | None = Field(None, description="Window type to set.")
    windowby_column: str | None = Field(None, description="Column to window by.")


class TaskConfig(BaseModel):
    name: str = Field(..., description="Name of the task.")
    windowby_column: str | None = Field(None, description="Column to window by.")
    input: InputConfig | None = Field(None, description="Input source configuration.")
    output: OutputConfig | None = Field(None, description="Output sink configuration.")
    instant_checks: list[InstantCheckConfig] = Field(default_factory=list)
    window_checks_config: WindowChecksConfig | None = None
    status: TaskStatus = Field(default=TaskStatus.DRAFT, description="Current lifecycle status.")


class SessionStatus(BaseModel):
    status: Literal["running", "stopped", "failed"]
    active_tasks_count: int
    version: str

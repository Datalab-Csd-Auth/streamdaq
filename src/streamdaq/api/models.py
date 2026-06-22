from typing import Any, Dict, List, Literal, Optional, Union

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator, TypeAdapter, ValidationError

from streamdaq.api.registries import (
    INPUT_REGISTRY,
    INSTANT_CHECK_REGISTRY,
    MEASURE_REGISTRY,
    OUTPUT_REGISTRY,
    WINDOW_REGISTRY,
)

class InputConfig(BaseModel):
    type: str = Field(..., description="The type of input source (e.g., 'markdown_table', 'kafka').")
    params: Dict[str, Any] = Field(default_factory=dict, description="Configuration parameters for the input.")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in INPUT_REGISTRY:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Input type must be one of {list(INPUT_REGISTRY.keys())}")
        return v


class OutputConfig(BaseModel):
    type: str = Field(..., description="The type of output sink (e.g., 'jsonlines').")
    params: Dict[str, Any] = Field(default_factory=dict, description="Configuration parameters for the output.")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in OUTPUT_REGISTRY:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Output type must be one of {list(OUTPUT_REGISTRY.keys())}")
        return v


class InstantCheckConfig(BaseModel):
    name: str = Field(..., description="Human-readable name for the instant check.")
    check_class: str = Field(..., description="The class name of the check (e.g., 'InRange').")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the check instance.")

    @field_validator('check_class')
    @classmethod
    def validate_check_class(cls, v: str) -> str:
        if v not in INSTANT_CHECK_REGISTRY:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Check class must be one of {list(INSTANT_CHECK_REGISTRY.keys())}")
        return v

    @model_validator(mode='after')
    def validate_params(self) -> 'InstantCheckConfig':
        check_cls = INSTANT_CHECK_REGISTRY.get(self.check_class)
        if check_cls:
            try:
                validated_instance = TypeAdapter(check_cls).validate_python({"name": self.name, **self.params})
                import dataclasses
                if dataclasses.is_dataclass(validated_instance):
                    coerced_params = dataclasses.asdict(validated_instance)
                    coerced_params.pop('name', None)
                    self.params = coerced_params
            except ValidationError as e:
                errors = []
                for err in e.errors():
                    loc = ".".join(map(str, err.get('loc', [])))
                    errors.append(f"{loc}: {err.get('msg', 'Invalid')}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid params for {self.check_class}: {'; '.join(errors)}"
                )
        return self


class MeasureConfig(BaseModel):
    type: str = Field(..., description="The measure type (e.g., 'Mean', 'InRangeCount').")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the measure.")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in MEASURE_REGISTRY:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Measure type must be one of {list(MEASURE_REGISTRY.keys())}")
        return v


class WindowCheckConfig(BaseModel):
    name: str = Field(..., description="Human-readable name for the window check.")
    measure: MeasureConfig
    must_be: str = Field(..., description="Condition that the measure must satisfy (e.g., '[1, 4]', '>=2').")


class WindowConfig(BaseModel):
    type: str = Field(..., description="The type of window (e.g., 'sliding', 'tumbling').")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the window.")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in WINDOW_REGISTRY:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Window type must be one of {list(WINDOW_REGISTRY.keys())}")
        return v


class WindowChecksConfig(BaseModel):
    window: WindowConfig
    checks: List[WindowCheckConfig]


class TaskConfig(BaseModel):
    name: str = Field(..., description="Name of the task.")
    windowby_column: Optional[str] = Field(None, description="Column to window by.")
    input: InputConfig
    output: OutputConfig
    instant_checks: List[InstantCheckConfig] = Field(default_factory=list)
    window_checks_config: Optional[WindowChecksConfig] = None


class SessionStatus(BaseModel):
    status: Literal["running", "stopped", "failed"]
    active_tasks_count: int
    version: str

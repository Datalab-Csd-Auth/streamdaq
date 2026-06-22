from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class InputConfig(BaseModel):
    type: str = Field(..., description="The type of input source (e.g., 'markdown_table', 'kafka').")
    params: Dict[str, Any] = Field(default_factory=dict, description="Configuration parameters for the input.")


class OutputConfig(BaseModel):
    type: str = Field(..., description="The type of output sink (e.g., 'jsonlines').")
    params: Dict[str, Any] = Field(default_factory=dict, description="Configuration parameters for the output.")


class InstantCheckConfig(BaseModel):
    name: str = Field(..., description="Human-readable name for the instant check.")
    check_class: str = Field(..., description="The class name of the check (e.g., 'InRange').")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the check instance.")


class MeasureConfig(BaseModel):
    type: str = Field(..., description="The measure type (e.g., 'Mean', 'InRangeCount').")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the measure.")


class WindowCheckConfig(BaseModel):
    name: str = Field(..., description="Human-readable name for the window check.")
    measure: MeasureConfig
    must_be: str = Field(..., description="Condition that the measure must satisfy (e.g., '[1, 4]', '>=2').")


class WindowConfig(BaseModel):
    type: str = Field(..., description="The type of window (e.g., 'sliding', 'tumbling').")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the window.")


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
    uptime_seconds: int
    version: str

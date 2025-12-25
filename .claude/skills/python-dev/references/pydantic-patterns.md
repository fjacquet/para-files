# Pydantic Patterns for AI Agents

## Table of Contents
- [Basic Validation](#basic-validation)
- [Nested Models](#nested-models)
- [Custom Validators](#custom-validators)
- [Discriminated Unions](#discriminated-unions)
- [Serialization](#serialization)

## Basic Validation

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class AgentConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    model: Literal["gpt-4", "claude-3", "gemini"] = "claude-3"
    max_tokens: int = Field(default=1000, gt=0)
```

## Nested Models

```python
class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class Conversation(BaseModel):
    messages: list[Message]
    metadata: dict[str, str] = Field(default_factory=dict)
```

## Custom Validators

```python
from pydantic import field_validator, model_validator

class FileInput(BaseModel):
    path: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.endswith((".py", ".json", ".yaml")):
            raise ValueError("Unsupported file type")
        return v

class DateRange(BaseModel):
    start: str
    end: str

    @model_validator(mode="after")
    def validate_range(self) -> "DateRange":
        if self.start > self.end:
            raise ValueError("start must be before end")
        return self
```

## Discriminated Unions

```python
from typing import Annotated, Union
from pydantic import Discriminator

class TextAction(BaseModel):
    action: Literal["text"] = "text"
    content: str

class ImageAction(BaseModel):
    action: Literal["image"] = "image"
    url: str
    alt: str

Action = Annotated[
    Union[TextAction, ImageAction],
    Discriminator("action")
]

class ToolResponse(BaseModel):
    actions: list[Action]
```

## Serialization

```python
class OutputModel(BaseModel):
    data: dict

    model_config = {
        "json_schema_extra": {
            "examples": [{"data": {"key": "value"}}]
        }
    }

# Usage
output = OutputModel(data={"result": 42})
json_str = output.model_dump_json(indent=2)
schema = OutputModel.model_json_schema()
```

## Error Handling Pattern

```python
from pydantic import ValidationError

def safe_parse(model: type[BaseModel], data: dict) -> BaseModel | None:
    try:
        return model.model_validate(data)
    except ValidationError as e:
        print(f"Validation failed: {e.error_count()} errors")
        for error in e.errors():
            print(f"  - {error['loc']}: {error['msg']}")
        return None
```
"""Pydantic v2 Compatibility Shim.

Imports standard Pydantic v2 if installed; otherwise provides a lightweight,
type-safe BaseModel and Field fallback using Python dataclasses so that
the codebase and tests run with zero external dependencies when needed.
"""

from __future__ import annotations

import dataclasses
import inspect
from typing import Any, get_type_hints

try:
    from pydantic import BaseModel as _PydanticBaseModel, Field as _PydanticField
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


if HAS_PYDANTIC:
    BaseModel = _PydanticBaseModel
    Field = _PydanticField
else:
    def Field(
        default: Any = ...,
        *,
        default_factory: Any = None,
        description: str = "",
        ge: float | None = None,
        le: float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        **kwargs: Any,
    ) -> Any:
        metadata = {
            "description": description,
            "ge": ge,
            "le": le,
            "min_length": min_length,
            "max_length": max_length,
            **kwargs,
        }
        if default_factory is not None:
            return dataclasses.field(default_factory=default_factory, metadata=metadata)
        if default is not ...:
            return dataclasses.field(default=default, metadata=metadata)
        return dataclasses.field(metadata=metadata)

    class BaseModel:
        """Lightweight Pydantic BaseModel fallback."""

        def __init__(self, **data: Any):
            type_hints = get_type_hints(self.__class__)
            for name, _ in type_hints.items():
                if name in data:
                    setattr(self, name, data[name])
                elif hasattr(self.__class__, name):
                    val = getattr(self.__class__, name)
                    if isinstance(val, dataclasses.Field):
                        if val.default_factory is not dataclasses.MISSING:
                            setattr(self, name, val.default_factory())
                        elif val.default is not dataclasses.MISSING:
                            setattr(self, name, val.default)
                        else:
                            raise ValueError(f"Missing required field '{name}' for {self.__class__.__name__}")
                    else:
                        setattr(self, name, val)
                else:
                    raise ValueError(f"Missing required field '{name}' for {self.__class__.__name__}")

        @classmethod
        def model_validate(cls, data: Any) -> BaseModel:
            if isinstance(data, cls):
                return data
            if isinstance(data, dict):
                return cls(**data)
            raise TypeError(f"Cannot validate {type(data)} into {cls.__name__}")

        def model_dump(self) -> dict[str, Any]:
            res: dict[str, Any] = {}
            for k, v in self.__dict__.items():
                if isinstance(v, BaseModel):
                    res[k] = v.model_dump()
                elif isinstance(v, list):
                    res[k] = [item.model_dump() if isinstance(item, BaseModel) else item for item in v]
                else:
                    res[k] = v
            return res

        @classmethod
        def model_json_schema(cls) -> dict[str, Any]:
            properties: dict[str, Any] = {}
            required: list[str] = []
            type_hints = get_type_hints(cls)
            
            for name, type_hint in type_hints.items():
                prop_info: dict[str, Any] = {"title": name.replace("_", " ").title()}
                if hasattr(cls, name):
                    field_obj = getattr(cls, name)
                    if isinstance(field_obj, dataclasses.Field) and field_obj.metadata:
                        desc = field_obj.metadata.get("description")
                        if desc:
                            prop_info["description"] = desc
                    if not (isinstance(field_obj, dataclasses.Field) and field_obj.default is not dataclasses.MISSING):
                        required.append(name)
                else:
                    required.append(name)
                properties[name] = prop_info

            return {
                "title": cls.__name__,
                "type": "object",
                "properties": properties,
                "required": required,
            }

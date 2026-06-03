"""Morning briefing editorial renderer package."""

from importlib import import_module
from typing import Any

__all__ = [
    "BriefingConfig",
    "RenderConfig",
    "build",
    "load_config",
    "render",
]


def build(*args: Any, **kwargs: Any) -> str:
    module = import_module(".build", __name__)
    return module.build(*args, **kwargs)


def render(*args: Any, **kwargs: Any) -> str:
    module = import_module(".render", __name__)
    return module.render(*args, **kwargs)


def __getattr__(name: str) -> Any:
    if name in {"BriefingConfig", "RenderConfig", "load_config"}:
        return getattr(import_module(".config", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

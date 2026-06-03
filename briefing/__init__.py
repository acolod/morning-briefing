"""Morning briefing pipeline package."""

from importlib import import_module
from typing import Any

__all__ = [
    "Article",
    "BriefingConfig",
    "CategoryConfig",
    "RankedArticle",
    "build",
    "gather",
    "load_config",
    "load_momentum",
    "rank",
    "render",
]


def build(*args: Any, **kwargs: Any) -> str:
    module = import_module(".build", __name__)
    globals()["build"] = _build_export

    return module.build(*args, **kwargs)


def gather(*args: Any, **kwargs: Any) -> Any:
    module = import_module(".gather", __name__)
    globals()["gather"] = _gather_export

    return module.gather(*args, **kwargs)


def rank(*args: Any, **kwargs: Any) -> Any:
    module = import_module(".rank", __name__)
    globals()["rank"] = _rank_export

    return module.rank(*args, **kwargs)


def render(*args: Any, **kwargs: Any) -> str:
    module = import_module(".render", __name__)
    globals()["render"] = _render_export

    return module.render(*args, **kwargs)


_build_export = build
_gather_export = gather
_rank_export = rank
_render_export = render


def __getattr__(name: str) -> Any:
    if name in {"BriefingConfig", "CategoryConfig", "load_config", "load_momentum"}:
        return getattr(import_module(".config", __name__), name)
    if name == "Article":
        module = import_module(".gather", __name__)
        globals()["gather"] = _gather_export
        return module.Article
    if name == "RankedArticle":
        module = import_module(".rank", __name__)
        globals()["rank"] = _rank_export
        return module.RankedArticle
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

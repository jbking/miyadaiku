from __future__ import annotations

from typing import (
    Dict,
    List,
    Callable,
    Any,
    TYPE_CHECKING,
    Optional,
    Sequence,
    Tuple,
)
import runpy

import enum
from pathlib import Path


if TYPE_CHECKING:
    from . import site
    from . import ContentSrc
    from .context import OutputContext

HOOKS = enum.Enum(
    "HOOKS",
    (
        "start",
        "initialized",
        "pre_load",
        "post_load",
        "pre_build",
        "post_build",
        "finished",
    ),
)


def load_hook(path: Path) -> None:
    hooks_started.clear()
    hooks_initialized.clear()
    hooks_pre_load.clear()
    hooks_post_load.clear()
    hooks_pre_build.clear()
    hooks_post_build.clear()
    hooks_finished.clear()
    jinja_globals.clear()

    hook = (path / "hooks.py").resolve()
    if hook.exists():
        runpy.run_path(str(hook))


if TYPE_CHECKING:
    HOOK_START = Callable[[], None]

hooks_started: List[HOOK_START] = []


def started(f: HOOK_START) -> HOOK_START:
    hooks_started.append(f)
    return f


def run_start() -> None:
    for hook in hooks_started:
        hook()


if TYPE_CHECKING:
    HOOK_INITIALIZED = Callable[[site.Site], None]
hooks_initialized: List[HOOK_INITIALIZED] = []


def initialized(f: HOOK_INITIALIZED) -> HOOK_INITIALIZED:
    hooks_initialized.append(f)
    return f


def run_initialized(site: site.Site) -> None:
    for hook in hooks_initialized:
        hook(site)


if TYPE_CHECKING:
    HOOK_PRE_LOAD = Callable[[site.Site, ContentSrc, bool], Optional[ContentSrc]]

hooks_pre_load: List[HOOK_PRE_LOAD] = []


def pre_load(f: HOOK_PRE_LOAD) -> HOOK_PRE_LOAD:
    hooks_pre_load.append(f)
    return f


def run_pre_load(
    site: site.Site, contentsrc: ContentSrc, binary: bool
) -> Optional[ContentSrc]:
    ret: Optional[ContentSrc] = contentsrc
    for hook in hooks_pre_load:
        if not ret:
            break
        ret = hook(site, ret, binary)

    return ret


if TYPE_CHECKING:
    HOOK_POST_LOAD = Callable[
        [site.Site, ContentSrc, bool, Optional[bytes]],
        Tuple[ContentSrc, Optional[bytes]],
    ]

hooks_post_load: List[HOOK_POST_LOAD] = []


def post_load(f: HOOK_POST_LOAD) -> HOOK_POST_LOAD:
    hooks_post_load.append(f)
    return f


def run_post_load(
    site: site.Site, contentsrc: ContentSrc, binary: bool, body: Optional[bytes]
) -> Tuple[Optional[ContentSrc], Optional[bytes]]:
    ret: Optional[ContentSrc] = contentsrc
    for hook in hooks_post_load:
        if not ret:
            break
        ret, body = hook(site, ret, binary, body)
    return contentsrc, body


if TYPE_CHECKING:
    HOOK_LOAD_FINISHED = Callable[[site.Site], None]

hooks_load_finished: List[HOOK_LOAD_FINISHED] = []


def load_finished(f: HOOK_LOAD_FINISHED) -> HOOK_LOAD_FINISHED:
    hooks_load_finished.append(f)
    return f


def run_load_finished(site: site.Site) -> None:
    for hook in hooks_load_finished:
        hook(site)


if TYPE_CHECKING:
    HOOK_PRE_BUILD = Callable[[OutputContext], Optional[OutputContext]]

hooks_pre_build: List[HOOK_PRE_BUILD] = []


def pre_build(f: HOOK_PRE_BUILD) -> HOOK_PRE_BUILD:
    hooks_pre_build.append(f)
    return f


def run_pre_build(context: OutputContext) -> Optional[OutputContext]:
    ret: Optional[OutputContext] = context
    for hook in hooks_pre_build:
        if not ret:
            break
        ret = hook(ret)
    return ret


if TYPE_CHECKING:
    HOOK_POST_BUILD = Callable[[OutputContext, Sequence[Path]], None]

hooks_post_build: List[HOOK_POST_BUILD] = []


def post_build(f: HOOK_POST_BUILD) -> HOOK_POST_BUILD:
    hooks_post_build.append(f)
    return f


def run_post_build(context: OutputContext, filenames: Sequence[Path]) -> None:
    for hook in hooks_post_build:
        hook(context, filenames)


if TYPE_CHECKING:
    HOOK_FINISHED = Callable[[site.Site], None]

hooks_finished: List[HOOK_FINISHED] = []


def finished(f: HOOK_FINISHED) -> HOOK_FINISHED:
    hooks_finished.append(f)
    return f


def run_finished(site: site.Site) -> None:
    for hook in hooks_finished:
        hook(site)


jinja_globals: Dict[str, Any] = {}


def jinja_global(f: Callable[..., None]) -> Callable[..., None]:
    jinja_globals[f.__name__] = f
    return f
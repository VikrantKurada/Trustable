from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from trustable.plugins.capabilities import InputGuard, OutputGuard, Tracer
from trustable.plugins.context import InteractionContext

logger = logging.getLogger("trustable.runtime")


class Pipeline:
    def __init__(self, modules: list[object]) -> None:
        self._input_guards = [m for m in modules if isinstance(m, InputGuard)]
        self._output_guards = [m for m in modules if isinstance(m, OutputGuard)]
        self._tracers = [m for m in modules if isinstance(m, Tracer)]

    def run_input_guards(self, ctx: InteractionContext) -> None:
        for guard in self._input_guards:
            if ctx.blocked:
                return
            try:
                guard.check_input(ctx)
            except Exception:
                logger.exception("input guard %r failed; skipping", guard)

    def run_output_guards(self, ctx: InteractionContext) -> None:
        for guard in self._output_guards:
            try:
                guard.check_output(ctx)
            except Exception:
                logger.exception("output guard %r failed; skipping", guard)

    @contextmanager
    def trace(self, ctx: InteractionContext) -> Iterator[InteractionContext]:
        for tracer in self._tracers:
            try:
                tracer.start_trace(ctx)
            except Exception:
                logger.exception("tracer %r start failed; skipping", tracer)
        try:
            yield ctx
        finally:
            for tracer in reversed(self._tracers):
                try:
                    tracer.end_trace(ctx)
                except Exception:
                    logger.exception("tracer %r end failed; skipping", tracer)

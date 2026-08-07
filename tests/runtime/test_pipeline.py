
from trustable.plugins.context import InteractionContext
from trustable.runtime.pipeline import Pipeline


class RecordingInput:
    def __init__(self, tag, block=False):
        self.tag, self.block = tag, block

    def check_input(self, ctx):
        ctx.records.append({"in": self.tag})
        if self.block:
            ctx.blocked = True
            ctx.block_reason = self.tag


class ThrowingInput:
    def check_input(self, ctx):
        raise RuntimeError("boom")


class RecordingTracer:
    def start_trace(self, ctx):
        ctx.records.append({"trace": "start"})

    def end_trace(self, ctx):
        ctx.records.append({"trace": "end"})


def test_input_guards_run_in_given_order():
    ctx = InteractionContext(prompt="x")
    Pipeline([RecordingInput("a"), RecordingInput("b")]).run_input_guards(ctx)
    assert ctx.records == [{"in": "a"}, {"in": "b"}]


def test_blocked_short_circuits_remaining_guards():
    ctx = InteractionContext(prompt="x")
    Pipeline([RecordingInput("a", block=True), RecordingInput("b")]).run_input_guards(ctx)
    assert ctx.blocked is True and ctx.block_reason == "a"
    assert ctx.records == [{"in": "a"}]  # "b" never ran


def test_throwing_module_is_failed_open():
    ctx = InteractionContext(prompt="x")
    Pipeline([ThrowingInput(), RecordingInput("b")]).run_input_guards(ctx)
    assert ctx.records == [{"in": "b"}]  # pipeline survived the exception


def test_trace_context_manager_wraps():
    ctx = InteractionContext(prompt="x")
    pipe = Pipeline([RecordingTracer()])
    with pipe.trace(ctx):
        ctx.records.append({"call": "llm"})
    assert ctx.records == [{"trace": "start"}, {"call": "llm"}, {"trace": "end"}]

from trustable.plugins.context import InteractionContext


def test_defaults_are_independent():
    a = InteractionContext(prompt="hi")
    b = InteractionContext(prompt="yo")
    a.metadata["k"] = 1
    a.records.append({"x": 1})
    assert b.metadata == {}  # no shared mutable default
    assert b.records == []
    assert a.response is None and a.blocked is False and a.block_reason is None


def test_fields_are_mutable():
    ctx = InteractionContext(prompt="hi")
    ctx.response = "answer"
    ctx.blocked = True
    ctx.block_reason = "injection"
    assert ctx.response == "answer"
    assert ctx.blocked and ctx.block_reason == "injection"

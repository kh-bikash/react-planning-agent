from react_planning_agent.engine import ReActAgent


class Stub:
    def __init__(self, replies):
        self.replies = iter(replies)

    def complete(self, messages, *, model=None):
        return next(self.replies)


def test_tool_then_final():
    agent = ReActAgent(Stub(['{"action":"lookup","input":"x"}', '{"final":"done"}']), {"lookup": lambda _: "found"})
    result = agent.run("Find x")
    assert result.answer == "done" and result.steps[0].observation == "found"


def test_stops_repeat():
    action = '{"action":"lookup","input":"x"}'
    result = ReActAgent(Stub([action, action]), {"lookup": lambda _: "missing"}).run("Find x")
    assert result.stopped_reason == "repeated_action"


def test_self_critique_requests_revision():
    calls = []
    def critic(task, answer, steps):
        calls.append(answer)
        return (answer == "correct", "missing evidence")
    agent = ReActAgent(Stub(['{"final":"guess"}', '{"final":"correct"}']), {}, critic=critic)
    result = agent.run("Answer with evidence")
    assert result.answer == "correct" and calls == ["guess", "correct"]
    assert result.steps[0].action == "self_critique"

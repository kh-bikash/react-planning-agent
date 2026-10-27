import json

import pytest

from react_planning_agent.__main__ import calculate, main, tools_for


def test_product_tools_are_useful_and_scoped(tmp_path):
    (tmp_path / "terms.txt").write_text("Refunds within 30 days", encoding="utf-8")
    tools = tools_for(tmp_path)
    assert tools["calculate"]("(12 + 8) / 2") == "10.0"
    assert "terms.txt" in tools["search_files"]("Refunds")
    assert tools["read_file"]("terms.txt") == "Refunds within 30 days"
    with pytest.raises(ValueError):
        tools["read_file"]("../outside.txt")
    with pytest.raises(ValueError):
        calculate("__import__('os').system('echo bad')")


def test_cli_uses_document_tool_then_answers(tmp_path, monkeypatch, capsys):
    (tmp_path / "terms.txt").write_text("Refunds within 30 days", encoding="utf-8")

    class FakeLLM:
        def __init__(self):
            self.calls = 0

        def complete(self, messages, *, model=None):
            self.calls += 1
            if self.calls == 1:
                return '{"action":"read_file","input":"terms.txt"}'
            return '{"final":"Refunds are available within 30 days."}'

    monkeypatch.setattr(
        "react_planning_agent.__main__.OpenAICompatibleLLM.from_env",
        FakeLLM,
    )
    assert main(["--root", str(tmp_path), "run", "What are the terms?"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["stopped_reason"] == "completed"
    assert result["steps"][0]["action"] == "read_file"

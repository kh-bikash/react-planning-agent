from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from .llm import LLM


@dataclass(frozen=True)
class Step:
    action: str
    observation: str


@dataclass(frozen=True)
class PlanResult:
    answer: str
    steps: tuple[Step, ...]
    stopped_reason: str


class ReActAgent:
    def __init__(
        self,
        llm: LLM,
        tools: dict[str, Callable[[str], str]],
        *,
        max_steps: int = 5,
        max_observation_chars: int = 2000,
        critic: Callable[[str, str, tuple[Step, ...]], tuple[bool, str]] | None = None,
    ):
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        self.llm, self.tools = llm, dict(tools)
        self.max_steps, self.max_observation_chars = max_steps, max_observation_chars
        self.critic = critic

    def run(self, task: str) -> PlanResult:
        messages = [
            {
                "role": "system",
                "content": 'Choose one JSON object each turn: {"action":tool_name,"input":string} or {"final":answer}. Available tools: '
                + ", ".join(sorted(self.tools))
                + ". Do not repeat failed actions.",
            },
            {"role": "user", "content": task},
        ]
        steps: list[Step] = []
        seen: set[tuple[str, str]] = set()
        for _ in range(self.max_steps):
            raw = self.llm.complete(messages)
            try:
                decision = json.loads(raw)
                if "final" in decision:
                    proposed = str(decision["final"])
                    if self.critic:
                        accepted, feedback = self.critic(task, proposed, tuple(steps))
                        if not accepted:
                            messages.extend(
                                [
                                    {"role": "assistant", "content": raw[:4000]},
                                    {
                                        "role": "user",
                                        "content": "Self-critique rejected the proposed answer: "
                                        + feedback[:1000]
                                        + ". Continue with a new action or revised final answer.",
                                    },
                                ]
                            )
                            steps.append(
                                Step(
                                    "self_critique",
                                    feedback[: self.max_observation_chars],
                                )
                            )
                            continue
                    return PlanResult(proposed, tuple(steps), "completed")
                action, argument = str(decision["action"]), str(decision["input"])
            except (ValueError, KeyError, TypeError):
                observation = (
                    "Invalid JSON action; provide a valid action or final answer."
                )
                action, argument = "invalid", ""
            else:
                if action not in self.tools:
                    observation = "Tool unavailable or not permitted."
                elif (action, argument) in seen:
                    return PlanResult(
                        "I could not make further progress.",
                        tuple(steps),
                        "repeated_action",
                    )
                else:
                    seen.add((action, argument))
                    try:
                        observation = str(self.tools[action](argument))[
                            : self.max_observation_chars
                        ]
                    except Exception as exc:  # noqa: BLE001 - tool failures become observations
                        observation = "Tool failed: " + type(exc).__name__
            steps.append(Step(action, observation))
            messages.extend(
                [
                    {"role": "assistant", "content": raw[:4000]},
                    {
                        "role": "user",
                        "content": "Observation: "
                        + observation
                        + "\nReflect briefly and choose next action or final.",
                    },
                ]
            )
        return PlanResult(
            "I stopped at the configured step limit.", tuple(steps), "step_limit"
        )

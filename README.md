# React Planning Agent

Run a bounded observe, reason, act loop over an explicit tool allowlist with repeat detection and graceful tool failure.

Pass a `critic(task, proposed_answer, steps)` callback to reject an unsupported final answer and return targeted feedback. Revisions count against `max_steps`.

## Quick start

Requires Python 3.11 or newer. From this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
pytest -q
```

For live model calls, set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` and `OPENAI_BASE_URL` as shown in `.env.example`. The test suite uses stubs and needs no model key.

```python
from react_planning_agent.engine import ReActAgent
from react_planning_agent.llm import OpenAICompatibleLLM

agent = ReActAgent(OpenAICompatibleLLM.from_env(), {"lookup": lambda key: {"a": "Found A"}.get(key, "Missing")}, max_steps=4)
print(agent.run("Look up a and answer"))
```

## Architecture

Task -> JSON action decision -> permitted tool -> bounded observation -> reflection -> final answer or configured stop reason.

See [ARCHITECTURE.md](ARCHITECTURE.md) for components, state, failure behavior, and operations.

## Deployment and safety

Tool handlers are trusted application code. Register read only handlers by default, enforce authorization inside handlers, and set network and execution timeouts. Tool exceptions are reduced to class names in observations.

Install this as a library in an authenticated application or worker. Supply the LLM adapter through dependency injection. Keep secrets in environment variables, never in source control.

## Verification

`pytest -q` runs deterministic tests. GitHub Actions runs the same suite on pushes and pull requests.

## License

MIT. See [LICENSE](LICENSE).

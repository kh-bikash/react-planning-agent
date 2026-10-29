# React Planning Agent

## About

This is a task assistant that can take a few deliberate steps instead of guessing from a single prompt. It can search or read files inside a folder you choose and do bounded arithmetic. After each tool result, it decides whether to continue or answer. You can inspect the steps it took and why it stopped.

### What you can do

- Ask questions about a local set of documents, such as finding a policy and summarizing it.
- Limit the number of steps so a task cannot run indefinitely.
- Restrict the assistant to the tools and folder you explicitly provide.
- Add a critic callback that asks for a revision when a final answer is unsupported.

The CLI and local browser are ready to run on your machine or your own server. They need a configured model key for live answers. The supplied tools are read-only, and custom tools should enforce their own permissions and timeouts. This repository does not have a public hosted URL yet.

## Quick start

Requires Python 3.11 or newer. From this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
pytest -q
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
```

For live model calls, set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` and `OPENAI_BASE_URL` as shown in `.env.example`. The test suite uses stubs and needs no model key.

The installed `react-planner` command answers tasks using only three built-in tools: bounded arithmetic, read-only files under `--root`, and bounded text search under that root. Run `react-planner --root ./docs run "Find the refund terms and summarize them"`. For the local browser, run `react-planner --root ./docs serve --port 8080` and open `http://127.0.0.1:8080`. Set `OPENAI_API_KEY` for either mode. The agent exposes its step trace and stop reason in the result.

```python
from react_planning_agent.engine import ReActAgent
from react_planning_agent.llm import OpenAICompatibleLLM

agent = ReActAgent(OpenAICompatibleLLM.from_env(), {"lookup": lambda key: {"a": "Found A"}.get(key, "Missing")}, max_steps=4)
print(agent.run("Look up a and answer"))
```

## Architecture

```mermaid
flowchart LR
    CLI[Command line] --> Task
    Browser[Browser interface] --> Task
    Task[Task] --> Planner[JSON decision planner]
    Planner -->|Permitted action| Tool[Allowlisted tool]
    Tool --> Observation[Bounded observation]
    Observation --> Planner
    Planner -->|Final answer| Critic[Optional self critique]
    Critic -->|Rejected| Planner
    Critic -->|Accepted| Result[Final result]
    Planner -->|Repeat or step limit| Stop[Safe stop]
```

| Component | Responsibility |
|---|---|
| Planner | Chooses one JSON action or final answer per step. |
| Tool boundary | Runs only registered handlers and truncates observations. |
| Stop controller | Enforces iteration limits and repeated action detection. |

Task -> JSON action decision -> permitted tool -> bounded observation -> reflection -> final answer or configured stop reason.

See [ARCHITECTURE.md](ARCHITECTURE.md) for components, state, failure behavior, and operations.

## Deployment and safety

See [DEPLOYMENT.md](DEPLOYMENT.md) for the non-root container, token-protected browser, data mounts, and release checks.

Tool handlers are trusted application code. Register read only handlers by default, enforce authorization inside handlers, and set network and execution timeouts. Tool exceptions are reduced to class names in observations.

Install this as a library in an authenticated application or worker. Supply the LLM adapter through dependency injection. Keep secrets in environment variables, never in source control.

## Verification

`pytest -q` runs deterministic tests. GitHub Actions runs the same suite on pushes and pull requests.

## License

MIT. See [LICENSE](LICENSE).

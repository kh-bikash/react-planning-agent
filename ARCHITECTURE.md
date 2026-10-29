# Architecture

## Goal

Run a bounded observe, reason, act loop over an explicit tool allowlist with repeat detection and graceful tool failure.

## Request path

Task -> JSON action decision -> permitted tool -> bounded observation -> reflection -> final answer or configured stop reason.

## Components

- `src/react_planning_agent/engine.py`: policy and state transitions for this project.
- `src/react_planning_agent/llm.py`: injected model protocol and HTTPS OpenAI-compatible adapter with timeouts and retry for transient transport failures.
- `tests/test_engine.py`: deterministic behavior and failure tests.
- `.github/workflows/ci.yml`: install and test gate.


## State and failure behavior

Tool handlers are trusted application code. Register read only handlers by default, enforce authorization inside handlers, and set network and execution timeouts. Tool exceptions are reduced to class names in observations.

The LLM adapter times out after 30 seconds and retries transient HTTP failures twice. Model output is untrusted input and is parsed or validated at the project boundary.

## Operations checklist

1. Set secrets through a secret manager and rotate them regularly.
2. Put the service or integrating application behind TLS and authentication.
3. This planner keeps steps only for one invocation. Persist caller checkpoints if a workflow must resume after a process restart.
4. Run `pytest -q` in CI before deployment.
5. Define workload specific evaluation cases, latency objectives, and rollback criteria before serving real users.

## State machine

The planner requests one JSON decision per turn: a permitted tool action or a final answer. Tool names come only from the caller's allowlist. Every tool result is truncated to `max_observation_chars`, and the pair `(tool, input)` is recorded to stop repeated actions. Errors become short observations with the exception class, so a recoverable tool failure can lead to a different action. `max_steps` stops all paths.

An optional `critic` receives the proposed final answer and accumulated steps. It can reject the answer with bounded feedback, which consumes another step. The returned `stopped_reason` distinguishes completion, repeated actions, and step limits. Tool handlers should enforce their own authorization and I/O deadlines. The planner itself never grants additional tool permissions.

## Product interfaces and trust boundary

The installed console command and local browser call the same product operation in `src/*/__main__.py`; the browser does not replace the engine's validation or state transitions. `src/*/web.py` serves HTML and a JSON action endpoint with a one-megabyte request limit and a per-process CSRF token. It binds to loopback by default. A non-loopback bind requires `AGENT_WEB_TOKEN` of at least 16 characters, checked on every action request. The page never embeds the access token; an operator enters it in the browser. Treat the browser as an operator interface and place TLS plus identity-aware access control in front of any public endpoint. The non-root container is described in `DEPLOYMENT.md`.

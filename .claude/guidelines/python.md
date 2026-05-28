# Python Guidelines

## Version & Tooling

- Python 3.12+
- Environment & packaging: `uv` (lockfile committed)
- Format + lint: `ruff format` and `ruff check` (zero warnings)
- Types: `mypy --strict` (or `pyright`) clean
- Security: `pip-audit` on the lockfile; Dependabot/Renovate
- Coverage: 50% minimum, 80% target (reported per test tier)

## Style

- Full type hints on all function signatures and public attributes
- `async def` for I/O; no blocking calls in async paths
- Pydantic v2 for all external/structured data (requests, responses,
  frontmatter); models are the schema source of truth
- No module-level side effects on import; no mutable global state
- Pass dependencies explicitly (FastAPI `Depends`), not via globals

## Error Handling

- Typed exceptions from the project error taxonomy; one central exception
  handler maps them to HTTP responses
- Validate external input at the boundary; trust internal calls
- No bare `except`; no silent swallowing — handle or propagate
- Never put secrets in messages, logs, or traces

## Testing

- `pytest` for units; `pytest-bdd` for Gherkin features; `pytest-playwright`
  for `@e2e` browser scenarios (see `guidelines/bdd.md`)
- Stub external HTTP (GitLab/Graph/Slack) at the edge with `respx`; a
  `@contract` tier runs against real disposable instances managed with
  Docker + Testcontainers (`testcontainers-python`)
- `testdata/` (or fixtures) for sample frontmatter, emails, payloads
- Assert real state, not just status codes or "mock was called"
- Negative/permission scenarios are mandatory where authorization applies

## Build & Run

- `pyproject.toml` (PEP 621); tasks via a `Makefile` or `uv run` scripts
- `make` (no target) runs the full pre-commit pipeline: format, lint, type,
  test
- Container: multi-stage, non-root runtime, no dev deps in the final image

## CI Pipeline

Three-stage (see `guidelines/ci.md`): Build → Validate → Test.

## Patterns

- Dependency injection over globals/singletons
- Small, single-responsibility modules; files under ~500 lines
- `httpx.AsyncClient` with explicit timeouts on every external call
- Bounded concurrency (`asyncio.Semaphore`/`TaskGroup`) for fan-out (indexer)
- Generate OpenAPI from Pydantic; never hand-maintain duplicate types

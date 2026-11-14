# CI Doctor

CI Doctor investigates failing CI runs. It parses JUnit XML, fingerprints
failures, detects flaky tests from stored run history, and asks Gemini
(primary) or Ollama to explain the root cause.

## Stack

Python 3.11+, uv, src layout (`src/cidoctor`), Typer + Rich, Pydantic v2,
defusedxml, rapidfuzz, httpx, google-genai, pytest, ruff, mypy.

## Install

```sh
# From source
git clone https://github.com/arka79/HackMatrix.git
cd HackMatrix
uv sync --all-groups
```

Or install from PyPI:

```sh
pip install cidoctor
```

## Quick start

```sh
# 1. Initialize the project (creates cidoctor.toml and .cidoctor/runs/)
cidoctor init

# 2. Set your Gemini API key (get one from https://aistudio.google.com/)
#    Or copy .env.local to .env and fill in GEMINI_API_KEY
export GEMINI_API_KEY=your-key

# 3. Generate simulated demo data (clearly marked as simulated)
cidoctor demo seed

# 4. Analyze a JUnit results file (real or simulated)
cidoctor analyze test-results.xml --commit abc123 --branch main

# 5. Check for flaky tests across stored runs
cidoctor flaky --since 14d

# 6. Explain the root cause (Gemini by default)
cidoctor explain latest

# 7. Use Ollama instead
cidoctor launch --model llama3

# 8. Post a PR comment (dry run first)
cidoctor comment latest --dry-run
```

## Live demo with actual CI data

To showcase CI Doctor with real test results:

```sh
# 1. Initialize the store
cidoctor init

# 2. Point at your JUnit XML (pytest, jest-junit, surefire, etc.)
cidoctor analyze path/to/junit.xml --commit <sha> --branch main --format json

# 3. See failure groups fingerprinted by root cause
cidoctor analyze path/to/junit.xml --format table

# 4. Detect flaky tests across history
cidoctor flaky --since 14d --format table

# 5. Get an AI explanation of failures (requires GEMINI_API_KEY)
set -a && . .env && set +a
cidoctor explain latest --provider gemini

# 6. Preview a GitHub PR comment
cidoctor comment latest --dry-run
```

### Minimal JUnit XML example (`test-results.xml`)

```xml
<testsuite name="demo" tests="3" failures="1">
  <testcase name="test_pass" classname="tests.demo" time="0.5"/>
  <testcase name="test_fail" classname="tests.demo" time="0.3">
    <failure message="assertion failed">assert x == 1</failure>
  </testcase>
  <testcase name="test_skip" classname="tests.demo" time="0.1">
    <skipped message="not implemented"/>
  </testcase>
</testsuite>
```

The analyzer accepts any file ending in `.xml` (pytest, jest-junit, Maven
surefire, etc.) using `defusedxml` for safe parsing.

## Configuration

Create a `cidoctor.toml`:

```toml
[cidoctor]
store_path = ".cidoctor/runs"
provider = "gemini"
model = "gemini-3.5-flash-lite"
window_days = 14
min_runs = 10
threshold = 0.95
main_branch = "main"
max_log_chars = 400000
ollama_host = "http://localhost:11434"
```

## Commands

| Command | Description |
|---------|-------------|
| `cidoctor init` | Write config and create `.cidoctor/` directory |
| `cidoctor analyze <file>` | Analyze a JUnit results file |
| `cidoctor flaky` | Show flaky-test verdicts |
| `cidoctor explain <run-id\|latest>` | Explain root cause (Gemini by default) |
| `cidoctor launch [<run-id>]` | Pick a model and run the investigation agent |
| `cidoctor comment <run-id> [--dry-run]` | Post a PR comment |
| `cidoctor demo seed` | Generate simulated demo data |

## Security

- All XML parsing uses `defusedxml` (no XXE)
- Secrets (API keys, tokens) are redacted before logging or sending to AI providers
- No `shell=True` anywhere in the source
- File paths are validated to prevent traversal

## Deploy

### Option 1: Install from PyPI (recommended for users)

```sh
pip install cidoctor
cidoctor --version
```

### Option 2: Run with Docker

```sh
# Build the image
docker build -t cidoctor .

# Run with your JUnit XML mounted
docker run --rm -v $(pwd):/data -e GEMINI_API_KEY=your-key \
  cidoctor analyze /data/junit.xml --commit abc123 --branch main

# Or use the built image from a registry once published
docker run --rm -e GEMINI_API_KEY=your-key cidoctor:latest --help
```

### Option 3: Install from source

```sh
git clone <your-repo>
cd HackMatrix
uv sync --all-groups
uv run cidoctor --version
```

### Publishing to PyPI (maintainers)

Push a version tag to trigger the release workflow:

```sh
git tag v0.1.0 && git push origin v0.1.0
```

GitHub Actions builds the wheel and publishes to PyPI using the `PYPI_API_TOKEN` secret.

## Project contract

See [AGENTS.md](AGENTS.md) for the full project contract, fixed data contracts,
and per-block implementation rules.

# Task 3: Config-Driven Retry Policy (`retry-policy-config`)

> **Learning objective**
> Build a realistic demo Harbor task with a small verifier runner, and separate hidden tests in `tests/test_outputs.py`.

## Repository Layout

```text
harbor-agent-tasks/
└── tasks/
    ├── nginx-log-fix/
    ├── user-validation-gap/
    └── retry-policy-config/
        ├── task.toml
        ├── instruction.md
        ├── environment/
        │   ├── Dockerfile
        │   ├── retry-policy.json
        │   └── retry_policy.py
        ├── solution/
        │   └── solve.sh
        └── tests/
            ├── test.sh
            └── test_outputs.py
```

`tests/test_outputs.py` contains the hidden pytest checks. `tests/test.sh` only starts pytest and writes Harbor's reward.

## Step 1: Scaffold the Task

From `harbor-agent-tasks/tasks`, scaffold Task 3:

```bash
harbor init retry-policy-config
# Select 't' when prompted to create a task.
# Organization: demo

cd retry-policy-config
```

## Step 2: Create the Task Files

Replace the generated placeholder content with the files below.

### `task.toml`

```toml
schema_version = "1.3"
artifacts = []

[task]
name = "local/retry-policy-config"
description = "Repair a command-line retry scheduler so it validates and applies runtime JSON configuration."
authors = [{ name = "Peter Mwenda" }]
keywords = ["python", "configuration", "retry", "backoff", "validation"]
category = "debugging"
```

### `instruction.md`

````markdown
# Problem Statement

The command-line program at `/app/retry_policy.py` is intended to calculate an exponential retry delay from a JSON configuration file. It currently ignores the configuration and returns a hardcoded delay.

Fix `/app/retry_policy.py`.

## Command

The program must support:

```bash
python3 /app/retry_policy.py --config <config-path> --attempt <positive-integer>
```

## Configuration

The configuration file must contain one JSON object with:

- `base_delay_ms`: an integer greater than or equal to `0`. Boolean values are invalid.
- `multiplier`: an integer or decimal number greater than or equal to `1`. Boolean values are invalid.
- `max_delay_ms`: an integer greater than or equal to `base_delay_ms`. Boolean values are invalid.

The program must read the file specified by `--config` at runtime. It must not assume that every configuration uses the same values.

## Delay Calculation

For attempt `n`, calculate:

```text
base_delay_ms * multiplier ** (n - 1)
```

Cap the result at `max_delay_ms`, then round it down to an integer number of milliseconds.

## Successful Output

On success, exit with status `0` and write one JSON object to standard output:

```json
{
  "attempt": 3,
  "delay_ms": 2000
}
```

The `attempt` value must equal the requested attempt and `delay_ms` must contain the calculated delay.

## Error Handling

Exit with a non-zero status, print a useful message to standard error, and do not print a Python traceback when:

- The configuration file is missing or unreadable.
- The file does not contain valid JSON.
- The JSON root is not an object.
- A required configuration field is missing or invalid.
- `--attempt` is missing, is not an integer, or is less than `1`.

Do not modify the supplied configuration file.
````

Everything checked by the hidden tests is stated in `instruction.md`. The instructions describe the expected outcome without revealing the implementation.

### `environment/retry-policy.json`

```json
{
  "base_delay_ms": 500,
  "multiplier": 2,
  "max_delay_ms": 5000
}
```

### `environment/retry_policy.py`

```python
import argparse
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as source:
        json.load(source)

    result = {
        "attempt": args.attempt,
        "delay_ms": 500,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
```

The starter program confirms that the configuration contains JSON but ignores its values. It always returns `500`, does not apply exponential backoff or the maximum delay, and does not provide controlled error handling.

### `environment/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir pytest==8.4.1

COPY retry-policy.json /app/retry-policy.json
COPY retry_policy.py /app/retry_policy.py

CMD ["bash"]
```

The Dockerfile copies only the broken project and its runtime configuration. It must never copy the reference solution or tests into the image.

### `solution/solve.sh`

```bash
#!/bin/bash
set -e

cat <<'PYTHON' > /app/retry_policy.py
import argparse
import json
import sys


def load_config(path):
    with open(path, encoding="utf-8") as source:
        config = json.load(source)

    if not isinstance(config, dict):
        raise ValueError("configuration root must be an object")

    base_delay = config.get("base_delay_ms")
    multiplier = config.get("multiplier")
    max_delay = config.get("max_delay_ms")

    if (
        isinstance(base_delay, bool)
        or not isinstance(base_delay, int)
        or base_delay < 0
    ):
        raise ValueError("base_delay_ms must be an integer greater than or equal to 0")

    if (
        isinstance(multiplier, bool)
        or not isinstance(multiplier, (int, float))
        or multiplier < 1
    ):
        raise ValueError("multiplier must be a number greater than or equal to 1")

    if (
        isinstance(max_delay, bool)
        or not isinstance(max_delay, int)
        or max_delay < base_delay
    ):
        raise ValueError("max_delay_ms must be an integer greater than or equal to base_delay_ms")

    return base_delay, multiplier, max_delay


def calculate_delay(base_delay, multiplier, max_delay, attempt):
    if attempt < 1:
        raise ValueError("attempt must be greater than or equal to 1")

    delay_ms = min(max_delay, base_delay * multiplier ** (attempt - 1))
    return int(delay_ms)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    args = parser.parse_args()

    try:
        base_delay, multiplier, max_delay = load_config(args.config)
        delay_ms = calculate_delay(
            base_delay,
            multiplier,
            max_delay,
            args.attempt,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(json.dumps({
        "attempt": args.attempt,
        "delay_ms": delay_ms,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PYTHON

python3 /app/retry_policy.py \
  --config /app/retry-policy.json \
  --attempt 3 >/dev/null
```

The reference solution reads the requested configuration at runtime, validates it, calculates the capped delay, and reports controlled errors. It must pass every hidden test and receive `1.0` during the Oracle run.

### `tests/test_outputs.py`

```python
import json
import subprocess
import sys
from pathlib import Path

import pytest


PROGRAM = Path("/app/retry_policy.py")


def write_config(tmp_path, content):
    config_path = tmp_path / "retry-policy.json"
    config_path.write_text(json.dumps(content), encoding="utf-8")
    return config_path


def run_policy(config_path, attempt):
    return subprocess.run(
        [
            sys.executable,
            str(PROGRAM),
            "--config",
            str(config_path),
            "--attempt",
            str(attempt),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def assert_success(result, attempt, delay_ms):
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "attempt": attempt,
        "delay_ms": delay_ms,
    }
    assert result.stderr == ""


def assert_controlled_failure(result):
    assert result.returncode != 0
    assert result.stderr.strip()
    assert "Traceback" not in result.stderr


def test_default_configuration_applies_backoff_and_cap(tmp_path):
    """Checks exponential growth and the configured maximum delay."""
    config = write_config(tmp_path, {
        "base_delay_ms": 500,
        "multiplier": 2,
        "max_delay_ms": 5000,
    })

    expected = {
        1: 500,
        2: 1000,
        3: 2000,
        4: 4000,
        5: 5000,
        8: 5000,
    }

    for attempt, delay_ms in expected.items():
        assert_success(run_policy(config, attempt), attempt, delay_ms)


def test_alternate_configuration_prevents_hardcoded_solution(tmp_path):
    """Checks that values are read from the requested config file."""
    config = write_config(tmp_path, {
        "base_delay_ms": 125,
        "multiplier": 3,
        "max_delay_ms": 2000,
    })

    expected = {
        1: 125,
        2: 375,
        3: 1125,
        4: 2000,
    }

    for attempt, delay_ms in expected.items():
        assert_success(run_policy(config, attempt), attempt, delay_ms)


def test_decimal_multiplier_rounds_down(tmp_path):
    """Checks decimal multipliers and integer millisecond output."""
    config = write_config(tmp_path, {
        "base_delay_ms": 100,
        "multiplier": 1.5,
        "max_delay_ms": 1000,
    })

    assert_success(run_policy(config, 4), 4, 337)


@pytest.mark.parametrize("attempt", [0, -1, "not-an-integer"])
def test_invalid_attempts_fail_without_traceback(tmp_path, attempt):
    """Checks controlled failures for invalid attempt values."""
    config = write_config(tmp_path, {
        "base_delay_ms": 500,
        "multiplier": 2,
        "max_delay_ms": 5000,
    })

    assert_controlled_failure(run_policy(config, attempt))


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"base_delay_ms": True, "multiplier": 2, "max_delay_ms": 5000},
        {"base_delay_ms": -1, "multiplier": 2, "max_delay_ms": 5000},
        {"base_delay_ms": 500, "multiplier": False, "max_delay_ms": 5000},
        {"base_delay_ms": 500, "multiplier": 0.5, "max_delay_ms": 5000},
        {"base_delay_ms": 500, "multiplier": 2, "max_delay_ms": True},
        {"base_delay_ms": 500, "multiplier": 2, "max_delay_ms": 499},
    ],
)
def test_invalid_configuration_values_fail(tmp_path, config):
    """Checks required fields, types, ranges, and boolean rejection."""
    config_path = write_config(tmp_path, config)
    assert_controlled_failure(run_policy(config_path, 1))


def test_malformed_and_non_object_json_fail(tmp_path):
    """Checks malformed JSON and non-object JSON roots."""
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")
    assert_controlled_failure(run_policy(malformed, 1))

    non_object = tmp_path / "array.json"
    non_object.write_text("[]", encoding="utf-8")
    assert_controlled_failure(run_policy(non_object, 1))


def test_missing_configuration_file_fails(tmp_path):
    """Checks a controlled error for an unreadable config path."""
    missing = tmp_path / "missing.json"
    assert_controlled_failure(run_policy(missing, 1))


def test_missing_required_arguments_fail(tmp_path):
    """Checks controlled argparse errors for missing required options."""
    config = write_config(tmp_path, {
        "base_delay_ms": 500,
        "multiplier": 2,
        "max_delay_ms": 5000,
    })

    missing_attempt = subprocess.run(
        [sys.executable, str(PROGRAM), "--config", str(config)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert_controlled_failure(missing_attempt)

    missing_config = subprocess.run(
        [sys.executable, str(PROGRAM), "--attempt", "1"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert_controlled_failure(missing_config)


def test_configuration_file_is_not_modified(tmp_path):
    """Checks that runtime configuration remains unchanged."""
    config = write_config(tmp_path, {
        "base_delay_ms": 250,
        "multiplier": 2,
        "max_delay_ms": 3000,
    })
    original = config.read_bytes()

    assert_success(run_policy(config, 3), 3, 1000)
    assert config.read_bytes() == original
```

These tests are outcome-based: they execute the command as a user would and validate exit status, JSON output, calculated delays, required arguments, controlled errors, and configuration-file preservation.

### `tests/test.sh`

```bash
#!/bin/bash

mkdir -p /logs/verifier

pytest -q /tests/test_outputs.py

if [ $? -eq 0 ]; then
  echo "1.0" > /logs/verifier/reward.txt
else
  echo "0.0" > /logs/verifier/reward.txt
fi
```

Keep the reward-writing tail unchanged. `test.sh` is only the verifier entry point; the hidden checks belong in `test_outputs.py`.

## Step 3: Validate the Reference Solution

Return to the `harbor-agent-tasks` project root:

```bash
cd ../../
```

Run Oracle:

```bash
harbor run -p ./tasks/retry-policy-config --agent oracle
```

The Oracle run executes `solution/solve.sh` and then the hidden tests. It must receive:

```text
1.0
```

If Oracle does not receive `1.0`, the task is not ready. Correct the environment, reference solution, instructions, or tests before evaluating a real agent.

## Step 4: Confirm That a Lazy Wrong Solution Fails

Passing Oracle does not yet prove that a wrong solution fails.

Temporarily change this line inside the Python content written by `solution/solve.sh`:

```python
delay_ms = calculate_delay(
    base_delay,
    multiplier,
    max_delay,
    args.attempt,
)
```

to the following lazy implementation:

```python
delay_ms = 500
```

Run Oracle again:

```bash
harbor run -p ./tasks/retry-policy-config --agent oracle
```

The hardcoded solution must receive:

```text
0.0
```

The hidden tests use more than one configuration and several attempt values, so returning a constant cannot pass.

Restore the original `calculate_delay(...)` block in `solution/solve.sh`, then run Oracle once more:

```bash
harbor run -p ./tasks/retry-policy-config --agent oracle
```

The restored reference solution must again receive:

```text
1.0
```

## Step 5: Evaluate a Real Agent

Run five attempts:

```bash
harbor run \
  -p ./tasks/retry-policy-config \
  -a gemini-cli \
  -m google/gemini-3.5-flash-lite \
  --ae GEMINI_API_KEY="$GEMINI_API_KEY" \
  --n-attempts 4
```

Aim for a solve rate between roughly `1 in 8` and `3 in 4`:

- If every attempt passes, the task may be too easy.

## Step 6: Inspect the Runs

```bash
harbor view jobs
```

Review the agent's changes and failures. Confirm that the tests reward the required end state rather than a particular implementation route.

### Remember

A task is only as reliable as its verifier. A correct solution passing is necessary, but a plausible wrong solution failing is what makes the evaluation meaningful.
